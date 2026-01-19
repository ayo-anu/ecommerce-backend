"""
Demand Forecasting Service - Main Application
Time series forecasting and inventory optimization
Port: 8006
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from routers import forecasting
from shared.monitoring import setup_monitoring, service_up
from shared.logger import setup_logger
from shared.health import create_health_router
from shared.exceptions import setup_exception_handlers
from shared.validation import InputValidationMiddleware
from shared.config import get_settings
from shared.service_auth_middleware import ServiceAuthMiddleware

logger = setup_logger("demand_forecasting")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("📈 Demand Forecasting Service starting...")
    logger.info("  - Time series forecasting")
    logger.info("  - Seasonality & trend detection")
    logger.info("  - Inventory optimization")
    logger.info("  - Anomaly detection")

    # Mark service as up
    service_up.labels(service_name="demand_forecasting").set(1)
    logger.info("✅ Demand Forecasting Service ready on port 8006")

    yield

    # Shutdown
    logger.info("Demand Forecasting Service shutting down...")
    service_up.labels(service_name="demand_forecasting").set(0)


app = FastAPI(
    title="E-commerce Demand Forecasting",
    description="Time series forecasting and inventory optimization",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# ZERO-TRUST: Add service authentication middleware
# ============================================================
app.add_middleware(ServiceAuthMiddleware, settings=settings)
logger.info("✅ Service authentication middleware enabled (zero-trust)")

# Setup global exception handlers
setup_exception_handlers(app)
logger.info("✅ Exception handlers registered")

# Add input validation middleware
app.add_middleware(InputValidationMiddleware)
logger.info("✅ Input validation middleware enabled")

setup_monitoring(app, "demand_forecasting")

# Include standardized health checks
health_router = create_health_router(
    service_name="demand_forecasting",
    version="1.0.0",
    dependencies=["postgres"]
)
app.include_router(health_router)
logger.info("✅ Health checks enabled (/health, /health/live, /health/ready)")

app.include_router(forecasting.router)


@app.get("/")
async def root():
    return {
        "service": "demand_forecasting",
        "version": "1.0.0",
        "status": "running",
        "capabilities": [
            "time_series_forecasting",
            "seasonality_detection",
            "trend_analysis",
            "inventory_optimization",
            "promotional_impact",
            "anomaly_detection",
            "accuracy_evaluation"
        ],
        "methods": [
            "moving_average",
            "exponential_smoothing",
            "linear_regression",
            "seasonal_naive"
        ],
        "endpoints": {
            "forecast": "/forecast/demand",
            "seasonality": "/forecast/seasonality",
            "trend": "/forecast/trend",
            "optimize_inventory": "/forecast/inventory/optimize",
            "promotional_impact": "/forecast/promotional/impact",
            "anomalies": "/forecast/anomalies",
            "accuracy": "/forecast/accuracy",
            "stats": "/forecast/stats",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "demand_forecasting"}


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Demand Forecasting Service on port 8006...")
    uvicorn.run("main:app", host="0.0.0.0", port=8006, reload=True, log_level="info")
