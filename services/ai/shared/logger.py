"""JSON logging configuration for AI services."""
import json
import logging
import sys
import traceback
import threading
from datetime import datetime
from pathlib import Path
from .config import get_settings

settings = get_settings()


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logs."""

    def __init__(self, service_name: str = "ai-service"):
        super().__init__()
        self.service_name = service_name

    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'service': self.service_name,
            'logger': record.name,
            'message': record.getMessage(),
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

        if hasattr(record, 'duration_ms'):
            log_data['duration_ms'] = record.duration_ms

        return json.dumps(log_data)


class RequestIDFilter(logging.Filter):
    """Add request_id to log records."""

    def filter(self, record):
        local = getattr(threading.current_thread(), 'request_id', None)
        record.request_id = local if local else 'no-request-id'

        return True


def setup_logging(service_name: str = "ai-service", use_json: bool = True):
    """Configure application logging."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.LOG_LEVEL))

    logger.handlers = []

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    if use_json:
        formatter = JSONFormatter(service_name=service_name)
        request_id_filter = RequestIDFilter()
        console_handler.addFilter(request_id_filter)
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


def setup_logger(name: str, service_name: str = None) -> logging.Logger:
    """Setup and return a named logger."""
    if service_name is None:
        service_name = name

    use_json = getattr(settings, 'ENVIRONMENT', 'production') != 'development'
    setup_logging(service_name=service_name, use_json=use_json)

    return logging.getLogger(name)


def get_logger(name: str) -> logging.Logger:
    """Get a named logger."""
    return logging.getLogger(name)
