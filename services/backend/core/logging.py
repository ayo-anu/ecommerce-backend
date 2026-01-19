"""Structured JSON logging helpers."""
import json
import logging
import traceback
from datetime import datetime
from django.conf import settings


class JSONFormatter(logging.Formatter):
    """Format log records as JSON."""

    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'service': getattr(settings, 'SERVICE_NAME', 'ecommerce-backend'),
            'environment': getattr(settings, 'ENVIRONMENT', 'production'),
        }

        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id

        log_data['location'] = {
            'file': record.pathname,
            'line': record.lineno,
            'function': record.funcName,
        }

        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': traceback.format_exception(*record.exc_info),
            }

        if hasattr(record, 'extra_data'):
            log_data['extra'] = record.extra_data

        return json.dumps(log_data)


class RequestIDFilter(logging.Filter):
    """Add request_id to log records."""

    def filter(self, record):
        import threading

        local = getattr(threading.current_thread(), 'request_id', None)
        record.request_id = local if local else 'no-request-id'

        return True
