"""
Pricing Engine Schemas - Request/Response models
Dynamic pricing, optimization, and competitor analysis
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class PricingStrategy(str, Enum):
    """Pricing strategy types"""
    COST_PLUS = "cost_plus"
    COMPETITIVE = "competitive"
    DYNAMIC = "dynamic"
    PENETRATION = "penetration"
    PREMIUM = "premium"
    PSYCHOLOGICAL = "psychological"


class PriceAdjustmentReason(str, Enum):
    """Reasons for price changes"""
    DEMAND = "demand"
    COMPETITION = "competition"
    INVENTORY = "inventory"
    SEASONALITY = "seasonality"
    PROMOTION = "promotion"
    COST_CHANGE = "cost_change"


class ProductPriceRequest(BaseModel):
    """Request for product pricing"""
    product_id: str
    base_cost: float = Field(..., gt=0, description="Product cost")
    current_price: Optional[float] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    
    # Market data
    competitor_prices: Optional[List[float]] = None
    market_average: Optional[float] = None
    
    # Inventory data
    current_stock: int = Field(default=100, ge=0)
    target_stock: Optional[int] = None
    
    # Sales data
    units_sold_7d: int = Field(default=0, ge=0)
    units_sold_30d: int = Field(default=0, ge=0)
    conversion_rate: Optional[float] = Field(None, ge=0, le=1)
    
    # Constraints
    min_margin_percent: float = Field(default=20.0, ge=0, le=100)
    max_discount_percent: float = Field(default=50.0, ge=0, le=100)
    
    strategy: PricingStrategy = PricingStrategy.DYNAMIC


class PriceRecommendation(BaseModel):
    """Recommended price with reasoning"""
    product_id: str
    recommended_price: float
    current_price: Optional[float]
    price_change_percent: float
    
    # Margins
    margin_percent: float
    profit_per_unit: float
    
    # Reasoning
    strategy_used: PricingStrategy
    adjustment_reasons: List[PriceAdjustmentReason]
    confidence_score: float = Field(..., ge=0, le=1)
    
    # Predictions
    estimated_demand_change: Optional[float] = None
    estimated_revenue_impact: Optional[float] = None
    
    # Comparisons
    vs_market_average: Optional[float] = None
    vs_competitors: Optional[str] = None  # "lower", "similar", "higher"
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class BulkPricingRequest(BaseModel):
    """Bulk pricing update request"""
    products: List[ProductPriceRequest]
    apply_changes: bool = Field(default=False)


class BulkPricingResponse(BaseModel):
    """Bulk pricing results"""
    total_products: int
    recommendations: List[PriceRecommendation]
    avg_price_change: float
    total_revenue_impact: Optional[float] = None


class CompetitorPrice(BaseModel):
    """Competitor price data"""
    competitor_name: str
    product_id: str
    price: float
    in_stock: bool = True
    url: Optional[str] = None
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class CompetitorAnalysisRequest(BaseModel):
    """Request for competitor analysis"""
    product_id: str
    our_price: float
    competitor_prices: List[CompetitorPrice]


class CompetitorAnalysisResponse(BaseModel):
    """Competitor pricing analysis"""
    product_id: str
    our_price: float
    market_position: str  # "lowest", "competitive", "premium"
    
    # Statistics
    competitor_min: float
    competitor_max: float
    competitor_avg: float
    competitor_median: float
    
    # Recommendations
    price_gap: float
    recommended_action: str
    suggested_price: Optional[float] = None


class DiscountOptimizationRequest(BaseModel):
    """Request for discount optimization"""
    product_id: str
    base_price: float
    target_units: int
    current_demand: int
    available_stock: int
    
    # Constraints
    min_margin_percent: float = 20.0
    max_discount_percent: float = 50.0


class DiscountRecommendation(BaseModel):
    """Optimal discount recommendation"""
    product_id: str
    original_price: float
    discounted_price: float
    discount_percent: float
    
    # Predictions
    expected_units_sold: int
    expected_revenue: float
    expected_profit: float
    
    # Metrics
    margin_percent: float
    roi_score: float


class PriceElasticityRequest(BaseModel):
    """Request for price elasticity calculation"""
    product_id: str
    historical_data: List[Dict[str, Any]]  # price, units_sold, date


class PriceElasticityResponse(BaseModel):
    """Price elasticity analysis"""
    product_id: str
    elasticity_coefficient: float
    interpretation: str  # "elastic", "inelastic", "unit_elastic"
    
    # Predictions
    optimal_price_point: float
    max_revenue_price: float
    max_profit_price: float


class ABTestRequest(BaseModel):
    """A/B test for pricing"""
    product_id: str
    control_price: float
    test_price: float
    test_duration_days: int = 7


class ABTestResult(BaseModel):
    """A/B test results"""
    product_id: str
    control_price: float
    test_price: float
    
    # Metrics
    control_conversion: float
    test_conversion: float
    conversion_lift: float
    
    control_revenue: float
    test_revenue: float
    revenue_lift: float
    
    statistical_significance: bool
    confidence_level: float
    
    recommendation: str


class PricingRules(BaseModel):
    """Pricing rules and constraints"""
    min_margin_percent: float = 15.0
    max_discount_percent: float = 60.0
    round_to_99: bool = True  # Psychological pricing
    
    # Competitive rules
    match_competitors: bool = False
    undercut_by_percent: Optional[float] = None
    
    # Dynamic rules
    increase_on_low_stock: bool = True
    decrease_on_high_stock: bool = True
    seasonal_adjustments: bool = True


class PricingStatsResponse(BaseModel):
    """Pricing engine statistics"""
    total_products_managed: int
    avg_margin_percent: float
    total_recommendations_generated: int
    avg_price_optimization: float
    active_ab_tests: int


class PriceHistory(BaseModel):
    """Historical price data"""
    product_id: str
    price: float
    timestamp: datetime
    reason: Optional[str] = None
    margin_percent: float
