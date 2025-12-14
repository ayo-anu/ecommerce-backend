"""
Pydantic schemas for search engine
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class SearchResult(BaseModel):
    """Single search result"""
    product_id: str
    name: str  # Product name
    description: Optional[str] = None
    price: Optional[float] = None
    image_url: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = []
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")
    highlight: Optional[str] = None  # Highlighted matching text
    
    # Aliases for backward compatibility
    @property
    def product_name(self) -> str:
        return self.name
    
    @property
    def product_price(self) -> Optional[float]:
        return self.price
    
    @property
    def product_image(self) -> Optional[str]:
        return self.image_url
    
    @property
    def score(self) -> float:
        return self.relevance_score


class TextSearchRequest(BaseModel):
    """Text search request"""
    query: str = Field(..., min_length=1, max_length=500)
    limit: int = Field(10, ge=1, le=100)
    top_k: Optional[int] = Field(None, ge=1, le=100, description="Alias for limit")
    filters: Optional[dict] = None  # category, price_range, etc.
    include_facets: bool = Field(False, description="Include aggregations")
    use_semantic: bool = Field(False, description="Use semantic search in addition to text")
    
    def __init__(self, **data):
        super().__init__(**data)
        # If top_k is provided but not limit, use top_k as limit
        if self.top_k is not None and 'limit' not in data:
            self.limit = self.top_k
        # If neither provided, ensure top_k matches limit
        if self.top_k is None:
            self.top_k = self.limit


class SemanticSearchRequest(BaseModel):
    """Semantic search using embeddings"""
    query: str = Field(..., min_length=1, max_length=500)
    limit: int = Field(10, ge=1, le=100)
    similarity_threshold: float = Field(0.5, ge=0.0, le=1.0)
    filters: Optional[dict] = None


class VisualSearchRequest(BaseModel):
    """Visual search using images"""
    image_url: Optional[str] = None
    image_base64: Optional[str] = None
    limit: int = Field(10, ge=1, le=50)
    similarity_threshold: float = Field(0.6, ge=0.0, le=1.0)


class SearchResponse(BaseModel):
    """Search response with results"""
    results: List[SearchResult]
    total_results: int
    query: str
    processing_time_ms: float
    search_type: str  # text, semantic, visual, hybrid
    cached: bool = False
    facets: Optional[dict] = None  # Aggregations (categories, price ranges, etc.)


# Alias for backwards compatibility
SearchRequest = TextSearchRequest


class AutocompleteRequest(BaseModel):
    """Autocomplete request"""
    prefix: str = Field(..., min_length=1, max_length=100)
    limit: int = Field(10, ge=1, le=20)


class AutocompleteResponse(BaseModel):
    """Autocomplete suggestions"""
    prefix: str
    suggestions: List[str]


class SearchStatsResponse(BaseModel):
    """Search engine statistics"""
    total_products: int
    semantic_indexed: int
    visual_indexed: int
    is_initialized: bool


class SearchAnalytics(BaseModel):
    """Search analytics data"""
    total_searches: int
    avg_results_returned: float
    top_queries: List[dict]
    zero_result_queries: List[str]
    avg_response_time_ms: float
