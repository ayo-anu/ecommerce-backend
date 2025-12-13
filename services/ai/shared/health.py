"""
Standardized Health Check Module for AI Microservices.

Provides consistent health check endpoints across all AI services.

Usage in FastAPI service:

    from shared.health import create_health_router

    app = FastAPI()
    app.include_router(create_health_router(
        service_name="recommendation-engine",
        version="1.0.0",
        dependencies=["postgres", "redis"]
    ))
"""

import time
import logging
from typing import List, Dict, Optional, Callable
from fastapi import APIRouter, Response, status
from pydantic import BaseModel
import psutil
import os

logger = logging.getLogger(__name__)


class HealthStatus(BaseModel):
    """Health check response model."""
    status: str  # "healthy", "degraded", "unhealthy"
    service: str
    version: str
    timestamp: float
    checks: Dict[str, Dict]
    system: Optional[Dict] = None


class LivenessResponse(BaseModel):
    """Liveness probe response."""
    status: str  # "alive"
    service: str


class ReadinessResponse(BaseModel):
    """Readiness probe response."""
    status: str  # "ready", "not_ready"
    service: str
    checks: Dict[str, bool]
    errors: Optional[List[str]] = None


def check_postgres(host: str = "postgres", port: int = 5432, timeout: int = 5) -> Dict:
    """Check PostgreSQL connection."""
    try:
        import psycopg2
        start = time.time()
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "postgres"),
            dbname=os.getenv("POSTGRES_DB", "ecommerce_ai"),
            connect_timeout=timeout
        )
        conn.close()
        latency = (time.time() - start) * 1000
        return {
            "status": "healthy",
            "latency_ms": round(latency, 2)
        }
    except Exception as e:
        logger.error(f"PostgreSQL health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


def check_redis(host: str = "redis", port: int = 6379, timeout: int = 5) -> Dict:
    """Check Redis connection."""
    try:
        import redis
        start = time.time()
        r = redis.Redis(
            host=host,
            port=port,
            password=os.getenv("REDIS_PASSWORD", None),
            socket_connect_timeout=timeout,
            socket_timeout=timeout
        )
        r.ping()
        latency = (time.time() - start) * 1000
        return {
            "status": "healthy",
            "latency_ms": round(latency, 2)
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


def check_elasticsearch(url: str = "http://elasticsearch:9200", timeout: int = 5) -> Dict:
    """Check Elasticsearch connection."""
    try:
        from elasticsearch import Elasticsearch
        start = time.time()
        es = Elasticsearch([url], timeout=timeout)
        if es.ping():
            latency = (time.time() - start) * 1000
            return {
                "status": "healthy",
                "latency_ms": round(latency, 2)
            }
        else:
            return {
                "status": "unhealthy",
                "error": "Ping failed"
            }
    except Exception as e:
        logger.error(f"Elasticsearch health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


def check_qdrant(url: str = "http://qdrant:6333", timeout: int = 5) -> Dict:
    """Check Qdrant vector database connection."""
    try:
        import httpx
        start = time.time()
        response = httpx.get(f"{url}/healthz", timeout=timeout)
        latency = (time.time() - start) * 1000
        if response.status_code == 200:
            return {
                "status": "healthy",
                "latency_ms": round(latency, 2)
            }
        else:
            return {
                "status": "unhealthy",
                "error": f"Status code: {response.status_code}"
            }
    except Exception as e:
        logger.error(f"Qdrant health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


def get_system_metrics() -> Dict:
    """Get system resource metrics."""
    try:
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
        }
    except Exception as e:
        logger.warning(f"Failed to get system metrics: {e}")
        return {}


def create_health_router(
    service_name: str,
    version: str = "1.0.0",
    dependencies: Optional[List[str]] = None,
    custom_checks: Optional[Dict[str, Callable]] = None
) -> APIRouter:
    """
    Create a health check router for a FastAPI service.

    Args:
        service_name: Name of the service (e.g., "recommendation-engine")
        version: Service version
        dependencies: List of dependencies to check ["postgres", "redis", "elasticsearch", "qdrant"]
        custom_checks: Dictionary of custom check functions {name: callable}

    Returns:
        FastAPI APIRouter with health check endpoints
    """
    router = APIRouter(tags=["health"])
    dependencies = dependencies or []
    custom_checks = custom_checks or {}

    # Map dependency names to check functions
    DEPENDENCY_CHECKS = {
        "postgres": check_postgres,
        "redis": check_redis,
        "elasticsearch": check_elasticsearch,
        "qdrant": check_qdrant,
    }

    @router.get("/health", response_model=HealthStatus, status_code=200)
    async def health():
        """
        Detailed health check endpoint.

        Returns comprehensive health information including:
        - Overall service status
        - Individual dependency checks with latency
        - System resource metrics
        """
        checks = {}
        overall_status = "healthy"

        # Check configured dependencies
        for dep in dependencies:
            check_func = DEPENDENCY_CHECKS.get(dep)
            if check_func:
                result = check_func()
                checks[dep] = result
                if result["status"] != "healthy":
                    overall_status = "degraded"

        # Run custom checks
        for check_name, check_func in custom_checks.items():
            try:
                result = check_func()
                checks[check_name] = result
                if result.get("status") != "healthy":
                    overall_status = "degraded"
            except Exception as e:
                checks[check_name] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                overall_status = "degraded"

        return HealthStatus(
            status=overall_status,
            service=service_name,
            version=version,
            timestamp=time.time(),
            checks=checks,
            system=get_system_metrics()
        )

    @router.get("/health/live", response_model=LivenessResponse, status_code=200)
    async def liveness():
        """
        Kubernetes liveness probe.

        Checks if the service process is alive.
        If this fails, Kubernetes will restart the pod.
        """
        return LivenessResponse(
            status="alive",
            service=service_name
        )

    @router.get("/health/ready", response_model=ReadinessResponse)
    async def readiness(response: Response):
        """
        Kubernetes readiness probe.

        Checks if the service is ready to accept traffic.
        If this fails, Kubernetes will stop routing traffic to the pod.
        """
        checks_status = {}
        errors = []
        all_ready = True

        # Check critical dependencies only
        critical_deps = [dep for dep in dependencies if dep in ["postgres", "redis"]]

        for dep in critical_deps:
            check_func = DEPENDENCY_CHECKS.get(dep)
            if check_func:
                result = check_func()
                is_healthy = result["status"] == "healthy"
                checks_status[dep] = is_healthy

                if not is_healthy:
                    all_ready = False
                    errors.append(f"{dep}: {result.get('error', 'unhealthy')}")

        if not all_ready:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

        return ReadinessResponse(
            status="ready" if all_ready else "not_ready",
            service=service_name,
            checks=checks_status,
            errors=errors if errors else None
        )

    return router
