"""
Centralized JSON logging configuration for AI services

Provides structured JSON logging with standardized fields for better
observability and integration with log aggregation tools.
"""
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
    """
    Custom JSON formatter for structured logging.

    Outputs logs as JSON with standardized fields:
    - timestamp: ISO 8601 formatted timestamp
    - level: Log level (INFO, WARNING, ERROR, etc.)
    - service: Service name
    - message: Log message
    - request_id: Request ID if available
    - exception: Exception details if present
    """

    def __init__(self, service_name: str = "ai-service"):
        """
        Initialize JSON formatter.

        Args:
            service_name: Name of the service for logging
        """
        super().__init__()
        self.service_name = service_name

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
            'service': self.service_name,
            'logger': record.name,
            'message': record.getMessage(),
            'environment': getattr(settings, 'ENVIRONMENT', 'production'),
        }

        # Add request ID if available
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id

        # Add file and line information for debugging
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

        # Add duration if available (for request timing)
        if hasattr(record, 'duration_ms'):
            log_data['duration_ms'] = record.duration_ms

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
        # Try to get request_id from thread-local storage
        local = getattr(threading.current_thread(), 'request_id', None)
        record.request_id = local if local else 'no-request-id'

        return True


def setup_logging(service_name: str = "ai-service", use_json: bool = True):
    """
    Configure application logging with JSON formatting.

    Args:
        service_name: Name of the service for logging
        use_json: Whether to use JSON formatting (True for production)

    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Create logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.LOG_LEVEL))

    # Remove existing handlers
    logger.handlers = []

    # Console handler (stdout for Docker)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    # Choose formatter based on environment
    if use_json:
        formatter = JSONFormatter(service_name=service_name)
        # Add request ID filter for JSON logging
        request_id_filter = RequestIDFilter()
        console_handler.addFilter(request_id_filter)
    else:
        # Simple text formatter for development
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


def setup_logger(name: str, service_name: str = None) -> logging.Logger:
    """
    Setup and return a named logger with JSON formatting.

    Args:
        name: Logger name (usually the module name)
        service_name: Service name for logging (defaults to name)

    Returns:
        Configured logger instance
    """
    # Use name as service_name if not provided
    if service_name is None:
        service_name = name

    # Setup global logging if not already done
    # Use JSON formatting in production (when ENVIRONMENT != development)
    use_json = getattr(settings, 'ENVIRONMENT', 'production') != 'development'
    setup_logging(service_name=service_name, use_json=use_json)

    # Return named logger
    return logging.getLogger(name)


def get_logger(name: str) -> logging.Logger:
    """
    Get logger for specific module.

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
