"""Gateway middleware."""
from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import time
import logging
from typing import Callable

from shared.config import get_settings
from shared.redis_client import redis_client
from shared.monitoring import (
    http_requests_total,
    http_request_duration_seconds
)

import uuid
class TraceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4()))
        request.state.trace_id = trace_id

        response = await call_next(request)
        response.headers["X-Trace-ID"] = trace_id
        return response


logger = logging.getLogger(__name__)
settings = get_settings()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting with Redis."""
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        if request.url.path in ["/health", "/metrics"]:
            return await call_next(request)
        
        client_ip = request.client.host
        identifier = client_ip
        rate_limit_key = f"rate_limit:{identifier}:{int(time.time() / 60)}"
        
        try:
            request_count = await redis_client.increment(rate_limit_key)
            
            if request_count == 1:
                await redis_client.expire(rate_limit_key, 60)
            
            if request_count > settings.RATE_LIMIT_PER_MINUTE:
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Rate limit exceeded. Try again later.",
                        "retry_after": 60
                    },
                    headers={"Retry-After": "60"}
                )
            
            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(settings.RATE_LIMIT_PER_MINUTE)
            response.headers["X-RateLimit-Remaining"] = str(
                settings.RATE_LIMIT_PER_MINUTE - request_count
            )
            response.headers["X-RateLimit-Reset"] = str(int(time.time() / 60) * 60 + 60)
            
            return response
            
        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            return await call_next(request)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Track request metrics."""
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        start_time = time.time()
        
        response = await call_next(request)
        
        duration = time.time() - start_time
        
        http_requests_total.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()
        
        http_request_duration_seconds.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)
        
        response.headers["X-Process-Time"] = str(duration)
        
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Request/response logging."""
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        logger.info(
            f"Request: {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "client_ip": request.client.host,
                "user_agent": request.headers.get("user-agent")
            }
        )
        
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            duration = time.time() - start_time
            logger.info(
                f"Response: {response.status_code} {request.url.path}",
                extra={
                    "status_code": response.status_code,
                    "duration": duration,
                    "path": request.url.path
                }
            )
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"Request failed: {request.url.path}",
                extra={
                    "error": str(e),
                    "duration": duration,
                    "path": request.url.path
                }
            )
            raise


def setup_cors(app):
    """Configure CORS middleware."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"]
    )


class WAFMiddleware(BaseHTTPMiddleware):
    """Web application firewall middleware."""

    def __init__(self, app, waf_instance):
        super().__init__(app)
        self.waf = waf_instance

    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        # Skip WAF for health checks and metrics
        if request.url.path in ["/health", "/health/live", "/health/ready", "/metrics"]:
            return await call_next(request)

        try:
            # Validate request
            await self.waf.validate_request(request)

            # Process request
            response = await call_next(request)

            # Add security headers to response
            from .waf import add_security_headers
            for header_name, header_value in add_security_headers({}).items():
                response.headers[header_name] = header_value

            return response

        except Exception as e:
            # WAF will raise HTTPException for malicious requests
            raise


def setup_middlewares(app):
    """Setup all middlewares"""
    # Initialize WAF
    from .waf import WAF
    waf = WAF(
        max_body_size=10 * 1024 * 1024,  # 10MB
        max_header_size=8 * 1024,  # 8KB
        enable_sql_injection_check=True,
        enable_xss_check=True,
        enable_path_traversal_check=True,
        enable_command_injection_check=True,
    )

    # Order matters! Applied in reverse order
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(WAFMiddleware, waf_instance=waf)  # WAF before rate limiting
    setup_cors(app)

    logger.info("Middlewares configured successfully (CORS, WAF, Rate Limiting, Metrics, Logging)")
