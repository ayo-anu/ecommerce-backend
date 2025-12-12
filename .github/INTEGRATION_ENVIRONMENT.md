# Integration Environment Documentation

**Last Updated:** 2025-12-12
**PR:** PR-I - Add Integration Environment (Local + CI)

---

## Overview

This repository includes two Docker Compose environments for running integrated services:

1. **`docker-compose.local.yml`** - Full local development stack with Postgres
2. **`docker-compose.ci.yml`** - Lightweight CI environment with SQLite

Both environments enable the backend and AI Gateway to run together with proper service dependencies and health checks.

---

## Local Development Environment

### Quick Start

```bash
# Start all services
docker compose -f docker-compose.local.yml up

# Start in detached mode
docker compose -f docker-compose.local.yml up -d

# View logs
docker compose -f docker-compose.local.yml logs -f

# Stop all services
docker compose -f docker-compose.local.yml down

# Stop and remove volumes
docker compose -f docker-compose.local.yml down -v
```

### Services Included

| Service | Port | Description |
|---------|------|-------------|
| **backend** | 8000 | Django backend with Gunicorn |
| **api-gateway** | 9000 | AI services API Gateway (maps to internal 8080) |
| **postgres** | 5432 | PostgreSQL 15 database |
| **redis** | 6379 | Redis cache |

### Service Dependencies

```
postgres ─┐
          ├─> backend ─> api-gateway
redis ────┘
```

- Backend waits for Postgres and Redis to be healthy
- API Gateway waits for Backend to be healthy
- All services include health checks

### Environment Variables (Local)

**Backend:**
- `DJANGO_SETTINGS_MODULE=config.settings.development`
- `DATABASE_URL=postgresql://postgres:postgres@postgres:5432/postgres`
- `REDIS_URL=redis://redis:6379/0`
- `VAULT_DISABLED=true`
- `DEBUG=True`

**API Gateway:**
- `BACKEND_URL=http://backend:8000`
- `REDIS_URL=redis://redis:6379/0`
- `VAULT_DISABLED=true`

### Accessing Services

```bash
# Backend health check
curl http://localhost:8000/health/

# API Gateway health check
curl http://localhost:9000/health

# Backend admin (if available)
open http://localhost:8000/admin/

# API Gateway docs (if available)
open http://localhost:9000/docs
```

### Data Persistence

Postgres data is persisted in a named volume:
```bash
# View volumes
docker volume ls | grep ecommerce

# Inspect volume
docker volume inspect ecommerce-postgres-data

# Remove volume (WARNING: deletes all data)
docker volume rm ecommerce-postgres-data
```

### Troubleshooting Local Environment

**Services won't start:**
```bash
# Check service status
docker compose -f docker-compose.local.yml ps

# View specific service logs
docker compose -f docker-compose.local.yml logs backend
docker compose -f docker-compose.local.yml logs api-gateway

# Rebuild images
docker compose -f docker-compose.local.yml build --no-cache
```

**Database connection errors:**
```bash
# Ensure Postgres is healthy
docker compose -f docker-compose.local.yml ps postgres

# Check Postgres logs
docker compose -f docker-compose.local.yml logs postgres

# Reset database
docker compose -f docker-compose.local.yml down -v
docker compose -f docker-compose.local.yml up -d
```

**Port conflicts:**
```bash
# Check what's using a port
lsof -i :8000
lsof -i :9000
lsof -i :5432

# Use different ports (edit docker-compose.local.yml)
```

---

## CI Environment

### Overview

The CI environment (`docker-compose.ci.yml`) is designed for GitHub Actions integration tests:

- **Faster startup** - Uses SQLite instead of Postgres
- **Lightweight** - No persistent volumes
- **Isolated** - Runs on dedicated `ci-network`
- **Ephemeral** - Clean state on every run

### How CI Uses It

The integration environment is used in both `backend-ci.yml` and `ai-services-ci.yml`:

```yaml
integration-tests:
  needs: [lint-and-tests, docker-lint, build-sanity]
  steps:
    - Start docker-compose.ci.yml
    - Wait for services to be healthy
    - Run integration tests
    - Show logs on failure
    - Shutdown environment
```

