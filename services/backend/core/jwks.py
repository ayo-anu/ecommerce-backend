"""
JSON Web Key Set (JWKS) support for service authentication.

Provides public key distribution for asymmetric (RS256) token verification
and key rotation management.
"""

import logging
from typing import List, Dict, Optional
from django.conf import settings
from django.http import JsonResponse
from django.views import View
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)


class JWKSManager:
    """
    Manage JSON Web Key Sets for service authentication.

    For HS256 (symmetric), JWKS is not used (keys are secret).
    For RS256 (asymmetric), JWKS exposes public keys for verification.
    """

    @classmethod
    def get_algorithm(cls) -> str:
        """Get the configured JWT algorithm."""
        return getattr(settings, 'SERVICE_AUTH_ALGORITHM', 'HS256')

    @classmethod
    def is_asymmetric(cls) -> bool:
        """Check if using asymmetric algorithm (RS256, ES256, etc)."""
        return cls.get_algorithm().startswith(('RS', 'ES', 'PS'))

    @classmethod
    def get_public_key_pem(cls, service_name: str, kid: Optional[str] = None) -> Optional[str]:
        """
        Get public key in PEM format for a service.

        Args:
            service_name: Name of the service
            kid: Key ID (optional)

        Returns:
            Public key PEM string or None if not available

        Note:
            Only applicable for RS256 algorithm.
            For HS256, there are no public keys (symmetric).
        """
        if not cls.is_asymmetric():
            logger.warning("JWKS public keys only available for asymmetric algorithms (RS256, ES256)")
            return None

        # Normalize service name
        normalized_name = service_name.upper().replace('-', '_')

        # Build env var name for public key
        if kid:
            env_key = f'SERVICE_AUTH_PUBLIC_KEY_{normalized_name}_{kid.upper()}'
        else:
            env_key = f'SERVICE_AUTH_PUBLIC_KEY_{normalized_name}'

        public_key_pem = getattr(settings, env_key, None)

        if not public_key_pem:
            logger.warning(f"Public key not found: {env_key}")
            return None

        return public_key_pem

    @classmethod
    def pem_to_jwk(cls, public_key_pem: str, kid: str, service_name: str) -> Optional[Dict]:
        """
        Convert PEM public key to JWK (JSON Web Key) format.

        Args:
            public_key_pem: Public key in PEM format
            kid: Key ID
            service_name: Service name

        Returns:
            JWK dictionary or None if conversion fails
        """
        try:
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.hazmat.primitives.serialization import load_pem_public_key
            import base64

            # Load public key
            public_key = load_pem_public_key(
                public_key_pem.encode('utf-8'),
                backend=default_backend()
            )

            if not isinstance(public_key, rsa.RSAPublicKey):
                logger.error(f"Unsupported key type for service {service_name}")
                return None

            # Get public numbers
            numbers = public_key.public_numbers()

            # Convert to JWK format
            def int_to_base64(n):
                """Convert integer to base64url without padding."""
                byte_length = (n.bit_length() + 7) // 8
                bytes_repr = n.to_bytes(byte_length, byteorder='big')
                return base64.urlsafe_b64encode(bytes_repr).decode('utf-8').rstrip('=')

            jwk = {
                'kty': 'RSA',
                'use': 'sig',  # Signature
                'kid': kid,
                'alg': cls.get_algorithm(),
                'n': int_to_base64(numbers.n),  # Modulus
                'e': int_to_base64(numbers.e),  # Exponent
                # Optional metadata
                'service': service_name,
            }

            return jwk

        except Exception as e:
            logger.error(f"Failed to convert PEM to JWK for {service_name}: {e}")
            return None

    @classmethod
    def get_jwks(cls) -> Dict:
        """
        Get JWKS (JSON Web Key Set) for all services.

        Returns:
            JWKS dictionary with format:
            {
                "keys": [
                    {
                        "kty": "RSA",
                        "use": "sig",
                        "kid": "django-backend-v1",
                        "alg": "RS256",
                        "n": "...",
                        "e": "AQAB"
                    },
                    ...
                ]
            }

        Note:
            Only applicable for RS256. For HS256, returns empty key set.
        """
        if not cls.is_asymmetric():
            return {
                "keys": [],
                "note": "JWKS not applicable for symmetric algorithms (HS256). Keys are secret."
            }

        keys = []

        # Define services and their key IDs
        # In production, this should come from a database or config
        service_keys = getattr(settings, 'SERVICE_AUTH_JWKS_CONFIG', {})

        # Example format:
        # SERVICE_AUTH_JWKS_CONFIG = {
        #     'django-backend': ['v1', 'v2'],
        #     'api-gateway': ['v1'],
        #     'celery-worker': ['v1'],
        # }

        for service_name, kids in service_keys.items():
            for kid in kids:
                # Get public key
                public_key_pem = cls.get_public_key_pem(service_name, kid)
                if public_key_pem:
                    # Convert to JWK
                    full_kid = f"{service_name}-{kid}"
                    jwk = cls.pem_to_jwk(public_key_pem, full_kid, service_name)
                    if jwk:
                        keys.append(jwk)

        return {"keys": keys}


class JWKSView(View):
    """
    Django view to expose JWKS endpoint.

    GET /.well-known/jwks.json
    Returns public keys for all services
    """

    def get(self, request):
        """Handle GET request for JWKS."""
        jwks = JWKSManager.get_jwks()
        return JsonResponse(jwks, json_dumps_params={'indent': 2})
