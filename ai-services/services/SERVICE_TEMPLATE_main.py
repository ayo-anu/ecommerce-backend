"""
Template Main File for AI Microservices.

This template shows the standard structure for all AI services with:
- Standardized health checks
- Prometheus metrics
- Structured logging
- Request tracing

Copy this file and customize for your service.
"""

from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from prometheus_client import make_asgi_app
import logging

# Shared modules
from shared.health import create_health_router
from shared.logger import setup_logging
from shared.tracing import setup_tracing
from shared.monitoring import service_up, request_count, request_duration
from shared.exceptions import setup_exception_handlers
from shared.validation import InputValidationMiddleware

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("🚀 Starting [SERVICE_NAME]...")

    try:
        # Initialize dependencies here
        # e.g., database connections, ML model loading

        # Mark service as up
        service_up.labels(service_name="[SERVICE_NAME]").set(1)

        logger.info("✅ [SERVICE_NAME] started successfully")

    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down [SERVICE_NAME]...")
    service_up.labels(service_name="[SERVICE_NAME]").set(0)
    logger.info("[SERVICE_NAME] shut down")


# Create FastAPI app
app = FastAPI(
    title="[SERVICE_NAME]",
    description="[SERVICE_DESCRIPTION]",
    version="1.0.0",
    lifespan=lifespan
)

# Setup distributed tracing
tracer = setup_tracing(app, "[SERVICE_NAME]")

# Setup global exception handlers
setup_exception_handlers(app)
logger.info("✅ Exception handlers registered")

# Add input validation middleware
app.add_middleware(InputValidationMiddleware)
logger.info("✅ Input validation middleware enabled")

# Include standardized health checks
health_router = create_health_router(
    service_name="[SERVICE_NAME]",
    version="1.0.0",
    dependencies=["postgres", "redis"]  # Customize based on your dependencies
)
app.include_router(health_router)
logger.info("✅ Health checks enabled (/health, /health/live, /health/ready)")

# Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
logger.info("✅ Prometheus metrics exposed at /metrics")


# Middleware for request tracking
@app.middleware("http")
async def track_requests(request: Request, call_next):
    """Track request metrics"""
    import time
    start_time = time.time()

    # Process request
    response = await call_next(request)

    # Record metrics
    duration = time.time() - start_time
    request_count.labels(
        service="[SERVICE_NAME]",
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()

    request_duration.labels(
        service="[SERVICE_NAME]",
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)

    return response


# ==============================================================================
# API Endpoints
# ==============================================================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "[SERVICE_NAME]",
        "version": "1.0.0",
        "status": "operational"
    }


# Add your service-specific endpoints here
# Example:
#
# @app.post("/predict")
# async def predict(data: PredictionRequest):
#     """Make a prediction"""
#     # Your logic here
#     pass
