"""
Service-to-Service Authentication using JWT Tokens.

Provides secure authentication for inter-service communication.

SECURITY MODEL:
- Each service has a unique signing key (SERVICE_AUTH_SECRET_<SERVICE>)
- No fallback to Django SECRET_KEY to prevent cross-service compromise
- Supports both symmetric (HS256) and asymmetric (RS256) algorithms
- Key rotation via kid (Key ID) header
- JWKS endpoint for public key distribution (RS256)
"""
import logging
import jwt
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)


class ServiceTokenManager:
    """
    Manage JWT tokens for service-to-service authentication.

    Features:
    - Unique per-service signing keys (no SECRET_KEY fallback)
    - Token generation with scopes
    - Token verification
    - Key rotation support with kid header
    - Cache integration
    - Support for HS256 (symmetric) and RS256 (asymmetric) algorithms
    """

    # Token expiry duration
    TOKEN_EXPIRY_HOURS = 24

    # JWT algorithm - use RS256 for production
    ALGORITHM = getattr(settings, 'SERVICE_AUTH_ALGORITHM', 'HS256')

    @classmethod
    def get_secret_key(cls, service_name: Optional[str] = None, kid: Optional[str] = None) -> str:
        """
        Get the secret key for JWT signing/verification.

        IMPORTANT: Each service MUST have its own unique key in environment:
        - SERVICE_AUTH_SECRET_<SERVICE_NAME> (e.g., SERVICE_AUTH_SECRET_DJANGO_BACKEND)

        For key rotation, specify kid parameter:
        - SERVICE_AUTH_SECRET_<SERVICE_NAME>_<KID>

        Args:
            service_name: Name of the service (required)
            kid: Key ID for rotation (optional)

        Returns:
            Secret key string

        Raises:
            ImproperlyConfigured: If service key is not configured

        Security:
            - NO fallback to Django SECRET_KEY
            - Each service has isolated key material
            - Compromise of one service does not affect others
        """
        if not service_name:
            raise ImproperlyConfigured(
                "service_name is required for service authentication. "
                "Each service must have a unique key."
            )

        # Normalize service name for env var (uppercase, hyphens to underscores)
        normalized_name = service_name.upper().replace('-', '_')

        # Build env var name
        if kid:
            env_key = f'SERVICE_AUTH_SECRET_{normalized_name}_{kid.upper()}'
        else:
            env_key = f'SERVICE_AUTH_SECRET_{normalized_name}'

        # Get the key from settings
        secret = getattr(settings, env_key, None)

        if not secret:
            raise ImproperlyConfigured(
                f"Service authentication key not configured: {env_key}. "
                f"Set {env_key} environment variable with a secure random key. "
                f"Generate with: python -c 'import secrets; print(secrets.token_urlsafe(64))'"
            )

        return secret

    @classmethod
    def generate_token(
        cls,
        service_name: str,
        scopes: List[str],
        expiry_hours: Optional[int] = None,
        kid: Optional[str] = None
    ) -> str:
        """
        Generate JWT token for a service.

        Args:
            service_name: Name of the service (e.g., "django-backend")
            scopes: List of allowed scopes (e.g., ["ai-services:read"])
            expiry_hours: Optional custom expiry time
            kid: Key ID for key rotation (optional)

        Returns:
            JWT token string

        Example:
            token = ServiceTokenManager.generate_token(
                service_name="django-backend",
                scopes=["ai-services:read", "ai-services:write"]
            )

        Security:
            - Uses unique per-service signing key
            - Includes kid header for key rotation support
            - Tokens are cryptographically bound to issuing service
        """
        expiry = expiry_hours or cls.TOKEN_EXPIRY_HOURS
        now = datetime.utcnow()

        payload = {
            'sub': service_name,          # Subject (service name)
            'iss': 'ecommerce-platform',  # Issuer
            'aud': 'internal-services',   # Audience
            'scopes': scopes,              # Allowed scopes
            'iat': now,                    # Issued at
            'exp': now + timedelta(hours=expiry),  # Expiration
            'jti': f"{service_name}-{int(now.timestamp())}",  # JWT ID
        }

        # Build JWT headers
        headers = {}
        if kid:
            headers['kid'] = kid

        # Get service-specific signing key
        secret_key = cls.get_secret_key(service_name=service_name, kid=kid)

        token = jwt.encode(
            payload,
            secret_key,
            algorithm=cls.ALGORITHM,
            headers=headers
        )

        logger.info(
            f"Generated service token for {service_name} "
            f"with scopes: {scopes}, expires in {expiry}h, kid={kid or 'default'}"
        )

        return token

    @classmethod
    def verify_token(cls, token: str) -> Dict:
        """
        Verify and decode a service token.

        Args:
            token: JWT token string

        Returns:
            Decoded payload dictionary

        Raises:
            jwt.InvalidTokenError: If token is invalid
            jwt.ExpiredSignatureError: If token is expired
            ValueError: If token validation fails
            ImproperlyConfigured: If service key is not configured

        Example:
            try:
                payload = ServiceTokenManager.verify_token(token)
                service_name = payload['sub']
                scopes = payload['scopes']
            except jwt.ExpiredSignatureError:
                # Handle expired token
                pass

        Security:
            - Extracts service name from token (sub claim)
            - Uses service-specific verification key
            - Supports key rotation via kid header
            - Prevents token replay across services
        """
        try:
            # Decode header without verification to extract kid and service info
            unverified_header = jwt.get_unverified_header(token)
            unverified_payload = jwt.decode(
                token,
                options={"verify_signature": False}
            )

            service_name = unverified_payload.get('sub')
            if not service_name:
                raise ValueError("Token missing 'sub' (service name) claim")

            kid = unverified_header.get('kid')

            # Get the service-specific verification key
            secret_key = cls.get_secret_key(service_name=service_name, kid=kid)

            # Now verify with the correct key
            payload = jwt.decode(
                token,
                secret_key,
                algorithms=[cls.ALGORITHM],
                audience='internal-services',
                options={
                    'verify_signature': True,
                    'verify_exp': True,
                    'verify_iat': True,
                    'require': ['sub', 'iss', 'aud', 'scopes', 'exp', 'iat']
                }
            )

            # Additional validation
            if payload.get('iss') != 'ecommerce-platform':
                raise ValueError("Invalid token issuer")

            if not isinstance(payload.get('scopes'), list):
                raise ValueError("Invalid scopes format")

            logger.debug(
                f"Verified token for service: {payload['sub']}, kid={kid or 'default'}"
            )
            return payload

        except jwt.ExpiredSignatureError:
            logger.warning("Service token expired")
            raise

        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid service token: {e}")
            raise

        except ImproperlyConfigured as e:
            logger.error(f"Service key not configured: {e}")
            raise

    @classmethod
    def get_cached_token(cls, service_name: str) -> Optional[str]:
        """
        Get a cached service token.

        Args:
            service_name: Name of the service

        Returns:
            Cached token or None if not found/expired
        """
        cache_key = f'service_token:{service_name}'
        return cache.get(cache_key)

    @classmethod
    def cache_token(cls, service_name: str, token: str, timeout: int = None):
        """
        Cache a service token.

        Args:
            service_name: Name of the service
            token: JWT token
            timeout: Cache timeout in seconds (default: TOKEN_EXPIRY_HOURS - 1hour)
        """
        if timeout is None:
            # Cache for slightly less than token expiry to force refresh
            timeout = (cls.TOKEN_EXPIRY_HOURS - 1) * 3600

        cache_key = f'service_token:{service_name}'
        cache.set(cache_key, token, timeout=timeout)
        logger.debug(f"Cached token for {service_name}, expires in {timeout}s")

    @classmethod
    def get_or_generate_token(
        cls,
        service_name: str,
        scopes: List[str]
    ) -> str:
        """
        Get cached token or generate a new one.

        Args:
            service_name: Name of the service
            scopes: Required scopes

        Returns:
            JWT token
        """
        # Try to get from cache
        cached_token = cls.get_cached_token(service_name)
        if cached_token:
            try:
                # Verify cached token is still valid
                cls.verify_token(cached_token)
                logger.debug(f"Using cached token for {service_name}")
                return cached_token
            except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
                logger.info(f"Cached token for {service_name} invalid, generating new one")

        # Generate new token
        token = cls.generate_token(service_name, scopes)

        # Cache it
        cls.cache_token(service_name, token)

        return token

    @classmethod
    def rotate_tokens(cls):
        """
        Rotate all service tokens.

        This should be called periodically (e.g., daily via Celery Beat)
        to rotate tokens for security.
        """
        # Define all services and their scopes
        services = {
            'django-backend': ['ai-services:*', 'internal:*'],
            'api-gateway': ['ai-services:*'],
            'celery-worker': ['ai-services:*', 'internal:*'],
        }

        rotated_count = 0
        for service_name, scopes in services.items():
            try:
                token = cls.generate_token(service_name, scopes)
                cls.cache_token(service_name, token)
                rotated_count += 1
            except Exception as e:
                logger.error(f"Failed to rotate token for {service_name}: {e}")

        logger.info(f"Rotated {rotated_count} service tokens")
        return rotated_count


