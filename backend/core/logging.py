"""
JSON Logging Formatter for Production

Provides structured JSON logging with standardized fields for better
observability and integration with log aggregation tools.
"""
import json
import logging
import traceback
from datetime import datetime
from django.conf import settings


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.

    Outputs logs as JSON with standardized fields:
    - timestamp: ISO 8601 formatted timestamp
    - level: Log level (INFO, WARNING, ERROR, etc.)
    - logger: Logger name
    - message: Log message
    - request_id: Request ID if available
    - environment: Environment name (production, staging, etc.)
    - service: Service name
    - exception: Exception details if present
    """

    def format(self, record):
        """
        Format log record as JSON.

        Args:
            record: LogRecord instance

        Returns:
            JSON string with structured log data
        """
        # Base log data
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'service': getattr(settings, 'SERVICE_NAME', 'ecommerce-backend'),
            'environment': getattr(settings, 'ENVIRONMENT', 'production'),
        }

        # Add request ID if available
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id

        # Add file and line information
        log_data['location'] = {
            'file': record.pathname,
            'line': record.lineno,
            'function': record.funcName,
        }

        # Add exception information if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': traceback.format_exception(*record.exc_info),
            }

        # Add extra fields passed to logger
        if hasattr(record, 'extra_data'):
            log_data['extra'] = record.extra_data

        return json.dumps(log_data)


class RequestIDFilter(logging.Filter):
    """
    Logging filter to add request_id to all log records.

    Extracts request_id from thread-local storage and adds it to the log record.
    """

    def filter(self, record):
        """
        Add request_id to log record if available.

        Args:
            record: LogRecord instance

        Returns:
            True to allow the record to be logged
        """
        import threading

        # Try to get request_id from thread-local storage
        local = getattr(threading.current_thread(), 'request_id', None)
        record.request_id = local if local else 'no-request-id'

        return True
