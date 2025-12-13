"""
Structured JSON Logging with Request IDs.

Provides consistent JSON logging across all services with:
- Request ID correlation
- Structured fields
- Timestamp standardization
- Log levels
- Service identification
"""

import logging
import json
import sys
import time
import uuid
from datetime import datetime
from typing import Any, Dict
from pythonjsonlogger import jsonlogger


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter with additional fields.

    Adds:
    - timestamp (ISO 8601 format)
    - service_name
    - request_id (from context)
    - trace_id (from context)
    - environment
    """

    def __init__(self, *args, service_name: str = "unknown", environment: str = "development", **kwargs):
        super().__init__(*args, **kwargs)
        self.service_name = service_name
        self.environment = environment

    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]):
        """Add custom fields to log record."""
        super().add_fields(log_record, record, message_dict)

        # Add timestamp in ISO 8601 format
        log_record["timestamp"] = datetime.utcnow().isoformat() + "Z"

        # Add service identification
        log_record["service"] = self.service_name
        log_record["environment"] = self.environment

        # Add log level
        log_record["level"] = record.levelname
        log_record["logger_name"] = record.name

        # Add source location
        log_record["source"] = {
            "file": record.pathname,
            "line": record.lineno,
            "function": record.funcName,
        }

        # Add request_id and trace_id if available (from context)
        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id

        if hasattr(record, "trace_id"):
            log_record["trace_id"] = record.trace_id

        # Add user_id if available
        if hasattr(record, "user_id"):
            log_record["user_id"] = record.user_id

        # Add duration if available (for request logging)
        if hasattr(record, "duration"):
            log_record["duration_ms"] = round(record.duration * 1000, 2)

        # Add HTTP fields if available
        if hasattr(record, "method"):
            log_record["http"] = {
                "method": record.method,
                "path": getattr(record, "path", None),
                "status_code": getattr(record, "status_code", None),
                "user_agent": getattr(record, "user_agent", None),
                "client_ip": getattr(record, "client_ip", None),
            }

        # Add error information if exception
        if record.exc_info:
            log_record["error"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "stack_trace": self.formatException(record.exc_info) if record.exc_info else None,
            }


def setup_json_logging(
    service_name: str,
    environment: str = "development",
    log_level: str = "INFO",
    include_console: bool = True,
    log_file: str = None,
):
    """
    Setup JSON logging for a service.

    Args:
        service_name: Name of the service
        environment: Environment (development, staging, production)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        include_console: Whether to log to console
        log_file: Optional log file path

    Example:
        setup_json_logging(
            service_name="api-gateway",
            environment="production",
            log_level="INFO"
        )
    """
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    root_logger.handlers = []

    # Create JSON formatter
    formatter = CustomJsonFormatter(
        service_name=service_name,
        environment=environment,
        fmt="%(message)s"
    )

    # Console handler
    if include_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # File handler
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Set log level for third-party libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    logging.info(
        f"JSON logging configured",
        extra={
            "service_name": service_name,
            "environment": environment,
            "log_level": log_level,
        }
    )


class RequestIDLogger(logging.LoggerAdapter):
    """
    Logger adapter that adds request_id and trace_id to all log messages.

    Usage:
        logger = RequestIDLogger(logging.getLogger(__name__), request)
        logger.info("Processing request")
    """

    def __init__(self, logger: logging.Logger, request=None):
        super().__init__(logger, {})
        self.request = request

    def process(self, msg, kwargs):
        """Add request context to log records."""
        extra = kwargs.get("extra", {})

        if self.request:
            # Add request_id
            if hasattr(self.request.state, "request_id"):
                extra["request_id"] = self.request.state.request_id

            # Add trace_id
            if hasattr(self.request.state, "trace_id"):
                extra["trace_id"] = self.request.state.trace_id

            # Add user_id
            if hasattr(self.request.state, "user_id"):
                extra["user_id"] = self.request.state.user_id

        kwargs["extra"] = extra
        return msg, kwargs


# ==============================================================================
# Request ID Middleware
# ==============================================================================

import contextvars
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# Context variable for request ID
request_id_var = contextvars.ContextVar("request_id", default=None)
trace_id_var = contextvars.ContextVar("trace_id", default=None)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to generate and attach request IDs.

    Adds:
    - X-Request-ID header (unique per request)
    - X-Trace-ID header (for distributed tracing)
    """

    async def dispatch(self, request: Request, call_next):
        # Generate or extract request ID
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        request.state.request_id = request_id
        request_id_var.set(request_id)

        # Generate or extract trace ID
        trace_id = request.headers.get("x-trace-id", str(uuid.uuid4()))
        request.state.trace_id = trace_id
        trace_id_var.set(trace_id)

        # Log request start
        logger = logging.getLogger(__name__)
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "trace_id": trace_id,
                "method": request.method,
                "path": request.url.path,
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            }
        )

        start_time = time.time()

        # Process request
        try:
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Log request completion
            logger.info(
                f"Request completed: {request.method} {request.url.path}",
                extra={
                    "request_id": request_id,
                    "trace_id": trace_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration": duration,
                }
            )

            # Add headers to response
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Trace-ID"] = trace_id

            return response

        except Exception as e:
            duration = time.time() - start_time

            # Log error
            logger.error(
                f"Request failed: {request.method} {request.url.path}",
                extra={
                    "request_id": request_id,
                    "trace_id": trace_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration": duration,
                    "error": str(e),
                },
                exc_info=True
            )

            raise


# ==============================================================================
# Helper Functions
# ==============================================================================

def get_current_request_id() -> str:
    """Get current request ID from context."""
    return request_id_var.get() or "no-request-id"


def get_current_trace_id() -> str:
    """Get current trace ID from context."""
    return trace_id_var.get() or "no-trace-id"


def log_with_context(logger: logging.Logger, level: str, message: str, **kwargs):
    """
    Log message with automatic request context.

    Example:
        log_with_context(logger, "info", "Processing order", order_id=123)
    """
    extra = kwargs.copy()
    extra["request_id"] = get_current_request_id()
    extra["trace_id"] = get_current_trace_id()

    log_func = getattr(logger, level.lower())
    log_func(message, extra=extra)
