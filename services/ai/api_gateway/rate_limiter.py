"""Rate limiting with Redis."""

import time
from typing import Optional
from fastapi import Request, HTTPException
from starlette.status import HTTP_429_TOO_MANY_REQUESTS
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self, redis_client):
        self.redis = redis_client

    async def check_rate_limit(
        self,
        identifier: str,
        limit_per_minute: int = 60,
        limit_per_hour: int = 1000,
    ) -> tuple[bool, dict]:
        """Check if a request should be rate limited."""
        current_time = int(time.time())

        minute_key = f"rate_limit:{identifier}:minute:{current_time // 60}"
        hour_key = f"rate_limit:{identifier}:hour:{current_time // 3600}"

        minute_count = await self.redis.increment(minute_key)
        hour_count = await self.redis.increment(hour_key)

        if minute_count == 1:
            await self.redis.expire(minute_key, 60)

        if hour_count == 1:
            await self.redis.expire(hour_key, 3600)

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
        """Check rate limit and raise if exceeded."""
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
    """Client identifier for rate limiting."""
    if hasattr(request.state, "user_id"):
        return f"user:{request.state.user_id}"

    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else "unknown"

    return f"ip:{client_ip}"


def get_endpoint_identifier(request: Request) -> str:
    """Endpoint identifier for rate limiting."""
    return f"{request.method}:{request.url.path}"
