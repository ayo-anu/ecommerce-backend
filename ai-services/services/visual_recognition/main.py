"""
Visual Recognition Service - Main Application
Computer vision for product images
Port: 8007 - THE FINAL SERVICE!
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from .routers import vision
from shared.monitoring import setup_monitoring, service_up
from shared.logger import setup_logger
from shared.health import create_health_router
from shared.exceptions import setup_exception_handlers
from shared.validation import InputValidationMiddleware
from shared.config import get_settings
from shared.service_auth_middleware import ServiceAuthMiddleware

logger = setup_logger("visual_recognition")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("🖼️  Visual Recognition Service starting - FINAL SERVICE!")
    logger.info("  - Image quality assessment")
    logger.info("  - Object detection")
    logger.info("  - Color extraction")
    logger.info("  - Category prediction")
    logger.info("  - Tag generation")
    logger.info("  - Scene understanding")

    # Mark service as up
    service_up.labels(service_name="visual_recognition").set(1)
    logger.info("✅ Visual Recognition Service ready on port 8007")
    logger.info("🎉 ALL AI SERVICES SECURED!")

    yield

    # Shutdown
    logger.info("Visual Recognition Service shutting down...")
    service_up.labels(service_name="visual_recognition").set(0)


app = FastAPI(
    title="E-commerce Visual Recognition",
    description="Computer vision for product image analysis",
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

setup_monitoring(app, "visual_recognition")

# Include standardized health checks
health_router = create_health_router(
    service_name="visual_recognition",
    version="1.0.0",
    dependencies=["postgres"]
)
app.include_router(health_router)
logger.info("✅ Health checks enabled (/health, /health/live, /health/ready)")

app.include_router(vision.router)


@app.get("/")
async def root():
    return {
        "service": "visual_recognition",
        "version": "1.0.0",
        "status": "running",
        "message": "🎉 FINAL SERVICE - PLATFORM COMPLETE!",
        "capabilities": [
            "image_analysis",
            "quality_assessment",
            "object_detection",
            "color_extraction",
            "category_prediction",
            "tag_generation",
            "scene_understanding",
            "image_comparison",
            "batch_processing"
        ],
        "endpoints": {
            "analyze": "/vision/analyze",
            "quality": "/vision/quality",
            "colors": "/vision/colors",
            "category": "/vision/category",
            "tags": "/vision/tags",
            "compare": "/vision/compare",
            "scene": "/vision/scene",
            "batch": "/vision/batch",
            "stats": "/vision/stats",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "visual_recognition",
        "message": "Platform 100% complete!"
    }


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Visual Recognition Service - THE FINAL SERVICE!")
    uvicorn.run("main:app", host="0.0.0.0", port=8007, reload=True, log_level="info")