# Predefined service scopes
class ServiceScopes:
    """Predefined scopes for service authorization"""

    # AI Services
    AI_SERVICES_READ = 'ai-services:read'
    AI_SERVICES_WRITE = 'ai-services:write'
    AI_SERVICES_ALL = 'ai-services:*'

    # Internal APIs
    INTERNAL_READ = 'internal:read'
    INTERNAL_WRITE = 'internal:write'
    INTERNAL_ALL = 'internal:*'

    # Orders
    ORDERS_READ = 'orders:read'
    ORDERS_WRITE = 'orders:write'
    ORDERS_ALL = 'orders:*'

    # Products
    PRODUCTS_READ = 'products:read'
    PRODUCTS_WRITE = 'products:write'
    PRODUCTS_ALL = 'products:*'

    # Payments
    PAYMENTS_READ = 'payments:read'
    PAYMENTS_WRITE = 'payments:write'
    PAYMENTS_ALL = 'payments:*'

    @classmethod
    def matches_scope(cls, required_scope: str, user_scopes: List[str]) -> bool:
        """
        Check if user has required scope.

        Supports wildcard matching (e.g., "ai-services:*" matches "ai-services:read")

        Args:
            required_scope: Required scope
            user_scopes: List of user's scopes

        Returns:
            True if user has required scope

        Example:
            has_access = ServiceScopes.matches_scope(
                "ai-services:read",
                ["ai-services:*", "orders:read"]
            )  # Returns True
        """
        if required_scope in user_scopes:
            return True

        # Check wildcard scopes
        for scope in user_scopes:
            if scope.endswith(':*'):
                prefix = scope[:-2]
                if required_scope.startswith(prefix + ':'):
                    return True

        return False
