

import logging

from typing import List, Dict, Optional

from django.conf import settings

from django.http import JsonResponse

from django.views import View

from cryptography.hazmat.backends import default_backend


logger = logging.getLogger(__name__)



class JWKSManager:


    @classmethod

    def get_algorithm(cls) -> str:

        return getattr(settings, 'SERVICE_AUTH_ALGORITHM', 'HS256')


    @classmethod

    def is_asymmetric(cls) -> bool:

        return cls.get_algorithm().startswith(('RS', 'ES', 'PS'))


    @classmethod

    def get_public_key_pem(cls, service_name: str, kid: Optional[str] = None) -> Optional[str]:

        if not cls.is_asymmetric():

            logger.warning("JWKS public keys only available for asymmetric algorithms (RS256, ES256)")

            return None


        normalized_name = service_name.upper().replace('-', '_')


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

        try:

            from cryptography.hazmat.primitives.asymmetric import rsa

            from cryptography.hazmat.primitives.serialization import load_pem_public_key

            import base64


            public_key = load_pem_public_key(

                public_key_pem.encode('utf-8'),

                backend=default_backend()

            )


            if not isinstance(public_key, rsa.RSAPublicKey):

                logger.error(f"Unsupported key type for service {service_name}")

                return None


            numbers = public_key.public_numbers()


            def int_to_base64(n):

                byte_length = (n.bit_length() + 7) // 8

                bytes_repr = n.to_bytes(byte_length, byteorder='big')

                return base64.urlsafe_b64encode(bytes_repr).decode('utf-8').rstrip('=')


            jwk = {

                'kty': 'RSA',

                'use': 'sig',

                'kid': kid,

                'alg': cls.get_algorithm(),

                'n': int_to_base64(numbers.n),

                'e': int_to_base64(numbers.e),

                'service': service_name,

            }


            return jwk


        except Exception as e:

            logger.error(f"Failed to convert PEM to JWK for {service_name}: {e}")

            return None


    @classmethod

    def get_jwks(cls) -> Dict:

        if not cls.is_asymmetric():

            return {

                "keys": [],

                "note": "JWKS not applicable for symmetric algorithms (HS256). Keys are secret."

            }


        keys = []


        service_keys = getattr(settings, 'SERVICE_AUTH_JWKS_CONFIG', {})


        for service_name, kids in service_keys.items():

            for kid in kids:

                public_key_pem = cls.get_public_key_pem(service_name, kid)

                if public_key_pem:

                    full_kid = f"{service_name}-{kid}"

                    jwk = cls.pem_to_jwk(public_key_pem, full_kid, service_name)

                    if jwk:

                        keys.append(jwk)


        return {"keys": keys}



class JWKSView(View):


    def get(self, request):

        jwks = JWKSManager.get_jwks()

        return JsonResponse(jwks, json_dumps_params={'indent': 2})

