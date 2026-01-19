"""
Chatbot RAG Schemas - Request/Response models
Conversational AI with knowledge retrieval
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    """Message role types"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class IntentType(str, Enum):
    """Detected user intent"""
    PRODUCT_INQUIRY = "product_inquiry"
    ORDER_STATUS = "order_status"
    RETURNS = "returns"
    SHIPPING = "shipping"
    PAYMENT = "payment"
    GENERAL_QUESTION = "general_question"
    COMPLAINT = "complaint"
    RECOMMENDATION = "recommendation"
    UNKNOWN = "unknown"


class Message(BaseModel):
    """Single conversation message"""
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = None


class ConversationHistory(BaseModel):
    """Full conversation context"""
    conversation_id: str
    messages: List[Message] = []
    user_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ChatRequest(BaseModel):
    """User chat message request"""
    message: str = Field(..., min_length=1, max_length=2000)
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional context (order_id, product_id, etc.)"
    )
    use_rag: bool = Field(default=True, description="Use knowledge retrieval")
    temperature: float = Field(default=0.7, ge=0, le=2)


class RetrievedDocument(BaseModel):
    """Document retrieved from knowledge base"""
    content: str
    source: str
    relevance_score: float = Field(..., ge=0, le=1)
    metadata: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """Chatbot response"""
    conversation_id: str
    message: str
    intent: IntentType
    confidence: float = Field(..., ge=0, le=1)
    
    # RAG-specific fields
    retrieved_documents: List[RetrievedDocument] = []
    sources_used: List[str] = []
    
    # Suggestions and follow-ups
    suggested_questions: List[str] = []
    suggested_actions: List[str] = []
    
    # Metadata
    processing_time_ms: float
    tokens_used: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class KnowledgeDocument(BaseModel):
    """Document to add to knowledge base"""
    content: str = Field(..., min_length=10)
    title: str
    category: str
    tags: List[str] = []
    metadata: Optional[Dict[str, Any]] = None
    source_url: Optional[str] = None


class KnowledgeIndexRequest(BaseModel):
    """Request to index documents"""
    documents: List[KnowledgeDocument]
    collection_name: str = "ecommerce_kb"


class KnowledgeSearchRequest(BaseModel):
    """Search knowledge base"""
    query: str
    top_k: int = Field(default=5, ge=1, le=20)
    category_filter: Optional[str] = None
    min_score: float = Field(default=0.5, ge=0, le=1)


class KnowledgeSearchResponse(BaseModel):
    """Knowledge search results"""
    query: str
    results: List[RetrievedDocument]
    total_found: int


class OrderStatusRequest(BaseModel):
    """Order status inquiry"""
    order_id: str
    user_id: Optional[str] = None


class OrderStatusResponse(BaseModel):
    """Order status information"""
    order_id: str
    status: str
    tracking_number: Optional[str] = None
    estimated_delivery: Optional[datetime] = None
    items: List[Dict[str, Any]] = []
    total_amount: float


class ProductQuestionRequest(BaseModel):
    """Product-specific question"""
    product_id: str
    question: str
    user_id: Optional[str] = None


class ProductQuestionResponse(BaseModel):
    """Answer to product question"""
    product_id: str
    question: str
    answer: str
    confidence: float
    sources: List[str] = []
    related_products: List[str] = []


class ConversationStatsResponse(BaseModel):
    """Chatbot statistics"""
    total_conversations: int
    total_messages: int
    avg_messages_per_conversation: float
    intent_distribution: Dict[str, int]
    avg_response_time_ms: float
    knowledge_base_size: int
    satisfaction_score: Optional[float] = None


class FeedbackRequest(BaseModel):
    """User feedback on response"""
    conversation_id: str
    message_id: Optional[str] = None
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None
    helpful: bool


class ChatbotConfig(BaseModel):
    """Chatbot configuration"""
    model_name: str = "gpt-3.5-turbo"
    temperature: float = 0.7
    max_tokens: int = 500
    use_rag: bool = True
    rag_top_k: int = 5
    rag_min_score: float = 0.5
    enable_intent_detection: bool = True
    enable_suggestions: bool = True
    system_prompt: Optional[str] = None


class HealthCheckResponse(BaseModel):
    """Service health status"""
    status: str
    knowledge_base_ready: bool
    conversations_active: int
    uptime_seconds: float
