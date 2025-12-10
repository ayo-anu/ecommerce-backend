"""
Pricing Engine Service - Main Application
Dynamic pricing, discount optimization, and competitor analysis
Port: 8005
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from .routers import pricing
from shared.monitoring import setup_monitoring, service_up
from shared.logger import setup_logger
from shared.health import create_health_router
from shared.exceptions import setup_exception_handlers
from shared.validation import InputValidationMiddleware
from shared.config import get_settings
from shared.service_auth_middleware import ServiceAuthMiddleware

# Setup logging
logger = setup_logger("pricing_engine")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("💰 Pricing Engine Service starting up...")
    logger.info("Capabilities:")
    logger.info("  - Dynamic pricing algorithms")
    logger.info("  - Competitor price analysis")
    logger.info("  - Discount optimization")
    logger.info("  - Price elasticity calculation")
    logger.info("  - A/B testing for prices")
    logger.info("  - Revenue maximization")

    # Mark service as up
    service_up.labels(service_name="pricing_engine").set(1)
    logger.info("✅ Pricing Engine Service ready on port 8005")

    yield

    # Shutdown
    logger.info("Pricing Engine Service shutting down...")
    service_up.labels(service_name="pricing_engine").set(0)


# Create FastAPI app
app = FastAPI(
    title="E-commerce Pricing Engine",
    description="Intelligent dynamic pricing with competitor analysis and optimization",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
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

# Setup monitoring (adds /metrics endpoint)
setup_monitoring(app, "pricing_engine")

# Include standardized health checks
health_router = create_health_router(
    service_name="pricing_engine",
    version="1.0.0",
    dependencies=["redis", "postgres"]  # Pricing uses redis cache and postgres
)
app.include_router(health_router)
logger.info("✅ Health checks enabled (/health, /health/live, /health/ready)")

# Include routers
app.include_router(pricing.router)


@app.get("/")
async def root():
    """Root endpoint with service info"""
    return {
        "service": "pricing_engine",
        "version": "1.0.0",
        "status": "running",
        "capabilities": [
            "dynamic_pricing",
            "competitor_analysis",
            "discount_optimization",
            "price_elasticity",
            "ab_testing",
            "demand_prediction",
            "revenue_optimization",
            "margin_protection",
            "bulk_pricing"
        ],
        "strategies": [
            "cost_plus",
            "competitive",
            "dynamic",
            "penetration",
            "premium",
            "psychological"
        ],
        "endpoints": {
            "recommend": "/pricing/recommend",
            "bulk_recommend": "/pricing/recommend/bulk",
            "competitor_analysis": "/pricing/competitor/analyze",
            "discount_optimize": "/pricing/discount/optimize",
            "elasticity": "/pricing/elasticity",
            "ab_test": "/pricing/abtest/create",
            "simulate": "/pricing/simulate",
            "stats": "/pricing/stats",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "service": "pricing_engine"
    }


if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting Pricing Engine Service on port 8005...")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8005,
        reload=True,
        log_level="info"
    )
