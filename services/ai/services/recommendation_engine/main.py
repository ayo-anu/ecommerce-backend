"""
Recommendation Engine Service - Main Application
"""
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from prometheus_client import make_asgi_app
import logging
import time
from shared.logger import setup_logging
from shared.monitoring import service_up, http_requests_total, http_request_duration_seconds
from shared.tracing import setup_tracing
from shared.config import get_settings
from shared.service_auth_middleware import ServiceAuthMiddleware
from routers import recommendations

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)
settings = get_settings()

# Global model instances (loaded on startup)
recommendation_models = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("🚀 Starting Recommendation Engine Service...")

    # Initialize models (in production, load from files)
    from .models.hybrid import HybridModel
    recommendation_models['hybrid'] = HybridModel()

    service_up.labels(service_name="recommendation_engine").set(1)
    logger.info("✅ Recommendation Engine Service started")

    yield

    # Shutdown
    service_up.labels(service_name="recommendation_engine").set(0)
    logger.info("Recommendation Engine Service shut down")


# Create FastAPI app
app = FastAPI(
    title="Recommendation Engine",
    description="AI-powered product recommendation service",
    version="1.0.0",
    lifespan=lifespan
)

# ============================================================
# ZERO-TRUST: Add service authentication middleware
# ============================================================
app.add_middleware(ServiceAuthMiddleware, settings=settings)
logger.info("✅ Service authentication middleware enabled (zero-trust)")

# Setup distributed tracing
tracer = setup_tracing(app, "recommendation-engine")

# Include routers
app.include_router(recommendations.router, prefix="/recommendations", tags=["recommendations"])
recommendations.recommendation_models = recommendation_models

# Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
logger.info("✅ Prometheus metrics exposed at /metrics")

# Middleware for request tracking
@app.middleware("http")
async def track_requests(request: Request, call_next):
    """Track request metrics"""
    start_time = time.time()

    # Process request
    response = await call_next(request)

    # Skip metrics endpoint from tracking to avoid recursion
    if not request.url.path.startswith("/metrics"):
        # Record metrics
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

    return response

@app.get("/")
async def root():
    return {
        "service": "Recommendation Engine",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "recommendation_engine",
        "models_loaded": len(recommendation_models)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
