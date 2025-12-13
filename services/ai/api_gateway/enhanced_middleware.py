"""
Enhanced Middleware for API Gateway

Provides:
- Request correlation IDs
- Performance tracking
- Error handling
- Request/response logging
"""

import time
import uuid
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """
    Add correlation ID to all requests for distributed tracing.

    The correlation ID is propagated through all microservices.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get or generate correlation ID
        correlation_id = request.headers.get("X-Correlation-ID")

        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        # Store in request state
        request.state.correlation_id = correlation_id

        # Process request
        response = await call_next(request)

        # Add to response headers
        response.headers["X-Correlation-ID"] = correlation_id

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Log all incoming requests and responses.

    Includes timing, status code, and correlation ID.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Start timer
        start_time = time.time()

        # Get correlation ID
        correlation_id = getattr(request.state, "correlation_id", "unknown")

        # Log request
        logger.info(
            "Request started",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": str(request.url.path),
                "client_ip": request.client.host if request.client else "unknown",
            },
        )

        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code

        except Exception as e:
            logger.error(
                f"Request failed with exception: {e}",
                extra={"correlation_id": correlation_id},
                exc_info=True,
            )
            raise

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log response
        log_level = logging.INFO if status_code < 400 else logging.WARNING

        logger.log(
            log_level,
            "Request completed",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": str(request.url.path),
                "status_code": status_code,
                "duration_ms": round(duration_ms, 2),
            },
        )

        # Add timing header
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Global error handling middleware.

    Catches all exceptions and returns proper error responses.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            return response

        except Exception as e:
            correlation_id = getattr(request.state, "correlation_id", "unknown")

            logger.error(
                f"Unhandled exception: {type(e).__name__}: {str(e)}",
                extra={"correlation_id": correlation_id},
                exc_info=True,
            )

            # Return JSON error response
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "type": "internal_server_error",
                        "message": "An unexpected error occurred",
                        "correlation_id": correlation_id,
                    }
                },
                headers={"X-Correlation-ID": correlation_id},
            )


def setup_enhanced_middlewares(app: ASGIApp):
    """
    Setup all enhanced middlewares.

    Args:
        app: FastAPI application
    """
    # Add middlewares in reverse order (last added is executed first)
    app.add_middleware(ErrorHandlingMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(CorrelationIDMiddleware)

    logger.info("Enhanced middlewares configured")
