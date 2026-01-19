"""Request ID middleware."""
import uuid
import threading


class RequestIDMiddleware:
    """Generate and attach request IDs."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.META.get('HTTP_X_REQUEST_ID')

        if not request_id:
            request_id = str(uuid.uuid4())

        request.request_id = request_id

        threading.current_thread().request_id = request_id

        response = self.get_response(request)

        response['X-Request-ID'] = request_id

        if hasattr(threading.current_thread(), 'request_id'):
            delattr(threading.current_thread(), 'request_id')

        return response
