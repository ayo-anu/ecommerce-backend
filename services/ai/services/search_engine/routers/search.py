"""
Search API Router - Endpoints for all search functionality
Handles text, semantic, visual, and hybrid search
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from fastapi.responses import JSONResponse
from typing import Optional, List
import base64
from PIL import Image
import io
import logging

from ..schemas.search import (
    SearchRequest,
    SearchResponse,
    SearchResult,
    VisualSearchRequest,
    AutocompleteRequest,
    AutocompleteResponse,
    SearchStatsResponse
)
from ..models.hybrid_search import HybridSearchEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])

# Global search engine instance
search_engine = HybridSearchEngine()


@router.post("/initialize", status_code=200)
async def initialize_search_engine(products: List[dict]):
    """
    Initialize search engine with product catalog
    
    Indexes products for text, semantic, and visual search
    """
    try:
        search_engine.initialize(products)
        return {
            "status": "success",
            "message": f"Search engine initialized with {len(products)} products",
            "stats": search_engine.get_search_stats()
        }
    except Exception as e:
        logger.error(f"Search initialization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/text", response_model=SearchResponse)
async def text_search(request: SearchRequest):
    """
    Text-based product search
    
    Supports:
    - Keyword matching
    - Semantic understanding
    - Filter extraction from natural language
    - Spell correction
    """
    import time
    start_time = time.time()
    
    try:
        results = search_engine.search(
            query=request.query,
            top_k=request.top_k,
            filters=request.filters,
            search_mode="hybrid" if request.use_semantic else "text"
        )
        
        # Convert to SearchResult schema
        search_results = [
            SearchResult(
                product_id=r['id'],
                name=r['name'],
                description=r.get('description', ''),
                price=r.get('price', 0.0),
                image_url=r.get('primary_image', ''),
                category=r.get('category', ''),
                relevance_score=r['relevance_score'],
                tags=r.get('tags', [])
            )
            for r in results
        ]
        
        processing_time = (time.time() - start_time) * 1000
        
        return SearchResponse(
            query=request.query,
            total_results=len(search_results),
            results=search_results,
            search_type="hybrid" if request.use_semantic else "text",
            processing_time_ms=processing_time
        )
        
    except Exception as e:
        logger.error(f"Text search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/semantic", response_model=SearchResponse)
async def semantic_search(request: SearchRequest):
    """
    Semantic search - understands user intent
    
    Uses sentence transformers to understand meaning beyond keywords
    """
    import time
    start_time = time.time()
    
    try:
        results = search_engine.search(
            query=request.query,
            top_k=request.top_k,
            filters=request.filters,
            search_mode="semantic"
        )
        
        search_results = [
            SearchResult(
                product_id=r['id'],
                name=r['name'],
                description=r.get('description', ''),
                price=r.get('price', 0.0),
                image_url=r.get('primary_image', ''),
                category=r.get('category', ''),
                relevance_score=r['relevance_score'],
                tags=r.get('tags', [])
            )
            for r in results
        ]
        
        processing_time = (time.time() - start_time) * 1000
        
        return SearchResponse(
            query=request.query,
            total_results=len(search_results),
            results=search_results,
            search_type="semantic",
            processing_time_ms=processing_time
        )
        
    except Exception as e:
        logger.error(f"Semantic search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/visual", response_model=SearchResponse)
async def visual_search_base64(request: VisualSearchRequest):
    """
    Visual search using base64-encoded image
    
    Find similar products by uploading an image
    """
    try:
        # Decode base64 image
        image = search_engine.visual_model.load_image_from_base64(request.image_base64)
        if image is None:
            raise HTTPException(status_code=400, detail="Invalid image data")
        
        results = search_engine.search(
            image=image,
            top_k=request.top_k,
            filters=request.filters,
            search_mode="visual"
        )
        
        search_results = [
            SearchResult(
                product_id=r['id'],
                name=r['name'],
                description=r.get('description', ''),
                price=r.get('price', 0.0),
                image_url=r.get('primary_image', ''),
                category=r.get('category', ''),
                relevance_score=r['relevance_score'],
                tags=r.get('tags', [])
            )
            for r in results
        ]
        
        return SearchResponse(
            query="<visual search>",
            total_results=len(search_results),
            results=search_results,
            search_type="visual"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Visual search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/visual/upload")
async def visual_search_upload(
    file: UploadFile = File(...),
    top_k: int = Query(20, ge=1, le=100)
):
    """
    Visual search by uploading image file
    
    Accepts: JPEG, PNG, WebP
    """
    try:
        # Validate file type
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read and open image
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert('RGB')
        
        results = search_engine.search(
            image=image,
            top_k=top_k,
            search_mode="visual"
        )
        
        search_results = [
            SearchResult(
                product_id=r['id'],
                name=r['name'],
                description=r.get('description', ''),
                price=r.get('price', 0.0),
                image_url=r.get('primary_image', ''),
                category=r.get('category', ''),
                relevance_score=r['relevance_score'],
                tags=r.get('tags', [])
            )
            for r in results
        ]
        
        return SearchResponse(
            query="<visual upload>",
            total_results=len(search_results),
            results=search_results,
            search_type="visual"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Visual upload search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/hybrid", response_model=SearchResponse)
async def hybrid_search(
    query: Optional[str] = None,
    image_base64: Optional[str] = None,
    top_k: int = Query(20, ge=1, le=100),
    filters: Optional[dict] = None
):
    """
    Hybrid search - combines text, semantic, and visual
    
    Best results by fusing multiple search strategies
    """
    try:
        image = None
        if image_base64:
            image = search_engine.visual_model.load_image_from_base64(image_base64)
        
        results = search_engine.search(
            query=query,
            image=image,
            top_k=top_k,
            filters=filters,
            search_mode="hybrid"
        )
        
        search_results = [
            SearchResult(
                product_id=r['id'],
                name=r['name'],
                description=r.get('description', ''),
                price=r.get('price', 0.0),
                image_url=r.get('primary_image', ''),
                category=r.get('category', ''),
                relevance_score=r['relevance_score'],
                tags=r.get('tags', [])
            )
            for r in results
        ]
        
        return SearchResponse(
            query=query or "<hybrid search>",
            total_results=len(search_results),
            results=search_results,
            search_type="hybrid"
        )
        
    except Exception as e:
        logger.error(f"Hybrid search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/autocomplete", response_model=AutocompleteResponse)
async def autocomplete(request: AutocompleteRequest):
    """
    Autocomplete suggestions for search queries
    
    Returns popular/relevant query completions
    """
    try:
        suggestions = search_engine.autocomplete(request.prefix, request.limit)
        
        # Ensure suggestions is a list
        if not isinstance(suggestions, list):
            suggestions = []
        
        return AutocompleteResponse(
            prefix=request.prefix,
            suggestions=suggestions
        )
        
    except Exception as e:
        logger.error(f"Autocomplete error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=SearchStatsResponse)
async def get_search_stats():
    """
    Get search engine statistics
    
    Returns indexing status and performance metrics
    """
    try:
        stats = search_engine.get_search_stats()
        
        return SearchStatsResponse(
            total_products=stats['total_products'],
            semantic_indexed=stats['semantic_indexed'],
            visual_indexed=stats['visual_indexed'],
            is_initialized=stats['is_initialized']
        )
        
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "search_engine",
        "initialized": search_engine.is_initialized
    }
