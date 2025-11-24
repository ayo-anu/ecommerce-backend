"""
Fraud Detection Service - Main Application
Real-time transaction fraud detection and risk scoring
Port: 8003
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from .routers import fraud
from shared.monitoring import setup_monitoring
from shared.logger import setup_logger

# Setup logging
logger = setup_logger("fraud_detection")

# Create FastAPI app
app = FastAPI(
    title="E-commerce Fraud Detection",
    description="Real-time fraud detection using ML and rule-based systems",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup monitoring
setup_monitoring(app, "fraud_detection")

# Include routers
app.include_router(fraud.router)


@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    logger.info("🛡️ Fraud Detection Service starting up...")
    logger.info("Detection methods:")
    logger.info("  - ML-based anomaly detection (Isolation Forest)")
    logger.info("  - Rule-based expert system (10+ rules)")
    logger.info("  - Velocity checks")
    logger.info("  - Device fingerprinting")
    logger.info("  - Risk scoring & decision engine")
    logger.info("Service ready on port 8003")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Fraud Detection Service shutting down...")


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
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "service": "fraud_detection"
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
