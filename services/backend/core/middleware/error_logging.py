import logging

import traceback



logger = logging.getLogger(__name__)



class ErrorLoggingMiddleware:


    def __init__(self, get_response):

        self.get_response = get_response


    def __call__(self, request):

        return self.get_response(request)


    def process_exception(self, request, exception):

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


        if request.GET:

            error_context['query_params'] = dict(request.GET)


        logger.error(

            f"Unhandled exception in {request.method} {request.path}: {type(exception).__name__}",

            extra={

                'request_id': error_context['request_id'],

                'extra_data': error_context

            },

            exc_info=True

        )


        return None


    def _get_client_ip(self, request):

        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')

        if x_forwarded_for:

            ip = x_forwarded_for.split(',')[0].strip()

        else:

            ip = request.META.get('REMOTE_ADDR', 'unknown')

        return ip

