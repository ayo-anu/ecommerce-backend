"""Health checks for the recommendation service."""

from shared.health_check import (
    HealthChecker,
    check_redis_connection,
    check_model_loaded,
    create_liveness_check,
)
from shared.redis_client import redis_client


health_checker = HealthChecker(
    service_name="recommendation-engine",
    version="1.0.0"
)


def setup_health_checks(recommendation_models: dict):
    """Register health checks."""
    health_checker.add_check(
        "liveness",
        create_liveness_check(),
        critical=True,
        timeout=1.0
    )

    health_checker.add_check(
        "model",
        lambda: check_model_loaded(recommendation_models, 'hybrid'),
        critical=True,
        timeout=2.0
    )

    health_checker.add_check(
        "redis",
        lambda: check_redis_connection(redis_client),
        critical=False,  # Non-critical - service can work without cache
        timeout=3.0
    )


async def liveness():
    """Liveness probe."""
    return {
        "status": "ok",
        "service": "recommendation-engine",
    }


async def readiness():
    """Readiness probe."""
    result = await health_checker.check_health()

    status_code = 200 if result["status"] == "healthy" else 503

    return result, status_code
