"""
Rate Limiting Implementation

Provides request rate limiting using Redis.
Supports per-user, per-IP, and per-endpoint limits.
"""

import time
from typing import Optional
from fastapi import Request, HTTPException
from starlette.status import HTTP_429_TOO_MANY_REQUESTS
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter using Redis.

    Limits requests per minute and per hour.
    """

    def __init__(self, redis_client):
        """
        Initialize rate limiter.

        Args:
            redis_client: Redis client instance
        """
        self.redis = redis_client

    async def check_rate_limit(
        self,
        identifier: str,
        limit_per_minute: int = 60,
        limit_per_hour: int = 1000,
    ) -> tuple[bool, dict]:
        """
        Check if request should be rate limited.

        Args:
            identifier: Unique identifier (user_id, IP, etc.)
            limit_per_minute: Maximum requests per minute
            limit_per_hour: Maximum requests per hour

        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        current_time = int(time.time())

        # Keys for different time windows
        minute_key = f"rate_limit:{identifier}:minute:{current_time // 60}"
        hour_key = f"rate_limit:{identifier}:hour:{current_time // 3600}"

        # Increment counters
        minute_count = await self.redis.increment(minute_key)
        hour_count = await self.redis.increment(hour_key)

        # Set expiration on first request
        if minute_count == 1:
            await self.redis.expire(minute_key, 60)

        if hour_count == 1:
            await self.redis.expire(hour_key, 3600)

        # Check limits
        is_allowed = (
            minute_count <= limit_per_minute and hour_count <= limit_per_hour
        )

        rate_limit_info = {
            "limit_per_minute": limit_per_minute,
            "remaining_minute": max(0, limit_per_minute - minute_count),
            "limit_per_hour": limit_per_hour,
            "remaining_hour": max(0, limit_per_hour - hour_count),
            "reset_minute": ((current_time // 60) + 1) * 60,
            "reset_hour": ((current_time // 3600) + 1) * 3600,
        }

        return is_allowed, rate_limit_info

    async def check_and_raise(
        self,
        identifier: str,
        limit_per_minute: int = 60,
        limit_per_hour: int = 1000,
    ) -> dict:
        """
        Check rate limit and raise HTTPException if exceeded.

        Args:
            identifier: Unique identifier
            limit_per_minute: Max requests per minute
            limit_per_hour: Max requests per hour

        Returns:
            Rate limit info

        Raises:
            HTTPException: If rate limit exceeded
        """
        is_allowed, info = await self.check_rate_limit(
            identifier, limit_per_minute, limit_per_hour
        )

        if not is_allowed:
            logger.warning(
                f"Rate limit exceeded for {identifier}: "
                f"{info['remaining_minute']}/{limit_per_minute} minute, "
                f"{info['remaining_hour']}/{limit_per_hour} hour"
            )

            raise HTTPException(
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "limit_per_minute": limit_per_minute,
                    "limit_per_hour": limit_per_hour,
                    "retry_after": info["reset_minute"] - int(time.time()),
                },
                headers={
                    "X-RateLimit-Limit-Minute": str(limit_per_minute),
                    "X-RateLimit-Remaining-Minute": str(info["remaining_minute"]),
                    "X-RateLimit-Reset-Minute": str(info["reset_minute"]),
                    "X-RateLimit-Limit-Hour": str(limit_per_hour),
                    "X-RateLimit-Remaining-Hour": str(info["remaining_hour"]),
                    "X-RateLimit-Reset-Hour": str(info["reset_hour"]),
                    "Retry-After": str(info["reset_minute"] - int(time.time())),
                },
            )

        return info


async def get_client_identifier(request: Request) -> str:
    """
    Get client identifier for rate limiting.

    Uses user ID if authenticated, otherwise IP address.

    Args:
        request: FastAPI request

    Returns:
        Client identifier string
    """
    # Try to get user ID from request state (set by auth middleware)
    if hasattr(request.state, "user_id"):
        return f"user:{request.state.user_id}"

    # Fallback to IP address
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Get first IP from X-Forwarded-For header
        client_ip = forwarded_for.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else "unknown"

    return f"ip:{client_ip}"


def get_endpoint_identifier(request: Request) -> str:
    """
    Get endpoint identifier for rate limiting.

    Args:
        request: FastAPI request

    Returns:
        Endpoint identifier (path + method)
    """
    return f"{request.method}:{request.url.path}"
