"""
Intent Classifier - Detect user intent from messages
Classifies queries into categories for better handling
"""
from typing import Dict, Tuple
import re
import logging

from ..schemas.chat import IntentType

logger = logging.getLogger(__name__)


class IntentClassifier:
    """
    Rule-based intent classifier
    
    In production, could use ML models for better accuracy
    """
    
    def __init__(self):
        """Initialize intent classifier with patterns"""
        self.intent_patterns = self._build_patterns()
        self.intent_keywords = self._build_keywords()
        
        logger.info("Intent classifier initialized")
    
    def _build_patterns(self) -> Dict[IntentType, list]:
        """Build regex patterns for each intent"""
        return {
            IntentType.ORDER_STATUS: [
                r'\border\b.*\bstatus\b',
                r'\btrack\b.*\border\b',
                r'\bwhere\b.*\border\b',
                r'\bwhen\b.*\barrive\b',
                r'\bdelivery\b.*\bdate\b',
                r'\bshipped\b',
                r'\btracking\b.*\bnumber\b',
                r'ORDER[- ]?\d+',
                r'#\d{5,}'
            ],
            IntentType.RETURNS: [
                r'\breturn\b',
                r'\brefund\b',
                r'\bexchange\b',
                r'\bsend\b.*\bback\b',
                r'\bmoney\b.*\bback\b'
            ],
            IntentType.SHIPPING: [
                r'\bshipping\b',
                r'\bdelivery\b',
                r'\bhow\b.*\blong\b',
                r'\bfree\b.*\bshipping\b',
                r'\bexpress\b',
                r'\binternational\b.*\bship\b'
            ],
            IntentType.PAYMENT: [
                r'\bpayment\b',
                r'\bpay\b',
                r'\bcredit\b.*\bcard\b',
                r'\bpaypal\b',
                r'\bcheckout\b',
                r'\bpromo\b.*\bcode\b',
                r'\bdiscount\b'
            ],
            IntentType.PRODUCT_INQUIRY: [
                r'\bproduct\b',
                r'\bitem\b',
                r'\btell\b.*\babout\b',
                r'\bdetails\b',
                r'\bspecification\b',
                r'\bsize\b',
                r'\bcolor\b',
                r'\bavailable\b',
                r'\bin\b.*\bstock\b'
            ],
            IntentType.COMPLAINT: [
                r'\bcomplaint\b',
                r'\bissue\b',
                r'\bproblem\b',
                r'\bnot\b.*\bwork\b',
                r'\bdamaged\b',
                r'\bdefective\b',
                r'\bdisappointed\b',
                r'\bunhappy\b'
            ],
            IntentType.RECOMMENDATION: [
                r'\brecommend\b',
                r'\bsuggest\b',
                r'\bwhat\b.*\bshould\b.*\bbuy\b',
                r'\bsimilar\b',
                r'\balternative\b',
                r'\bbest\b.*\bfor\b'
            ]
        }
    
    def _build_keywords(self) -> Dict[IntentType, list]:
        """Build keyword lists for each intent"""
        return {
            IntentType.ORDER_STATUS: [
                'order', 'tracking', 'shipment', 'delivery', 'status', 
                'arrive', 'eta', 'when', 'where'
            ],
            IntentType.RETURNS: [
                'return', 'refund', 'exchange', 'send back', 'money back',
                'cancel', 'unwanted'
            ],
            IntentType.SHIPPING: [
                'shipping', 'delivery', 'ship', 'deliver', 'express',
                'free shipping', 'international', 'freight'
            ],
            IntentType.PAYMENT: [
                'payment', 'pay', 'credit card', 'paypal', 'checkout',
                'promo code', 'discount', 'coupon', 'billing'
            ],
            IntentType.PRODUCT_INQUIRY: [
                'product', 'item', 'details', 'specs', 'specification',
                'size', 'color', 'material', 'available', 'stock'
            ],
            IntentType.COMPLAINT: [
                'complaint', 'issue', 'problem', 'not working', 'damaged',
                'defective', 'disappointed', 'unhappy', 'angry', 'frustrated'
            ],
            IntentType.RECOMMENDATION: [
                'recommend', 'suggest', 'should i buy', 'similar',
                'alternative', 'best', 'which one'
            ],
            IntentType.GENERAL_QUESTION: [
                'how', 'what', 'when', 'where', 'why', 'help',
                'question', 'info', 'information'
            ]
        }
    
    def classify(self, message: str) -> Tuple[IntentType, float]:
        """
        Classify user message intent
        
        Args:
            message: User message text
            
        Returns:
            (intent_type, confidence_score)
        """
        message_lower = message.lower()
        
        # Check patterns first (higher confidence)
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    logger.debug(f"Intent {intent} matched by pattern: {pattern}")
                    return intent, 0.9
        
        # Check keywords (medium confidence)
        intent_scores = {}
        for intent, keywords in self.intent_keywords.items():
            score = sum(1 for keyword in keywords if keyword in message_lower)
            if score > 0:
                intent_scores[intent] = score
        
        if intent_scores:
            best_intent = max(intent_scores, key=intent_scores.get)
            max_score = intent_scores[best_intent]
            confidence = min(0.7, 0.5 + (max_score * 0.1))
            
            logger.debug(f"Intent {best_intent} matched by keywords with score {max_score}")
            return best_intent, confidence
        
        # Default to general question
        logger.debug("No specific intent matched, defaulting to GENERAL_QUESTION")
        return IntentType.GENERAL_QUESTION, 0.5
    
    def get_suggested_followups(self, intent: IntentType) -> list:
        """
        Get suggested follow-up questions based on intent
        
        Args:
            intent: Detected intent
            
        Returns:
            List of suggested questions
        """
        suggestions = {
            IntentType.ORDER_STATUS: [
                "When will my order arrive?",
                "How can I track my package?",
                "Can I change my delivery address?"
            ],
            IntentType.RETURNS: [
                "What is your return policy?",
                "How do I start a return?",
                "When will I receive my refund?"
            ],
            IntentType.SHIPPING: [
                "Do you offer free shipping?",
                "What are the shipping options?",
                "Do you ship internationally?"
            ],
            IntentType.PAYMENT: [
                "What payment methods do you accept?",
                "Is my payment information secure?",
                "Do you have any promo codes?"
            ],
            IntentType.PRODUCT_INQUIRY: [
                "What are the product specifications?",
                "Is this item in stock?",
                "What sizes are available?"
            ],
            IntentType.COMPLAINT: [
                "How can I report a problem?",
                "What is your warranty policy?",
                "Can I speak to a manager?"
            ],
            IntentType.RECOMMENDATION: [
                "What are your best sellers?",
                "Can you recommend similar products?",
                "What do other customers buy?"
            ],
            IntentType.GENERAL_QUESTION: [
                "How can I contact customer support?",
                "What are your business hours?",
                "Where are you located?"
            ]
        }
        
        return suggestions.get(intent, [])
    
    def extract_entities(self, message: str, intent: IntentType) -> Dict:
        """
        Extract relevant entities based on intent
        
        Args:
            message: User message
            intent: Detected intent
            
        Returns:
            Dictionary of extracted entities
        """
        entities = {}
        message_lower = message.lower()
        
        # Extract order ID
        if intent == IntentType.ORDER_STATUS:
            order_patterns = [
                r'ORDER[- ]?(\d+)',
                r'#(\d+)',
                r'\b(\d{5,})\b'
            ]
            for pattern in order_patterns:
                match = re.search(pattern, message, re.IGNORECASE)
                if match:
                    entities['order_id'] = match.group(1)
                    break
        
        # Extract product name (basic)
        if intent == IntentType.PRODUCT_INQUIRY:
            # Look for text after "about" or product names in quotes
            if 'about' in message_lower:
                parts = message.split('about', 1)
                if len(parts) > 1:
                    product_text = parts[1].strip()
                    entities['product_mention'] = product_text.split()[0:5]
        
        # Extract amounts for returns/refunds
        if intent == IntentType.RETURNS:
            amount_match = re.search(r'\$(\d+\.?\d*)', message)
            if amount_match:
                entities['amount'] = float(amount_match.group(1))
        
        return entities
    
    def is_urgent(self, message: str, intent: IntentType) -> bool:
        """
        Determine if message requires urgent attention
        
        Args:
            message: User message
            intent: Detected intent
            
        Returns:
            True if urgent
        """
        urgent_keywords = [
            'urgent', 'emergency', 'asap', 'immediately', 'now',
            'critical', 'never received', 'still waiting', 'angry'
        ]
        
        message_lower = message.lower()
        
        # Check for urgent keywords
        if any(keyword in message_lower for keyword in urgent_keywords):
            return True
        
        # Complaints are usually urgent
        if intent == IntentType.COMPLAINT:
            return True
        
        # Multiple exclamation marks suggest urgency
        if message.count('!') >= 2:
            return True
        
        return False
