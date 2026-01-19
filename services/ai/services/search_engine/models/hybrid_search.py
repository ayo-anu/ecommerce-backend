"""
Hybrid Search Orchestrator - Combines multiple search strategies
Merges text, semantic, and visual search results intelligently
"""
from typing import List, Dict, Optional, Tuple
import numpy as np
from collections import defaultdict
import logging

from .semantic_search import SemanticSearchModel
from .visual_search import VisualSearchModel
from .query_processor import QueryProcessor

logger = logging.getLogger(__name__)


class HybridSearchEngine:
    """
    Multi-modal search engine combining:
    - Text/keyword search
    - Semantic search (understanding intent)
    - Visual search (image similarity)
    """
    
    def __init__(self):
        self.semantic_model = SemanticSearchModel()
        self.visual_model = VisualSearchModel()
        self.query_processor = QueryProcessor()
        self.products_data = []
        self.is_initialized = False
        
    def initialize(self, products: List[Dict]):
        """Initialize all search models with product data"""
        logger.info(f"Initializing hybrid search with {len(products)} products")
        
        # Normalize products to ensure consistent 'id' field
        normalized_products = []
        for p in products:
            normalized = p.copy()
            # Ensure 'id' field exists (use product_id if id is missing)
            if 'id' not in normalized:
                normalized['id'] = p.get('product_id', f"prod_{len(normalized_products)}")
            normalized_products.append(normalized)
        
        self.products_data = normalized_products
        
        # Index products for semantic search
        try:
            self.semantic_model.index_products(normalized_products)
            logger.info("Semantic search indexed successfully")
        except Exception as e:
            logger.error(f"Semantic indexing error: {e}")
        
        # Index product images for visual search (optional)
        try:
            self.visual_model.index_product_images(normalized_products)
            logger.info("Visual search indexed successfully")
        except Exception as e:
            logger.warning(f"Visual indexing skipped: {e}")
        
        self.is_initialized = True
        logger.info("Hybrid search initialized successfully")
    
    def search(
        self,
        query: Optional[str] = None,
        image: Optional[object] = None,
        top_k: int = 20,
        filters: Optional[Dict] = None,
        search_mode: str = "hybrid"  # "text", "semantic", "visual", "hybrid"
    ) -> List[Dict]:
        """
        Unified search interface
        
        Args:
            query: Text search query
            image: PIL Image for visual search
            top_k: Number of results
            filters: Additional filters (price, category, etc.)
            search_mode: Which search strategy to use
            
        Returns:
            List of product results with scores
        """
        if not self.is_initialized:
            logger.warning("Search engine not initialized")
            return []
        
        results = []
        
        # Process query if provided
        processed_query = None
        extracted_filters = {}
        if query:
            processed_query = self.query_processor.process_query(query)
            extracted_filters = self.query_processor.extract_filters(query)
        
        # Merge explicit filters with extracted filters
        all_filters = {**(filters or {}), **extracted_filters}
        
        # Execute searches based on mode
        if search_mode == "hybrid" or search_mode == "semantic":
            if query:
                semantic_results = self.semantic_model.search(
                    processed_query['final_query'],
                    top_k=top_k * 2  # Get more for fusion
                )
                results.append(('semantic', semantic_results))
        
        if search_mode == "hybrid" or search_mode == "text":
            if query:
                text_results = self._text_search(query, top_k * 2)
                results.append(('text', text_results))
        
        if search_mode == "visual" or (search_mode == "hybrid" and image):
            if image:
                visual_results = self.visual_model.search_by_image(image, top_k=top_k * 2)
                results.append(('visual', visual_results))
        
        # Fuse results from multiple sources
        if len(results) > 1:
            fused_results = self._fuse_results(results, top_k)
        elif len(results) == 1:
            fused_results = results[0][1][:top_k]
        else:
            fused_results = []
        
        # Apply filters and enrich with product data
        final_results = self._apply_filters_and_enrich(fused_results, all_filters)
        
        return final_results[:top_k]
    
    def _text_search(self, query: str, top_k: int) -> List[Tuple[str, float]]:
        """Simple text-based keyword search with normalized scores"""
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        scores = []
        for product in self.products_data:
            # Search in title, description, category
            searchable_text = ' '.join([
                product.get('name', ''),
                product.get('description', ''),
                product.get('category', ''),
                ' '.join(product.get('tags', []))
            ]).lower()
            
            # Simple scoring: count matching words
            matches = sum(1 for word in query_words if word in searchable_text)
            if matches > 0:
                # Boost exact phrase matches
                if query_lower in searchable_text:
                    matches += 2
                # Normalize score to 0-1 range
                score = min(matches / max(len(query_words), 1), 1.0)
                scores.append((product['id'], score))
        
        # Sort by score
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]
    
    def _fuse_results(
        self,
        results: List[Tuple[str, List[Tuple[str, float]]]],
        top_k: int
    ) -> List[Tuple[str, float]]:
        """
        Fuse results from multiple search strategies using Reciprocal Rank Fusion
        
        Args:
            results: List of (search_type, [(product_id, score), ...])
            top_k: Number of final results
            
        Returns:
            Fused list of (product_id, score) normalized to 0-1
        """
        # Weights for different search types
        weights = {
            'semantic': 0.5,
            'text': 0.3,
            'visual': 0.4
        }
        
        # Reciprocal Rank Fusion
        k = 60  # RRF constant
        fusion_scores = defaultdict(float)
        
        for search_type, result_list in results:
            weight = weights.get(search_type, 0.33)
            for rank, (product_id, score) in enumerate(result_list, 1):
                # RRF score: 1 / (k + rank)
                rrf_score = 1.0 / (k + rank)
                # Combine with original score (already 0-1) and weight
                fusion_scores[product_id] += (rrf_score + score) * weight
        
        # Sort by fused score
        fused = sorted(fusion_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Normalize scores to 0-1 range
        if fused and fused[0][1] > 0:
            max_score = fused[0][1]
            fused = [(pid, min(score / max_score, 1.0)) for pid, score in fused]
        
        return fused[:top_k]
    
    def _apply_filters_and_enrich(
        self,
        results: List[Tuple[str, float]],
        filters: Dict
    ) -> List[Dict]:
        """Apply filters and add full product data"""
        product_map = {p['id']: p for p in self.products_data}
        
        enriched = []
        for product_id, score in results:
            product = product_map.get(product_id)
            if not product:
                continue
            
            # Apply filters
            if filters:
                if 'min_price' in filters and product.get('price', 0) < filters['min_price']:
                    continue
                if 'max_price' in filters and product.get('price', float('inf')) > filters['max_price']:
                    continue
                if 'category' in filters and product.get('category') != filters['category']:
                    continue
                if 'in_stock' in filters and filters['in_stock'] and not product.get('in_stock', True):
                    continue
            
            # Add to results with score
            result = {**product, 'relevance_score': float(score)}
            enriched.append(result)
        
        return enriched
    
    def autocomplete(self, prefix: str, limit: int = 10) -> List[str]:
        """Generate autocomplete suggestions"""
        if not self.products_data:
            return []
        
        suggestions = set()
        prefix_lower = prefix.lower()
        
        for product in self.products_data:
            name = product.get('name', '')
            if name and prefix_lower in name.lower():
                suggestions.add(name)
        
        return sorted(list(suggestions))[:limit]
    
    def get_search_stats(self) -> Dict:
        """Get search engine statistics"""
        return {
            'total_products': len(self.products_data),
            'semantic_indexed': len(self.semantic_model.product_embeddings) if self.semantic_model.is_loaded and self.semantic_model.product_embeddings is not None else 0,
            'visual_indexed': len(self.visual_model.product_image_embeddings) if hasattr(self.visual_model, 'is_trained') and self.visual_model.is_trained and self.visual_model.product_image_embeddings is not None else 0,
            'is_initialized': self.is_initialized
        }
