"""Health checks for AI services."""

import time
import psutil
import logging
from typing import Dict, List, Any, Callable, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheck:
    """Individual health check."""
    name: str
    check_func: Callable
    critical: bool = True
    timeout: float = 5.0


@dataclass
class HealthCheckResult:
    """Result of a single health check."""
    name: str
    status: HealthStatus
    message: str
    duration_ms: float
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    details: Dict[str, Any] = field(default_factory=dict)


class HealthChecker:
    """Health checker for AI services."""

    def __init__(self, service_name: str, version: str = "1.0.0"):
        self.service_name = service_name
        self.version = version
        self.checks: List[HealthCheck] = []
        self.start_time = time.time()

    def add_check(
        self,
        name: str,
        check_func: Callable,
        critical: bool = True,
        timeout: float = 5.0
    ):
        self.checks.append(HealthCheck(
            name=name,
            check_func=check_func,
            critical=critical,
            timeout=timeout
        ))

    async def check_health(self) -> Dict[str, Any]:
        check_results = []
        overall_status = HealthStatus.HEALTHY

        for check in self.checks:
            result = await self._run_check(check)
            check_results.append(result)

            if result.status == HealthStatus.UNHEALTHY:
                if check.critical:
                    overall_status = HealthStatus.UNHEALTHY
                elif overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED

        system_metrics = self._get_system_metrics()

        uptime_seconds = time.time() - self.start_time

        return {
            "service": self.service_name,
            "version": self.version,
            "status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": round(uptime_seconds, 2),
            "checks": [
                {
                    "name": r.name,
                    "status": r.status.value,
                    "message": r.message,
                    "duration_ms": r.duration_ms,
                    "details": r.details,
                }
                for r in check_results
            ],
            "system": system_metrics,
        }

    async def _run_check(self, check: HealthCheck) -> HealthCheckResult:
        start_time = time.time()

        try:
            import asyncio

            if asyncio.iscoroutinefunction(check.check_func):
                result = await asyncio.wait_for(
                    check.check_func(),
                    timeout=check.timeout
                )
            else:
                result = check.check_func()

            duration_ms = (time.time() - start_time) * 1000

            if isinstance(result, dict):
                status = HealthStatus.HEALTHY if result.get('status') == 'ok' else HealthStatus.UNHEALTHY
                message = result.get('message', 'Check passed')
                details = result.get('details', {})
            elif result is True:
                status = HealthStatus.HEALTHY
                message = "Check passed"
                details = {}
            else:
                status = HealthStatus.UNHEALTHY
                message = "Check failed"
                details = {}

            return HealthCheckResult(
                name=check.name,
                status=status,
                message=message,
                duration_ms=round(duration_ms, 2),
                details=details,
            )

        except asyncio.TimeoutError:
            duration_ms = check.timeout * 1000
            return HealthCheckResult(
                name=check.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check timed out after {check.timeout}s",
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Health check '{check.name}' failed: {e}", exc_info=True)

            return HealthCheckResult(
                name=check.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check failed: {str(e)}",
                duration_ms=round(duration_ms, 2),
            )

    def _get_system_metrics(self) -> Dict[str, Any]:
        """Get system resource metrics."""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            return {
                "cpu_percent": round(cpu_percent, 2),
                "memory_percent": round(memory.percent, 2),
                "memory_used_mb": round(memory.used / 1024 / 1024, 2),
                "memory_total_mb": round(memory.total / 1024 / 1024, 2),
                "disk_percent": round(disk.percent, 2),
                "disk_used_gb": round(disk.used / 1024 / 1024 / 1024, 2),
                "disk_total_gb": round(disk.total / 1024 / 1024 / 1024, 2),
            }

        except Exception as e:
            logger.warning(f"Failed to get system metrics: {e}")
            return {}


async def check_redis_connection(redis_client) -> Dict[str, Any]:
    """Check Redis connectivity."""
    try:
        await redis_client.redis.ping()
        return {
            "status": "ok",
            "message": "Redis is reachable",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Redis connection failed: {str(e)}",
        }


async def check_postgres_connection(database) -> Dict[str, Any]:
    """Check PostgreSQL connectivity."""
    try:
        await database.execute("SELECT 1")
        return {
            "status": "ok",
            "message": "PostgreSQL is reachable",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"PostgreSQL connection failed: {str(e)}",
        }


async def check_vector_db_connection(vector_db_client) -> Dict[str, Any]:
    """Check vector DB connectivity."""
    try:
        vector_db_client.client.get_collections()
        return {
            "status": "ok",
            "message": "Vector DB is reachable",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Vector DB connection failed: {str(e)}",
        }


def check_model_loaded(model_dict: Dict, model_name: str) -> Dict[str, Any]:
    """Check if a model is loaded."""
    if model_name in model_dict and model_dict[model_name] is not None:
        return {
            "status": "ok",
            "message": f"Model '{model_name}' is loaded",
        }
    else:
        return {
            "status": "error",
            "message": f"Model '{model_name}' is not loaded",
        }


def create_readiness_check(dependencies: List[str]) -> Callable:
    """Create a readiness check for dependencies."""
    def check() -> Dict[str, Any]:
        return {
            "status": "ok",
            "message": "Service is ready",
            "details": {"dependencies": dependencies},
        }
    return check


def create_liveness_check() -> Callable:
    """Create a simple liveness check."""
    def check() -> Dict[str, Any]:
        return {
            "status": "ok",
            "message": "Service is alive",
        }
    return check
