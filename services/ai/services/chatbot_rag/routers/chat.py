"""
Chatbot RAG API Router - Conversational AI endpoints
Handles chat, knowledge management, and statistics
"""
from fastapi import APIRouter, HTTPException
from typing import Optional
import logging

from ..schemas.chat import (
    ChatRequest,
    ChatResponse,
    KnowledgeIndexRequest,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    ConversationStatsResponse,
    FeedbackRequest,
    RetrievedDocument
)
from ..models.rag_engine import RAGChatbot

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chatbot"])

# Global chatbot instance
chatbot = RAGChatbot(use_default_kb=True)


@router.post("/message", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """
    Send message to chatbot and get response
    
    Supports:
    - Conversational context
    - RAG-based knowledge retrieval
    - Intent detection
    - Suggested follow-ups
    """
    try:
        result = chatbot.chat(
            message=request.message,
            conversation_id=request.conversation_id,
            user_id=request.user_id,
            use_rag=request.use_rag,
            context=request.context
        )
        
        response = ChatResponse(
            conversation_id=result['conversation_id'],
            message=result['message'],
            intent=result['intent'],
            confidence=result['confidence'],
            retrieved_documents=result['retrieved_documents'],
            sources_used=result['sources_used'],
            suggested_questions=result['suggested_questions'],
            suggested_actions=result['suggested_actions'],
            processing_time_ms=result['processing_time_ms']
        )
        
        logger.info(
            f"Chat response generated: intent={result['intent']}, "
            f"confidence={result['confidence']:.2f}"
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conversation/new")
async def create_conversation(user_id: Optional[str] = None):
    """
    Create new conversation session
    
    Returns:
        conversation_id for subsequent messages
    """
    try:
        conversation_id = chatbot.conversation_manager.create_conversation(user_id)
        
        return {
            "conversation_id": conversation_id,
            "status": "created",
            "message": "New conversation started"
        }
        
    except Exception as e:
        logger.error(f"Conversation creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversation/{conversation_id}/history")
async def get_conversation_history(conversation_id: str, last_n: Optional[int] = None):
    """
    Get conversation history
    
    Args:
        conversation_id: Conversation identifier
        last_n: Get only last N messages
    """
    try:
        history = chatbot.conversation_manager.get_history(conversation_id, last_n)
        
        if not history:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return {
            "conversation_id": conversation_id,
            "messages": [
                {
                    "role": msg.role.value,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat()
                }
                for msg in history
            ],
            "total_messages": len(history)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"History retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/conversation/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete conversation and its history"""
    try:
        chatbot.conversation_manager.clear_conversation(conversation_id)
        
        return {
            "conversation_id": conversation_id,
            "status": "deleted",
            "message": "Conversation cleared"
        }
        
    except Exception as e:
        logger.error(f"Conversation deletion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge/index", status_code=200)
async def index_knowledge(request: KnowledgeIndexRequest):
    """
    Add documents to knowledge base
    
    Documents are indexed for semantic search
    """
    try:
        documents = [doc.dict() for doc in request.documents]
        count = chatbot.add_knowledge(documents)
        
        logger.info(f"Indexed {count} documents to knowledge base")
        
        return {
            "status": "success",
            "documents_indexed": count,
            "total_documents": chatbot.knowledge_base.get_stats()['total_documents'],
            "collection": request.collection_name
        }
        
    except Exception as e:
        logger.error(f"Knowledge indexing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge/search", response_model=KnowledgeSearchResponse)
async def search_knowledge(request: KnowledgeSearchRequest):
    """
    Search knowledge base directly
    
    Useful for testing or direct knowledge retrieval
    """
    try:
        results = chatbot.knowledge_base.search(
            query=request.query,
            top_k=request.top_k,
            category_filter=request.category_filter,
            min_score=request.min_score
        )
        
        retrieved = [
            RetrievedDocument(**doc) for doc in results
        ]
        
        return KnowledgeSearchResponse(
            query=request.query,
            results=retrieved,
            total_found=len(retrieved)
        )
        
    except Exception as e:
        logger.error(f"Knowledge search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge/categories")
async def get_knowledge_categories():
    """Get all available knowledge categories"""
    try:
        categories = chatbot.knowledge_base.get_categories()
        stats = chatbot.knowledge_base.get_stats()
        
        return {
            "categories": categories,
            "category_stats": stats['categories']
        }
        
    except Exception as e:
        logger.error(f"Categories error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=ConversationStatsResponse)
async def get_stats():
    """
    Get chatbot statistics
    
    Returns metrics about usage and performance
    """
    try:
        stats = chatbot.get_stats()
        kb_stats = chatbot.knowledge_base.get_stats()
        
        # Calculate intent distribution (would need tracking in production)
        intent_distribution = {
            "product_inquiry": 0,
            "order_status": 0,
            "shipping": 0,
            "returns": 0,
            "general": 0
        }
        
        return ConversationStatsResponse(
            total_conversations=stats['total_conversations'],
            total_messages=stats['total_messages'],
            avg_messages_per_conversation=stats['avg_messages_per_conversation'],
            intent_distribution=intent_distribution,
            avg_response_time_ms=stats['avg_response_time_ms'],
            knowledge_base_size=kb_stats['total_documents'],
            satisfaction_score=None  # Would track from feedback
        )
        
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feedback", status_code=200)
async def submit_feedback(request: FeedbackRequest):
    """
    Submit feedback on chatbot response
    
    Helps improve response quality
    """
    try:
        # In production, would store feedback in database
        logger.info(
            f"Feedback received: conversation={request.conversation_id}, "
            f"rating={request.rating}, helpful={request.helpful}"
        )
        
        return {
            "status": "received",
            "message": "Thank you for your feedback!",
            "conversation_id": request.conversation_id
        }
        
    except Exception as e:
        logger.error(f"Feedback error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup")
async def cleanup_sessions():
    """
    Clean up expired conversation sessions
    
    Removes sessions that have been inactive
    """
    try:
        removed = chatbot.conversation_manager.cleanup_expired_sessions()
        
        return {
            "status": "complete",
            "sessions_removed": removed,
            "active_sessions": len(chatbot.conversation_manager.conversations)
        }
        
    except Exception as e:
        logger.error(f"Cleanup error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/intents")
async def get_available_intents():
    """
    Get list of available intents
    
    Useful for understanding chatbot capabilities
    """
    from ..schemas.chat import IntentType
    
    return {
        "intents": [intent.value for intent in IntentType],
        "descriptions": {
            "product_inquiry": "Questions about products, specifications, availability",
            "order_status": "Track orders, delivery status, shipping updates",
            "returns": "Return policy, refund requests, exchanges",
            "shipping": "Shipping options, delivery times, international shipping",
            "payment": "Payment methods, promo codes, billing questions",
            "general_question": "General inquiries and information",
            "complaint": "Issues, problems, complaints about products or service",
            "recommendation": "Product recommendations and suggestions"
        }
    }


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    kb_stats = chatbot.knowledge_base.get_stats()
    
    return {
        "status": "healthy",
        "service": "chatbot_rag",
        "knowledge_base_ready": kb_stats['total_documents'] > 0,
        "active_conversations": len(chatbot.conversation_manager.conversations)
    }
