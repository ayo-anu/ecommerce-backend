"""
Enhanced Health Checks for Recommendation Engine Service

Provides comprehensive health monitoring including:
- Model availability
- Database connectivity
- Redis connectivity
- System resources
"""

from shared.health_check import (
    HealthChecker,
    check_redis_connection,
    check_model_loaded,
    create_liveness_check,
)
from shared.redis_client import redis_client


# Create health checker instance
health_checker = HealthChecker(
    service_name="recommendation-engine",
    version="1.0.0"
)


def setup_health_checks(recommendation_models: dict):
    """
    Setup health checks for the service.

    Args:
        recommendation_models: Dictionary of loaded models
    """
    # Liveness check - simple check that service is running
    health_checker.add_check(
        "liveness",
        create_liveness_check(),
        critical=True,
        timeout=1.0
    )

    # Model check - verify ML model is loaded
    health_checker.add_check(
        "model",
        lambda: check_model_loaded(recommendation_models, 'hybrid'),
        critical=True,
        timeout=2.0
    )

    # Redis check - verify cache connectivity
    health_checker.add_check(
        "redis",
        lambda: check_redis_connection(redis_client),
        critical=False,  # Non-critical - service can work without cache
        timeout=3.0
    )


# Liveness endpoint (simple, fast check for Kubernetes)
async def liveness():
    """
    Liveness probe - checks if service is alive.
    Used by Kubernetes to restart unhealthy pods.
    """
    return {
        "status": "ok",
        "service": "recommendation-engine",
    }


# Readiness endpoint (comprehensive check for Kubernetes)
async def readiness():
    """
    Readiness probe - checks if service is ready to serve traffic.
    Used by Kubernetes to route traffic to healthy pods.
    """
    result = await health_checker.check_health()

    # Return appropriate status code
    status_code = 200 if result["status"] == "healthy" else 503

    return result, status_code
