"""
Chatbot RAG Service - Main Application
Conversational AI with Retrieval-Augmented Generation
Port: 8004
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from .routers import chat
from shared.monitoring import setup_monitoring
from shared.logger import setup_logger

# Setup logging
logger = setup_logger("chatbot_rag")

# Create FastAPI app
app = FastAPI(
    title="E-commerce Chatbot with RAG",
    description="Intelligent conversational AI with knowledge retrieval for customer support",
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
setup_monitoring(app, "chatbot_rag")

# Include routers
app.include_router(chat.router)


@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    logger.info("🤖 Chatbot RAG Service starting up...")
    logger.info("Capabilities:")
    logger.info("  - Conversational AI with context")
    logger.info("  - Retrieval-Augmented Generation (RAG)")
    logger.info("  - Vector-based knowledge search")
    logger.info("  - Intent detection & classification")
    logger.info("  - Multi-turn conversations")
    logger.info("  - Product Q&A, order tracking, support")
    logger.info("Service ready on port 8004")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Chatbot RAG Service shutting down...")


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
