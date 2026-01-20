

import re

import logging

from typing import List, Set, Optional

from django.conf import settings

from django.http import HttpResponse

from django.utils.deprecation import MiddlewareMixin


logger = logging.getLogger(__name__)



class SecureCORSMiddleware(MiddlewareMixin):


    def __init__(self, get_response):

        super().__init__(get_response)

        self.allowed_origins = self._parse_allowed_origins()

        self.allowed_origin_patterns = self._compile_origin_patterns()


    def _parse_allowed_origins(self) -> Set[str]:

        origins = getattr(settings, 'SECURE_CORS_ALLOWED_ORIGINS', [])

        if isinstance(origins, str):

            origins = [o.strip() for o in origins.split(',') if o.strip()]

        return set(origins)


    def _compile_origin_patterns(self) -> List[re.Pattern]:

        patterns = getattr(settings, 'SECURE_CORS_ORIGIN_PATTERNS', [])

        compiled = []


        for pattern in patterns:

            regex_pattern = pattern.replace('.', r'\.')

            regex_pattern = regex_pattern.replace('*', r'[a-zA-Z0-9-]+')

            regex_pattern = f"^{regex_pattern}$"

            compiled.append(re.compile(regex_pattern))


        return compiled


    def process_request(self, request):

        origin = request.META.get('HTTP_ORIGIN')


        if not origin:

            return None


        logger.debug(

            f"CORS request",

            extra={

                'origin': origin,

                'method': request.method,

                'path': request.path,

                'user': request.user.username if request.user.is_authenticated else 'anonymous',

            }

        )


        if request.method == 'OPTIONS':

            return self._handle_preflight(request, origin)


        if not self._is_origin_allowed(origin, request):

            logger.warning(

                f"CORS request from unauthorized origin",

                extra={

                    'origin': origin,

                    'method': request.method,

                    'path': request.path,

                    'ip': self._get_client_ip(request),

                }

            )

            return None


        return None


    def process_response(self, request, response):

        origin = request.META.get('HTTP_ORIGIN')


        if not origin:

            return response


        if not self._is_origin_allowed(origin, request):

            return response


        response['Access-Control-Allow-Origin'] = origin


        if self._should_allow_credentials(origin):

            response['Access-Control-Allow-Credentials'] = 'true'


        exposed_headers = getattr(settings, 'SECURE_CORS_EXPOSE_HEADERS', [])

        if exposed_headers:

            response['Access-Control-Expose-Headers'] = ', '.join(exposed_headers)


        return response


    def _handle_preflight(self, request, origin: str) -> HttpResponse:

        if not self._is_origin_allowed(origin, request):

            return HttpResponse('Origin not allowed', status=403)


        response = HttpResponse()

        response['Access-Control-Allow-Origin'] = origin


        if self._should_allow_credentials(origin):

            response['Access-Control-Allow-Credentials'] = 'true'


        allowed_methods = self._get_allowed_methods(origin)

        response['Access-Control-Allow-Methods'] = ', '.join(allowed_methods)


        allowed_headers = self._get_allowed_headers()

        response['Access-Control-Allow-Headers'] = ', '.join(allowed_headers)


        response['Access-Control-Max-Age'] = '86400'


        return response


    def _is_origin_allowed(self, origin: str, request) -> bool:

        if origin in self.allowed_origins:

            return True


        for pattern in self.allowed_origin_patterns:

            if pattern.match(origin):

                return True


        method_origins = getattr(settings, f'SECURE_CORS_{request.method}_ORIGINS', None)

        if method_origins and origin in method_origins:

            return True


        return False


    def _should_allow_credentials(self, origin: str) -> bool:

        trusted_origins = getattr(settings, 'SECURE_CORS_TRUSTED_ORIGINS', set())

        return origin in trusted_origins


    def _get_allowed_methods(self, origin: str) -> List[str]:

        default_methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']


        method_restrictions = getattr(settings, 'SECURE_CORS_METHOD_RESTRICTIONS', {})


        if origin in method_restrictions:

            return method_restrictions[origin]


        return default_methods


    def _get_allowed_headers(self) -> List[str]:

        return getattr(

            settings,

            'SECURE_CORS_ALLOW_HEADERS',

            [

                'Accept',

                'Accept-Language',

                'Content-Type',

                'Content-Language',

                'Authorization',

                'X-Requested-With',

                'X-CSRFToken',

            ]

        )


    def _get_client_ip(self, request) -> str:

        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')

        if x_forwarded_for:

            return x_forwarded_for.split(',')[0].strip()

        return request.META.get('REMOTE_ADDR', '')

