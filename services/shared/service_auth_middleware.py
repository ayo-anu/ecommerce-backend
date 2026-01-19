"""Service-to-service auth middleware."""

import logging
import secrets
from typing import Optional, Set
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class ServiceAuthMiddleware(BaseHTTPMiddleware):
    """Validate internal service authentication."""

    def __init__(
        self,
        app: ASGIApp,
        settings,
        public_paths: Optional[Set[str]] = None,
    ):
        super().__init__(app)
        self.settings = settings
        self.service_auth_secret = settings.SERVICE_AUTH_SECRET
        self.service_name = settings.SERVICE_NAME

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
        """Validate service authentication before processing a request."""
        if request.url.path in self.public_paths:
            return await call_next(request)

        if request.method == "OPTIONS":
            return await call_next(request)

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

        request.state.authenticated_service = True
        request.state.service_name = self.service_name

        response = await call_next(request)

        return response


def verify_service_auth(request: Request) -> bool:
    """Check if request is service-authenticated."""
    return getattr(request.state, "authenticated_service", False)
