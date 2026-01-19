"""
Recommendation Engine API Router
All API endpoints for recommendations
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List
import time
import logging

from ..schemas.recommendation import (
    RecommendationRequest,
    RecommendationResponse,
    ProductRecommendation,
    UserInteraction,
    BatchRecommendationRequest,
    SimilarProductsRequest,
    ModelPerformance
)
from ..models.hybrid import HybridModel
from shared.redis_client import get_redis, RedisClient
from shared.monitoring import track_inference_time

logger = logging.getLogger(__name__)

router = APIRouter()

# Global model instance (initialized in main.py)
recommendation_models = {}


@router.get("/user/{user_id}", response_model=RecommendationResponse)
@track_inference_time(model_name="hybrid", service="recommendation")
async def get_user_recommendations(
    user_id: str,
    limit: int = 10,
    algorithm: str = "hybrid",
    redis: RedisClient = Depends(get_redis)
):
    """
    Get personalized product recommendations for a user
    
    Args:
        user_id: User UUID
        limit: Number of recommendations (1-100)
        algorithm: collaborative, content_based, or hybrid
        
    Returns:
        List of recommended products with scores
    """
    start_time = time.time()
    
    # Check cache first
    cache_key = f"recommendations:user:{user_id}:{algorithm}:{limit}"
    cached_result = await redis.get(cache_key)
    
    if cached_result:
        logger.info(f"Cache hit for user {user_id}")
        cached_result['cached'] = True
        return cached_result
    
    try:
        # Get user's interaction history (in production, fetch from Django/DB)
        # For now, using mock data
        user_history = await _get_user_history(user_id)
        
        # Get model
        model = recommendation_models.get('hybrid')
        if not model:
            raise HTTPException(status_code=503, detail="Model not loaded")
        
        # Generate recommendations
        if algorithm == "hybrid":
            recommendations = model.recommend(user_id, user_history, limit)
        elif algorithm == "collaborative":
            recommendations = model.collaborative_model.predict_for_user(user_id, limit)
        elif algorithm == "content_based":
            recommendations = model.content_model.recommend_for_user_history(user_history, limit)
        else:
            raise HTTPException(status_code=400, detail="Invalid algorithm")
        
        # Convert to response format
        product_recommendations = []
        for product_id, score in recommendations:
            # In production, fetch product metadata from Django
            product_data = await _get_product_metadata(product_id)
            
            product_recommendations.append(
                ProductRecommendation(
                    product_id=product_id,
                    score=float(score),
                    reason=_generate_reason(algorithm, score),
                    product_name=product_data.get('name'),
                    product_price=product_data.get('price'),
                    product_image=product_data.get('image')
                )
            )
        
        processing_time = (time.time() - start_time) * 1000
        
        response = RecommendationResponse(
            recommendations=product_recommendations,
            algorithm_used=algorithm,
            processing_time_ms=processing_time,
            user_id=user_id,
            cached=False
        )
        
        # Cache result for 5 minutes
        await redis.set(cache_key, response.dict(), expire=300)
        
        logger.info(f"Generated {len(product_recommendations)} recommendations for user {user_id}")
        return response
        
    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/product/{product_id}/similar", response_model=RecommendationResponse)
@track_inference_time(model_name="content_based", service="recommendation")
async def get_similar_products(
    product_id: str,
    limit: int = 10,
    redis: RedisClient = Depends(get_redis)
):
    """
    Get products similar to a given product
    
    Args:
        product_id: Product UUID
        limit: Number of similar products
        
    Returns:
        List of similar products with similarity scores
    """
    start_time = time.time()
    
    # Check cache
    cache_key = f"recommendations:similar:{product_id}:{limit}"
    cached_result = await redis.get(cache_key)
    
    if cached_result:
        logger.info(f"Cache hit for similar products to {product_id}")
        cached_result['cached'] = True
        return cached_result
    
    try:
        model = recommendation_models.get('hybrid')
        if not model:
            raise HTTPException(status_code=503, detail="Model not loaded")
        
        # Get similar products using content-based model
        similar_products = model.content_model.get_similar_products(product_id, limit)
        
        # Also try collaborative model for item-item similarity
        collab_similar = model.collaborative_model.get_similar_items(product_id, limit)
        
        # Combine results (weighted average)
        combined_scores = {}
        for pid, score in similar_products:
            combined_scores[pid] = score * 0.6
        
        for pid, score in collab_similar:
            if pid in combined_scores:
                combined_scores[pid] += score * 0.4
            else:
                combined_scores[pid] = score * 0.4
        
        # Sort and take top-k
        sorted_products = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)[:limit]
        
        # Format response
        product_recommendations = []
        for pid, score in sorted_products:
            product_data = await _get_product_metadata(pid)
            
            product_recommendations.append(
                ProductRecommendation(
                    product_id=pid,
                    score=float(score),
                    reason="Similar based on content and user behavior",
                    product_name=product_data.get('name'),
                    product_price=product_data.get('price'),
                    product_image=product_data.get('image')
                )
            )
        
        processing_time = (time.time() - start_time) * 1000
        
        response = RecommendationResponse(
            recommendations=product_recommendations,
            algorithm_used="content_collaborative_hybrid",
            processing_time_ms=processing_time,
            cached=False
        )
        
        # Cache for 10 minutes
        await redis.set(cache_key, response.dict(), expire=600)
        
        return response
        
    except Exception as e:
        logger.error(f"Error finding similar products: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch", response_model=List[RecommendationResponse])
async def get_batch_recommendations(
    request: BatchRecommendationRequest,
    redis: RedisClient = Depends(get_redis)
):
    """
    Get recommendations for multiple users at once
    
    Args:
        request: Batch request with user IDs
        
    Returns:
        List of recommendation responses
    """
    results = []
    
    for user_id in request.user_ids:
        try:
            recommendations = await get_user_recommendations(
                user_id=user_id,
                limit=request.limit,
                redis=redis
            )
            results.append(recommendations)
        except Exception as e:
            logger.error(f"Error processing user {user_id}: {e}")
            # Continue with other users
            
    return results


@router.post("/interaction")
async def record_interaction(
    interaction: UserInteraction,
    redis: RedisClient = Depends(get_redis)
):
    """
    Record a user interaction for model retraining
    
    Args:
        interaction: User interaction event
        
    Returns:
        Success status
    """
    try:
        # Store interaction for batch processing
        interaction_key = f"interactions:{interaction.user_id}"
        
        # Get existing interactions
        existing = await redis.get(interaction_key) or []
        existing.append(interaction.dict())
        
        # Store with 7-day expiration
        await redis.set(interaction_key, existing, expire=604800)
        
        # Invalidate user's recommendation cache
        pattern = f"recommendations:user:{interaction.user_id}:*"
        await redis.flush_pattern(pattern)
        
        logger.info(f"Recorded {interaction.interaction_type} interaction for user {interaction.user_id}")
        
        return {
            "status": "success",
            "message": "Interaction recorded",
            "user_id": interaction.user_id,
            "product_id": interaction.product_id
        }
        
    except Exception as e:
        logger.error(f"Error recording interaction: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trending")
async def get_trending_products(
    limit: int = 10,
    redis: RedisClient = Depends(get_redis)
):
    """
    Get currently trending products
    
    Args:
        limit: Number of trending products
        
    Returns:
        List of trending products
    """
    cache_key = f"recommendations:trending:{limit}"
    cached_result = await redis.get(cache_key)
    
    if cached_result:
        return cached_result
    
    try:
        model = recommendation_models.get('hybrid')
        if not model:
            raise HTTPException(status_code=503, detail="Model not loaded")
        
        # Get popular items from collaborative model
        trending = model.collaborative_model._get_popular_items(limit)
        
        trending_products = []
        for product_id, score in trending:
            product_data = await _get_product_metadata(product_id)
            
            trending_products.append({
                "product_id": product_id,
                "score": float(score),
                "product_name": product_data.get('name'),
                "product_price": product_data.get('price'),
                "product_image": product_data.get('image')
            })
        
        result = {
            "trending": trending_products,
            "generated_at": time.time()
        }
        
        # Cache for 1 hour
        await redis.set(cache_key, result, expire=3600)
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting trending products: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=ModelPerformance)
async def get_model_stats():
    """
    Get model performance statistics
    
    Returns:
        Model performance metrics
    """
    try:
        model = recommendation_models.get('hybrid')
        if not model:
            raise HTTPException(status_code=503, detail="Model not loaded")
        
        collab_stats = model.collaborative_model.get_model_stats()
        
        return ModelPerformance(
            model_name="hybrid_recommendation",
            last_trained=collab_stats.get('last_trained'),
            total_predictions=0,  # Track in production
            accuracy=None,  # Calculate from validation set
            precision=None,
            recall=None,
            f1_score=None
        )
        
    except Exception as e:
        logger.error(f"Error getting model stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/initialize")
async def initialize_products(products: List[dict]):
    """Initialize recommendation engine with product catalog"""
    try:
        model = recommendation_models.get('hybrid')
        if not model:
            raise HTTPException(status_code=503, detail="Model not loaded")
        
        # Load products into content-based model
        model.content_model.fit(products)
        
        logger.info(f"Initialized with {len(products)} products")
        
        return {
            "status": "success",
            "message": f"Initialized with {len(products)} products",
            "total_products": len(products)
        }
    except Exception as e:
        logger.error(f"Initialization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/load_interactions")
async def load_interactions(interactions: List[dict]):
    """Load user interaction history for recommendations"""
    try:
        model = recommendation_models.get('hybrid')
        if not model:
            raise HTTPException(status_code=503, detail="Model not loaded")
        
        # Train collaborative model with interactions
        model.collaborative_model.fit(interactions)
        
        logger.info(f"Loaded {len(interactions)} interactions")
        
        return {
            "status": "success",
            "message": f"Loaded {len(interactions)} interactions",
            "total_interactions": len(interactions)
        }
    except Exception as e:
        logger.error(f"Error loading interactions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Helper functions
async def _get_user_history(user_id: str) -> List[str]:
    """Get user product interaction history."""
    return []


async def _get_product_metadata(product_id: str) -> dict:
    """Get product metadata."""
    return {
        "name": f"Product {product_id[:8]}",
        "price": 99.99,
        "image": f"https://example.com/images/{product_id}.jpg"
    }


def _generate_reason(algorithm: str, score: float) -> str:
    """Generate human-readable recommendation reason"""
    if algorithm == "collaborative":
        return f"Users with similar taste also liked this (confidence: {score:.0%})"
    elif algorithm == "content_based":
        return f"Similar to products you've viewed (match: {score:.0%})"
    else:
        return f"Recommended based on your preferences (score: {score:.0%})"
