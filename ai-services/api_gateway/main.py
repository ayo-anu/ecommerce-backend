"""
API Gateway - Main FastAPI Application
Entry point for all AI services
"""
from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from prometheus_client import make_asgi_app
from contextlib import asynccontextmanager
import logging
import httpx
from datetime import datetime

from shared.config import get_settings
from shared.logger import setup_logging
from shared.redis_client import redis_client
from shared.vector_db import vector_db_client
from shared.monitoring import service_up
from .middleware import setup_middlewares
from .auth import (
    Token,
    create_access_token,
    get_current_active_user,
    User
)

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("🚀 Starting E-Commerce AI Gateway...")
    
    try:
        # Connect to Redis
        await redis_client.connect()
        logger.info("✅ Redis connected")
        
        # Connect to Qdrant
        vector_db_client.connect()
        logger.info("✅ Qdrant connected")
        
        # Mark service as up
        service_up.labels(service_name="api_gateway").set(1)
        
        logger.info("✅ API Gateway started successfully")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down API Gateway...")
    await redis_client.close()
    service_up.labels(service_name="api_gateway").set(0)
    logger.info("API Gateway shut down")


# Create FastAPI app
app = FastAPI(
    title="E-Commerce AI Platform",
    description="Production-grade AI microservices for e-commerce",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Setup middlewares
setup_middlewares(app)


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.errors(),
            "body": exc.body
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    checks = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "api_gateway",
        "checks": {}
    }
    
    # Check Redis
    try:
        await redis_client.redis.ping()
        checks["checks"]["redis"] = "ok"
    except:
        checks["checks"]["redis"] = "error"
        checks["status"] = "degraded"
    
    # Check Qdrant
    try:
        vector_db_client.client.get_collections()
        checks["checks"]["qdrant"] = "ok"
    except:
        checks["checks"]["qdrant"] = "error"
        checks["status"] = "degraded"
    
    status_code = 200 if checks["status"] == "healthy" else 503
    return JSONResponse(content=checks, status_code=status_code)


# Metrics endpoint for Prometheus
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "E-Commerce AI Platform API Gateway",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }


# Authentication endpoints
@app.post("/api/v1/auth/login", response_model=Token)
async def login(email: str, password: str):
    """
    Login endpoint - generates JWT token
    
    In production, validate against Django backend
    """
    # TODO: Validate credentials against Django backend
    # For now, create token directly
    
    token_data = {
        "sub": "user_uuid_here",  # User ID
        "email": email,
        "scopes": ["user"]
    }
    
    access_token = create_access_token(data=token_data)
    
    return Token(
        access_token=access_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@app.get("/api/v1/auth/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user information"""
    return current_user


# Proxy endpoints to AI services
@app.api_route(
    "/api/v1/recommendations/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE"]
)
async def proxy_recommendations(
    request: Request,
    path: str,
    current_user: User = Depends(get_current_active_user)
):
    """Proxy requests to recommendation service"""
    url = f"{settings.RECOMMENDATION_SERVICE_URL}/{path}"
    return await proxy_request(request, url)


@app.api_route(
    "/api/v1/search/{path:path}",
    methods=["GET", "POST"]
)
async def proxy_search(
    request: Request,
    path: str,
    current_user: User = Depends(get_current_active_user)
):
    """Proxy requests to search service"""
    url = f"{settings.SEARCH_SERVICE_URL}/{path}"
    return await proxy_request(request, url)


@app.api_route(
    "/api/v1/pricing/{path:path}",
    methods=["GET", "POST"]
)
async def proxy_pricing(
    request: Request,
    path: str,
    current_user: User = Depends(get_current_active_user)
):
    """Proxy requests to pricing service"""
    url = f"{settings.PRICING_SERVICE_URL}/{path}"
    return await proxy_request(request, url)


@app.api_route(
    "/api/v1/chat/{path:path}",
    methods=["GET", "POST"]
)
async def proxy_chatbot(
    request: Request,
    path: str,
    current_user: User = Depends(get_current_active_user)
):
    """Proxy requests to chatbot service"""
    url = f"{settings.CHATBOT_SERVICE_URL}/{path}"
    return await proxy_request(request, url)


@app.api_route(
    "/api/v1/fraud/{path:path}",
    methods=["GET", "POST"]
)
async def proxy_fraud(
    request: Request,
    path: str,
    current_user: User = Depends(get_current_active_user)
):
    """Proxy requests to fraud detection service"""
    url = f"{settings.FRAUD_SERVICE_URL}/{path}"
    return await proxy_request(request, url)


@app.api_route(
    "/api/v1/forecast/{path:path}",
    methods=["GET", "POST"]
)
async def proxy_forecast(
    request: Request,
    path: str,
    current_user: User = Depends(get_current_active_user)
):
    """Proxy requests to forecasting service"""
    url = f"{settings.FORECAST_SERVICE_URL}/{path}"
    return await proxy_request(request, url)


@app.api_route(
    "/api/v1/vision/{path:path}",
    methods=["GET", "POST"]
)
async def proxy_vision(
    request: Request,
    path: str,
    current_user: User = Depends(get_current_active_user)
):
    """Proxy requests to visual recognition service"""
    url = f"{settings.VISION_SERVICE_URL}/{path}"
    return await proxy_request(request, url)


async def proxy_request(request: Request, url: str):
    """
    Generic proxy function to forward requests to microservices
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Get request body
        body = await request.body()
        
        # Forward request
        try:
            response = await client.request(
                method=request.method,
                url=url,
                content=body,
                headers=dict(request.headers),
                params=dict(request.query_params)
            )
            
            return JSONResponse(
                content=response.json() if response.text else {},
                status_code=response.status_code,
                headers=dict(response.headers)
            )
            
        except httpx.RequestError as e:
            logger.error(f"Proxy request failed: {e}")
            return JSONResponse(
                status_code=503,
                content={"detail": "Service temporarily unavailable"}
            )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api_gateway.main:app",
        host=settings.GATEWAY_HOST,
        port=settings.GATEWAY_PORT,
        reload=settings.DEBUG
    )
