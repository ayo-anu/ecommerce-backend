"""
Visual Recognition API Router
Computer vision endpoints for product images
"""
from fastapi import APIRouter, HTTPException
import logging
import time

from ..schemas.vision import *
from ..models.image_analyzer import ImageAnalyzer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vision", tags=["visual_recognition"])

# Global analyzer
analyzer = ImageAnalyzer()


@router.post("/analyze", response_model=ImageAnalysisResponse)
async def analyze_image(request: ImageAnalysisRequest):
    """
    Complete image analysis
    
    Includes quality assessment, object detection, color extraction, and tag generation
    """
    try:
        start_time = time.time()
        
        result = analyzer.analyze_image(
            image_base64=request.image_base64,
            analyze_quality=request.analyze_quality,
            detect_objects=request.detect_objects,
            extract_colors=request.extract_colors,
            generate_tags=request.generate_tags
        )
        
        processing_time = (time.time() - start_time) * 1000
        
        response = ImageAnalysisResponse(
            product_id=request.product_id,
            processing_time_ms=round(processing_time, 2),
            **result
        )
        
        logger.info(f"Image analyzed: quality={result.get('quality_metrics', {}).get('overall_quality')}")
        return response
        
    except Exception as e:
        logger.error(f"Image analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quality", response_model=ImageQualityMetrics)
async def assess_quality(image_base64: str):
    """Assess image quality only"""
    try:
        image = analyzer._decode_image(image_base64)
        if image is None:
            raise HTTPException(status_code=400, detail="Invalid image")
        
        metrics = analyzer._assess_quality(image)
        return ImageQualityMetrics(**metrics)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Quality assessment error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/colors", response_model=ColorExtractionResponse)
async def extract_colors(request: ColorExtractionRequest):
    """Extract dominant colors"""
    try:
        image = analyzer._decode_image(request.image_base64)
        if image is None:
            raise HTTPException(status_code=400, detail="Invalid image")
        
        colors = analyzer._extract_colors(image, request.num_colors)
        
        palette = [c['hex_code'] for c in colors]
        primary = colors[0]['name'] if colors else "unknown"
        
        return ColorExtractionResponse(
            colors=[ColorInfo(**c) for c in colors],
            color_palette=palette,
            primary_color=primary
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Color extraction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/category", response_model=CategoryPredictionResponse)
async def predict_category(request: CategoryPredictionRequest):
    """Predict product category"""
    try:
        image = analyzer._decode_image(request.image_base64)
        if image is None:
            raise HTTPException(status_code=400, detail="Invalid image")
        
        # Simplified category prediction
        category, confidence = analyzer._predict_category(image)
        
        predictions = [
            CategoryPrediction(
                category=ProductCategory.OTHER,
                confidence=confidence
            )
        ]
        
        return CategoryPredictionResponse(
            predictions=predictions,
            top_category=ProductCategory.OTHER,
            confidence=confidence
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Category prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tags", response_model=TagGenerationResponse)
async def generate_tags(request: TagGenerationRequest):
    """Generate descriptive tags"""
    try:
        result = analyzer.analyze_image(
            image_base64=request.image_base64,
            analyze_quality=True,
            detect_objects=True,
            extract_colors=True,
            generate_tags=True
        )
        
        tags = result.get('tags', [])[:request.max_tags]
        
        # Simple confidence scores
        confidence_scores = {tag: 0.8 for tag in tags}
        
        return TagGenerationResponse(
            tags=tags,
            confidence_scores=confidence_scores
        )
        
    except Exception as e:
        logger.error(f"Tag generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare", response_model=ImageComparisonResponse)
async def compare_images(request: ImageComparisonRequest):
    """Compare two images for similarity"""
    try:
        result = analyzer.compare_images(
            request.image1_base64,
            request.image2_base64
        )
        
        return ImageComparisonResponse(**result)
        
    except Exception as e:
        logger.error(f"Image comparison error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scene", response_model=SceneUnderstandingResponse)
async def understand_scene(request: SceneUnderstandingRequest):
    """Understand image scene and context"""
    try:
        image = analyzer._decode_image(request.image_base64)
        if image is None:
            raise HTTPException(status_code=400, detail="Invalid image")
        
        description = analyzer._understand_scene(image)
        
        return SceneUnderstandingResponse(
            scene_type="indoor",
            scene_description=description,
            detected_context=["product", "photography"],
            is_product_focused=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Scene understanding error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch", response_model=BatchImageResponse)
async def batch_analyze(request: BatchImageRequest):
    """Batch process multiple images"""
    try:
        results = []
        total_time = 0
        
        for img_data in request.images:
            start = time.time()
            
            result = analyzer.analyze_image(
                image_base64=img_data['image_base64'],
                analyze_quality=True,
                detect_objects=True,
                extract_colors=True,
                generate_tags=True
            )
            
            proc_time = (time.time() - start) * 1000
            total_time += proc_time
            
            results.append(ImageAnalysisResponse(
                product_id=img_data.get('product_id'),
                processing_time_ms=round(proc_time, 2),
                **result
            ))
        
        avg_time = total_time / len(request.images) if request.images else 0
        
        logger.info(f"Batch processed {len(request.images)} images")
        
        return BatchImageResponse(
            total_images=len(results),
            results=results,
            avg_processing_time_ms=round(avg_time, 2)
        )
        
    except Exception as e:
        logger.error(f"Batch analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=RecognitionStatsResponse)
async def get_stats():
    """Get service statistics"""
    try:
        stats = analyzer.get_stats()
        
        return RecognitionStatsResponse(
            most_common_category=None,
            **stats
        )
        
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check"""
    return {
        "status": "healthy",
        "service": "visual_recognition",
        "images_processed": analyzer.stats['images_processed']
    }
