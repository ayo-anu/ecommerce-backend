"""
Conversation Manager - Handle chat sessions and context
Maintains conversation history and state
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import uuid
import logging
from collections import defaultdict

from ..schemas.chat import Message, ConversationHistory, MessageRole

logger = logging.getLogger(__name__)


class ConversationManager:
    """
    Manage conversation sessions and history
    
    In production, this would use Redis or a database
    """
    
    def __init__(self, max_history_length: int = 20, session_timeout_minutes: int = 30):
        """
        Initialize conversation manager
        
        Args:
            max_history_length: Max messages to keep per conversation
            session_timeout_minutes: Minutes before session expires
        """
        self.conversations: Dict[str, ConversationHistory] = {}
        self.max_history_length = max_history_length
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        self.stats = defaultdict(int)
        
        logger.info(
            f"Conversation manager initialized "
            f"(max_history={max_history_length}, timeout={session_timeout_minutes}m)"
        )
    
    def create_conversation(self, user_id: Optional[str] = None) -> str:
        """
        Create new conversation session
        
        Returns:
            conversation_id
        """
        conversation_id = str(uuid.uuid4())
        
        self.conversations[conversation_id] = ConversationHistory(
            conversation_id=conversation_id,
            user_id=user_id,
            messages=[]
        )
        
        self.stats['total_conversations'] += 1
        logger.info(f"Created conversation {conversation_id}")
        
        return conversation_id
    
    def get_conversation(self, conversation_id: str) -> Optional[ConversationHistory]:
        """Get conversation by ID"""
        conversation = self.conversations.get(conversation_id)
        
        if conversation:
            # Check if session expired
            time_since_update = datetime.utcnow() - conversation.updated_at
            if time_since_update > self.session_timeout:
                logger.info(f"Conversation {conversation_id} expired")
                del self.conversations[conversation_id]
                return None
        
        return conversation
    
    def add_message(
        self,
        conversation_id: str,
        role: MessageRole,
        content: str,
        metadata: Optional[Dict] = None
    ):
        """
        Add message to conversation
        
        Args:
            conversation_id: Conversation identifier
            role: Message role (user/assistant/system)
            content: Message content
            metadata: Optional metadata
        """
        conversation = self.get_conversation(conversation_id)
        
        if not conversation:
            logger.warning(f"Conversation {conversation_id} not found")
            return
        
        message = Message(
            role=role,
            content=content,
            metadata=metadata
        )
        
        conversation.messages.append(message)
        conversation.updated_at = datetime.utcnow()
        
        # Trim history if too long
        if len(conversation.messages) > self.max_history_length:
            # Keep system messages and recent history
            system_messages = [m for m in conversation.messages if m.role == MessageRole.SYSTEM]
            recent_messages = [m for m in conversation.messages if m.role != MessageRole.SYSTEM][-self.max_history_length:]
            conversation.messages = system_messages + recent_messages
        
        self.stats['total_messages'] += 1
        logger.debug(f"Added {role} message to conversation {conversation_id}")
    
    def get_history(
        self,
        conversation_id: str,
        last_n: Optional[int] = None
    ) -> List[Message]:
        """
        Get conversation history
        
        Args:
            conversation_id: Conversation identifier
            last_n: Get only last N messages
            
        Returns:
            List of messages
        """
        conversation = self.get_conversation(conversation_id)
        
        if not conversation:
            return []
        
        messages = conversation.messages
        
        if last_n:
            messages = messages[-last_n:]
        
        return messages
    
    def format_history_for_llm(
        self,
        conversation_id: str,
        last_n: int = 10
    ) -> List[Dict[str, str]]:
        """
        Format conversation history for LLM API
        
        Returns:
            List of message dicts in LLM format
        """
        messages = self.get_history(conversation_id, last_n)
        
        formatted = []
        for msg in messages:
            formatted.append({
                'role': msg.role.value,
                'content': msg.content
            })
        
        return formatted
    
    def get_context_summary(self, conversation_id: str) -> str:
        """
        Get summary of conversation context
        
        Returns:
            Text summary of recent conversation
        """
        messages = self.get_history(conversation_id, last_n=5)
        
        if not messages:
            return "No conversation history"
        
        summary_parts = []
        for msg in messages:
            prefix = "User" if msg.role == MessageRole.USER else "Assistant"
            content_preview = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
            summary_parts.append(f"{prefix}: {content_preview}")
        
        return "\n".join(summary_parts)
    
    def clear_conversation(self, conversation_id: str):
        """Clear conversation history"""
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
            logger.info(f"Cleared conversation {conversation_id}")
    
    def cleanup_expired_sessions(self):
        """Remove expired conversation sessions"""
        now = datetime.utcnow()
        expired = []
        
        for conv_id, conv in self.conversations.items():
            if now - conv.updated_at > self.session_timeout:
                expired.append(conv_id)
        
        for conv_id in expired:
            del self.conversations[conv_id]
        
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")
        
        return len(expired)
    
    def get_stats(self) -> Dict:
        """Get conversation statistics"""
        active_conversations = len(self.conversations)
        total_conversations = self.stats['total_conversations']
        total_messages = self.stats['total_messages']
        
        avg_messages = total_messages / total_conversations if total_conversations > 0 else 0
        
        return {
            'active_conversations': active_conversations,
            'total_conversations': total_conversations,
            'total_messages': total_messages,
            'avg_messages_per_conversation': round(avg_messages, 2)
        }
    
    def get_user_conversations(self, user_id: str) -> List[str]:
        """Get all conversation IDs for a user"""
        return [
            conv_id for conv_id, conv in self.conversations.items()
            if conv.user_id == user_id
        ]


class ContextExtractor:
    """
    Extract structured context from conversation
    
    Identifies entities, intents, and relevant information
    """
    
    @staticmethod
    def extract_order_id(text: str) -> Optional[str]:
        """Extract order ID from text"""
        import re
        # Match patterns like: ORDER-12345, #12345, order 12345
        patterns = [
            r'ORDER[- ]?(\d+)',
            r'#(\d+)',
            r'order[- ]?(\d+)',
            r'\b(\d{5,})\b'  # 5+ digit numbers
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    @staticmethod
    def extract_product_name(text: str) -> Optional[str]:
        """Extract product name (basic implementation)"""
        # In production, use NER or more sophisticated extraction
        keywords = ['product', 'item', 'about the']
        
        for keyword in keywords:
            if keyword in text.lower():
                # Extract text after keyword
                parts = text.lower().split(keyword)
                if len(parts) > 1:
                    # Get next few words
                    words = parts[1].strip().split()[:5]
                    return ' '.join(words).strip('?.,!')
        
        return None
    
    @staticmethod
    def extract_email(text: str) -> Optional[str]:
        """Extract email address"""
        import re
        pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        match = re.search(pattern, text)
        return match.group(0) if match else None
    
    @staticmethod
    def detect_sentiment(text: str) -> str:
        """
        Detect message sentiment (basic)
        
        Returns: positive, negative, or neutral
        """
        positive_words = ['thank', 'great', 'excellent', 'love', 'perfect', 'happy', 'good']
        negative_words = ['bad', 'terrible', 'awful', 'hate', 'problem', 'issue', 'complain', 'disappointed']
        
        text_lower = text.lower()
        
        pos_count = sum(1 for word in positive_words if word in text_lower)
        neg_count = sum(1 for word in negative_words if word in text_lower)
        
        if pos_count > neg_count:
            return 'positive'
        elif neg_count > pos_count:
            return 'negative'
        else:
            return 'neutral'
