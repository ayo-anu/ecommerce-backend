"""
Service-to-Service Authentication Middleware.

Authenticates requests from other internal services using JWT tokens.
"""
import logging
import jwt
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

from core.service_tokens import ServiceTokenManager, ServiceScopes

logger = logging.getLogger(__name__)


class ServiceAuthMiddleware(MiddlewareMixin):
    """
    Middleware to authenticate service-to-service requests.

    Checks for X-Service-Token header and verifies JWT token.
    Attaches service information to request object.
    """

    # Paths that don't require service authentication
    EXCLUDE_PATHS = [
        '/admin/',
        '/api/docs/',
        '/api/schema/',
        '/health/',
        '/metrics/',
    ]

    # Paths that require service authentication
    SERVICE_AUTH_PATHS = [
        '/internal/',
        '/api/internal/',
    ]

    def process_request(self, request):
        """
        Process incoming request for service authentication.

        Checks if path requires service auth, validates token,
        and attaches service info to request.
        """
        # Skip excluded paths
        if any(request.path.startswith(path) for path in self.EXCLUDE_PATHS):
            return None

        # Check if this path requires service auth
        requires_service_auth = any(
            request.path.startswith(path) for path in self.SERVICE_AUTH_PATHS
        )

        if not requires_service_auth:
            return None

        # Get service token from header
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

        # Verify token
        try:
            payload = ServiceTokenManager.verify_token(service_token)

            # Attach service info to request
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
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


def require_service_scope(scope: str):
    """
    Decorator to require specific service scope for a view.

    Usage:
        @require_service_scope('ai-services:write')
        def my_internal_api_view(request):
            # Only services with 'ai-services:write' scope can access
            pass

    Args:
        scope: Required scope string
    """
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            # Check if service is authenticated
            if not getattr(request, 'service_authenticated', False):
                return JsonResponse({
                    'error': 'service_auth_required',
                    'message': 'Service authentication required'
                }, status=401)

            # Check if service has required scope
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

            # Service has required scope, proceed
            return view_func(request, *args, **kwargs)

        wrapper.__name__ = view_func.__name__
        wrapper.__doc__ = view_func.__doc__
        return wrapper

    return decorator