### Running CI Environment Locally

```bash
# Start CI environment
docker compose -f docker-compose.ci.yml up -d

# Run smoke tests
docker run --network ecommerce-ci-network --rm \
  -v $PWD/integration_tests:/tests \
  alpine/curl:latest sh /tests/test_health_endpoints.sh

# Cleanup
docker compose -f docker-compose.ci.yml down -v
```

### Differences from Local Environment

| Feature | Local | CI |
|---------|-------|-----|
| Database | Postgres 15 | SQLite (in-memory) |
| Volumes | Persistent | None |
| Network | `ecommerce-local-network` | `ecommerce-ci-network` |
| Workers | 2 Gunicorn workers | 1 Gunicorn worker |
| Purpose | Development | Automated testing |

---

## Integration Tests

### Test Scripts

Located in `integration_tests/`:

1. **`test_health_endpoints.sh`**
   - Tests backend health endpoint (HTTP 200)
   - Tests API Gateway health endpoint (HTTP 200)
   - Fails fast if any endpoint is unhealthy

2. **`test_service_connectivity.sh`**
   - Tests API Gateway → Backend connectivity
   - Non-blocking (warnings only)
   - Gracefully handles missing endpoints

### Running Tests Manually

**From host machine:**
```bash
# Start environment
docker compose -f docker-compose.ci.yml up -d

# Wait for services
sleep 30

# Run health tests
docker run --network ecommerce-ci-network --rm \
  -v $PWD/integration_tests:/tests \
  alpine/curl:latest sh /tests/test_health_endpoints.sh

# Run connectivity tests
docker run --network ecommerce-ci-network --rm \
  -v $PWD/integration_tests:/tests \
  alpine/curl:latest sh /tests/test_service_connectivity.sh

# Cleanup
docker compose -f docker-compose.ci.yml down -v
```

**From within a container:**
```bash
# Start environment
docker compose -f docker-compose.ci.yml up -d

# Execute tests from backend container
docker compose -f docker-compose.ci.yml exec backend \
  sh /app/../integration_tests/test_health_endpoints.sh

# Cleanup
docker compose -f docker-compose.ci.yml down -v
```

### Test Output

**Success:**
```
=== Testing Health Endpoints ===

Testing backend health endpoint...
✅ Backend health endpoint returned HTTP 200
Testing API Gateway health endpoint...
✅ API Gateway health endpoint returned HTTP 200

🎉 All health endpoints are responding correctly!
```

**Failure:**
```
=== Testing Health Endpoints ===

Testing backend health endpoint...
❌ Backend health check failed! HTTP 500
```

---

## Extending Integration Tests

### Adding New Test Scripts

1. Create new script in `integration_tests/`:
```bash
#!/bin/bash
set -e
echo "=== My Custom Test ==="
# Your test logic here
exit 0
```

2. Make executable:
```bash
chmod +x integration_tests/my_test.sh
```

3. Add to CI workflows:
```yaml
- name: Run my custom test
  run: |
    docker run --network ecommerce-ci-network --rm \
      -v $PWD/integration_tests:/tests \
      alpine/curl:latest sh /tests/my_test.sh
```

### Adding New Services

To add a new service to the integration environment:

1. **Update `docker-compose.local.yml`:**
```yaml
  my-service:
    build:
      context: ./my-service
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    depends_on:
      backend:
        condition: service_healthy
    networks:
      - app-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

2. **Update `docker-compose.ci.yml`** with the same service (adjust for CI)

3. **Add health check tests** in `integration_tests/`

4. **Update workflows** to wait for new service

---

## Health Check Endpoints

### Backend Health Endpoint

**URL:** `http://backend:8000/health/`
**Expected Response:** HTTP 200
**Response Format:** JSON or text containing "ok" or "healthy"

### API Gateway Health Endpoint

**URL:** `http://api-gateway:8080/health`
**Expected Response:** HTTP 200
**Response Format:** JSON or text indicating health status

### Implementing Health Checks

If health endpoints don't exist yet, implement them:

