"""
API Gateway - Central Routing Table
====================================

This is the SINGLE CONTROL PLANE for all API traffic.
All requests from Nginx are routed through this gateway.

Architecture:
    Client → Nginx → API Gateway → Internal Services

Routing Map:
    /backend/*              → Django Backend (port 8000)
    /ai/recommender/*       → Recommendation Engine (port 8001)
    /ai/search/*            → Search Engine (port 8002)
    /ai/pricing/*           → Pricing Engine (port 8003)
    /ai/chatbot/*           → Chatbot RAG (port 8004)
    /ai/fraud/*             → Fraud Detection (port 8005)
    /ai/forecasting/*       → Demand Forecasting (port 8006)
    /ai/vision/*            → Visual Recognition (port 8007)
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
import httpx
import logging
from typing import Optional

from .resilient_proxy import proxy_registry, ResilientProxy
from .circuit_breaker import CircuitBreakerConfig

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# ==============================================================================
# SERVICE CONFIGURATION
# ==============================================================================

BACKEND_URL = "http://backend:8000"
AI_SERVICES = {
    "recommender": "http://recommender:8001",
    "search": "http://search:8002",
    "pricing": "http://pricing:8003",
    "chatbot": "http://chatbot:8004",
    "fraud": "http://fraud:8005",
    "forecasting": "http://forecasting:8006",
    "vision": "http://vision:8007",
}

# ==============================================================================
# ROUTE 1: DJANGO BACKEND
# ==============================================================================

@router.api_route(
    "/backend/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    tags=["backend"]
)
async def route_to_backend(request: Request, path: str):
    """
    Route all /backend/* requests to Django backend.
    
    Examples:
        /backend/api/products/ → http://backend:8000/api/products/
        /backend/api/auth/login/ → http://backend:8000/api/auth/login/
        /backend/admin/ → http://backend:8000/admin/
    """
    target_url = f"{BACKEND_URL}/{path}"
    
    # Get or create resilient proxy for backend
    proxy = proxy_registry.get_proxy(
        "backend",
        CircuitBreakerConfig(
            failure_threshold=5,
            success_threshold=2,
            timeout=30.0
        )
    )
    
    logger.info(f"Routing to backend: {path}")
    return await proxy.proxy_request(request, target_url)


# ==============================================================================
# ROUTE 2: AI MICROSERVICES
# ==============================================================================

@router.api_route(
    "/ai/recommender/{path:path}",
    methods=["GET", "POST"],
    tags=["ai", "recommender"]
)
async def route_to_recommender(request: Request, path: str):
    """
    Route to Recommendation Engine.
    
    Examples:
        /ai/recommender/user/123/ → http://recommender:8001/user/123/
        /ai/recommender/product/456/ → http://recommender:8001/product/456/
    """
    target_url = f"{AI_SERVICES['recommender']}/{path}"
    
    proxy = proxy_registry.get_proxy(
        "recommender",
        CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout=10.0
        )
    )
    
    logger.info(f"Routing to recommender: {path}")
    return await proxy.proxy_request(request, target_url)


@router.api_route(
    "/ai/search/{path:path}",
    methods=["GET", "POST"],
    tags=["ai", "search"]
)
async def route_to_search(request: Request, path: str):
    """
    Route to Search Engine.
    
    Examples:
        /ai/search/query/ → http://search:8002/query/
        /ai/search/suggest/ → http://search:8002/suggest/
    """
    target_url = f"{AI_SERVICES['search']}/{path}"
    
    proxy = proxy_registry.get_proxy(
        "search",
        CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout=10.0
        )
    )
    
    logger.info(f"Routing to search: {path}")
    return await proxy.proxy_request(request, target_url)


@router.api_route(
    "/ai/pricing/{path:path}",
    methods=["GET", "POST"],
    tags=["ai", "pricing"]
)
async def route_to_pricing(request: Request, path: str):
    """
    Route to Pricing Engine.
    
    Examples:
        /ai/pricing/calculate/ → http://pricing:8003/calculate/
        /ai/pricing/optimize/ → http://pricing:8003/optimize/
    """
    target_url = f"{AI_SERVICES['pricing']}/{path}"
    
    proxy = proxy_registry.get_proxy(
        "pricing",
        CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout=15.0
        )
    )
    
    logger.info(f"Routing to pricing: {path}")
    return await proxy.proxy_request(request, target_url)


@router.api_route(
    "/ai/chatbot/{path:path}",
    methods=["GET", "POST"],
    tags=["ai", "chatbot"]
)
async def route_to_chatbot(request: Request, path: str):
    """
    Route to Chatbot RAG Service.
    
    Examples:
        /ai/chatbot/query/ → http://chatbot:8004/query/
        /ai/chatbot/context/ → http://chatbot:8004/context/
    """
    target_url = f"{AI_SERVICES['chatbot']}/{path}"
    
    proxy = proxy_registry.get_proxy(
        "chatbot",
        CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout=30.0  # Longer timeout for LLM
        )
    )
    
    logger.info(f"Routing to chatbot: {path}")
    return await proxy.proxy_request(request, target_url)


@router.api_route(
    "/ai/fraud/{path:path}",
    methods=["POST"],
    tags=["ai", "fraud"]
)
async def route_to_fraud(request: Request, path: str):
    """
    Route to Fraud Detection Service.
    
    Examples:
        /ai/fraud/analyze/ → http://fraud:8005/analyze/
        /ai/fraud/score/ → http://fraud:8005/score/
    """
    target_url = f"{AI_SERVICES['fraud']}/{path}"
    
    proxy = proxy_registry.get_proxy(
        "fraud",
        CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout=5.0
        )
    )
    
    logger.info(f"Routing to fraud: {path}")
    return await proxy.proxy_request(request, target_url)


@router.api_route(
    "/ai/forecasting/{path:path}",
    methods=["GET", "POST"],
    tags=["ai", "forecasting"]
)
async def route_to_forecasting(request: Request, path: str):
    """
    Route to Demand Forecasting Service.
    
    Examples:
        /ai/forecasting/predict/ → http://forecasting:8006/predict/
        /ai/forecasting/trends/ → http://forecasting:8006/trends/
    """
    target_url = f"{AI_SERVICES['forecasting']}/{path}"
    
    proxy = proxy_registry.get_proxy(
        "forecasting",
        CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout=15.0
        )
    )
    
    logger.info(f"Routing to forecasting: {path}")
    return await proxy.proxy_request(request, target_url)


@router.api_route(
    "/ai/vision/{path:path}",
    methods=["POST"],
    tags=["ai", "vision"]
)
async def route_to_vision(request: Request, path: str):
    """
    Route to Visual Recognition Service.
    
    Examples:
        /ai/vision/classify/ → http://vision:8007/classify/
        /ai/vision/detect/ → http://vision:8007/detect/
    """
    target_url = f"{AI_SERVICES['vision']}/{path}"
    
    proxy = proxy_registry.get_proxy(
        "vision",
        CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout=20.0  # Longer timeout for image processing
        )
    )
    
    logger.info(f"Routing to vision: {path}")
    return await proxy.proxy_request(request, target_url)


# ==============================================================================
# ROUTE 3: HEALTH & STATUS
# ==============================================================================
# NOTE: For full health checks with dependency validation, use the standardized
# health router from shared.health module. This simple endpoint is kept for
# backward compatibility and basic liveness checks.

@router.get("/health", tags=["health"])
async def gateway_health():
    """
    Basic gateway health check endpoint.

    For detailed health with dependency checks, see:
    - /health/live - Kubernetes liveness probe
    - /health/ready - Kubernetes readiness probe (checks Redis, Qdrant)
    """
    return {
        "status": "healthy",
        "service": "api-gateway",
        "version": "1.0.0"
    }


@router.get("/routes", tags=["info"])
async def list_routes():
    """
    List all available routes through the gateway.
    Useful for documentation and debugging.
    """
    return {
        "gateway": "API Gateway - Single Control Plane",
        "routes": {
            "backend": {
                "pattern": "/backend/*",
                "target": BACKEND_URL,
                "description": "Django REST API"
            },
            "ai_services": {
                service: {
                    "pattern": f"/ai/{service}/*",
                    "target": url,
                    "description": f"{service.capitalize()} AI Service"
                }
                for service, url in AI_SERVICES.items()
            }
        },
        "notes": [
            "All routes protected by circuit breakers",
            "Automatic retry on transient failures",
            "Request/response logging enabled",
            "Distributed tracing active"
        ]
    }
