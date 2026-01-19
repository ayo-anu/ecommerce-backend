"""
Visual Recognition Schemas - Request/Response models
Computer vision for product images
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ImageQuality(str, Enum):
    """Image quality levels"""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"


class ProductCategory(str, Enum):
    """Common product categories"""
    CLOTHING = "clothing"
    ELECTRONICS = "electronics"
    FURNITURE = "furniture"
    FOOD = "food"
    TOYS = "toys"
    BOOKS = "books"
    SPORTS = "sports"
    BEAUTY = "beauty"
    HOME = "home"
    JEWELRY = "jewelry"
    AUTOMOTIVE = "automotive"
    OTHER = "other"


class ImageAnalysisRequest(BaseModel):
    """Request for image analysis"""
    image_base64: str = Field(..., description="Base64 encoded image")
    product_id: Optional[str] = None
    analyze_quality: bool = True
    detect_objects: bool = True
    extract_colors: bool = True
    generate_tags: bool = True


class ColorInfo(BaseModel):
    """Detected color information"""
    name: str
    hex_code: str
    percentage: float = Field(..., ge=0, le=100)
    rgb: tuple


class DetectedObject(BaseModel):
    """Detected object in image"""
    label: str
    confidence: float = Field(..., ge=0, le=1)
    bounding_box: Optional[Dict[str, int]] = None


class ImageQualityMetrics(BaseModel):
    """Image quality assessment"""
    overall_quality: ImageQuality
    resolution: tuple  # (width, height)
    file_size_kb: float
    
    # Quality factors
    sharpness_score: float = Field(..., ge=0, le=1)
    brightness_score: float = Field(..., ge=0, le=1)
    contrast_score: float = Field(..., ge=0, le=1)
    
    issues: List[str] = []
    recommendations: List[str] = []


class ImageAnalysisResponse(BaseModel):
    """Complete image analysis result"""
    product_id: Optional[str]
    
    # Quality assessment
    quality_metrics: Optional[ImageQualityMetrics] = None
    
    # Object detection
    detected_objects: List[DetectedObject] = []
    primary_object: Optional[str] = None
    
    # Color analysis
    dominant_colors: List[ColorInfo] = []
    
    # Category prediction
    predicted_category: Optional[ProductCategory] = None
    category_confidence: Optional[float] = None
    
    # Generated tags
    tags: List[str] = []
    
    # Scene understanding
    scene_description: Optional[str] = None
    
    processing_time_ms: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CategoryPredictionRequest(BaseModel):
    """Request for category prediction"""
    image_base64: str
    top_k: int = Field(default=3, ge=1, le=10)


class CategoryPrediction(BaseModel):
    """Single category prediction"""
    category: ProductCategory
    confidence: float = Field(..., ge=0, le=1)


class CategoryPredictionResponse(BaseModel):
    """Category prediction results"""
    predictions: List[CategoryPrediction]
    top_category: ProductCategory
    confidence: float


class LogoDetectionRequest(BaseModel):
    """Request for brand logo detection"""
    image_base64: str
    known_brands: Optional[List[str]] = None


class DetectedLogo(BaseModel):
    """Detected brand logo"""
    brand_name: str
    confidence: float = Field(..., ge=0, le=1)
    location: Optional[Dict[str, int]] = None


class LogoDetectionResponse(BaseModel):
    """Logo detection results"""
    logos_detected: List[DetectedLogo]
    has_logo: bool
    primary_brand: Optional[str] = None


class ColorExtractionRequest(BaseModel):
    """Request for color extraction"""
    image_base64: str
    num_colors: int = Field(default=5, ge=1, le=10)


class ColorExtractionResponse(BaseModel):
    """Color extraction results"""
    colors: List[ColorInfo]
    color_palette: List[str]  # Hex codes
    primary_color: str


class ImageComparisonRequest(BaseModel):
    """Compare two images"""
    image1_base64: str
    image2_base64: str
    comparison_type: str = Field(default="similarity")  # similarity, difference


class ImageComparisonResponse(BaseModel):
    """Image comparison results"""
    similarity_score: float = Field(..., ge=0, le=1)
    are_similar: bool
    differences: List[str] = []


class BatchImageRequest(BaseModel):
    """Batch image analysis"""
    images: List[Dict[str, str]]  # [{product_id, image_base64}]
    analysis_type: str = "full"  # full, quality_only, category_only


class BatchImageResponse(BaseModel):
    """Batch analysis results"""
    total_images: int
    results: List[ImageAnalysisResponse]
    avg_processing_time_ms: float


class TagGenerationRequest(BaseModel):
    """Generate tags from image"""
    image_base64: str
    max_tags: int = Field(default=10, ge=1, le=20)


class TagGenerationResponse(BaseModel):
    """Generated tags"""
    tags: List[str]
    confidence_scores: Dict[str, float]


class SceneUnderstandingRequest(BaseModel):
    """Understand scene/context"""
    image_base64: str


class SceneUnderstandingResponse(BaseModel):
    """Scene analysis"""
    scene_type: str  # indoor, outdoor, studio, etc.
    scene_description: str
    detected_context: List[str]
    is_product_focused: bool


class QualityImprovementRequest(BaseModel):
    """Suggest quality improvements"""
    image_base64: str


class QualityImprovementResponse(BaseModel):
    """Quality improvement suggestions"""
    current_quality: ImageQuality
    issues_found: List[str]
    recommendations: List[str]
    estimated_improvement: str


class VisualSearchRequest(BaseModel):
    """Visual similarity search"""
    query_image_base64: str
    catalog_images: List[Dict[str, str]]  # [{product_id, image_base64}]
    top_k: int = Field(default=10, ge=1, le=50)


class VisualSearchResult(BaseModel):
    """Similar image result"""
    product_id: str
    similarity_score: float
    thumbnail_url: Optional[str] = None


class VisualSearchResponse(BaseModel):
    """Visual search results"""
    results: List[VisualSearchResult]
    total_found: int


class RecognitionStatsResponse(BaseModel):
    """Service statistics"""
    total_images_processed: int
    avg_processing_time_ms: float
    most_common_category: Optional[ProductCategory]
    avg_quality_score: float
    total_tags_generated: int
