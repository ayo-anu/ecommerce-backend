import logging

import jwt

from functools import wraps

from django.http import JsonResponse

from django.utils.deprecation import MiddlewareMixin


from core.service_tokens import ServiceTokenManager, ServiceScopes


logger = logging.getLogger(__name__)



class ServiceAuthMiddleware(MiddlewareMixin):


    EXCLUDE_PATHS = [

        '/admin/',

        '/api/docs/',

        '/api/schema/',

        '/health/',

        '/metrics/',

    ]


    SERVICE_AUTH_PATHS = [

        '/internal/',

        '/api/internal/',

    ]


    def process_request(self, request):

        if any(request.path.startswith(path) for path in self.EXCLUDE_PATHS):

            return None


        requires_service_auth = any(

            request.path.startswith(path) for path in self.SERVICE_AUTH_PATHS

        )


        if not requires_service_auth:

            return None


        service_token = request.META.get('HTTP_X_SERVICE_TOKEN')


        if not service_token:

            logger.warning(

                f"Service token missing for {request.path}",

                extra={

                    'path': request.path,

                    'method': request.method,

                    'ip': self._get_client_ip(request),

                }

            )

            return JsonResponse({

                'error': 'service_auth_required',

                'message': 'Service authentication token required',

                'detail': 'Include X-Service-Token header with valid JWT token'

            }, status=401)


        try:

            payload = ServiceTokenManager.verify_token(service_token)


            request.service_name = payload['sub']

            request.service_scopes = payload['scopes']

            request.service_authenticated = True


            logger.debug(

                f"Service authenticated: {request.service_name}",

                extra={

                    'service': request.service_name,

                    'scopes': request.service_scopes,

                    'path': request.path,

                }

            )


            return None


        except jwt.ExpiredSignatureError:

            logger.warning(

                f"Expired service token for {request.path}",

                extra={'path': request.path}

            )

            return JsonResponse({

                'error': 'token_expired',

                'message': 'Service token has expired',

                'detail': 'Request a new token from token service'

            }, status=401)


        except jwt.InvalidTokenError as e:

            logger.error(

                f"Invalid service token: {e}",

                extra={'path': request.path}

            )

            return JsonResponse({

                'error': 'invalid_token',

                'message': 'Invalid service token',

                'detail': str(e)

            }, status=401)


        except Exception as e:

            logger.error(

                f"Service auth error: {e}",

                extra={'path': request.path},

                exc_info=True

            )

            return JsonResponse({

                'error': 'authentication_error',

                'message': 'Service authentication failed'

            }, status=500)


    def _get_client_ip(self, request):

        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')

        if x_forwarded_for:

            ip = x_forwarded_for.split(',')[0]

        else:

            ip = request.META.get('REMOTE_ADDR')

        return ip



def require_service_scope(scope: str):

    def decorator(view_func):

        @wraps(view_func)

        def wrapper(request, *args, **kwargs):

            if not getattr(request, 'service_authenticated', False):

                return JsonResponse({

                    'error': 'service_auth_required',

                    'message': 'Service authentication required'

                }, status=401)


            service_scopes = getattr(request, 'service_scopes', [])


            if not ServiceScopes.matches_scope(scope, service_scopes):

                logger.warning(

                    f"Service {request.service_name} lacks scope {scope}",

                    extra={

                        'service': request.service_name,

                        'required_scope': scope,

                        'service_scopes': service_scopes,

                    }

                )

                return JsonResponse({

                    'error': 'insufficient_permissions',

                    'message': f'Scope "{scope}" required',

                    'detail': f'Your service has scopes: {service_scopes}'

                }, status=403)


            return view_func(request, *args, **kwargs)


        return wrapper


    return decorator

