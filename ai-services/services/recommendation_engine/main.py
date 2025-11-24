"""
Recommendation Engine Service - Main Application
"""
from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging
from shared.logger import setup_logging
from shared.monitoring import service_up
from .routers import recommendations

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

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

# Include routers
app.include_router(recommendations.router, prefix="/recommendations", tags=["recommendations"])
recommendations.recommendation_models = recommendation_models

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
