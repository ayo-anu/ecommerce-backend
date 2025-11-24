from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler for consistent error responses
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    if response is not None:
        # Customize the response format
        custom_response_data = {
            'error': True,
            'message': str(exc),
            'status_code': response.status_code,
        }
        
        # Add field errors if available
        if hasattr(response, 'data') and isinstance(response.data, dict):
            custom_response_data['errors'] = response.data
        
        response.data = custom_response_data
        
        # Log the error
        logger.error(
            f"API Error: {exc}",
            extra={
                'status_code': response.status_code,
                'path': context.get('request').path if context.get('request') else None,
                'method': context.get('request').method if context.get('request') else None,
            }
        )
    else:
        # Handle unexpected errors (500 errors)
        logger.exception(f"Unhandled exception: {exc}")
        response = Response(
            {
                'error': True,
                'message': 'An unexpected error occurred. Please try again later.',
                'status_code': status.HTTP_500_INTERNAL_SERVER_ERROR,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    return response