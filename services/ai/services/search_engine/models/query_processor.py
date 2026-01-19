"""
Query Processing for Search
Handles spell correction, query expansion, tokenization
"""
import re
from typing import List, Set, Dict
import logging
from difflib import get_close_matches

logger = logging.getLogger(__name__)


class QueryProcessor:
    """
    Enterprise-grade query processing
    Handles spelling, expansion, normalization
    """
    
    def __init__(self):
        self.stop_words = self._load_stop_words()
        self.query_cache = {}
        self.popular_terms = set()
        
    def _load_stop_words(self) -> Set[str]:
        """Load common stop words"""
        return {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
            'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'should', 'could', 'may', 'might', 'must', 'can'
        }
    
    def process_query(self, query: str) -> Dict[str, any]:
        """
        Process search query with all enhancements
        
        Args:
            query: Raw search query
            
        Returns:
            Dict with processed query and metadata
        """
        # Normalize
        normalized = self.normalize(query)
        
        # Tokenize
        tokens = self.tokenize(normalized)
        
        # Remove stop words
        filtered_tokens = self.remove_stop_words(tokens)
        
        # Spell correction
        corrected_tokens = [self.spell_correct(token) for token in filtered_tokens]
        
        # Query expansion
        expanded_terms = self.expand_query(corrected_tokens)
        
        return {
            'original': query,
            'normalized': normalized,
            'tokens': tokens,
            'filtered_tokens': filtered_tokens,
            'corrected_tokens': corrected_tokens,
            'expanded_terms': expanded_terms,
            'final_query': ' '.join(corrected_tokens)
        }
    
    def normalize(self, query: str) -> str:
        """Normalize query text"""
        # Lowercase
        query = query.lower()
        
        # Remove special characters but keep spaces
        query = re.sub(r'[^a-z0-9\s]', ' ', query)
        
        # Remove extra spaces
        query = ' '.join(query.split())
        
        return query
    
    def tokenize(self, query: str) -> List[str]:
        """Tokenize query into words."""
        return query.split()
    
    def remove_stop_words(self, tokens: List[str]) -> List[str]:
        """Remove common stop words."""
        return [token for token in tokens if token not in self.stop_words]
    
    def spell_correct(self, word: str) -> str:
        """Basic spell correction."""
        if self.popular_terms:
            matches = get_close_matches(word, self.popular_terms, n=1, cutoff=0.8)
            if matches:
                return matches[0]
        
        return word
    
    def expand_query(self, tokens: List[str]) -> List[str]:
        """Expand query with synonyms."""
        synonyms = {
            'phone': ['mobile', 'smartphone', 'cell'],
            'laptop': ['notebook', 'computer'],
            'dress': ['gown', 'frock'],
            'shoe': ['footwear', 'sneaker'],
            'bag': ['handbag', 'purse'],
        }
        
        expanded = list(tokens)
        for token in tokens:
            if token in synonyms:
                expanded.extend(synonyms[token])
        
        return list(set(expanded))  # Remove duplicates
    
    def extract_filters(self, query: str) -> Dict[str, any]:
        """
        Extract filters from natural language query
        
        Examples:
            "red dress under $50" -> {color: red, price_max: 50}
            "laptops above $1000" -> {category: laptops, price_min: 1000}
        """
        filters = {}
        
        # Price extraction
        price_pattern = r'(?:under|below|less than|<)\s*\$?(\d+(?:\.\d{2})?)'
        match = re.search(price_pattern, query.lower())
        if match:
            filters['price_max'] = float(match.group(1))
        
        price_pattern = r'(?:above|over|more than|>)\s*\$?(\d+(?:\.\d{2})?)'
        match = re.search(price_pattern, query.lower())
        if match:
            filters['price_min'] = float(match.group(1))
        
        # Color extraction
        colors = ['red', 'blue', 'green', 'black', 'white', 'yellow', 'pink', 'purple']
        for color in colors:
            if color in query.lower():
                filters['color'] = color
                break
        
        # Size extraction
        sizes = ['small', 'medium', 'large', 'xl', 'xxl', 's', 'm', 'l']
        for size in sizes:
            if f' {size} ' in f' {query.lower()} ':
                filters['size'] = size
                break
        
        return filters
    
    def generate_suggestions(self, query: str, popular_queries: List[str], limit: int = 5) -> List[str]:
        """
        Generate autocomplete suggestions
        
        Args:
            query: Partial query
            popular_queries: List of popular past queries
            limit: Max suggestions
            
        Returns:
            List of suggested completions
        """
        query_lower = query.lower()
        
        # Filter popular queries that start with or contain the query
        suggestions = []
        
        # Exact prefix matches first
        for popular in popular_queries:
            if popular.lower().startswith(query_lower):
                suggestions.append(popular)
        
        # Then contains matches
        for popular in popular_queries:
            if query_lower in popular.lower() and popular not in suggestions:
                suggestions.append(popular)
        
        return suggestions[:limit]
    
    def update_popular_terms(self, terms: Set[str]):
        """Update popular terms for spell correction"""
        self.popular_terms = terms
        logger.info(f"Updated popular terms: {len(terms)} terms")
