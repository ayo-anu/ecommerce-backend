"""
Custom middleware for CORS, rate limiting, and logging
"""
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

logger = logging.getLogger(__name__)
settings = get_settings()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using Redis"""
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/metrics"]:
            return await call_next(request)
        
        # Get client identifier (IP or user ID)
        client_ip = request.client.host
        
        # Try to get user from token
        user_id = None
        auth_header = request.headers.get("Authorization")
        if auth_header:
            # Extract user_id from token if needed
            # For now, use IP
            pass
        
        # Rate limit key
        identifier = user_id if user_id else client_ip
        rate_limit_key = f"rate_limit:{identifier}:{int(time.time() / 60)}"
        
        try:
            # Increment request count
            request_count = await redis_client.increment(rate_limit_key)
            
            # Set expiration on first request
            if request_count == 1:
                await redis_client.expire(rate_limit_key, 60)
            
            # Check if rate limit exceeded
            if request_count > settings.RATE_LIMIT_PER_MINUTE:
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Rate limit exceeded. Try again later.",
                        "retry_after": 60
                    },
                    headers={"Retry-After": "60"}
                )
            
            # Add rate limit headers
            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(settings.RATE_LIMIT_PER_MINUTE)
            response.headers["X-RateLimit-Remaining"] = str(
                settings.RATE_LIMIT_PER_MINUTE - request_count
            )
            response.headers["X-RateLimit-Reset"] = str(int(time.time() / 60) * 60 + 60)
            
            return response
            
        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            # If Redis fails, allow request to proceed
            return await call_next(request)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to track request metrics"""
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Record metrics
        http_requests_total.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()
        
        http_request_duration_seconds.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)
        
        # Add custom headers
        response.headers["X-Process-Time"] = str(duration)
        
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging"""
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        # Log request
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
            
            # Log response
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
    """Configure CORS middleware"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"]
    )


def setup_middlewares(app):
    """Setup all middlewares"""
    # Order matters! Applied in reverse order
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(RateLimitMiddleware)
    setup_cors(app)
    
    logger.info("Middlewares configured successfully")
