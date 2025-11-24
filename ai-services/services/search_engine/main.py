"""
Search Engine Service - Main Application
Multi-modal product search: text, semantic, and visual
Port: 8002
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from .routers import search
from shared.monitoring import setup_monitoring
from shared.logger import setup_logger

# Setup logging
logger = setup_logger("search_engine")

# Create FastAPI app
app = FastAPI(
    title="E-commerce Search Engine",
    description="Multi-modal product search with text, semantic, and visual capabilities",
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
setup_monitoring(app, "search_engine")

# Include routers
app.include_router(search.router)


@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    logger.info("🔍 Search Engine Service starting up...")
    logger.info("Available search modes:")
    logger.info("  - Text search (keyword matching)")
    logger.info("  - Semantic search (intent understanding)")
    logger.info("  - Visual search (image similarity)")
    logger.info("  - Hybrid search (fusion of all modes)")
    logger.info("Service ready on port 8002")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Search Engine Service shutting down...")


@app.get("/")
async def root():
    """Root endpoint with service info"""
    return {
        "service": "search_engine",
        "version": "1.0.0",
        "status": "running",
        "features": [
            "text_search",
            "semantic_search",
            "visual_search",
            "hybrid_search",
            "autocomplete",
            "spell_correction",
            "filter_extraction"
        ],
        "endpoints": {
            "text_search": "/search/text",
            "semantic_search": "/search/semantic",
            "visual_search": "/search/visual",
            "hybrid_search": "/search/hybrid",
            "autocomplete": "/search/autocomplete",
            "stats": "/search/stats",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "service": "search_engine"
    }


if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting Search Engine Service on port 8002...")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8002,
        reload=True,
        log_level="info"
    )
