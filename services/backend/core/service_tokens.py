"""Service-to-service JWT handling."""
import logging
import jwt
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)


class ServiceTokenManager:
    """JWT tokens for service auth."""

    TOKEN_EXPIRY_HOURS = 24

    ALGORITHM = getattr(settings, 'SERVICE_AUTH_ALGORITHM', 'HS256')

    @classmethod
    def get_secret_key(cls, service_name: Optional[str] = None, kid: Optional[str] = None) -> str:
        if not service_name:
            raise ImproperlyConfigured(
                "service_name is required for service authentication. "
                "Each service must have a unique key."
            )

        normalized_name = service_name.upper().replace('-', '_')

        if kid:
            env_key = f'SERVICE_AUTH_SECRET_{normalized_name}_{kid.upper()}'
        else:
            env_key = f'SERVICE_AUTH_SECRET_{normalized_name}'

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
        expiry = expiry_hours or cls.TOKEN_EXPIRY_HOURS
        now = datetime.utcnow()

        payload = {
            'sub': service_name,
            'iss': 'ecommerce-platform',
            'aud': 'internal-services',
            'scopes': scopes,
            'iat': now,
            'exp': now + timedelta(hours=expiry),
            'jti': f"{service_name}-{int(now.timestamp())}",
        }

        headers = {}
        if kid:
            headers['kid'] = kid

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
        try:
            unverified_header = jwt.get_unverified_header(token)
            unverified_payload = jwt.decode(
                token,
                options={"verify_signature": False}
            )

            service_name = unverified_payload.get('sub')
            if not service_name:
                raise ValueError("Token missing 'sub' (service name) claim")

            kid = unverified_header.get('kid')

            secret_key = cls.get_secret_key(service_name=service_name, kid=kid)

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
        cache_key = f'service_token:{service_name}'
        return cache.get(cache_key)

    @classmethod
    def cache_token(cls, service_name: str, token: str, timeout: int = None):
        if timeout is None:
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
        cached_token = cls.get_cached_token(service_name)
        if cached_token:
            try:
                cls.verify_token(cached_token)
                logger.debug(f"Using cached token for {service_name}")
                return cached_token
            except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
                logger.info(f"Cached token for {service_name} invalid, generating new one")

        token = cls.generate_token(service_name, scopes)

        cls.cache_token(service_name, token)

        return token

    @classmethod
    def rotate_tokens(cls):
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


class ServiceScopes:
    """Scope constants."""

    AI_SERVICES_READ = 'ai-services:read'
    AI_SERVICES_WRITE = 'ai-services:write'
    AI_SERVICES_ALL = 'ai-services:*'

    INTERNAL_READ = 'internal:read'
    INTERNAL_WRITE = 'internal:write'
    INTERNAL_ALL = 'internal:*'

    ORDERS_READ = 'orders:read'
    ORDERS_WRITE = 'orders:write'
    ORDERS_ALL = 'orders:*'

    PRODUCTS_READ = 'products:read'
    PRODUCTS_WRITE = 'products:write'
    PRODUCTS_ALL = 'products:*'

    PAYMENTS_READ = 'payments:read'
    PAYMENTS_WRITE = 'payments:write'
    PAYMENTS_ALL = 'payments:*'

    @classmethod
    def matches_scope(cls, required_scope: str, user_scopes: List[str]) -> bool:
        if required_scope in user_scopes:
            return True

        for scope in user_scopes:
            if scope.endswith(':*'):
                prefix = scope[:-2]
                if required_scope.startswith(prefix + ':'):
                    return True

        return False
