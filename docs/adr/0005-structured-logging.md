# 5. Structured JSON Logging

Date: 2025-12-04

## Status

Accepted

## Context

Application logging is critical for:
- Debugging production issues
- Security monitoring
- Performance analysis
- Compliance and auditing

Current challenges:
- Unstructured text logs are hard to parse and analyze
- No request correlation across services
- Sensitive data sometimes leaked in logs
- Inconsistent log formats across services

## Decision

Adopt **structured JSON logging** across all services with:

- JSON format for all log output
- Consistent schema with required fields
- Request ID propagation across services
- Trace ID for distributed tracing
- Automatic PII scrubbing
- Contextual metadata

### Log Schema

```json
{
  "timestamp": "2025-12-04T10:30:45.123Z",
  "level": "INFO",
  "service": "backend",
  "environment": "production",
  "request_id": "req_1234567890",
  "trace_id": "trace_abc123",
  "user_id": "user_456",
  "message": "Order created successfully",
  "context": {
    "order_id": "ord_789",
    "amount": 99.99,
    "duration_ms": 150
  }
}
```

## Consequences

### Positive

- **Parseable**: Easy to ingest into log aggregation systems (Loki, Elasticsearch)
- **Searchable**: Can query by any field
- **Correlated**: Request IDs link logs across services
- **Structured**: Consistent format across all services
- **Debuggable**: Rich context for troubleshooting
- **Secure**: Automatic scrubbing of sensitive data
- **Monitored**: Can create alerts on log patterns

### Negative

- **Readability**: JSON harder to read than plain text (mitigated by log viewers)
- **Storage**: Slightly larger than plain text
- **Learning Curve**: Team needs to understand structured logging

### Neutral

- **Tooling**: Need log aggregation system to view effectively
- **Development**: Local development can use pretty-printed JSON

## Implementation

### Backend (Django)

```python
# Implemented in: backend/core/middleware/logging_middleware.py
import logging
import json
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)

class RequestLoggingMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.request_id = generate_request_id()

        logger.info(
            "Request started",
            extra={
                'request_id': request.request_id,
                'method': request.method,
                'path': request.path,
                'user_id': str(request.user.id) if request.user.is_authenticated else None,
                'ip': get_client_ip(request),
            }
        )
```

### AI Services (FastAPI)

```python
# Implemented in: ai-services/shared/json_logger.py
from shared.json_logger import setup_json_logging

setup_json_logging(
    service_name="api-gateway",
    environment=os.getenv("ENVIRONMENT"),
    log_level="INFO"
)
```

### Request ID Propagation

```python
# Middleware adds X-Request-ID header
response['X-Request-ID'] = request.request_id

# Services forward the header to downstream services
headers = {
    'X-Request-ID': request.headers.get('X-Request-ID'),
    'X-Trace-ID': request.headers.get('X-Trace-ID', generate_trace_id()),
}
```

## Design Decisions

### Why JSON vs Other Formats?

**JSON chosen** because:
- Universal standard
- Native support in log aggregation tools
- Easy to parse and query
- Can be nested/structured
- Human-readable (with pretty-printing)

**Alternatives rejected**:
- Logfmt: Less tooling support
- XML: Too verbose
- Binary: Not human-readable

### Why Include Request/Trace IDs?

Critical for:
- Tracing requests across microservices
- Debugging distributed systems
- Understanding user journeys
- Performance analysis

### What NOT to Log?

Never log:
- Passwords
- API keys
- Credit card numbers
- Session tokens
- Social security numbers
- Full user objects (only user_id)

### Development vs Production

**Development**: Pretty-printed JSON
```json
{
  "level": "INFO",
  "message": "User logged in"
}
```

**Production**: Single-line JSON
```json
{"level":"INFO","message":"User logged in","request_id":"req_123"}
```

## Alternatives Considered

### Plain Text Logging

**Rejected** because:
- Hard to parse programmatically
- Inconsistent formats
- Difficult to search/filter
- No structured metadata

### Binary Logging (Protocol Buffers)

**Rejected** because:
- Not human-readable
- Requires special tools
- Overkill for our scale

### Hybrid (Text + Structured)

**Rejected** because:
- Inconsistent
- More complex to implement
- Harder to maintain

## Implementation Phases

1. ✅ Phase 1: Implement in AI services (`shared/json_logger.py`)
2. ✅ Phase 2: Request ID middleware
3. ✅ Phase 3: Trace ID propagation
4. ✅ Phase 4: PII scrubbing
5. [ ] Phase 5: Backend full adoption (in progress)
6. [ ] Phase 6: Log aggregation setup (Loki/Elasticsearch)

## Log Aggregation Strategy

### Local Development

```bash
# View logs with jq for pretty-printing
docker-compose logs backend | jq .
```

### Production

- Logs shipped to Loki/Elasticsearch
- Grafana dashboards for visualization
- Alerts on error patterns
- Retention: 90 days

## Success Metrics

- ✅ All services emit JSON logs
- ✅ Request IDs tracked across services
- ✅ No PII in production logs (verified by automated scans)
- ⏳ Mean time to resolution (MTTR) reduced by 40%
- ⏳ 95% of log searches complete in < 5 seconds

## Best Practices

### DO ✅

```python
# Include context
logger.info(
    "Payment processed",
    extra={
        'order_id': order.id,
        'amount': order.total,
        'payment_method': 'stripe',
        'duration_ms': duration,
    }
)

# Use appropriate log levels
logger.error("Payment failed", extra={'error': str(e)})
```

### DON'T ❌

```python
# Don't log sensitive data
logger.info(f"Password: {password}")  # BAD

# Don't log unstructured strings
logger.info(f"User {user.id} did something")  # BAD - use extra={}

# Don't log at wrong level
logger.error("User logged in")  # BAD - should be INFO
```

## References

- [Structured Logging Best Practices](https://www.loggly.com/ultimate-guide/python-logging-basics/)
- [12-Factor App - Logs](https://12factor.net/logs)
- [Google Cloud Logging](https://cloud.google.com/logging/docs/structured-logging)
- [Grafana Loki](https://grafana.com/docs/loki/latest/)
