"""
Demand Forecasting Schemas - Request/Response models
Time series forecasting and inventory optimization
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum


class ForecastMethod(str, Enum):
    """Forecasting methods"""
    MOVING_AVERAGE = "moving_average"
    EXPONENTIAL_SMOOTHING = "exponential_smoothing"
    ARIMA = "arima"
    PROPHET = "prophet"
    LINEAR_REGRESSION = "linear_regression"
    SEASONAL_NAIVE = "seasonal_naive"


class SeasonalityType(str, Enum):
    """Seasonality patterns"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    NONE = "none"


class TrendType(str, Enum):
    """Trend directions"""
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    VOLATILE = "volatile"


class HistoricalDataPoint(BaseModel):
    """Single data point in time series"""
    date: date
    demand: int = Field(..., ge=0)
    price: Optional[float] = None
    promotion_active: bool = False
    events: Optional[List[str]] = []


class ForecastRequest(BaseModel):
    """Request for demand forecast"""
    product_id: str
    historical_data: List[HistoricalDataPoint]
    forecast_periods: int = Field(default=30, ge=1, le=365, description="Days to forecast")
    
    # Method selection
    method: ForecastMethod = ForecastMethod.EXPONENTIAL_SMOOTHING
    
    # Additional context
    current_price: Optional[float] = None
    planned_promotions: Optional[List[date]] = []
    
    # Confidence level
    confidence_level: float = Field(default=0.95, ge=0.8, le=0.99)
    
    @validator('historical_data')
    def validate_historical_data(cls, v):
        if len(v) < 7:
            raise ValueError('At least 7 days of historical data required')
        return v


class ForecastPoint(BaseModel):
    """Single forecast point"""
    date: date
    predicted_demand: float
    lower_bound: float
    upper_bound: float
    confidence: float


class ForecastResponse(BaseModel):
    """Forecast results"""
    product_id: str
    method_used: ForecastMethod
    forecast: List[ForecastPoint]
    
    # Accuracy metrics
    mae: Optional[float] = Field(None, description="Mean Absolute Error")
    mape: Optional[float] = Field(None, description="Mean Absolute Percentage Error")
    rmse: Optional[float] = Field(None, description="Root Mean Square Error")
    
    # Pattern analysis
    detected_seasonality: Optional[SeasonalityType] = None
    detected_trend: Optional[TrendType] = None
    
    # Summary statistics
    avg_predicted_demand: float
    total_predicted_demand: float
    peak_demand_date: date
    low_demand_date: date
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SeasonalityAnalysisRequest(BaseModel):
    """Request for seasonality detection"""
    product_id: str
    historical_data: List[HistoricalDataPoint]
    detect_periods: List[SeasonalityType] = [
        SeasonalityType.WEEKLY,
        SeasonalityType.MONTHLY,
        SeasonalityType.YEARLY
    ]


class SeasonalPattern(BaseModel):
    """Detected seasonal pattern"""
    period_type: SeasonalityType
    strength: float = Field(..., ge=0, le=1, description="Pattern strength")
    pattern: List[float]  # Average demand for each period
    peak_period: int
    low_period: int


class SeasonalityAnalysisResponse(BaseModel):
    """Seasonality analysis results"""
    product_id: str
    patterns_detected: List[SeasonalPattern]
    dominant_pattern: Optional[SeasonalityType] = None
    overall_seasonality_strength: float


class TrendAnalysisRequest(BaseModel):
    """Request for trend analysis"""
    product_id: str
    historical_data: List[HistoricalDataPoint]
    smoothing_window: int = Field(default=7, ge=3, le=30)


class TrendAnalysisResponse(BaseModel):
    """Trend analysis results"""
    product_id: str
    trend_type: TrendType
    trend_strength: float = Field(..., ge=0, le=1)
    growth_rate: float  # Percentage per period
    is_accelerating: bool
    
    # Predictions
    predicted_30d_change: float
    predicted_90d_change: float


class InventoryOptimizationRequest(BaseModel):
    """Request for inventory optimization"""
    product_id: str
    current_stock: int = Field(..., ge=0)
    lead_time_days: int = Field(..., ge=1, le=90)
    
    # Costs
    holding_cost_per_unit: float = Field(..., gt=0)
    stockout_cost_per_unit: float = Field(..., gt=0)
    order_cost: float = Field(..., gt=0)
    
    # Forecast data
    forecasted_demand: List[ForecastPoint]
    
    # Service level
    target_service_level: float = Field(default=0.95, ge=0.8, le=0.99)


class InventoryRecommendation(BaseModel):
    """Inventory optimization recommendation"""
    product_id: str
    
    # Current state
    current_stock: int
    forecasted_demand: float
    
    # Recommendations
    recommended_order_quantity: int
    reorder_point: int
    safety_stock: int
    
    # Timing
    days_until_stockout: Optional[int] = None
    recommended_order_date: date
    
    # Costs
    estimated_holding_cost: float
    estimated_stockout_risk: float
    total_estimated_cost: float


class PromotionalImpactRequest(BaseModel):
    """Analyze impact of promotions"""
    product_id: str
    historical_data: List[HistoricalDataPoint]
    promotion_dates: List[date]


class PromotionalImpactResponse(BaseModel):
    """Promotional impact analysis"""
    product_id: str
    avg_baseline_demand: float
    avg_promotional_demand: float
    demand_lift_percent: float
    
    # ROI metrics
    promotion_effectiveness_score: float = Field(..., ge=0, le=1)
    
    # Patterns
    pre_promotion_dip: bool
    post_promotion_recovery_days: int


class MultiForecastRequest(BaseModel):
    """Forecast multiple products"""
    products: List[ForecastRequest]
    aggregate_forecast: bool = Field(default=False)


class MultiForecastResponse(BaseModel):
    """Multi-product forecast results"""
    forecasts: List[ForecastResponse]
    
    # Aggregate metrics (if requested)
    total_predicted_demand: Optional[float] = None
    correlation_matrix: Optional[Dict[str, Dict[str, float]]] = None


class DemandAnomalyRequest(BaseModel):
    """Detect demand anomalies"""
    product_id: str
    historical_data: List[HistoricalDataPoint]
    sensitivity: float = Field(default=2.0, ge=1.0, le=5.0, description="Std dev threshold")


class DemandAnomaly(BaseModel):
    """Detected anomaly"""
    date: date
    actual_demand: int
    expected_demand: float
    deviation_percent: float
    anomaly_score: float = Field(..., ge=0, le=1)
    potential_cause: Optional[str] = None


class DemandAnomalyResponse(BaseModel):
    """Anomaly detection results"""
    product_id: str
    anomalies_detected: List[DemandAnomaly]
    total_anomalies: int
    anomaly_rate: float


class ForecastAccuracyRequest(BaseModel):
    """Evaluate forecast accuracy"""
    product_id: str
    predictions: List[ForecastPoint]
    actuals: List[HistoricalDataPoint]


class ForecastAccuracyResponse(BaseModel):
    """Forecast accuracy metrics"""
    product_id: str
    
    # Error metrics
    mae: float
    mape: float
    rmse: float
    mase: float  # Mean Absolute Scaled Error
    
    # Direction accuracy
    directional_accuracy: float = Field(..., ge=0, le=1)
    
    # Bias
    forecast_bias: float
    is_overforecasting: bool


class ForecastingStatsResponse(BaseModel):
    """Service statistics"""
    total_forecasts_generated: int
    total_products_tracked: int
    avg_forecast_accuracy: float
    most_common_method: ForecastMethod
    total_inventory_optimizations: int
