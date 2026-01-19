"""
Pydantic schemas for recommendation engine
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class ProductRecommendation(BaseModel):
    """Single product recommendation"""
    product_id: str
    score: float = Field(..., ge=0.0, le=1.0, description="Recommendation score")
    reason: str = Field(..., description="Why this product is recommended")
    product_name: Optional[str] = None
    product_price: Optional[float] = None
    product_image: Optional[str] = None


class RecommendationRequest(BaseModel):
    """Request for recommendations"""
    user_id: Optional[str] = None
    product_id: Optional[str] = None
    limit: int = Field(10, ge=1, le=100, description="Number of recommendations")
    include_metadata: bool = Field(True, description="Include product metadata")
    algorithm: Optional[str] = Field(None, description="collaborative, content_based, or hybrid")


class RecommendationResponse(BaseModel):
    """Response with recommendations"""
    recommendations: List[ProductRecommendation]
    algorithm_used: str
    processing_time_ms: float
    user_id: Optional[str] = None
    cached: bool = False


class UserInteraction(BaseModel):
    """User interaction event"""
    user_id: str
    product_id: str
    interaction_type: str = Field(..., description="view, cart, purchase, rating")
    value: Optional[float] = Field(None, description="Rating value if applicable")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class BatchRecommendationRequest(BaseModel):
    """Batch recommendation request"""
    user_ids: List[str]
    limit: int = Field(10, ge=1, le=50)


class SimilarProductsRequest(BaseModel):
    """Request for similar products"""
    product_id: str
    limit: int = Field(10, ge=1, le=50)
    similarity_threshold: float = Field(0.5, ge=0.0, le=1.0)


class ModelPerformance(BaseModel):
    """Model performance metrics"""
    model_name: str
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None
    last_trained: datetime
    total_predictions: int
