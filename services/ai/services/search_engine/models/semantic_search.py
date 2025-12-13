"""
Semantic Search Model using Sentence Transformers
Converts queries and products to embeddings for similarity search
"""
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class SemanticSearchModel:
    """
    Semantic search using sentence embeddings
    Enterprise-grade with caching and optimization
    """
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
        self.product_embeddings = None
        self.product_id_map = {}
        self.reverse_product_map = {}
        self.is_loaded = False
        
    def load_model(self):
        """Load sentence transformer model"""
        try:
            logger.info(f"Loading semantic search model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            self.is_loaded = True
            logger.info("Semantic search model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    
    def encode_products(self, products: List[Dict]):
        """
        Encode product texts to embeddings
        
        Args:
            products: List of product dicts with id/product_id, name, description, category
        """
        if not self.is_loaded:
            self.load_model()
        
        logger.info(f"Encoding {len(products)} products...")
        
        # Create product ID mappings (handle both 'id' and 'product_id' fields)
        self.product_id_map = {}
        self.reverse_product_map = {}
        
        for idx, p in enumerate(products):
            # Support both 'id' and 'product_id' field names
            product_id = p.get('id') or p.get('product_id')
            if not product_id:
                logger.warning(f"Product at index {idx} missing 'id' or 'product_id', skipping")
                continue
            
            self.product_id_map[product_id] = idx
            self.reverse_product_map[idx] = product_id
        
        # Combine text fields for encoding
        product_texts = []
        for product in products:
            # Combine multiple text fields
            text_parts = [
                str(product.get('name', '')),
                str(product.get('description', '')),
                str(product.get('category', '')),
                str(product.get('brand', '')),
                ' '.join(product.get('tags', []))
            ]
            text = ' '.join(filter(None, text_parts))  # Remove empty strings
            product_texts.append(text)
        
        # Encode in batches for efficiency
        self.product_embeddings = self.model.encode(
            product_texts,
            batch_size=32,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True  # L2 normalization for cosine similarity
        )
        
        logger.info(f"Product embeddings created: shape {self.product_embeddings.shape}")
    
    def index_products(self, products: List[Dict]):
        """
        Index products for search (alias for encode_products)
        
        Args:
            products: List of product dicts
        """
        return self.encode_products(products)
    
    def search(
        self,
        query: str,
        top_k: int = 10,
        threshold: float = 0.5
    ) -> List[Tuple[str, float]]:
        """
        Search products using semantic similarity
        
        Args:
            query: Search query text
            top_k: Number of results to return
            threshold: Minimum similarity score
            
        Returns:
            List of (product_id, similarity_score) tuples
        """
        if not self.is_loaded or self.product_embeddings is None:
            logger.warning("Model not loaded or no products encoded")
            return []
        
        try:
            # Encode query
            query_embedding = self.model.encode(
                query,
                convert_to_numpy=True,
                normalize_embeddings=True
            )
            
            # Calculate cosine similarities (dot product since normalized)
            similarities = np.dot(self.product_embeddings, query_embedding)
            
            # Get top-k indices
            top_indices = np.argsort(similarities)[::-1][:top_k * 2]  # Get extra for filtering
            
            # Filter by threshold and format results
            results = []
            for idx in top_indices:
                score = float(similarities[idx])
                if score >= threshold:
                    product_id = self.reverse_product_map[idx]
                    results.append((product_id, score))
                
                if len(results) >= top_k:
                    break
            
            return results
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []
    
    def search_with_filters(
        self,
        query: str,
        top_k: int = 10,
        threshold: float = 0.5,
        category_filter: Optional[str] = None,
        price_range: Optional[Tuple[float, float]] = None,
        product_metadata: Optional[Dict] = None
    ) -> List[Tuple[str, float]]:
        """
        Search with additional filters
        
        Args:
            query: Search query
            top_k: Number of results
            threshold: Similarity threshold
            category_filter: Filter by category
            price_range: (min_price, max_price) tuple
            product_metadata: Dict mapping product_id to metadata
            
        Returns:
            Filtered search results
        """
        # Get initial semantic search results
        initial_results = self.search(query, top_k * 3, threshold)  # Get more for filtering
        
        if not product_metadata:
            return initial_results[:top_k]
        
        # Apply filters
        filtered_results = []
        for product_id, score in initial_results:
            metadata = product_metadata.get(product_id, {})
            
            # Category filter
            if category_filter and metadata.get('category') != category_filter:
                continue
            
            # Price range filter
            if price_range:
                price = metadata.get('price', 0)
                if not (price_range[0] <= price <= price_range[1]):
                    continue
            
            filtered_results.append((product_id, score))
            
            if len(filtered_results) >= top_k:
                break
        
        return filtered_results
    
    def get_embedding(self, text: str) -> np.ndarray:
        """Get embedding for arbitrary text"""
        if not self.is_loaded:
            self.load_model()
        
        return self.model.encode(
            text,
            convert_to_numpy=True,
            normalize_embeddings=True
        )
    
    def batch_search(
        self,
        queries: List[str],
        top_k: int = 10
    ) -> List[List[Tuple[str, float]]]:
        """
        Batch search for multiple queries
        More efficient than individual searches
        
        Args:
            queries: List of query strings
            top_k: Results per query
            
        Returns:
            List of result lists
        """
        if not self.is_loaded or self.product_embeddings is None:
            return [[] for _ in queries]
        
        # Encode all queries at once
        query_embeddings = self.model.encode(
            queries,
            batch_size=32,
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        
        # Calculate similarities for all queries
        similarities = np.dot(query_embeddings, self.product_embeddings.T)
        
        # Get top-k for each query
        results = []
        for query_similarities in similarities:
            top_indices = np.argsort(query_similarities)[::-1][:top_k]
            query_results = [
                (self.reverse_product_map[idx], float(query_similarities[idx]))
                for idx in top_indices
            ]
            results.append(query_results)
        
        return results
