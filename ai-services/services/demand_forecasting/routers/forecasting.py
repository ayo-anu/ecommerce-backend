"""
Demand Forecasting API Router
Time series forecasting and inventory optimization endpoints
"""
from fastapi import APIRouter, HTTPException
import logging

from ..schemas.forecasting import *
from ..models.time_series import TimeSeriesForecaster
from ..models.inventory_optimizer import InventoryOptimizer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/forecast", tags=["forecasting"])

# Global instances
forecaster = TimeSeriesForecaster()
optimizer = InventoryOptimizer()


@router.post("/demand", response_model=ForecastResponse)
async def forecast_demand(request: ForecastRequest):
    """
    Generate demand forecast
    
    Supports multiple forecasting methods and confidence intervals
    """
    try:
        historical = [d.dict() for d in request.historical_data]
        
        result = forecaster.forecast(
            historical_data=historical,
            periods=request.forecast_periods,
            method=request.method.value,
            confidence_level=request.confidence_level
        )
        
        response = ForecastResponse(
            product_id=request.product_id,
            method_used=request.method,
            **result
        )
        
        logger.info(f"Forecast generated for {request.product_id}: {request.forecast_periods} periods")
        return response
        
    except Exception as e:
        logger.error(f"Forecast error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/seasonality", response_model=SeasonalityAnalysisResponse)
async def analyze_seasonality(request: SeasonalityAnalysisRequest):
    """Detect seasonal patterns in demand"""
    try:
        historical = [d.dict() for d in request.historical_data]
        period_types = [p.value for p in request.detect_periods]
        
        result = forecaster.analyze_seasonality(historical, period_types)
        
        response = SeasonalityAnalysisResponse(
            product_id=request.product_id,
            **result
        )
        
        logger.info(f"Seasonality analysis for {request.product_id}")
        return response
        
    except Exception as e:
        logger.error(f"Seasonality error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trend", response_model=TrendAnalysisResponse)
async def analyze_trend(request: TrendAnalysisRequest):
    """Analyze demand trends"""
    try:
        historical = [d.dict() for d in request.historical_data]
        
        result = forecaster.analyze_trend(historical, request.smoothing_window)
        
        response = TrendAnalysisResponse(
            product_id=request.product_id,
            **result
        )
        
        logger.info(f"Trend analysis for {request.product_id}: {result['trend_type']}")
        return response
        
    except Exception as e:
        logger.error(f"Trend error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/inventory/optimize", response_model=InventoryRecommendation)
async def optimize_inventory(request: InventoryOptimizationRequest):
    """Calculate optimal inventory levels"""
    try:
        forecasted = [f.dict() for f in request.forecasted_demand]
        
        result = optimizer.optimize(
            current_stock=request.current_stock,
            lead_time_days=request.lead_time_days,
            holding_cost=request.holding_cost_per_unit,
            stockout_cost=request.stockout_cost_per_unit,
            order_cost=request.order_cost,
            forecasted_demand=forecasted,
            service_level=request.target_service_level
        )
        
        response = InventoryRecommendation(
            product_id=request.product_id,
            current_stock=request.current_stock,
            **result
        )
        
        logger.info(f"Inventory optimization for {request.product_id}")
        return response
        
    except Exception as e:
        logger.error(f"Inventory optimization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/promotional/impact", response_model=PromotionalImpactResponse)
async def analyze_promotional_impact(request: PromotionalImpactRequest):
    """Analyze impact of promotions on demand"""
    try:
        historical = [d.dict() for d in request.historical_data]
        
        result = optimizer.analyze_promotional_impact(
            historical_data=historical,
            promotion_dates=request.promotion_dates
        )
        
        response = PromotionalImpactResponse(
            product_id=request.product_id,
            **result
        )
        
        logger.info(f"Promotional impact for {request.product_id}")
        return response
        
    except Exception as e:
        logger.error(f"Promotional impact error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/anomalies", response_model=DemandAnomalyResponse)
async def detect_anomalies(request: DemandAnomalyRequest):
    """Detect demand anomalies"""
    try:
        historical = [d.dict() for d in request.historical_data]
        
        result = optimizer.detect_anomalies(
            historical_data=historical,
            sensitivity=request.sensitivity
        )
        
        response = DemandAnomalyResponse(
            product_id=request.product_id,
            **result
        )
        
        logger.info(f"Anomaly detection for {request.product_id}: {result['total_anomalies']} found")
        return response
        
    except Exception as e:
        logger.error(f"Anomaly detection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/accuracy", response_model=ForecastAccuracyResponse)
async def evaluate_accuracy(request: ForecastAccuracyRequest):
    """Evaluate forecast accuracy"""
    try:
        predictions = [p.dict() for p in request.predictions]
        actuals = [a.dict() for a in request.actuals]
        
        result = optimizer.calculate_forecast_accuracy(
            predictions=predictions,
            actuals=actuals
        )
        
        response = ForecastAccuracyResponse(
            product_id=request.product_id,
            **result
        )
        
        logger.info(f"Accuracy evaluation for {request.product_id}: MAPE={result['mape']:.2f}%")
        return response
        
    except Exception as e:
        logger.error(f"Accuracy evaluation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=ForecastingStatsResponse)
async def get_stats():
    """Get forecasting service statistics"""
    try:
        return ForecastingStatsResponse(
            total_forecasts_generated=forecaster.stats.get('total_forecasts', 0),
            total_products_tracked=0,  # Would track in production
            avg_forecast_accuracy=0.85,  # Would calculate from history
            most_common_method=ForecastMethod.EXPONENTIAL_SMOOTHING,
            total_inventory_optimizations=optimizer.stats.get('optimizations', 0)
        )
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check"""
    return {"status": "healthy", "service": "demand_forecasting"}
