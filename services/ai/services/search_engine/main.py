"""
Search Engine Service - Main Application
Multi-modal product search: text, semantic, and visual
Port: 8002
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from .routers import search
from shared.monitoring import setup_monitoring, service_up
from shared.logger import setup_logger
from shared.health import create_health_router
from shared.exceptions import setup_exception_handlers
from shared.validation import InputValidationMiddleware
from shared.config import get_settings
from shared.service_auth_middleware import ServiceAuthMiddleware

# Setup logging
logger = setup_logger("search_engine")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("🔍 Search Engine Service starting up...")
    logger.info("Available search modes:")
    logger.info("  - Text search (keyword matching)")
    logger.info("  - Semantic search (intent understanding)")
    logger.info("  - Visual search (image similarity)")
    logger.info("  - Hybrid search (fusion of all modes)")

    # Mark service as up
    service_up.labels(service_name="search_engine").set(1)
    logger.info("✅ Search Engine Service ready on port 8002")

    yield

    # Shutdown
    logger.info("Search Engine Service shutting down...")
    service_up.labels(service_name="search_engine").set(0)


# Create FastAPI app
app = FastAPI(
    title="E-commerce Search Engine",
    description="Multi-modal product search with text, semantic, and visual capabilities",
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
setup_monitoring(app, "search_engine")

# Include standardized health checks
health_router = create_health_router(
    service_name="search_engine",
    version="1.0.0",
    dependencies=["elasticsearch", "postgres"]  # Search uses both ES and postgres
)
app.include_router(health_router)
logger.info("✅ Health checks enabled (/health, /health/live, /health/ready)")

# Include routers
app.include_router(search.router)


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
