"""Structured JSON logging with request IDs."""

import logging
import sys
import time
import uuid
from datetime import datetime
from typing import Any, Dict
from pythonjsonlogger import jsonlogger


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """JSON formatter with service and request context."""

    def __init__(self, *args, service_name: str = "unknown", environment: str = "development", **kwargs):
        super().__init__(*args, **kwargs)
        self.service_name = service_name
        self.environment = environment

    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]):
        """Add custom fields to log record."""
        super().add_fields(log_record, record, message_dict)

        log_record["timestamp"] = datetime.utcnow().isoformat() + "Z"

        log_record["service"] = self.service_name
        log_record["environment"] = self.environment

        log_record["level"] = record.levelname
        log_record["logger_name"] = record.name

        log_record["source"] = {
            "file": record.pathname,
            "line": record.lineno,
            "function": record.funcName,
        }

        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id

        if hasattr(record, "trace_id"):
            log_record["trace_id"] = record.trace_id

        if hasattr(record, "user_id"):
            log_record["user_id"] = record.user_id

        if hasattr(record, "duration"):
            log_record["duration_ms"] = round(record.duration * 1000, 2)

        if hasattr(record, "method"):
            log_record["http"] = {
                "method": record.method,
                "path": getattr(record, "path", None),
                "status_code": getattr(record, "status_code", None),
                "user_agent": getattr(record, "user_agent", None),
                "client_ip": getattr(record, "client_ip", None),
            }

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
    """Setup JSON logging for a service."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    root_logger.handlers = []

    formatter = CustomJsonFormatter(
        service_name=service_name,
        environment=environment,
        fmt="%(message)s"
    )

    if include_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

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
    """Logger adapter adding request and trace IDs."""

    def __init__(self, logger: logging.Logger, request=None):
        super().__init__(logger, {})
        self.request = request

    def process(self, msg, kwargs):
        """Add request context to log records."""
        extra = kwargs.get("extra", {})

        if self.request:
            if hasattr(self.request.state, "request_id"):
                extra["request_id"] = self.request.state.request_id

            if hasattr(self.request.state, "trace_id"):
                extra["trace_id"] = self.request.state.trace_id

            if hasattr(self.request.state, "user_id"):
                extra["user_id"] = self.request.state.user_id

        kwargs["extra"] = extra
        return msg, kwargs


import contextvars
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

request_id_var = contextvars.ContextVar("request_id", default=None)
trace_id_var = contextvars.ContextVar("trace_id", default=None)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach request and trace IDs."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        request.state.request_id = request_id
        request_id_var.set(request_id)

        trace_id = request.headers.get("x-trace-id", str(uuid.uuid4()))
        request.state.trace_id = trace_id
        trace_id_var.set(trace_id)

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

        try:
            response = await call_next(request)

            duration = time.time() - start_time

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

            response.headers["X-Request-ID"] = request_id
            response.headers["X-Trace-ID"] = trace_id

            return response

        except Exception as e:
            duration = time.time() - start_time

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


def get_current_request_id() -> str:
    """Get current request ID from context."""
    return request_id_var.get() or "no-request-id"


def get_current_trace_id() -> str:
    """Get current trace ID from context."""
    return trace_id_var.get() or "no-trace-id"


def log_with_context(logger: logging.Logger, level: str, message: str, **kwargs):
    """Log with current request context."""
    extra = kwargs.copy()
    extra["request_id"] = get_current_request_id()
    extra["trace_id"] = get_current_trace_id()

    log_func = getattr(logger, level.lower())
    log_func(message, extra=extra)
