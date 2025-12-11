"""
Error Logging Middleware

Provides structured logging for unhandled exceptions with request context.
Logs errors as structured JSON events for better observability.
"""
import logging
import traceback


logger = logging.getLogger(__name__)


class ErrorLoggingMiddleware:
    """
    Middleware to log unhandled exceptions with request context.

    Features:
    - Catches all unhandled exceptions
    - Logs detailed error information in structured format
    - Includes request ID, path, method, and user information
    - Re-raises the exception for Django's default error handling
    - Does not interfere with normal error response flow
    """

    def __init__(self, get_response):
        """
        Initialize the middleware.

        Args:
            get_response: Next middleware or view in the chain
        """
        self.get_response = get_response

    def __call__(self, request):
        """
        Process the request and catch exceptions.

        Args:
            request: Django request object

        Returns:
            Response from next middleware or view
        """
        return self.get_response(request)

    def process_exception(self, request, exception):
        """
        Log unhandled exceptions with full context.

        Args:
            request: Django request object
            exception: Exception that was raised

        Returns:
            None (allows Django to handle the exception normally)
        """
        # Build error context
        error_context = {
            'request_id': getattr(request, 'request_id', 'no-request-id'),
            'path': request.path,
            'method': request.method,
            'user': str(request.user) if hasattr(request, 'user') else 'Anonymous',
            'user_id': request.user.id if hasattr(request, 'user') and hasattr(request.user, 'id') else None,
            'ip_address': self._get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', 'unknown'),
            'exception_type': type(exception).__name__,
            'exception_message': str(exception),
            'traceback': traceback.format_exc(),
        }

        # Add query parameters if present (be careful with sensitive data)
        if request.GET:
            error_context['query_params'] = dict(request.GET)

        # Log the error with structured context
        logger.error(
            f"Unhandled exception in {request.method} {request.path}: {type(exception).__name__}",
            extra={
                'request_id': error_context['request_id'],
                'extra_data': error_context
            },
            exc_info=True
        )

        # Return None to allow Django to handle the exception normally
        # This ensures proper error responses are sent to clients
        return None

    def _get_client_ip(self, request):
        """
        Extract client IP address from request.

        Handles proxies and load balancers by checking X-Forwarded-For header.

        Args:
            request: Django request object

        Returns:
            Client IP address as string
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # X-Forwarded-For can contain multiple IPs, get the first one
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')
        return ip
