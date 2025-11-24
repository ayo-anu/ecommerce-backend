"""
Pricing Engine API Router - Dynamic pricing and optimization
Handles price recommendations, competitor analysis, and discounts
"""
from fastapi import APIRouter, HTTPException
from typing import List
import logging

from ..schemas.pricing import (
    ProductPriceRequest,
    PriceRecommendation,
    BulkPricingRequest,
    BulkPricingResponse,
    CompetitorAnalysisRequest,
    CompetitorAnalysisResponse,
    DiscountOptimizationRequest,
    DiscountRecommendation,
    PriceElasticityRequest,
    PriceElasticityResponse,
    ABTestRequest,
    ABTestResult,
    PricingRules,
    PricingStatsResponse
)
from ..models.dynamic_pricing import DynamicPricingEngine
from ..models.competitor_analysis import CompetitorAnalyzer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pricing", tags=["pricing"])

# Global pricing engine instance
pricing_engine = DynamicPricingEngine()
competitor_analyzer = CompetitorAnalyzer()


@router.post("/recommend", response_model=PriceRecommendation)
async def get_price_recommendation(request: ProductPriceRequest):
    """
    Get optimal price recommendation for a product
    
    Uses dynamic pricing algorithm considering:
    - Cost and margins
    - Competitor prices
    - Inventory levels
    - Sales velocity
    - Market conditions
    """
    try:
        recommendation = pricing_engine.recommend_price(request.dict())
        
        logger.info(
            f"Price recommendation for {request.product_id}: "
            f"${recommendation['recommended_price']:.2f} "
            f"({recommendation['price_change_percent']:+.1f}%)"
        )
        
        return PriceRecommendation(**recommendation)
        
    except Exception as e:
        logger.error(f"Price recommendation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommend/bulk", response_model=BulkPricingResponse)
async def bulk_price_recommendations(request: BulkPricingRequest):
    """
    Get price recommendations for multiple products
    
    Efficient bulk processing for catalog-wide pricing updates
    """
    try:
        products_data = [p.dict() for p in request.products]
        results = pricing_engine.bulk_recommend(products_data)
        
        recommendations = [PriceRecommendation(**r) for r in results['recommendations']]
        
        logger.info(
            f"Bulk pricing: {len(recommendations)} products, "
            f"avg change: {results['avg_price_change']:.1f}%"
        )
        
        return BulkPricingResponse(
            total_products=len(recommendations),
            recommendations=recommendations,
            avg_price_change=results['avg_price_change'],
            total_revenue_impact=results.get('total_revenue_impact')
        )
        
    except Exception as e:
        logger.error(f"Bulk pricing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/competitor/analyze", response_model=CompetitorAnalysisResponse)
async def analyze_competitors(request: CompetitorAnalysisRequest):
    """
    Analyze competitor pricing and market position
    
    Provides insights on competitive positioning
    """
    try:
        analysis = competitor_analyzer.analyze(
            product_id=request.product_id,
            our_price=request.our_price,
            competitor_prices=[c.dict() for c in request.competitor_prices]
        )
        
        logger.info(
            f"Competitor analysis for {request.product_id}: "
            f"position={analysis['market_position']}"
        )
        
        return CompetitorAnalysisResponse(**analysis)
        
    except Exception as e:
        logger.error(f"Competitor analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/discount/optimize", response_model=DiscountRecommendation)
async def optimize_discount(request: DiscountOptimizationRequest):
    """
    Calculate optimal discount to achieve target sales
    
    Balances discount depth with profit margins
    """
    try:
        recommendation = pricing_engine.optimize_discount(request.dict())
        
        logger.info(
            f"Discount optimization for {request.product_id}: "
            f"{recommendation['discount_percent']:.1f}% off, "
            f"expected {recommendation['expected_units_sold']} units"
        )
        
        return DiscountRecommendation(**recommendation)
        
    except Exception as e:
        logger.error(f"Discount optimization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/elasticity", response_model=PriceElasticityResponse)
async def calculate_elasticity(request: PriceElasticityRequest):
    """
    Calculate price elasticity of demand
    
    Determines how price changes affect demand
    """
    try:
        analysis = pricing_engine.calculate_elasticity(
            product_id=request.product_id,
            historical_data=request.historical_data
        )
        
        logger.info(
            f"Elasticity for {request.product_id}: "
            f"{analysis['elasticity_coefficient']:.2f} "
            f"({analysis['interpretation']})"
        )
        
        return PriceElasticityResponse(**analysis)
        
    except Exception as e:
        logger.error(f"Elasticity calculation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/abtest/create")
async def create_ab_test(request: ABTestRequest):
    """
    Create A/B test for price comparison
    
    Test different price points to optimize revenue
    """
    try:
        test_id = pricing_engine.create_ab_test(request.dict())
        
        logger.info(
            f"Created A/B test for {request.product_id}: "
            f"control=${request.control_price} vs test=${request.test_price}"
        )
        
        return {
            "test_id": test_id,
            "product_id": request.product_id,
            "status": "active",
            "duration_days": request.test_duration_days,
            "message": "A/B test created successfully"
        }
        
    except Exception as e:
        logger.error(f"A/B test creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/abtest/{test_id}", response_model=ABTestResult)
async def get_ab_test_results(test_id: str):
    """
    Get A/B test results
    
    Returns statistical analysis of price test
    """
    try:
        results = pricing_engine.get_ab_test_results(test_id)
        
        if not results:
            raise HTTPException(status_code=404, detail="A/B test not found")
        
        return ABTestResult(**results)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"A/B test results error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rules/update")
async def update_pricing_rules(rules: PricingRules):
    """
    Update global pricing rules and constraints
    
    Controls pricing behavior across all products
    """
    try:
        pricing_engine.update_rules(rules.dict())
        
        logger.info(f"Pricing rules updated: {rules.dict()}")
        
        return {
            "status": "success",
            "message": "Pricing rules updated",
            "rules": rules.dict()
        }
        
    except Exception as e:
        logger.error(f"Rules update error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rules")
async def get_pricing_rules():
    """Get current pricing rules"""
    try:
        rules = pricing_engine.get_rules()
        return PricingRules(**rules)
        
    except Exception as e:
        logger.error(f"Rules retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/simulate")
async def simulate_price_change(
    product_id: str,
    current_price: float,
    new_price: float,
    current_demand: int = 100
):
    """
    Simulate impact of price change
    
    Predicts demand and revenue changes
    """
    try:
        simulation = pricing_engine.simulate_price_change(
            product_id=product_id,
            current_price=current_price,
            new_price=new_price,
            current_demand=current_demand
        )
        
        return simulation
        
    except Exception as e:
        logger.error(f"Simulation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=PricingStatsResponse)
async def get_pricing_stats():
    """
    Get pricing engine statistics
    
    Returns performance metrics and insights
    """
    try:
        stats = pricing_engine.get_stats()
        
        return PricingStatsResponse(**stats)
        
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{product_id}")
async def get_price_history(product_id: str, days: int = 30):
    """
    Get historical pricing data for product
    
    Shows price changes over time
    """
    try:
        history = pricing_engine.get_price_history(product_id, days)
        
        return {
            "product_id": product_id,
            "days": days,
            "history": history
        }
        
    except Exception as e:
        logger.error(f"History error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "pricing_engine",
        "rules_active": True
    }
