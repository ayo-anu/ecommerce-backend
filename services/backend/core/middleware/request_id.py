"""
Request ID Middleware

Generates or extracts request IDs for request tracing and observability.
Adds X-Request-ID header to all responses for request correlation.
"""
import uuid
import threading


class RequestIDMiddleware:
    """
    Middleware to generate and attach request IDs to all requests.

    Features:
    - Generates a unique request ID if not provided in request headers
    - Accepts existing request ID from X-Request-ID header
    - Attaches request ID to the request object
    - Adds X-Request-ID header to all responses
    - Stores request ID in thread-local storage for logging
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
        Process the request and add request ID.

        Args:
            request: Django request object

        Returns:
            Response with X-Request-ID header
        """
        # Get request ID from header or generate new one
        request_id = request.META.get('HTTP_X_REQUEST_ID')

        if not request_id:
            # Generate new UUID for request ID
            request_id = str(uuid.uuid4())

        # Attach request ID to request object
        request.request_id = request_id

        # Store request ID in thread-local storage for logging
        threading.current_thread().request_id = request_id

        # Process request
        response = self.get_response(request)

        # Add request ID to response headers
        response['X-Request-ID'] = request_id

        # Clean up thread-local storage
        if hasattr(threading.current_thread(), 'request_id'):
            delattr(threading.current_thread(), 'request_id')

        return response
