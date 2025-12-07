# Circuit Breakers & Resilience Patterns

**Last Updated**: 2025-12-04
**Status**: ✅ Implemented

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Implementation Details](#implementation-details)
4. [Usage Examples](#usage-examples)
5. [Configuration](#configuration)
6. [Monitoring & Metrics](#monitoring--metrics)
7. [Testing](#testing)
8. [Troubleshooting](#troubleshooting)

---

## Overview

This document describes the circuit breaker and resilience patterns implemented across the e-commerce platform to prevent cascading failures and improve system reliability.

### Key Features

- ✅ **Circuit Breakers** - Prevent cascading failures by failing fast when services are down
- ✅ **Retry Logic** - Exponential backoff with jitter for transient failures
- ✅ **Timeouts** - Configurable timeouts for all external calls
- ✅ **Fallbacks** - Graceful degradation when services are unavailable
- ✅ **Monitoring** - Comprehensive metrics and alerting via Prometheus/Grafana

### Benefits

1. **Improved Reliability** - System remains functional even when individual services fail
2. **Faster Failure Detection** - Circuit breakers detect failures quickly
3. **Resource Protection** - Prevents resource exhaustion from failing services
4. **Better User Experience** - Fallbacks provide degraded but functional service
5. **Observability** - Rich metrics for monitoring and debugging

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Client Request                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   API Gateway (FastAPI)                     │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  ResilientProxy (with Circuit Breaker + Retry)         │ │
│  │  - Circuit Breaker per service                         │ │
│  │  - Exponential backoff retry                           │ │
│  │  - Configurable timeouts                               │ │
│  │  - Prometheus metrics                                  │ │
│  └────────────────────────────────────────────────────────┘ │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ AI Service 1 │  │ AI Service 2 │  │ AI Service N │
│ (FastAPI)    │  │ (FastAPI)    │  │ (FastAPI)    │
└──────────────┘  └──────────────┘  └──────────────┘


┌─────────────────────────────────────────────────────────────┐
│                Django Backend (DRF)                         │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  ResilientAPIClient (with Circuit Breaker + Retry)     │ │
│  │  - Synchronous circuit breaker                         │ │
│  │  - Thread-safe implementation                          │ │
│  │  - Decorator-based (@with_retry)                       │ │
│  └────────────────────────────────────────────────────────┘ │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
                   AI Services (via Gateway)
```

### Circuit Breaker States

```
┌─────────────┐
│   CLOSED    │ ◄──┐ All requests pass through
│  (Normal)   │    │ Failures are tracked
└──────┬──────┘    │
       │           │
       │ Threshold │ Success
       │ Exceeded  │ Threshold
       │           │ Met
       ▼           │
┌─────────────┐    │
│    OPEN     │    │
│  (Failing)  │    │ Requests fail fast
└──────┬──────┘    │ No calls to service
       │           │
       │ Timeout   │
       │ Elapsed   │
       │           │
       ▼           │
┌─────────────┐    │
│ HALF_OPEN   │────┘ Limited requests allowed
│  (Testing)  │      Testing recovery
└─────────────┘
```

---

## Implementation Details

### API Gateway (FastAPI)

#### 1. Resilient Proxy

**Location**: `ai-services/api_gateway/resilient_proxy.py`

**Features**:
- Circuit breaker per AI service
- Exponential backoff retry (3 retries by default)
- Configurable timeouts (connect: 5s, read: 30s)
- Correlation ID propagation
- Prometheus metrics

**Key Classes**:
```python
class ResilientProxy:
    - Circuit breaker integration
    - Retry logic with exponential backoff
    - Timeout management
    - Error handling
    - Metrics tracking

class ProxyRegistry:
    - Manages proxies for all services
    - Singleton pattern
    - Service-specific configurations
```

#### 2. Circuit Breaker

**Location**: `ai-services/api_gateway/circuit_breaker.py`

**Configuration**:
```python
@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5      # Failures to open circuit
    success_threshold: int = 2      # Successes to close circuit
    timeout: int = 60              # Seconds before retry
    window_size: int = 100         # Sliding window size
```

**States**:
- **CLOSED**: Normal operation, all requests pass through
- **OPEN**: Too many failures, requests fail fast
- **HALF_OPEN**: Testing recovery, limited requests allowed

### Django Backend

#### 1. Resilience Module

**Location**: `backend/core/resilience.py`

**Features**:
- Thread-safe circuit breaker for synchronous code
- Decorator-based retry logic
- Configurable retry policies
- Django cache integration

**Key Classes**:
```python
class CircuitBreaker:
    - Thread-safe implementation
    - Sliding window failure tracking
    - State management

class ResilientAPIClient:
    - Synchronous HTTP client
    - Circuit breaker integration
    - Retry logic
    - Timeout management

@with_retry decorator:
    - Easy retry logic for any function
    - Circuit breaker integration
    - Configurable retry policy
```

#### 2. AI Service Clients

**Location**: `backend/core/ai_clients.py`

**Pre-configured clients**:
- `RecommendationClient` - Port 8001
- `SearchClient` - Port 8002
- `PricingClient` - Port 8003
- `ChatbotClient` - Port 8004
- `FraudClient` - Port 8005
- `ForecastingClient` - Port 8006
- `VisionClient` - Port 8007

---

## Usage Examples

### 1. API Gateway (FastAPI)

#### Basic Usage
```python
from ai_services.api_gateway.resilient_proxy import proxy_registry

@app.api_route("/api/v1/recommendations/{path:path}")
async def proxy_recommendations(request: Request, path: str):
    proxy = proxy_registry.get_proxy("recommendation-service")
    return await proxy.proxy_request(request, url)
```

#### Custom Configuration
```python
from ai_services.api_gateway.resilient_proxy import (
    proxy_registry,
    CircuitBreakerConfig,
    RetryConfig,
    TimeoutConfig,
)

proxy = proxy_registry.get_proxy(
    "recommendation-service",
    circuit_config=CircuitBreakerConfig(
        failure_threshold=10,  # More tolerant
        timeout=120,          # Longer timeout
    ),
    retry_config=RetryConfig(
        max_retries=5,        # More retries
        max_delay=30.0,       # Longer max delay
    ),
    timeout_config=TimeoutConfig(
        connect_timeout=10.0,
        read_timeout=60.0,
    ),
)
```

### 2. Django Backend

#### Using Pre-configured Clients
```python
from core.ai_clients import recommendation_client, fraud_client

# Get recommendations
recommendations = recommendation_client.get_user_recommendations(
    user_id=123,
    limit=10,
    filters={'category': 'electronics'}
)

# Analyze fraud
fraud_result = fraud_client.analyze_transaction({
    'user_id': 123,
    'amount': 1000.00,
    'payment_method': 'credit_card',
})

if fraud_result and fraud_result.get('risk_score', 0) > 0.8:
    # High risk transaction
    pass
```

#### Using Decorator
```python
from core.resilience import with_retry, RetryConfig, CircuitBreakerError
import requests

@with_retry(
    retry_config=RetryConfig(max_retries=3),
    circuit_breaker_name="external-api"
)
def call_external_api():
    response = requests.get("https://api.example.com/data")
    response.raise_for_status()
    return response.json()

try:
    data = call_external_api()
except CircuitBreakerError:
    # Circuit is open, use fallback
    data = get_cached_data()
```

#### Using ResilientAPIClient Directly
```python
from core.resilience import ResilientAPIClient

client = ResilientAPIClient("my-service")

try:
    response = client.get("http://service/api/endpoint")
    data = response.json()
except CircuitBreakerError:
    # Service is down, use fallback
    data = None
```

### 3. Celery Tasks

```python
from celery import shared_task
from core.ai_clients import recommendation_client

@shared_task
def update_user_recommendations(user_id):
    """Update user recommendations (runs async in background)"""
    recommendations = recommendation_client.get_user_recommendations(user_id)

    if recommendations:
        # Save to cache
        cache.set(f'recs:{user_id}', recommendations, timeout=3600)
    else:
        # Service is down, skip update
        pass
```

---

## Configuration

### Environment Variables

```bash
# API Gateway
GATEWAY_HOST=0.0.0.0
GATEWAY_PORT=8080

# AI Service URLs
RECOMMENDATION_SERVICE_URL=http://recommendation-service:8001
SEARCH_SERVICE_URL=http://search-service:8002
PRICING_SERVICE_URL=http://pricing-service:8003
CHATBOT_SERVICE_URL=http://chatbot-service:8004
FRAUD_SERVICE_URL=http://fraud-service:8005
FORECAST_SERVICE_URL=http://forecasting-service:8006
VISION_SERVICE_URL=http://vision-service:8007

# Circuit Breaker Settings (optional)
CB_FAILURE_THRESHOLD=5
CB_SUCCESS_THRESHOLD=2
CB_TIMEOUT=60
CB_WINDOW_SIZE=100

# Retry Settings (optional)
RETRY_MAX_RETRIES=3
RETRY_BASE_DELAY=0.1
RETRY_MAX_DELAY=10.0

# Timeout Settings (optional)
TIMEOUT_CONNECT=5.0
TIMEOUT_READ=30.0
```

### Per-Service Configuration

```python
# config/settings/production.py

CIRCUIT_BREAKER_CONFIG = {
    'recommendation-service': {
        'failure_threshold': 5,
        'timeout': 60,
    },
    'fraud-service': {
        'failure_threshold': 3,  # More sensitive
        'timeout': 30,           # Shorter timeout
    },
}

RETRY_CONFIG = {
    'fraud-service': {
        'max_retries': 1,  # Don't retry fraud checks
    },
}
```

---

## Monitoring & Metrics

### Prometheus Metrics

**API Gateway Metrics**:
```
# Total proxy requests
gateway_proxy_requests_total{service, method, status}

# Request duration
gateway_proxy_request_duration_seconds{service, method}

# Retry attempts
gateway_proxy_retries_total{service}

# Circuit breaker state changes
gateway_circuit_breaker_state_changes{service, state}
```

### Grafana Dashboard

**Location**: `monitoring/grafana/dashboards/circuit-breakers.json`

**Panels**:
1. Circuit Breaker States
2. Request Success Rate by Service
3. Retry Attempts by Service
4. Request Latency (p95)
5. Circuit Breaker State Changes
6. Error Rate by Service
7. Request Volume by Service

**Access**: http://localhost:3001 (admin/admin)

### Alerting Rules

```yaml
# monitoring/prometheus/alerts/circuit-breakers.yml
groups:
  - name: circuit_breakers
    rules:
      - alert: CircuitBreakerOpen
        expr: gateway_proxy_requests_total{status="circuit_open"} > 0
        for: 1m
        annotations:
          summary: "Circuit breaker is OPEN for {{$labels.service}}"

      - alert: HighErrorRate
        expr: |
          sum(rate(gateway_proxy_requests_total{status=~"error|circuit_open"}[5m])) by (service)
          / sum(rate(gateway_proxy_requests_total[5m])) by (service) > 0.1
        for: 5m
        annotations:
          summary: "High error rate (>10%) for {{$labels.service}}"

      - alert: HighRetryRate
        expr: rate(gateway_proxy_retries_total[5m]) > 1
        for: 5m
        annotations:
          summary: "High retry rate for {{$labels.service}}"
```

### Checking Circuit Breaker States

```bash
# Via API
curl http://localhost:8080/api/v1/circuit-breakers

# Response
{
  "circuit_breakers": {
    "recommendation-service": {
      "state": "closed",
      "failure_count": 0,
      "success_count": 0,
      "recent_failures": 0,
      "total_calls": 45
    }
  }
}

# Reset a circuit breaker
curl -X POST http://localhost:8080/api/v1/circuit-breakers/recommendation-service/reset
```

---

## Testing

### Unit Tests

```python
# tests/test_circuit_breaker.py
import pytest
from ai_services.api_gateway.circuit_breaker import CircuitBreaker

def test_circuit_breaker_opens_on_failures():
    breaker = CircuitBreaker("test")

    # Simulate failures
    for _ in range(5):
        try:
            breaker.call(lambda: 1/0)
        except:
            pass

    # Circuit should be open
    assert breaker.state == CircuitState.OPEN
```

### Integration Tests

```python
# tests/integration/test_resilient_proxy.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_proxy_with_circuit_breaker():
    # Start services
    async with AsyncClient() as client:
        # Make requests until circuit opens
        for i in range(10):
            response = await client.get(
                "http://gateway:8080/api/v1/recommendations/user/123"
            )

            if response.status_code == 503:
                # Circuit is open
                break
```

### Load Testing

```bash
# Use Locust for load testing
cd tests/load
locust -f circuit_breaker_test.py --host=http://localhost:8080
```

---

## Troubleshooting

### Common Issues

#### 1. Circuit Breaker Stuck Open

**Symptoms**: All requests fail with "Circuit breaker is OPEN"

**Causes**:
- Service is actually down
- Timeout is too short
- Threshold is too sensitive

**Solutions**:
```bash
# Check service health
curl http://service:8001/health

# Manually reset circuit breaker
curl -X POST http://gateway:8080/api/v1/circuit-breakers/service-name/reset

# Adjust configuration
# Increase timeout or failure threshold
```

#### 2. Too Many Retries

**Symptoms**: High latency, retry metrics increasing

**Causes**:
- max_retries too high
- Service intermittently failing

**Solutions**:
- Reduce max_retries
- Investigate service issues
- Adjust retry delays

#### 3. Requests Timing Out

**Symptoms**: TimeoutError exceptions

**Causes**:
- Timeout too short
- Service is slow

**Solutions**:
- Increase timeout settings
- Optimize service performance
- Add fallback logic

### Debug Mode

```python
# Enable debug logging
import logging
logging.getLogger('ai_services.api_gateway').setLevel(logging.DEBUG)

# Check circuit breaker state
from ai_services.api_gateway.circuit_breaker import circuit_breaker_registry
states = circuit_breaker_registry.get_all_states()
print(states)
```

---

## Best Practices

1. **Set Appropriate Thresholds**: Balance between false positives and quick failure detection
2. **Monitor Metrics**: Regularly review circuit breaker metrics
3. **Implement Fallbacks**: Always have a fallback strategy
4. **Test Failure Scenarios**: Regularly test circuit breaker behavior
5. **Document Service Dependencies**: Know which services have circuit breakers
6. **Use Correlation IDs**: Track requests across services
7. **Alert on Circuit Open**: Get notified when circuits open
8. **Regular Reviews**: Review and adjust configurations based on metrics

---

## References

- [Circuit Breaker Pattern](https://martinfowler.com/bliki/CircuitBreaker.html)
- [Release It! by Michael Nygard](https://pragprog.com/titles/mnee2/release-it-second-edition/)
- [Resilience Engineering](https://www.oreilly.com/library/view/designing-distributed-systems/9781491983638/)

---

**For Questions or Issues**: See [CONTRIBUTING.md](../CONTRIBUTING.md)