**Django Backend (`backend/core/views.py`):**
```python
from django.http import JsonResponse

def health_check(request):
    return JsonResponse({"status": "healthy", "service": "backend"})
```

**FastAPI Gateway (`ai-services/api_gateway/main.py`):**
```python
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "api-gateway"}
```

---

## Network Configuration

### Local Network

- **Name:** `ecommerce-local-network`
- **Driver:** bridge
- **Purpose:** Local development

**Services can communicate using service names:**
```bash
# From backend container
curl http://api-gateway:8080/health

# From API Gateway container
curl http://backend:8000/health/
```

### CI Network

- **Name:** `ecommerce-ci-network`
- **Driver:** bridge
- **Purpose:** CI integration tests

**Same service name resolution:**
```bash
# From test runner
curl http://backend:8000/health/
curl http://api-gateway:8080/health
```

---

## Best Practices

### For Developers

1. **Always use docker-compose.local.yml** for local development
2. **Don't commit sensitive data** to compose files
3. **Use `.env.local`** for local overrides (gitignored)
4. **Clean up regularly**: `docker compose down -v` to avoid stale data
5. **Monitor resource usage**: `docker stats`

### For CI

1. **Keep CI environment fast** - Use SQLite, minimal workers
2. **Add health checks** for all new services
3. **Make tests idempotent** - Should work on clean or dirty state
4. **Fail fast** - Exit immediately on critical failures
5. **Show logs on failure** - Always include `docker compose logs` step

### For Staging/Production

1. **Don't use these compose files in production** - Use Kubernetes/ECS
2. **For staging**, create `docker-compose.staging.yml` based on local
3. **Use secrets management** - Vault, AWS Secrets Manager, etc.
4. **Enable monitoring** - Prometheus, Grafana, DataDog, etc.
5. **Use production-grade database** - RDS, Cloud SQL, managed Postgres

---

## Future Enhancements

### Planned Improvements

- [ ] Add Redis Insights UI for local development
- [ ] Add pgAdmin for Postgres management
- [ ] Create `docker-compose.staging.yml` for staging environment
- [ ] Add E2E tests with Playwright/Cypress
- [ ] Add performance/load tests
- [ ] Add database migration tests
- [ ] Add backup/restore scripts

### Monitoring & Observability

Consider adding:
- Prometheus for metrics
- Grafana for dashboards
- Jaeger for distributed tracing
- ELK stack for log aggregation

### Testing Enhancements

Consider adding:
- Contract testing (Pact)
- API fuzzing (RestLer, ffuf)
- Security testing (ZAP, Burp Suite)
- Performance testing (k6, Locust)

---

## Troubleshooting

### Common Issues

**Issue:** "Port already in use"
```bash
# Find and kill process using port
lsof -ti:8000 | xargs kill -9
```

**Issue:** "Network not found"
```bash
# Recreate network
docker compose -f docker-compose.local.yml down
docker compose -f docker-compose.local.yml up -d
```

**Issue:** "Health check failing"
```bash
# Check container logs
docker compose -f docker-compose.local.yml logs backend

# Execute health check manually
docker compose -f docker-compose.local.yml exec backend curl -f http://localhost:8000/health/
```

**Issue:** "Out of disk space"
```bash
# Clean up Docker resources
docker system prune -a --volumes

# Check disk usage
docker system df
```

### Getting Help

1. Check logs: `docker compose -f docker-compose.local.yml logs`
2. Check service status: `docker compose -f docker-compose.local.yml ps`
3. Restart services: `docker compose -f docker-compose.local.yml restart`
4. Full reset: `docker compose -f docker-compose.local.yml down -v && docker compose -f docker-compose.local.yml up -d`

---

## References

- **PR-F:** CI/CD Automation workflows
- **PR-H:** Workflow cleanup
- **PR-G:** Requirements path fixes
- **Backend CI:** `.github/workflows/backend-ci.yml`
- **AI Services CI:** `.github/workflows/ai-services-ci.yml`
- **Docker Compose Docs:** https://docs.docker.com/compose/

---

**Maintained By:** DevOps/SRE Team
**Last Reviewed:** 2025-12-12
