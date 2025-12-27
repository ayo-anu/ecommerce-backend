"""
Fraud Detection Service - Main Application
Real-time transaction fraud detection and risk scoring
Port: 8003
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from routers import fraud
from shared.monitoring import setup_monitoring, service_up
from shared.logger import setup_logger
from shared.health import create_health_router
from shared.exceptions import setup_exception_handlers
from shared.validation import InputValidationMiddleware
from shared.config import get_settings
from shared.service_auth_middleware import ServiceAuthMiddleware

# Setup logging
logger = setup_logger("fraud_detection")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("🛡️ Fraud Detection Service starting up...")
    logger.info("Detection methods:")
    logger.info("  - ML-based anomaly detection (Isolation Forest)")
    logger.info("  - Rule-based expert system (10+ rules)")
    logger.info("  - Velocity checks")
    logger.info("  - Device fingerprinting")
    logger.info("  - Risk scoring & decision engine")

    # Mark service as up
    service_up.labels(service_name="fraud_detection").set(1)
    logger.info("✅ Fraud Detection Service ready on port 8003")

    yield

    # Shutdown
    logger.info("Fraud Detection Service shutting down...")
    service_up.labels(service_name="fraud_detection").set(0)


# Create FastAPI app
app = FastAPI(
    title="E-commerce Fraud Detection",
    description="Real-time fraud detection using ML and rule-based systems",
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
setup_monitoring(app, "fraud_detection")

# Include standardized health checks
health_router = create_health_router(
    service_name="fraud_detection",
    version="1.0.0",
    dependencies=["postgres"]  # Fraud service uses postgres for ML models
)
app.include_router(health_router)
logger.info("✅ Health checks enabled (/health, /health/live, /health/ready)")

# Include routers
app.include_router(fraud.router)


@app.get("/")
async def root():
    """Root endpoint with service info"""
    return {
        "service": "fraud_detection",
        "version": "1.0.0",
        "status": "running",
        "capabilities": [
            "real_time_fraud_detection",
            "ml_anomaly_detection",
            "rule_based_system",
            "velocity_checks",
            "device_fingerprinting",
            "risk_scoring",
            "batch_processing",
            "model_training"
        ],
        "risk_levels": ["low", "medium", "high", "critical"],
        "decisions": ["approve", "review", "decline"],
        "endpoints": {
            "analyze": "/fraud/analyze",
            "batch": "/fraud/analyze/batch",
            "train": "/fraud/train",
            "stats": "/fraud/stats",
            "rules": "/fraud/rules",
            "simulate": "/fraud/simulate",
            "health": "/health",
            "health_live": "/health/live",
            "health_ready": "/health/ready",
            "metrics": "/metrics",
            "docs": "/docs"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting Fraud Detection Service on port 8003...")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8003,
        reload=True,
        log_level="info"
    )
