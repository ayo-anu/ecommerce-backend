"""
Content-Based Filtering Model
Recommends items based on product features and user preferences
"""
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class ContentBasedModel:
    """
    Content-based filtering using TF-IDF and cosine similarity
    """
    
    def __init__(self, max_features: int = 5000):
        self.max_features = max_features
        self.vectorizer = TfidfVectorizer(max_features=max_features, stop_words='english')
        
        self.product_vectors = None
        self.product_id_map = {}
        self.reverse_product_map = {}
        
        self.is_trained = False
        
    def fit(self, products: List[Dict]):
        """
        Train content-based model
        
        Args:
            products: List of dicts with keys: product_id, name, description, category, tags
        """
        logger.info(f"Training content-based model with {len(products)} products")
        
        # Create product ID mappings
        self.product_id_map = {p['product_id']: idx for idx, p in enumerate(products)}
        self.reverse_product_map = {idx: p['product_id'] for idx, p in enumerate(products)}
        
        # Combine text features
        text_features = []
        for product in products:
            features = [
                product.get('name', ''),
                product.get('description', ''),
                product.get('category', ''),
                ' '.join(product.get('tags', []))
            ]
            text_features.append(' '.join(features))
        
        # Create TF-IDF vectors
        self.product_vectors = self.vectorizer.fit_transform(text_features)
        
        self.is_trained = True
        logger.info("Content-based model trained successfully")
        
    def get_similar_products(self, product_id: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """
        Get similar products based on content
        
        Args:
            product_id: Product ID
            top_k: Number of similar products
            
        Returns:
            List of (product_id, similarity_score) tuples
        """
        if not self.is_trained:
            return []
        
        if product_id not in self.product_id_map:
            logger.warning(f"Product {product_id} not found")
            return []
        
        idx = self.product_id_map[product_id]
        product_vector = self.product_vectors[idx]
        
        # Calculate cosine similarity
        similarities = cosine_similarity(product_vector, self.product_vectors)[0]
        
        # Get top-k similar products (excluding itself)
        similar_indices = similarities.argsort()[::-1][1:top_k+1]
        
        similar_products = [
            (self.reverse_product_map[i], float(similarities[i]))
            for i in similar_indices
        ]
        
        return similar_products
    
    def recommend_for_user_history(
        self, 
        user_product_history: List[str], 
        top_k: int = 10
    ) -> List[Tuple[str, float]]:
        """
        Recommend products based on user's interaction history
        
        Args:
            user_product_history: List of product IDs user has interacted with
            top_k: Number of recommendations
            
        Returns:
            List of (product_id, score) tuples
        """
        if not self.is_trained or not user_product_history:
            return []
        
        # Get vectors for user's history
        user_vectors = []
        for product_id in user_product_history:
            if product_id in self.product_id_map:
                idx = self.product_id_map[product_id]
                user_vectors.append(self.product_vectors[idx])
        
        if not user_vectors:
            return []
        
        # Create user profile (average of product vectors)
        user_profile = np.mean([v.toarray() for v in user_vectors], axis=0)
        
        # Calculate similarity with all products
        similarities = cosine_similarity(user_profile, self.product_vectors)[0]
        
        # Exclude products user already interacted with
        history_indices = [
            self.product_id_map[pid] 
            for pid in user_product_history 
            if pid in self.product_id_map
        ]
        similarities[history_indices] = -1
        
        # Get top-k recommendations
        top_indices = similarities.argsort()[::-1][:top_k]
        
        recommendations = [
            (self.reverse_product_map[idx], float(similarities[idx]))
            for idx in top_indices
            if similarities[idx] > 0
        ]
        
        return recommendations
