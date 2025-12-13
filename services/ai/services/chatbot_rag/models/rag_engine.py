"""
RAG Chatbot Engine - Main orchestrator
Combines knowledge retrieval with response generation
"""
import logging
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import time

from ..schemas.chat import (
    IntentType, MessageRole, RetrievedDocument
)
from ..knowledge_base.vector_store import VectorKnowledgeBase, EcommerceKnowledgeBase
from .conversation_manager import ConversationManager, ContextExtractor
from .intent_classifier import IntentClassifier

logger = logging.getLogger(__name__)


class RAGChatbot:
    """
    Retrieval-Augmented Generation Chatbot
    
    Combines vector search with response generation for accurate answers
    """
    
    def __init__(
        self,
        knowledge_base: Optional[VectorKnowledgeBase] = None,
        use_default_kb: bool = True
    ):
        """
        Initialize RAG chatbot
        
        Args:
            knowledge_base: Optional pre-initialized knowledge base
            use_default_kb: Load default e-commerce knowledge
        """
        # Initialize components
        self.knowledge_base = knowledge_base or VectorKnowledgeBase()
        self.conversation_manager = ConversationManager()
        self.intent_classifier = IntentClassifier()
        self.context_extractor = ContextExtractor()
        
        # Load default knowledge base
        if use_default_kb:
            self._load_default_knowledge()
        
        # Statistics
        self.stats = {
            'total_queries': 0,
            'rag_queries': 0,
            'total_response_time': 0.0
        }
        
        logger.info("RAG Chatbot initialized")
    
    def _load_default_knowledge(self):
        """Load default e-commerce knowledge"""
        default_docs = EcommerceKnowledgeBase.get_default_documents()
        self.knowledge_base.add_documents(default_docs)
        logger.info(f"Loaded {len(default_docs)} default knowledge documents")
    
    def chat(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        use_rag: bool = True,
        context: Optional[Dict] = None
    ) -> Dict:
        """
        Process chat message and generate response
        
        Args:
            message: User message
            conversation_id: Optional conversation ID
            user_id: Optional user ID
            use_rag: Whether to use RAG
            context: Additional context
            
        Returns:
            Response dictionary
        """
        start_time = time.time()
        
        # Create or get conversation
        if not conversation_id:
            conversation_id = self.conversation_manager.create_conversation(user_id)
        elif not self.conversation_manager.get_conversation(conversation_id):
            logger.warning(f"Conversation {conversation_id} not found, creating new")
            conversation_id = self.conversation_manager.create_conversation(user_id)
        
        # Classify intent
        intent, intent_confidence = self.intent_classifier.classify(message)
        
        # Extract entities
        entities = self.intent_classifier.extract_entities(message, intent)
        
        # Check urgency
        is_urgent = self.intent_classifier.is_urgent(message, intent)
        
        # Add user message to history
        self.conversation_manager.add_message(
            conversation_id,
            MessageRole.USER,
            message,
            metadata={'intent': intent.value, 'entities': entities, 'urgent': is_urgent}
        )
        
        # Retrieve relevant knowledge
        retrieved_docs = []
        if use_rag:
            retrieved_docs = self._retrieve_knowledge(message, intent)
        
        # Generate response
        response_text = self._generate_response(
            message=message,
            intent=intent,
            retrieved_docs=retrieved_docs,
            conversation_id=conversation_id,
            entities=entities,
            context=context
        )
        
        # Add assistant response to history
        self.conversation_manager.add_message(
            conversation_id,
            MessageRole.ASSISTANT,
            response_text,
            metadata={'intent': intent.value, 'sources_used': len(retrieved_docs)}
        )
        
        # Get suggested follow-ups
        suggested_questions = self.intent_classifier.get_suggested_followups(intent)
        
        # Calculate response time
        processing_time = (time.time() - start_time) * 1000
        
        # Update statistics
        self.stats['total_queries'] += 1
        if use_rag:
            self.stats['rag_queries'] += 1
        self.stats['total_response_time'] += processing_time
        
        return {
            'conversation_id': conversation_id,
            'message': response_text,
            'intent': intent,
            'confidence': intent_confidence,
            'retrieved_documents': [
                RetrievedDocument(**doc) for doc in retrieved_docs
            ],
            'sources_used': [doc['source'] for doc in retrieved_docs],
            'suggested_questions': suggested_questions[:3],  # Top 3
            'suggested_actions': self._get_suggested_actions(intent, entities),
            'processing_time_ms': round(processing_time, 2),
            'is_urgent': is_urgent
        }
    
    def _retrieve_knowledge(
        self,
        query: str,
        intent: IntentType,
        top_k: int = 3
    ) -> List[Dict]:
        """
        Retrieve relevant knowledge from vector store
        
        Args:
            query: User query
            intent: Detected intent
            top_k: Number of documents to retrieve
            
        Returns:
            List of retrieved documents
        """
        # Map intent to category filter
        category_mapping = {
            IntentType.SHIPPING: 'shipping',
            IntentType.RETURNS: 'returns',
            IntentType.PAYMENT: 'payment',
            IntentType.ORDER_STATUS: 'orders',
            IntentType.PRODUCT_INQUIRY: 'products'
        }
        
        category_filter = category_mapping.get(intent)
        
        # Search knowledge base
        results = self.knowledge_base.search(
            query=query,
            top_k=top_k,
            category_filter=category_filter,
            min_score=0.5
        )
        
        logger.info(f"Retrieved {len(results)} documents for query: {query[:50]}...")
        return results
    
    def _generate_response(
        self,
        message: str,
        intent: IntentType,
        retrieved_docs: List[Dict],
        conversation_id: str,
        entities: Dict,
        context: Optional[Dict]
    ) -> str:
        """
        Generate response using retrieved knowledge
        
        This is a template-based generator. In production, would use LLM API.
        
        Args:
            message: User message
            intent: Detected intent
            retrieved_docs: Retrieved knowledge documents
            conversation_id: Conversation ID
            entities: Extracted entities
            context: Additional context
            
        Returns:
            Generated response text
        """
        # Get conversation history for context
        history = self.conversation_manager.get_history(conversation_id, last_n=3)
        
        # Build context from retrieved documents
        knowledge_context = "\n".join([
            doc['content'] for doc in retrieved_docs[:2]
        ])
        
        # Generate response based on intent
        if intent == IntentType.ORDER_STATUS:
            return self._handle_order_status(entities, knowledge_context)
        
        elif intent == IntentType.RETURNS:
            return self._handle_returns(message, knowledge_context)
        
        elif intent == IntentType.SHIPPING:
            return self._handle_shipping(message, knowledge_context)
        
        elif intent == IntentType.PAYMENT:
            return self._handle_payment(message, knowledge_context)
        
        elif intent == IntentType.PRODUCT_INQUIRY:
            return self._handle_product_inquiry(message, knowledge_context, entities)
        
        elif intent == IntentType.COMPLAINT:
            return self._handle_complaint(message)
        
        elif intent == IntentType.RECOMMENDATION:
            return self._handle_recommendation(message)
        
        else:  # GENERAL_QUESTION or UNKNOWN
            return self._handle_general(message, knowledge_context)
    
    def _handle_order_status(self, entities: Dict, context: str) -> str:
        """Handle order status inquiries"""
        order_id = entities.get('order_id')
        
        if order_id:
            # In production, would query order database
            return (
                f"I'd be happy to help you check on order #{order_id}. "
                f"Let me look that up for you. Based on our records, your order is currently being processed. "
                f"You should receive a tracking number within 24 hours via email. "
                f"\n\nFor more details: {context[:200] if context else 'Please check your email for updates.'}"
            )
        else:
            return (
                "I can help you track your order! To look up your order status, I'll need your order number. "
                "You can find it in your order confirmation email. It usually starts with 'ORDER-' followed by numbers."
            )
    
    def _handle_returns(self, message: str, context: str) -> str:
        """Handle return requests"""
        if context:
            return (
                f"I can help you with returns. Here's our policy:\n\n{context}\n\n"
                "Would you like me to help you start a return? I'll need your order number to proceed."
            )
        else:
            return (
                "We accept returns within 30 days of purchase. Items must be unused and in original packaging. "
                "To start a return, please provide your order number and I'll guide you through the process."
            )
    
    def _handle_shipping(self, message: str, context: str) -> str:
        """Handle shipping inquiries"""
        if context:
            return f"Here's information about our shipping:\n\n{context}\n\nIs there anything specific you'd like to know about shipping?"
        else:
            return (
                "We offer multiple shipping options:\n"
                "- Free standard shipping on orders over $50 (5-7 business days)\n"
                "- Express shipping for $15 (2-3 business days)\n"
                "- International shipping available\n\n"
                "What would you like to know more about?"
            )
    
    def _handle_payment(self, message: str, context: str) -> str:
        """Handle payment inquiries"""
        if 'promo' in message.lower() or 'discount' in message.lower() or 'code' in message.lower():
            return (
                "For current promo codes and discounts, please check:\n"
                "- Our homepage banner for active promotions\n"
                "- Your email for personalized offers\n"
                "- Our newsletter for exclusive codes\n\n"
                "Is there anything else I can help you with?"
            )
        
        if context:
            return f"Here's information about payments:\n\n{context}\n\nDo you have any specific questions about payment?"
        else:
            return (
                "We accept all major credit cards, PayPal, Apple Pay, and Google Pay. "
                "All transactions are secured with SSL encryption. "
                "Your payment information is never stored on our servers."
            )
    
    def _handle_product_inquiry(self, message: str, context: str, entities: Dict) -> str:
        """Handle product questions"""
        product_mention = entities.get('product_mention')
        
        base_response = (
            f"I'd be happy to help you learn more about " +
            (f"{' '.join(product_mention)}!" if product_mention else "our products!")
        )
        
        if context:
            return f"{base_response}\n\n{context}\n\nWould you like me to check availability or specifications?"
        else:
            return (
                f"{base_response} "
                "To give you the most accurate information, could you tell me:\n"
                "- The specific product name or ID?\n"
                "- What information you're looking for (size, color, specs, availability)?"
            )
    
    def _handle_complaint(self, message: str) -> str:
        """Handle customer complaints"""
        return (
            "I'm very sorry to hear you're experiencing an issue. I want to make this right for you. "
            "Can you please provide more details about the problem?\n\n"
            "- Your order number\n"
            "- What happened\n"
            "- How you'd like this resolved\n\n"
            "I'll escalate this to our support team to ensure it's handled promptly. "
            "You can also reach our customer service directly at support@example.com or 1-800-123-4567."
        )
    
    def _handle_recommendation(self, message: str) -> str:
        """Handle recommendation requests"""
        return (
            "I'd be happy to recommend products! To give you the best suggestions, could you tell me:\n\n"
            "- What type of product are you looking for?\n"
            "- Your budget range?\n"
            "- Any specific features or preferences?\n\n"
            "You can also check out our:\n"
            "- Best Sellers section\n"
            "- New Arrivals\n"
            "- Customer Favorites"
        )
    
    def _handle_general(self, message: str, context: str) -> str:
        """Handle general questions"""
        if context:
            return f"Based on your question, here's what I found:\n\n{context}\n\nDoes this answer your question?"
        else:
            return (
                "I'm here to help! I can assist you with:\n"
                "- Order tracking and status\n"
                "- Product information\n"
                "- Shipping and delivery\n"
                "- Returns and refunds\n"
                "- Payment questions\n\n"
                "What would you like to know more about?"
            )
    
    def _get_suggested_actions(self, intent: IntentType, entities: Dict) -> List[str]:
        """Get suggested actions based on intent"""
        actions = {
            IntentType.ORDER_STATUS: ["Track Order", "Contact Support", "View Order History"],
            IntentType.RETURNS: ["Start Return", "Check Return Policy", "Contact Support"],
            IntentType.SHIPPING: ["View Shipping Options", "Track Package", "Estimate Delivery"],
            IntentType.PAYMENT: ["Update Payment Method", "Apply Promo Code", "View Billing"],
            IntentType.PRODUCT_INQUIRY: ["View Product Details", "Check Availability", "Add to Cart"],
            IntentType.COMPLAINT: ["Contact Manager", "File Complaint", "Request Callback"],
            IntentType.RECOMMENDATION: ["Browse Best Sellers", "View New Arrivals", "Get Personalized Picks"]
        }
        
        return actions.get(intent, ["Browse Products", "Contact Support", "View FAQs"])
    
    def add_knowledge(self, documents: List[Dict]) -> int:
        """Add documents to knowledge base"""
        return self.knowledge_base.add_documents(documents)
    
    def get_stats(self) -> Dict:
        """Get chatbot statistics"""
        conv_stats = self.conversation_manager.get_stats()
        kb_stats = self.knowledge_base.get_stats()
        
        avg_response_time = (
            self.stats['total_response_time'] / self.stats['total_queries']
            if self.stats['total_queries'] > 0 else 0
        )
        
        return {
            **conv_stats,
            'knowledge_base_size': kb_stats['total_documents'],
            'total_queries': self.stats['total_queries'],
            'rag_queries': self.stats['rag_queries'],
            'avg_response_time_ms': round(avg_response_time, 2)
        }
