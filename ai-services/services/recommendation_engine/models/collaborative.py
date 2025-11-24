"""
Collaborative Filtering Model
User-based and Item-based collaborative filtering for recommendations
"""
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Tuple, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class CollaborativeFilteringModel:
    """
    Collaborative Filtering using Matrix Factorization
    Implements both user-based and item-based approaches
    """
    
    def __init__(self, n_factors: int = 50, n_iterations: int = 20, learning_rate: float = 0.01):
        self.n_factors = n_factors
        self.n_iterations = n_iterations
        self.learning_rate = learning_rate
        
        # Model parameters
        self.user_factors = None
        self.item_factors = None
        self.user_bias = None
        self.item_bias = None
        self.global_mean = 0.0
        
        # Mappings
        self.user_id_map = {}
        self.item_id_map = {}
        self.reverse_user_map = {}
        self.reverse_item_map = {}
        
        # Interaction matrix
        self.interaction_matrix = None
        
        self.is_trained = False
        self.last_trained = None
        
    def _create_mappings(self, user_ids: List[str], item_ids: List[str]):
        """Create ID mappings for users and items"""
        unique_users = list(set(user_ids))
        unique_items = list(set(item_ids))
        
        self.user_id_map = {uid: idx for idx, uid in enumerate(unique_users)}
        self.item_id_map = {iid: idx for idx, iid in enumerate(unique_items)}
        
        self.reverse_user_map = {idx: uid for uid, idx in self.user_id_map.items()}
        self.reverse_item_map = {idx: iid for iid, idx in self.item_id_map.items()}
        
    def _initialize_factors(self, n_users: int, n_items: int):
        """Initialize factor matrices"""
        # Random initialization with small values
        self.user_factors = np.random.normal(0, 0.1, (n_users, self.n_factors))
        self.item_factors = np.random.normal(0, 0.1, (n_items, self.n_factors))
        
        # Initialize biases
        self.user_bias = np.zeros(n_users)
        self.item_bias = np.zeros(n_items)
        
    def fit(self, interactions: List[Dict]):
        """
        Train the collaborative filtering model
        
        Args:
            interactions: List of dicts with keys: user_id, product_id, rating/weight
        """
        logger.info(f"Training collaborative filtering model with {len(interactions)} interactions")
        
        # Extract user and item IDs
        user_ids = [i['user_id'] for i in interactions]
        item_ids = [i['product_id'] for i in interactions]
        ratings = [i.get('rating', 1.0) for i in interactions]  # Default weight of 1.0
        
        # Create mappings
        self._create_mappings(user_ids, item_ids)
        
        n_users = len(self.user_id_map)
        n_items = len(self.item_id_map)
        
        # Initialize factors
        self._initialize_factors(n_users, n_items)
        
        # Calculate global mean
        self.global_mean = np.mean(ratings)
        
        # Create interaction matrix
        self.interaction_matrix = np.zeros((n_users, n_items))
        for user_id, item_id, rating in zip(user_ids, item_ids, ratings):
            u_idx = self.user_id_map[user_id]
            i_idx = self.item_id_map[item_id]
            self.interaction_matrix[u_idx, i_idx] = rating
        
        # Matrix factorization using SGD
        for iteration in range(self.n_iterations):
            total_error = 0
            n_samples = 0
            
            for user_id, item_id, rating in zip(user_ids, item_ids, ratings):
                u_idx = self.user_id_map[user_id]
                i_idx = self.item_id_map[item_id]
                
                # Predict rating
                prediction = (
                    self.global_mean +
                    self.user_bias[u_idx] +
                    self.item_bias[i_idx] +
                    np.dot(self.user_factors[u_idx], self.item_factors[i_idx])
                )
                
                # Calculate error
                error = rating - prediction
                total_error += error ** 2
                n_samples += 1
                
                # Update biases
                self.user_bias[u_idx] += self.learning_rate * error
                self.item_bias[i_idx] += self.learning_rate * error
                
                # Update factors
                user_factor_update = error * self.item_factors[i_idx]
                item_factor_update = error * self.user_factors[u_idx]
                
                self.user_factors[u_idx] += self.learning_rate * user_factor_update
                self.item_factors[i_idx] += self.learning_rate * item_factor_update
            
            rmse = np.sqrt(total_error / n_samples)
            if iteration % 5 == 0:
                logger.info(f"Iteration {iteration}, RMSE: {rmse:.4f}")
        
        self.is_trained = True
        self.last_trained = datetime.utcnow()
        logger.info("Collaborative filtering model trained successfully")
        
    def predict_for_user(self, user_id: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """
        Get top-k product recommendations for a user
        
        Args:
            user_id: User ID
            top_k: Number of recommendations
            
        Returns:
            List of (product_id, score) tuples
        """
        if not self.is_trained:
            logger.warning("Model not trained, returning empty recommendations")
            return []
        
        # Check if user exists
        if user_id not in self.user_id_map:
            logger.warning(f"User {user_id} not in training data, returning popular items")
            return self._get_popular_items(top_k)
        
        u_idx = self.user_id_map[user_id]
        
        # Get items user hasn't interacted with
        user_interactions = self.interaction_matrix[u_idx]
        unrated_items = np.where(user_interactions == 0)[0]
        
        if len(unrated_items) == 0:
            return []
        
        # Predict ratings for unrated items
        predictions = []
        for i_idx in unrated_items:
            score = (
                self.global_mean +
                self.user_bias[u_idx] +
                self.item_bias[i_idx] +
                np.dot(self.user_factors[u_idx], self.item_factors[i_idx])
            )
            # Normalize score to 0-1 range
            normalized_score = (score - self.global_mean) / 5.0  # Assuming 5-star rating
            normalized_score = max(0, min(1, normalized_score))
            
            predictions.append((self.reverse_item_map[i_idx], normalized_score))
        
        # Sort by score and return top-k
        predictions.sort(key=lambda x: x[1], reverse=True)
        return predictions[:top_k]
    
    def get_similar_items(self, item_id: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """
        Get similar items using item factors
        
        Args:
            item_id: Product ID
            top_k: Number of similar items
            
        Returns:
            List of (product_id, similarity_score) tuples
        """
        if not self.is_trained:
            return []
        
        if item_id not in self.item_id_map:
            logger.warning(f"Item {item_id} not found")
            return []
        
        i_idx = self.item_id_map[item_id]
        item_vector = self.item_factors[i_idx].reshape(1, -1)
        
        # Calculate cosine similarity with all items
        similarities = cosine_similarity(item_vector, self.item_factors)[0]
        
        # Get top-k similar items (excluding the item itself)
        similar_indices = similarities.argsort()[::-1][1:top_k+1]
        
        similar_items = [
            (self.reverse_item_map[idx], float(similarities[idx]))
            for idx in similar_indices
        ]
        
        return similar_items
    
    def _get_popular_items(self, top_k: int) -> List[Tuple[str, float]]:
        """Get most popular items based on interaction counts"""
        if self.interaction_matrix is None:
            return []
        
        # Count interactions per item
        item_popularity = self.interaction_matrix.sum(axis=0)
        
        # Get top-k popular items
        popular_indices = item_popularity.argsort()[::-1][:top_k]
        
        max_popularity = item_popularity.max()
        popular_items = [
            (self.reverse_item_map[idx], float(item_popularity[idx] / max_popularity))
            for idx in popular_indices
        ]
        
        return popular_items
    
    def get_model_stats(self) -> Dict:
        """Get model statistics"""
        return {
            "n_users": len(self.user_id_map),
            "n_items": len(self.item_id_map),
            "n_factors": self.n_factors,
            "is_trained": self.is_trained,
            "last_trained": self.last_trained.isoformat() if self.last_trained else None,
            "sparsity": 1 - (np.count_nonzero(self.interaction_matrix) / self.interaction_matrix.size) if self.interaction_matrix is not None else None
        }
