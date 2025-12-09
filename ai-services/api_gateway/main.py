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
from shared.tracing import setup_tracing
from .middleware import setup_middlewares
from .auth import (
    Token,
    create_access_token,
    get_current_active_user,
    User
)
from .resilient_proxy import (
    proxy_registry,
    CircuitBreakerConfig,
    RetryConfig,
    TimeoutConfig,
)
from .circuit_breaker import circuit_breaker_registry
from enhanced_middleware import TraceMiddleware


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
app.add_middleware(TraceMiddleware)

# Setup distributed tracing
tracer = setup_tracing(app, "api-gateway")

# Include gateway routes (central routing table)
from . import gateway_routes
app.include_router(gateway_routes.router, prefix="", tags=["gateway"])
logger.info("✅ Gateway routing table initialized")

# Include standardized health checks with dependency validation
from shared.health import create_health_router
health_router = create_health_router(
    service_name="api-gateway",
    version="1.0.0",
    dependencies=["redis", "qdrant"]
)
app.include_router(health_router)
logger.info("✅ Standardized health checks enabled (/health/live, /health/ready)")

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
    proxy = proxy_registry.get_proxy(
        "recommendation-service",
        service_auth_secret=settings.SERVICE_AUTH_SECRET_RECOMMENDATION_ENGINE
    )
    return await proxy.proxy_request(request, url)


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
    proxy = proxy_registry.get_proxy(
        "search-service",
        service_auth_secret=settings.SERVICE_AUTH_SECRET_SEARCH_ENGINE
    )
    return await proxy.proxy_request(request, url)


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
    proxy = proxy_registry.get_proxy(
        "pricing-service",
        service_auth_secret=settings.SERVICE_AUTH_SECRET_PRICING_ENGINE
    )
    return await proxy.proxy_request(request, url)


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
    proxy = proxy_registry.get_proxy(
        "chatbot-service",
        service_auth_secret=settings.SERVICE_AUTH_SECRET_CHATBOT_RAG
    )
    return await proxy.proxy_request(request, url)


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
    proxy = proxy_registry.get_proxy(
        "fraud-service",
        service_auth_secret=settings.SERVICE_AUTH_SECRET_FRAUD_DETECTION
    )
    return await proxy.proxy_request(request, url)


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
    proxy = proxy_registry.get_proxy(
        "forecasting-service",
        service_auth_secret=settings.SERVICE_AUTH_SECRET_FORECASTING
    )
    return await proxy.proxy_request(request, url)


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
    proxy = proxy_registry.get_proxy(
        "vision-service",
        service_auth_secret=settings.SERVICE_AUTH_SECRET_VISUAL_RECOGNITION
    )
    return await proxy.proxy_request(request, url)


@app.get("/api/v1/circuit-breakers")
async def get_circuit_breaker_states(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current state of all circuit breakers.

    Requires authentication.
    """
    states = circuit_breaker_registry.get_all_states()
    proxy_states = proxy_registry.get_all_circuit_states()

    return {
        "circuit_breakers": states,
        "proxy_circuits": proxy_states,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.post("/api/v1/circuit-breakers/{service_name}/reset")
async def reset_circuit_breaker(
    service_name: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Manually reset a circuit breaker.

    Requires authentication. Use with caution.
    """
    circuit_breaker_registry.reset_breaker(service_name)

    return {
        "message": f"Circuit breaker '{service_name}' has been reset",
        "timestamp": datetime.utcnow().isoformat(),
    }

async def check_service(url: str, timeout: float = 3.0):
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(url)
        return r.status_code == 200
    except Exception:
        return False

@app.get("/health")
async def health():
    # Liveness: is the gateway alive?
    return {"status": "ok", "service": "gateway"}

@app.get("/readiness")
async def readiness():
    results = {
        "gateway": True,
        "backend": await check_service("http://backend:8000/health"),
        "recommender": await check_service("http://recommender:8001/health"),
        "search": await check_service("http://search:8002/health"),
        "pricing": await check_service("http://pricing:8003/health"),
        "chatbot": await check_service("http://chatbot:8004/health"),
        "fraud": await check_service("http://fraud:8005/health"),
        "forecasting": await check_service("http://forecasting:8006/health"),
        "vision": await check_service("http://vision:8007/health")
    }

    overall = all(results.values())
    return JSONResponse(
        status_code=200 if overall else 503,
        content={"ok": overall, "services": results}
    )




if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api_gateway.main:app",
        host=settings.GATEWAY_HOST,
        port=settings.GATEWAY_PORT,
        reload=settings.DEBUG
    )
