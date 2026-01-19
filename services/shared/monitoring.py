"""Prometheus metrics."""
from prometheus_client import Counter, Histogram, Gauge
import time
from functools import wraps
from typing import Callable

http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint']
)

model_inference_duration_seconds = Histogram(
    'model_inference_duration_seconds',
    'ML model inference time',
    ['model_name', 'service']
)

model_predictions_total = Counter(
    'model_predictions_total',
    'Total ML model predictions',
    ['model_name', 'service']
)

cache_hits_total = Counter('cache_hits_total', 'Total cache hits')
cache_misses_total = Counter('cache_misses_total', 'Total cache misses')

db_query_duration_seconds = Histogram(
    'db_query_duration_seconds',
    'Database query duration'
)

db_connections_active = Gauge(
    'db_connections_active',
    'Active database connections'
)

service_up = Gauge(
    'service_up',
    'Service health status',
    ['service_name']
)


def track_request_metrics(func: Callable) -> Callable:
    """Track request metrics."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            duration = time.time() - start_time
    
    return wrapper


def track_inference_time(model_name: str, service: str):
    """Track model inference time."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                model_predictions_total.labels(
                    model_name=model_name,
                    service=service
                ).inc()
                return result
            finally:
                duration = time.time() - start_time
                model_inference_duration_seconds.labels(
                    model_name=model_name,
                    service=service
                ).observe(duration)
        
        return wrapper
    return decorator


def setup_monitoring(app, service_name: str):
    """Setup Prometheus monitoring for a FastAPI app."""
    from fastapi import Request, Response
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    import time
    
    @app.middleware("http")
    async def prometheus_middleware(request: Request, call_next):
        """Track HTTP metrics."""
        start_time = time.time()
        
        response = await call_next(request)
        
        duration = time.time() - start_time
        http_requests_total.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()
        
        http_request_duration_seconds.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)
        
        return response
    
    @app.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint."""
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST
        )
    
    service_up.labels(service_name=service_name).set(1)
    
    return app
