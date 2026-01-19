"""
Hybrid Recommendation Model
Combines collaborative and content-based filtering
"""
from typing import List, Dict, Tuple
import logging
from .collaborative import CollaborativeFilteringModel
from .content_based import ContentBasedModel

logger = logging.getLogger(__name__)


class HybridModel:
    """
    Hybrid recommendation system combining multiple algorithms
    """
    
    def __init__(
        self, 
        collaborative_weight: float = 0.6,
        content_weight: float = 0.4
    ):
        self.collaborative_weight = collaborative_weight
        self.content_weight = content_weight
        
        self.collaborative_model = CollaborativeFilteringModel()
        self.content_model = ContentBasedModel()
        
    def fit(self, interactions: List[Dict], products: List[Dict]):
        """
        Train both models
        
        Args:
            interactions: User-product interactions
            products: Product metadata
        """
        logger.info("Training hybrid model...")
        
        # Train collaborative model
        self.collaborative_model.fit(interactions)
        
        # Train content-based model
        self.content_model.fit(products)
        
        logger.info("Hybrid model trained successfully")
        
    def recommend(
        self,
        user_id: str,
        user_history: List[str],
        top_k: int = 10
    ) -> List[Tuple[str, float]]:
        """
        Get hybrid recommendations
        
        Args:
            user_id: User ID
            user_history: User's product interaction history
            top_k: Number of recommendations
            
        Returns:
            List of (product_id, score) tuples
        """
        # Get collaborative recommendations
        collab_recs = self.collaborative_model.predict_for_user(user_id, top_k * 2)
        
        # Get content-based recommendations
        content_recs = self.content_model.recommend_for_user_history(user_history, top_k * 2)
        
        # Combine recommendations
        combined_scores = {}
        
        # Add collaborative scores
        for product_id, score in collab_recs:
            combined_scores[product_id] = score * self.collaborative_weight
        
        # Add content-based scores
        for product_id, score in content_recs:
            if product_id in combined_scores:
                combined_scores[product_id] += score * self.content_weight
            else:
                combined_scores[product_id] = score * self.content_weight
        
        # Sort and return top-k
        recommendations = sorted(
            combined_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_k]
        
        return recommendations
