"""
Visual Recognition Service - Main Application
Computer vision for product images
Port: 8007 - THE FINAL SERVICE!
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from .routers import vision
from shared.monitoring import setup_monitoring
from shared.logger import setup_logger

logger = setup_logger("visual_recognition")

app = FastAPI(
    title="E-commerce Visual Recognition",
    description="Computer vision for product image analysis",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

setup_monitoring(app, "visual_recognition")
app.include_router(vision.router)


@app.on_event("startup")
async def startup_event():
    logger.info("🖼️  Visual Recognition Service starting - FINAL SERVICE!")
    logger.info("  - Image quality assessment")
    logger.info("  - Object detection")
    logger.info("  - Color extraction")
    logger.info("  - Category prediction")
    logger.info("  - Tag generation")
    logger.info("  - Scene understanding")
    logger.info("Service ready on port 8007")
    logger.info("🎉 PLATFORM 100% COMPLETE!")


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
