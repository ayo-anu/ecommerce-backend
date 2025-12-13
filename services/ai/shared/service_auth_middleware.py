"""
Service-to-Service Authentication Middleware

Zero-trust internal authentication:
- Validates X-Service-Auth header on all requests
- Rejects requests with missing or invalid service tokens
- Prevents service impersonation attacks
- Each service validates using its own SERVICE_AUTH_SECRET

Usage:
    from shared.service_auth_middleware import ServiceAuthMiddleware
    from shared.config import get_settings

    app = FastAPI()
    settings = get_settings()
    app.add_middleware(ServiceAuthMiddleware, settings=settings)
"""

import logging
import secrets
from typing import Optional, Set
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class ServiceAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate internal service-to-service authentication.

    Features:
    - Validates X-Service-Auth header against SERVICE_AUTH_SECRET
    - Rejects unauthenticated internal requests
    - Allows public health/metrics endpoints
    - Prevents timing attacks using constant-time comparison
    - Logs authentication failures for security monitoring
    """

    def __init__(
        self,
        app: ASGIApp,
        settings,
        public_paths: Optional[Set[str]] = None,
    ):
        """
        Initialize service authentication middleware.

        Args:
            app: ASGI application
            settings: Settings object with SERVICE_AUTH_SECRET
            public_paths: Set of paths that don't require auth (default: health/metrics)
        """
        super().__init__(app)
        self.settings = settings
        self.service_auth_secret = settings.SERVICE_AUTH_SECRET
        self.service_name = settings.SERVICE_NAME

        # Default public paths (no auth required)
        self.public_paths = public_paths or {
            "/",
            "/health",
            "/health/live",
            "/health/ready",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
        }

        # Validate configuration
        if not self.service_auth_secret:
            logger.error(
                f"SERVICE_AUTH_SECRET is not configured for {self.service_name}! "
                "Service authentication is DISABLED. This is a CRITICAL security issue."
            )
            raise ValueError(
                f"SERVICE_AUTH_SECRET must be configured for {self.service_name}"
            )

        logger.info(
            f"✅ Service authentication enabled for {self.service_name} "
            f"(secret configured: {bool(self.service_auth_secret)})"
        )

    async def dispatch(self, request: Request, call_next):
        """
        Validate service authentication before processing request.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler

        Returns:
            Response or JSONResponse with 401 error
        """
        # Allow public paths without authentication
        if request.url.path in self.public_paths:
            return await call_next(request)

        # Allow OPTIONS requests for CORS preflight
        if request.method == "OPTIONS":
            return await call_next(request)

        # Extract X-Service-Auth header
        service_auth_header = request.headers.get("X-Service-Auth")

        if not service_auth_header:
            logger.warning(
                f"Rejected request to {request.url.path}: Missing X-Service-Auth header",
                extra={
                    "client_ip": request.client.host if request.client else "unknown",
                    "path": request.url.path,
                    "method": request.method,
                },
            )
            return JSONResponse(
                status_code=401,
                content={
                    "error": {
                        "type": "authentication_required",
                        "message": "Missing service authentication header",
                        "detail": "X-Service-Auth header is required for internal service calls",
                    }
                },
            )

        # Validate service auth token using constant-time comparison
        # This prevents timing attacks
        if not secrets.compare_digest(service_auth_header, self.service_auth_secret):
            logger.warning(
                f"Rejected request to {request.url.path}: Invalid X-Service-Auth token",
                extra={
                    "client_ip": request.client.host if request.client else "unknown",
                    "path": request.url.path,
                    "method": request.method,
                    "service": self.service_name,
                },
            )
            return JSONResponse(
                status_code=401,
                content={
                    "error": {
                        "type": "authentication_failed",
                        "message": "Invalid service authentication token",
                        "detail": "The provided X-Service-Auth header is invalid",
                    }
                },
            )

        # Authentication successful - add service info to request state
        request.state.authenticated_service = True
        request.state.service_name = self.service_name

        # Process request
        response = await call_next(request)

        return response


def verify_service_auth(request: Request) -> bool:
    """
    Helper function to check if request is service-authenticated.

    Args:
        request: FastAPI request

    Returns:
        True if request has valid service authentication
    """
    return getattr(request.state, "authenticated_service", False)
