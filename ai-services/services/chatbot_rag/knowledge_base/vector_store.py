"""
Vector Knowledge Base - Document storage and retrieval
Uses embeddings for semantic search
"""
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict, Tuple, Optional
import logging
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


class VectorKnowledgeBase:
    """
    Vector-based knowledge base for RAG
    
    Stores documents as embeddings for semantic retrieval
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize knowledge base
        
        Args:
            model_name: Sentence transformer model name
        """
        self.model = SentenceTransformer(model_name)
        self.documents = []
        self.embeddings = None
        self.metadata = []
        self.categories = defaultdict(list)
        
        logger.info(f"Initialized knowledge base with model: {model_name}")
    
    def add_documents(self, documents: List[Dict]) -> int:
        """
        Add documents to knowledge base
        
        Args:
            documents: List of document dicts with 'content', 'title', 'category'
            
        Returns:
            Number of documents added
        """
        if not documents:
            return 0
        
        logger.info(f"Adding {len(documents)} documents to knowledge base")
        
        start_idx = len(self.documents)
        
        # Extract content for embedding
        contents = [doc.get('content', '') for doc in documents]
        
        # Generate embeddings
        new_embeddings = self.model.encode(contents, convert_to_numpy=True)
        
        # Store documents and metadata
        for idx, doc in enumerate(documents):
            doc_id = start_idx + idx
            self.documents.append(doc.get('content', ''))
            self.metadata.append({
                'id': doc_id,
                'title': doc.get('title', 'Untitled'),
                'category': doc.get('category', 'general'),
                'tags': doc.get('tags', []),
                'source_url': doc.get('source_url'),
                'custom': doc.get('metadata', {})
            })
            
            # Index by category
            category = doc.get('category', 'general')
            self.categories[category].append(doc_id)
        
        # Update embeddings array
        if self.embeddings is None:
            self.embeddings = new_embeddings
        else:
            self.embeddings = np.vstack([self.embeddings, new_embeddings])
        
        logger.info(f"Knowledge base now contains {len(self.documents)} documents")
        return len(documents)
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        category_filter: Optional[str] = None,
        min_score: float = 0.5
    ) -> List[Dict]:
        """
        Search knowledge base with semantic similarity
        
        Args:
            query: Search query
            top_k: Number of results to return
            category_filter: Optional category to filter by
            min_score: Minimum similarity score
            
        Returns:
            List of relevant documents with scores
        """
        if self.embeddings is None or len(self.documents) == 0:
            logger.warning("Knowledge base is empty")
            return []
        
        # Encode query
        query_embedding = self.model.encode(query, convert_to_numpy=True)
        
        # Calculate similarities
        similarities = np.dot(self.embeddings, query_embedding)
        
        # Apply category filter if specified
        if category_filter:
            filtered_indices = self.categories.get(category_filter, [])
            if not filtered_indices:
                return []
            
            # Create mask for filtered indices
            mask = np.zeros(len(similarities), dtype=bool)
            mask[filtered_indices] = True
            similarities = np.where(mask, similarities, -np.inf)
        
        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        # Build results
        results = []
        for idx in top_indices:
            score = float(similarities[idx])
            
            if score < min_score:
                continue
            
            meta = self.metadata[idx]
            results.append({
                'content': self.documents[idx],
                'source': meta['title'],
                'relevance_score': score,
                'metadata': {
                    'id': meta['id'],
                    'category': meta['category'],
                    'tags': meta['tags'],
                    'source_url': meta['source_url'],
                    **meta.get('custom', {})
                }
            })
        
        logger.info(f"Found {len(results)} relevant documents for query: {query[:50]}...")
        return results
    
    def get_document_by_id(self, doc_id: int) -> Optional[Dict]:
        """Get specific document by ID"""
        if 0 <= doc_id < len(self.documents):
            return {
                'content': self.documents[doc_id],
                'metadata': self.metadata[doc_id]
            }
        return None
    
    def get_categories(self) -> List[str]:
        """Get all available categories"""
        return list(self.categories.keys())
    
    def get_stats(self) -> Dict:
        """Get knowledge base statistics"""
        return {
            'total_documents': len(self.documents),
            'categories': {cat: len(docs) for cat, docs in self.categories.items()},
            'embedding_dimensions': self.embeddings.shape[1] if self.embeddings is not None else 0
        }
    
    def clear(self):
        """Clear all documents"""
        self.documents = []
        self.embeddings = None
        self.metadata = []
        self.categories = defaultdict(list)
        logger.info("Knowledge base cleared")
    
    def save(self, filepath: str):
        """Save knowledge base to disk"""
        data = {
            'documents': self.documents,
            'embeddings': self.embeddings.tolist() if self.embeddings is not None else None,
            'metadata': self.metadata
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f)
        
        logger.info(f"Knowledge base saved to {filepath}")
    
    def load(self, filepath: str):
        """Load knowledge base from disk"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        self.documents = data['documents']
        self.embeddings = np.array(data['embeddings']) if data['embeddings'] else None
        self.metadata = data['metadata']
        
        # Rebuild category index
        self.categories = defaultdict(list)
        for meta in self.metadata:
            self.categories[meta['category']].append(meta['id'])
        
        logger.info(f"Knowledge base loaded from {filepath}")


class EcommerceKnowledgeBase:
    """
    Pre-populated e-commerce knowledge base
    
    Contains common product, shipping, return policies, etc.
    """
    
    @staticmethod
    def get_default_documents() -> List[Dict]:
        """Get default e-commerce knowledge documents"""
        return [
            {
                'title': 'Shipping Policy',
                'content': 'We offer free standard shipping on orders over $50. Standard shipping takes 5-7 business days. Express shipping is available for $15 and delivers in 2-3 business days. International shipping is available to select countries and takes 10-15 business days.',
                'category': 'shipping',
                'tags': ['policy', 'delivery', 'shipping']
            },
            {
                'title': 'Return Policy',
                'content': 'We accept returns within 30 days of purchase. Items must be unused and in original packaging. Refunds are processed within 5-7 business days. Return shipping is free for defective items. For other returns, customers are responsible for return shipping costs.',
                'category': 'returns',
                'tags': ['policy', 'returns', 'refund']
            },
            {
                'title': 'Payment Methods',
                'content': 'We accept all major credit cards (Visa, Mastercard, American Express, Discover), PayPal, Apple Pay, and Google Pay. All transactions are secured with SSL encryption. We do not store credit card information on our servers.',
                'category': 'payment',
                'tags': ['payment', 'security', 'checkout']
            },
            {
                'title': 'Order Tracking',
                'content': 'Once your order ships, you will receive a tracking number via email. You can track your package using this number on our website or the carrier\'s website. Tracking information is usually available within 24 hours of shipment.',
                'category': 'orders',
                'tags': ['tracking', 'shipping', 'orders']
            },
            {
                'title': 'Product Warranty',
                'content': 'All products come with a manufacturer\'s warranty. Electronics have a 1-year warranty. Clothing and accessories have a 90-day warranty against defects. To claim warranty service, contact our support team with your order number and photos of the defect.',
                'category': 'products',
                'tags': ['warranty', 'quality', 'support']
            },
            {
                'title': 'Size Guide',
                'content': 'For clothing: XS (32-34), S (34-36), M (36-38), L (38-40), XL (40-42), XXL (42-44). For shoes: US sizes with half sizes available. We recommend measuring yourself and referring to our detailed size charts on each product page for the best fit.',
                'category': 'products',
                'tags': ['sizing', 'fit', 'clothing']
            },
            {
                'title': 'Customer Support',
                'content': 'Our customer support team is available Monday-Friday 9 AM - 6 PM EST. You can reach us via email at support@example.com or phone at 1-800-123-4567. Average response time is 2-4 hours during business hours. We also offer live chat support on our website.',
                'category': 'support',
                'tags': ['contact', 'help', 'support']
            },
            {
                'title': 'Gift Cards',
                'content': 'Gift cards are available in denominations of $25, $50, $100, and $250. They never expire and can be used for any purchase on our website. You can check your gift card balance on the Gift Cards page. Gift cards are non-refundable but can be combined with other payment methods.',
                'category': 'payment',
                'tags': ['gift cards', 'payment']
            },
            {
                'title': 'Loyalty Program',
                'content': 'Join our rewards program for free! Earn 1 point per dollar spent. 100 points = $5 reward. Members get early access to sales, free birthday gift, and exclusive promotions. Points expire after 12 months of inactivity.',
                'category': 'promotions',
                'tags': ['rewards', 'loyalty', 'discounts']
            },
            {
                'title': 'Product Care Instructions',
                'content': 'Electronics: Keep away from moisture, avoid extreme temperatures. Clothing: Follow care labels - most items are machine washable in cold water. Leather goods: Use leather conditioner every 3-6 months. Store in dust bags when not in use.',
                'category': 'products',
                'tags': ['care', 'maintenance', 'instructions']
            }
        ]
