# API Gateway

Production-grade API Gateway for AI microservices with advanced resilience patterns.

## Features

### 🛡️ Circuit Breaker
Prevents cascading failures by failing fast when services are down.

**States:**
- **CLOSED**: Normal operation, requests pass through
- **OPEN**: Service failing, requests fail immediately
- **HALF_OPEN**: Testing recovery, allows limited requests

**Configuration:**
```python
from circuit_breaker import CircuitBreakerConfig

config = CircuitBreakerConfig(
    failure_threshold=5,  # Failures to open circuit
    success_threshold=2,  # Successes to close circuit
    timeout=60,  # Seconds before retry
    window_size=100,  # Sliding window size
)
```

### 🚦 Rate Limiting
Protects services from abuse using token bucket algorithm.

**Limits:**
- Per minute: 60 requests (default)
- Per hour: 1000 requests (default)
- Tracked by user ID or IP address

**Response Headers:**
```
X-RateLimit-Limit-Minute: 60
X-RateLimit-Remaining-Minute: 45
X-RateLimit-Reset-Minute: 1732123456
Retry-After: 42
```

### 🔗 Correlation IDs
Distributed tracing across all microservices.

Every request gets a unique correlation ID that flows through the entire system.

**Headers:**
- Request: `X-Correlation-ID` (auto-generated if not provided)
- Response: `X-Correlation-ID` (same as request)

### ⚡ Performance Tracking
Automatic timing and monitoring of all requests.

**Metrics Exposed:**
- `http_requests_total` - Total request count
- `http_request_duration_seconds` - Request latency
- `http_request_errors_total` - Error count
- `circuit_breaker_state` - Circuit breaker status

### 📝 Request Logging
Structured JSON logs with correlation IDs.

```json
{
  "timestamp": "2025-11-27T10:30:00Z",
  "level": "INFO",
  "message": "Request completed",
  "correlation_id": "abc-123-def",
  "method": "POST",
  "path": "/api/v1/recommendations",
  "status_code": 200,
  "duration_ms": 145.23
}
```

## Architecture

```
┌──────────┐
│  Client  │
└────┬─────┘
     │ HTTP Request
     ▼
┌─────────────────────────────────────┐
│      Enhanced Middlewares           │
│  1. Correlation ID                  │
│  2. Request Logging                 │
│  3. Error Handling                  │
└────┬────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────┐
│      Rate Limiter                   │
│  Check Redis for rate limits        │
└────┬────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────┐
│      Circuit Breaker                │
│  Check service health               │
└────┬────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────┐
│      Proxy to Microservice          │
│  Forward with retry logic           │
└─────────────────────────────────────┘
```

## Endpoints

### Health Check
```
GET /health
```

Returns status of gateway and dependencies:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-27T10:30:00Z",
  "service": "api_gateway",
  "checks": {
    "redis": "ok",
    "qdrant": "ok"
  }
}
```

### Metrics
```
GET /metrics
```

Prometheus-compatible metrics endpoint.

### Circuit Breaker Status
```
GET /circuit-breakers
```

Returns state of all circuit breakers:
```json
{
  "recommendation-service": {
    "state": "closed",
    "failure_count": 0,
    "recent_failures": 0,
    "total_calls": 42
  }
}
```

### AI Service Routes

All AI services are proxied through the gateway:

- `POST /api/v1/recommendations/*` → Recommendation Service
- `POST /api/v1/search/*` → Search Service
- `POST /api/v1/pricing/*` → Pricing Service
- `POST /api/v1/chat/*` → Chatbot Service
- `POST /api/v1/fraud/*` → Fraud Detection
- `POST /api/v1/forecast/*` → Demand Forecasting
- `POST /api/v1/vision/*` → Visual Recognition

## Configuration

### Environment Variables

```bash
# Redis
REDIS_URL=redis://localhost:6379/0

# Qdrant
QDRANT_URL=http://localhost:6333

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000

# Circuit Breaker
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_TIMEOUT=60

# Service URLs
RECOMMENDATION_SERVICE_URL=http://recommender:8001
SEARCH_SERVICE_URL=http://search:8002
PRICING_SERVICE_URL=http://pricing:8003
CHATBOT_SERVICE_URL=http://chatbot:8004
FRAUD_SERVICE_URL=http://fraud:8005
FORECAST_SERVICE_URL=http://forecasting:8006
VISION_SERVICE_URL=http://vision:8007

# Logging
LOG_LEVEL=INFO
LOG_JSON=true
```

## Usage

### Start Gateway

```bash
# Development
uvicorn main:app --host 0.0.0.0 --port 8080 --reload

# Production
gunicorn main:app -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8080 --workers 4
```

### Docker

```bash
# Build
docker build -t ai-gateway .

# Run
docker run -p 8080:8080 --env-file .env ai-gateway
```

## Error Handling

The gateway returns standardized error responses:

### Rate Limit Exceeded (429)
```json
{
  "detail": {
    "error": "Rate limit exceeded",
    "limit_per_minute": 60,
    "limit_per_hour": 1000,
    "retry_after": 42
  }
}
```

### Circuit Breaker Open (503)
```json
{
  "error": {
    "type": "service_unavailable",
    "message": "Circuit breaker 'recommendation-service' is OPEN",
    "correlation_id": "abc-123"
  }
}
```

### Internal Error (500)
```json
{
  "error": {
    "type": "internal_server_error",
    "message": "An unexpected error occurred",
    "correlation_id": "abc-123"
  }
}
```

## Monitoring

### Prometheus Metrics

```bash
curl http://localhost:8080/metrics
```

Key metrics:
- `http_requests_total{method, endpoint, status}`
- `http_request_duration_seconds{method, endpoint}`
- `circuit_breaker_state{service}`
- `rate_limit_exceeded_total{identifier}`

### Health Checks

```bash
# Gateway health
curl http://localhost:8080/health

# Circuit breaker status
curl http://localhost:8080/circuit-breakers
```

## Best Practices

1. **Always include correlation ID** in external requests
2. **Monitor circuit breaker states** to detect service issues
3. **Set appropriate rate limits** based on service capacity
4. **Use structured logging** for better observability
5. **Configure circuit breakers** per service requirements

## Troubleshooting

### Circuit Breaker Stuck Open

```python
# Manually reset circuit breaker
from circuit_breaker import circuit_breaker_registry

circuit_breaker_registry.reset_breaker("recommendation-service")
```

### Rate Limit Too Restrictive

Update environment variables:
```bash
RATE_LIMIT_PER_MINUTE=120
RATE_LIMIT_PER_HOUR=5000
```

### High Latency

Check:
1. Microservice response times
2. Redis latency
3. Network issues
4. Resource utilization

## Development

### Running Tests

```bash
pytest tests/
```

### Code Quality

```bash
# Format
black api_gateway/

# Lint
flake8 api_gateway/

# Type check
mypy api_gateway/
```

## Production Deployment

1. **Use multiple workers** for high throughput:
   ```bash
   gunicorn main:app -k uvicorn.workers.UvicornWorker --workers 8
   ```

2. **Configure circuit breakers** conservatively:
   - Start with high thresholds
   - Tune based on observed failure rates

3. **Monitor rate limits**:
   - Track `rate_limit_exceeded_total` metric
   - Adjust limits as needed

4. **Set up alerts**:
   - Circuit breaker opens
   - High error rates
   - Slow response times

---

**Built with resilience and performance in mind** 🚀
