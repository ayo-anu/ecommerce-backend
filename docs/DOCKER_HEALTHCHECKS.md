# Docker Healthchecks and Restart Policies

## Overview

This document describes the health check and restart policy configuration for all services in the e-commerce platform.

## Current Status

### ✅ Services with Healthchecks

1. **PostgreSQL (Main)** - `pg_isready` check
2. **PostgreSQL (AI)** - `pg_isready` check
3. **PgBouncer** - Connection pool stats check
4. **Redis** - `redis-cli ping` check
5. **Elasticsearch** - HTTP cluster health check
6. **Qdrant** - HTTP /health endpoint
7. **Backend (Django)** - HTTP /api/health/ endpoint
8. **API Gateway** - HTTP /health endpoint

### ⚠️ Services Missing Healthchecks

- **Celery Worker** - No healthcheck (process-based, difficult to health-check)
- **Celery Beat** - No healthcheck (scheduler, no HTTP endpoint)
- **AI Microservices** (recommendation, fraud, etc.) - Need to add after implementing /health endpoints
- **Monitoring Services** (Prometheus, Grafana, Jaeger) - Need to add

## Healthcheck Best Practices

### 1. Healthcheck Configuration

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:PORT/health/live"]
  interval: 30s        # How often to check
  timeout: 10s         # Max time for check to complete
  retries: 3           # Failures before marking unhealthy
  start_period: 40s    # Grace period during startup
```

### 2. Types of Health Checks

#### Liveness Probe
- **Purpose**: Is the service process alive?
- **Action on Failure**: Restart the container
- **Endpoint**: `/health/live`
- **Should Check**: Only if the application can respond

```bash
# Example
curl -f http://localhost:8000/health/live
```

#### Readiness Probe
- **Purpose**: Is the service ready to accept traffic?
- **Action on Failure**: Stop routing traffic
- **Endpoint**: `/health/ready`
- **Should Check**: Dependencies (database, cache, etc.)

```bash
# Example
curl -f http://localhost:8000/health/ready
```

### 3. Restart Policies

```yaml
# Development
restart: unless-stopped  # Restart unless manually stopped

# Production
restart: always         # Always restart on failure
```

## Adding Healthchecks to AI Services

After implementing the standardized health endpoints (using `shared/health.py`), add to docker-compose:

```yaml
recommender:
  # ... other config
  healthcheck:
    test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8001/health/live', timeout=5)"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 40s  # AI services need more time to load models
```

### Alternative: Using curl

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8001/health/live"]
  # ... same as above
```

Note: Requires curl to be installed in the container. Python method works since Python is already in the image.

## Celery Worker Healthcheck

Celery workers don't have HTTP endpoints, so we use a different approach:

### Option 1: Celery Inspect (Recommended)

```yaml
celery_worker:
  healthcheck:
    test: ["CMD", "celery", "-A", "config", "inspect", "ping", "-d", "celery@$$HOSTNAME"]
    interval: 30s
    timeout: 10s
    retries: 3
```

### Option 2: Process Check (Simple)

```yaml
celery_worker:
  healthcheck:
    test: ["CMD-SHELL", "pgrep -f 'celery worker' || exit 1"]
    interval: 30s
    timeout: 5s
    retries: 3
```

## Monitoring Services Healthchecks

### Prometheus

```yaml
prometheus:
  healthcheck:
    test: ["CMD", "wget", "--spider", "-q", "http://localhost:9090/-/healthy"]
    interval: 30s
    timeout: 10s
    retries: 3
```

### Grafana

```yaml
grafana:
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:3000/api/health"]
    interval: 30s
    timeout: 10s
    retries: 3
```

### Jaeger

```yaml
jaeger:
  healthcheck:
    test: ["CMD", "wget", "--spider", "-q", "http://localhost:14269/"]
    interval: 30s
    timeout: 10s
    retries: 3
```

## Depends_on with Health Conditions

