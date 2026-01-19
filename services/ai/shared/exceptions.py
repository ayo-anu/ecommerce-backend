"""Exception handling for AI services."""

import logging
import traceback
from typing import Callable, Optional
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class ServiceException(Exception):
    """Base exception for service errors."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: Optional[str] = None,
        details: Optional[dict] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or "INTERNAL_ERROR"
        self.details = details or {}
        super().__init__(self.message)


class ModelNotFoundException(ServiceException):
    """Model file or resource not found."""

    def __init__(self, message: str = "Model not found", details: Optional[dict] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="MODEL_NOT_FOUND",
            details=details
        )


class ModelInferenceException(ServiceException):
    """Error during model inference."""

    def __init__(self, message: str = "Model inference failed", details: Optional[dict] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="INFERENCE_ERROR",
            details=details
        )


class InvalidInputException(ServiceException):
    """Invalid input data."""

    def __init__(self, message: str = "Invalid input", details: Optional[dict] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="INVALID_INPUT",
            details=details
        )


class ResourceNotFoundException(ServiceException):
    """Requested resource not found."""

    def __init__(self, message: str = "Resource not found", details: Optional[dict] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="RESOURCE_NOT_FOUND",
            details=details
        )


class ExternalServiceException(ServiceException):
    """External service (database, cache, etc.) error."""

    def __init__(self, message: str = "External service error", details: Optional[dict] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="EXTERNAL_SERVICE_ERROR",
            details=details
        )


class RateLimitException(ServiceException):
    """Rate limit exceeded."""

    def __init__(self, message: str = "Rate limit exceeded", details: Optional[dict] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RATE_LIMIT_EXCEEDED",
            details=details
        )


def create_error_response(
    error_code: str,
    message: str,
    status_code: int,
    details: Optional[dict] = None,
    request_id: Optional[str] = None
) -> JSONResponse:
    """Create a standardized error response."""
    content = {
        "error": {
            "code": error_code,
            "message": message,
            "status": status_code
        }
    }

    if details:
        content["error"]["details"] = details

    if request_id:
        content["error"]["request_id"] = request_id

    return JSONResponse(
        status_code=status_code,
        content=content
    )


def setup_exception_handlers(app):
    """Register global exception handlers."""

    @app.exception_handler(ServiceException)
    async def service_exception_handler(request: Request, exc: ServiceException):
        """Handle custom service exceptions."""
        request_id = request.headers.get("X-Request-ID")

        logger.error(
            f"Service exception: {exc.error_code} - {exc.message}",
            extra={
                "error_code": exc.error_code,
                "status_code": exc.status_code,
                "details": exc.details,
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method
            }
        )

        return create_error_response(
            error_code=exc.error_code,
            message=exc.message,
            status_code=exc.status_code,
            details=exc.details,
            request_id=request_id
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle FastAPI HTTP exceptions."""
        request_id = request.headers.get("X-Request-ID")

        logger.warning(
            f"HTTP exception: {exc.status_code} - {exc.detail}",
            extra={
                "status_code": exc.status_code,
                "detail": exc.detail,
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method
            }
        )

        return create_error_response(
            error_code=f"HTTP_{exc.status_code}",
            message=str(exc.detail),
            status_code=exc.status_code,
            request_id=request_id
        )

    @app.exception_handler(StarletteHTTPException)
    async def starlette_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle Starlette HTTP exceptions."""
        request_id = request.headers.get("X-Request-ID")

        logger.warning(
            f"Starlette exception: {exc.status_code} - {exc.detail}",
            extra={
                "status_code": exc.status_code,
                "detail": exc.detail,
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method
            }
        )

        return create_error_response(
            error_code=f"HTTP_{exc.status_code}",
            message=str(exc.detail),
            status_code=exc.status_code,
            request_id=request_id
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle Pydantic validation errors."""
        request_id = request.headers.get("X-Request-ID")

        errors = []
        for error in exc.errors():
            errors.append({
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"]
            })

        logger.warning(
            f"Validation error: {len(errors)} validation errors",
            extra={
                "validation_errors": errors,
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method
            }
        )

        return create_error_response(
            error_code="VALIDATION_ERROR",
            message="Request validation failed",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details={"validation_errors": errors},
            request_id=request_id
        )

    @app.exception_handler(ValidationError)
    async def pydantic_validation_exception_handler(request: Request, exc: ValidationError):
        """Handle Pydantic ValidationError."""
        request_id = request.headers.get("X-Request-ID")

        errors = []
        for error in exc.errors():
            errors.append({
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"]
            })

        logger.warning(
            f"Pydantic validation error: {len(errors)} validation errors",
            extra={
                "validation_errors": errors,
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method
            }
        )

        return create_error_response(
            error_code="VALIDATION_ERROR",
            message="Data validation failed",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details={"validation_errors": errors},
            request_id=request_id
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Handle all uncaught exceptions."""
        request_id = request.headers.get("X-Request-ID")

        logger.error(
            f"Unhandled exception: {type(exc).__name__} - {str(exc)}",
            extra={
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
                "traceback": traceback.format_exc()
            },
            exc_info=True
        )

        return create_error_response(
            error_code="INTERNAL_ERROR",
            message="An internal error occurred. Please try again later.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={
                "type": type(exc).__name__
            },
            request_id=request_id
        )

    logger.info("✅ Global exception handlers registered")


def handle_exceptions(
    error_message: str = "Operation failed",
    error_code: str = "OPERATION_ERROR",
    reraise: bool = False
):
    """Decorator for handling exceptions in service functions."""
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except ServiceException:
                raise
            except Exception as e:
                logger.error(
                    f"Exception in {func.__name__}: {str(e)}",
                    exc_info=True
                )
                if reraise:
                    raise
                raise ServiceException(
                    message=error_message,
                    error_code=error_code,
                    details={"original_error": str(e)}
                )
        return wrapper
    return decorator
