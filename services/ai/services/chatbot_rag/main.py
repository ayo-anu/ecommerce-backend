"""
Chatbot RAG Service - Main Application
Conversational AI with Retrieval-Augmented Generation
Port: 8004
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from routers import chat
from shared.monitoring import setup_monitoring, service_up
from shared.logger import setup_logger
from shared.health import create_health_router
from shared.exceptions import setup_exception_handlers
from shared.validation import InputValidationMiddleware
from shared.config import get_settings
from shared.service_auth_middleware import ServiceAuthMiddleware

# Setup logging
logger = setup_logger("chatbot_rag")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("🤖 Chatbot RAG Service starting up...")
    logger.info("Capabilities:")
    logger.info("  - Conversational AI with context")
    logger.info("  - Retrieval-Augmented Generation (RAG)")
    logger.info("  - Vector-based knowledge search")
    logger.info("  - Intent detection & classification")
    logger.info("  - Multi-turn conversations")
    logger.info("  - Product Q&A, order tracking, support")

    # Mark service as up
    service_up.labels(service_name="chatbot_rag").set(1)
    logger.info("✅ Chatbot RAG Service ready on port 8004")

    yield

    # Shutdown
    logger.info("Chatbot RAG Service shutting down...")
    service_up.labels(service_name="chatbot_rag").set(0)


# Create FastAPI app
app = FastAPI(
    title="E-commerce Chatbot with RAG",
    description="Intelligent conversational AI with knowledge retrieval for customer support",
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
setup_monitoring(app, "chatbot_rag")

# Include standardized health checks
health_router = create_health_router(
    service_name="chatbot_rag",
    version="1.0.0",
    dependencies=["qdrant", "postgres"]  # Chatbot uses Qdrant for vector DB
)
app.include_router(health_router)
logger.info("✅ Health checks enabled (/health, /health/live, /health/ready)")

# Include routers
app.include_router(chat.router)


@app.get("/")
async def root():
    """Root endpoint with service info"""
    return {
        "service": "chatbot_rag",
        "version": "1.0.0",
        "status": "running",
        "features": [
            "conversational_ai",
            "rag_knowledge_retrieval",
            "intent_detection",
            "multi_turn_conversations",
            "context_awareness",
            "semantic_search",
            "suggested_responses",
            "order_tracking",
            "product_qa"
        ],
        "supported_intents": [
            "product_inquiry",
            "order_status",
            "returns",
            "shipping",
            "payment",
            "general_question",
            "complaint",
            "recommendation"
        ],
        "endpoints": {
            "chat": "/chat/message",
            "new_conversation": "/chat/conversation/new",
            "history": "/chat/conversation/{id}/history",
            "index_knowledge": "/chat/knowledge/index",
            "search_knowledge": "/chat/knowledge/search",
            "stats": "/chat/stats",
            "feedback": "/chat/feedback",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "service": "chatbot_rag"
    }


if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting Chatbot RAG Service on port 8004...")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8004,
        reload=True,
        log_level="info"
    )