Use health checks to ensure services start in the correct order:

```yaml
backend:
  depends_on:
    postgres:
      condition: service_healthy  # Wait for DB to be healthy
    redis:
      condition: service_healthy  # Wait for Redis to be healthy
```

## Testing Healthchecks

### 1. Check Health Status

```bash
# View health status of all services
docker-compose ps

# Check specific service
docker inspect ecommerce_backend --format='{{.State.Health.Status}}'
```

### 2. View Health Logs

```bash
docker inspect ecommerce_backend --format='{{range .State.Health.Log}}{{.Output}}{{end}}'
```

### 3. Manual Health Check Test

```bash
# Enter container
docker exec -it ecommerce_backend bash

# Run health check command manually
curl -f http://localhost:8000/health/live
```

## Troubleshooting

### Service Marked as Unhealthy

1. **Check health logs**:
   ```bash
   docker inspect SERVICE_NAME --format='{{json .State.Health}}' | jq
   ```

2. **Check application logs**:
   ```bash
   docker logs SERVICE_NAME
   ```

3. **Test health endpoint manually**:
   ```bash
   docker exec SERVICE_NAME curl http://localhost:PORT/health/live
   ```

### Common Issues

#### 1. Health Check Timeout
```
Error: context deadline exceeded
```
**Solution**: Increase `timeout` or `start_period`

#### 2. Service Not Ready
```
Error: connection refused
```
**Solution**: Service needs more time to start. Increase `start_period`

#### 3. Dependencies Not Available
```
Error: database connection failed
```
**Solution**: Check `depends_on` configuration and ensure dependencies have health checks

## Production Recommendations

1. **Start Period**: Set generous `start_period` (30-60s) for services that load models or large datasets
2. **Interval**: Use 30s for most services, 10s for critical infrastructure (databases)
3. **Retries**: Use 3 retries to avoid false positives
4. **Timeout**: Keep under 10s to avoid blocking orchestration
5. **Restart Policy**: Use `restart: always` in production
6. **Dependencies**: Always use `condition: service_healthy` for database dependencies

## Implementation Checklist

### Phase 1: Infrastructure (✅ Complete)
- [x] PostgreSQL
- [x] Redis
- [x] Elasticsearch
- [x] Qdrant
- [x] RabbitMQ

### Phase 2: Application Services (✅ Complete)
- [x] Backend (Django)
- [x] API Gateway

### Phase 3: Worker Services (Needs Implementation)
- [ ] Celery Worker (use `celery inspect ping`)
- [ ] Celery Beat (use process check)

### Phase 4: AI Services (Needs Implementation After Health Endpoints)
- [ ] Recommendation Engine
- [ ] Search Engine
- [ ] Pricing Engine
- [ ] Chatbot RAG
- [ ] Fraud Detection
- [ ] Demand Forecasting
- [ ] Visual Recognition

### Phase 5: Monitoring (Needs Implementation)
- [ ] Prometheus
- [ ] Grafana
- [ ] Jaeger

## Example: Complete Service Configuration

```yaml
backend:
  build:
    context: ../backend
    dockerfile: Dockerfile
  container_name: ecommerce_backend
  restart: always  # Production restart policy
  command: gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4
  volumes:
    - backend_static:/app/staticfiles
    - backend_media:/app/media
  environment:
    - DATABASE_URL=postgresql://...
  networks:
    - backend_network
  depends_on:
    postgres:
      condition: service_healthy  # Wait for healthy database
    redis:
      condition: service_healthy  # Wait for healthy cache
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health/live"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 40s  # Time for migrations and static collection
```

## References

- [Docker Compose Healthcheck Documentation](https://docs.docker.com/compose/compose-file/05-services/#healthcheck)
- [Kubernetes Probes (similar concepts)](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)
- Backend health endpoints: `backend/apps/health/views.py`
- AI services health module: `ai-services/shared/health.py`
