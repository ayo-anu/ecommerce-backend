# Development/Production Environment Parity

## Overview

This document defines the strategy for maintaining parity between development, staging, and production environments to minimize "works on my machine" issues and ensure smooth deployments.

**Last Updated**: 2025-12-04
**Version**: 1.0

---

## Table of Contents

1. [Environment Definitions](#environment-definitions)
2. [The 12-Factor Parity Principles](#the-12-factor-parity-principles)
3. [Parity Matrix](#parity-matrix)
4. [Container-Based Parity](#container-based-parity)
5. [Configuration Management](#configuration-management)
6. [Data Parity](#data-parity)
7. [Monitoring Parity](#monitoring-parity)
8. [Gap Analysis](#gap-analysis)
9. [Migration Plan](#migration-plan)

---

## Environment Definitions

### Development (Local)

**Purpose**: Individual developer workstations
**Users**: Engineers
**Data**: Synthetic/anonymized

**Characteristics**:
- Docker Compose setup
- Hot-reload enabled
- Debug mode ON
- Local file storage
- Simplified authentication

### Staging

**Purpose**: Pre-production testing and QA
**Users**: QA team, stakeholders
**Data**: Anonymized production-like data

**Characteristics**:
- Kubernetes cluster (mirrors production)
- Production-like configuration
- Debug mode OFF
- Cloud storage
- Full authentication stack

### Production

**Purpose**: Live customer-facing environment
**Users**: End users
**Data**: Real customer data

**Characteristics**:
- Kubernetes cluster
- Optimized for performance
- Debug mode OFF
- High availability
- Full monitoring and alerting

---

## The 12-Factor Parity Principles

### 1. Codebase Parity ✅

**Principle**: Same codebase across all environments

**Implementation**:
```bash
# All environments use same Docker images
docker pull ghcr.io/yourorg/ecommerce-backend:v1.2.3

# Tagged from same commit
git checkout v1.2.3
```

**Verification**:
```bash
# Check image digest matches
docker inspect ghcr.io/yourorg/ecommerce-backend:latest --format='{{.RepoDigests}}'
```

### 2. Dependencies Parity ✅

**Principle**: Explicitly declare and isolate dependencies

**Implementation**:
```python
# requirements/base.txt - same for all environments
Django==4.2.7
djangorestframework==3.14.0
psycopg2-binary==2.9.9

# requirements/dev.txt - development only
django-debug-toolbar==4.2.0
ipython==8.17.2
```

**Docker ensures dependency parity**:
```dockerfile
# Same base image across environments
FROM python:3.11-slim

# Install exact versions
COPY requirements/prod.txt .
RUN pip install --no-cache-dir -r prod.txt
```

### 3. Config Parity ⚠️

**Principle**: Store config in environment variables

**Implementation**:
```bash
# Development (.env.development)
DEBUG=True
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/ecommerce

# Production (injected via Kubernetes secrets)
DEBUG=False
DATABASE_URL=postgresql://user:pass@prod-db.region.rds.amazonaws.com:5432/ecommerce
```

**Gap**: Some config still in code (will migrate to env vars)

### 4. Backing Services Parity ⚠️

**Principle**: Treat backing services as attached resources

| Service | Development | Production | Parity |
|---------|-------------|------------|--------|
| PostgreSQL | 15-alpine (Docker) | RDS PostgreSQL 15 | ✅ Same version |
| Redis | 7-alpine (Docker) | ElastiCache Redis 7 | ✅ Same version |
| RabbitMQ | 3.12-alpine | Amazon MQ RabbitMQ 3.12 | ✅ Same version |
| Elasticsearch | 8.11 (Docker) | AWS OpenSearch 2.11 | ⚠️ Different engine |
| S3 | MinIO (Docker) | AWS S3 | ⚠️ Different impl |

**Mitigation**: Use compatibility layers (boto3 works with both)

### 5. Build, Release, Run Parity ✅

**Principle**: Strictly separate build and run stages

**Implementation**:
```bash
# 1. BUILD (CI)
docker build -t ecommerce-backend:$SHA .

# 2. RELEASE (CI)
docker tag ecommerce-backend:$SHA ecommerce-backend:v1.2.3
docker push ecommerce-backend:v1.2.3

# 3. RUN (All environments)
docker run ecommerce-backend:v1.2.3  # Same image everywhere
```

### 6. Processes Parity ✅

**Principle**: Execute app as stateless processes

**Implementation**:
- Session data in Redis (not in-process memory)
- File uploads to S3 (not local filesystem)
- Celery for background jobs (not threading)

### 7. Port Binding Parity ✅

**Principle**: Export services via port binding

```yaml
# Development
services:
  backend:
    ports:
      - "8000:8000"

# Production (Kubernetes)
apiVersion: v1
kind: Service
spec:
  ports:
    - port: 8000
      targetPort: 8000
```

### 8. Concurrency Parity ⚠️

**Principle**: Scale out via process model

| Environment | Backend Replicas | Celery Workers |
|-------------|------------------|----------------|
| Development | 1 | 1 |
| Staging | 2 | 2 |
| Production | 4-10 (auto-scale) | 3-6 |

**Gap**: Development doesn't test horizontal scaling

### 9. Disposability Parity ✅

**Principle**: Fast startup and graceful shutdown

**Implementation**:
```python
# Django handles SIGTERM gracefully
# Celery workers finish current task on SIGTERM
```

### 10. Dev/Prod Parity ⚠️

**This document!**

**Gaps identified**:
- Development uses Docker Compose, Production uses Kubernetes
- Different data volumes
- Different monitoring setup

### 11. Logs Parity ✅

**Principle**: Treat logs as event streams

**Implementation**:
```python
# All environments use same JSON logging
import logging
from shared.json_logger import setup_json_logging

setup_json_logging(
    service_name="backend",
    environment=os.getenv("ENVIRONMENT"),  # dev/staging/prod
    log_level=os.getenv("LOG_LEVEL", "INFO")
)
```

### 12. Admin Processes Parity ✅

**Principle**: Run admin tasks as one-off processes

```bash
# Same command in all environments
docker exec -it backend python manage.py migrate

# Kubernetes
kubectl exec -it backend-pod -- python manage.py migrate
```

---

## Parity Matrix

| Component | Development | Staging | Production | Parity Score |
|-----------|-------------|---------|------------|--------------|
| **Application Code** | Same commit | Same commit | Same commit | 100% ✅ |
| **Docker Images** | Same build | Same build | Same build | 100% ✅ |
| **Python Version** | 3.11 | 3.11 | 3.11 | 100% ✅ |
| **PostgreSQL** | 15-alpine | 15 | RDS Postgres 15 | 95% ✅ |
| **Redis** | 7-alpine | 7 | ElastiCache 7 | 95% ✅ |
| **Environment Vars** | .env file | K8s ConfigMap | K8s Secrets | 100% ✅ |
| **Orchestration** | Docker Compose | Kubernetes | Kubernetes | 60% ⚠️ |
| **Storage** | Local volumes | EBS volumes | EBS volumes | 70% ⚠️ |
| **Networking** | Docker bridge | K8s network | K8s network | 60% ⚠️ |
| **SSL/TLS** | Self-signed | Let's Encrypt | Let's Encrypt | 90% ✅ |
| **Logging** | JSON stdout | JSON → Loki | JSON → Loki | 100% ✅ |
| **Monitoring** | Prometheus | Prometheus | Prometheus | 100% ✅ |
| **Secrets** | .env file | K8s secrets | K8s secrets | 70% ⚠️ |

**Overall Parity Score**: **85%** 🎯

**Target**: 95%+

---

## Container-Based Parity

### Dockerfile Strategy

**Single Dockerfile for all environments** (with multi-stage builds):

```dockerfile
# ==================================================================
# Stage 1: Builder (same for all environments)
# ==================================================================
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements/ requirements/
RUN pip install --upgrade pip && \
    pip install -r requirements/prod.txt

# ==================================================================
# Stage 2: Runtime (same for all environments)
# ==================================================================
FROM python:3.11-slim AS runtime

# Runtime dependencies only
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=appuser:appuser . .

USER appuser

# Environment-specific settings via ENV VARS
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
```

**Benefits**:
- ✅ Same image runs in all environments
- ✅ Environment differences only in config
- ✅ Eliminates "works on my machine"

### Docker Compose for Development

**Purpose**: Mimic production as closely as possible locally

```yaml
# docker-compose.yaml (development)
version: '3.9'

services:
  backend:
    build:
      context: backend
      dockerfile: Dockerfile  # Same as production
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/ecommerce
      - REDIS_URL=redis://redis:6379/0
      - DEBUG=True  # Only difference
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app  # Hot reload for development
    depends_on:
      postgres:
        condition: service_healthy

  postgres:
    image: postgres:15-alpine  # Same version as production
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: ecommerce
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine  # Same version as production
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
```

---

## Configuration Management

### Environment Variable Strategy

**All environments use same variables, different values**:

```bash
# Common variables (all environments)
DATABASE_URL=<varies>
REDIS_URL=<varies>
SECRET_KEY=<varies>
ALLOWED_HOSTS=<varies>
DEBUG=<varies>
LOG_LEVEL=<varies>

# Service authentication (all environments)
SERVICE_AUTH_SECRET_DJANGO_BACKEND=<varies>
SERVICE_AUTH_SECRET_API_GATEWAY=<varies>
SERVICE_AUTH_SECRET_CELERY_WORKER=<varies>

# External services (all environments)
STRIPE_SECRET_KEY=<varies>  # test key in dev, live in prod
STRIPE_PUBLISHABLE_KEY=<varies>
SENTRY_DSN=<varies>  # different projects per environment
```

### Configuration Files Matrix

| File | Development | Staging | Production |
|------|-------------|---------|------------|
| `.env` | ✅ Checked in as `.env.development` | ❌ Not used | ❌ Not used |
| `ConfigMap` | ❌ Not used | ✅ K8s ConfigMap | ✅ K8s ConfigMap |
| `Secrets` | `.env` file | ✅ K8s Secrets | ✅ K8s Secrets |
| `settings.py` | `config/settings/development.py` | `config/settings/production.py` | `config/settings/production.py` |

**Validation**: Production settings validate at startup

```python
# config/settings/production.py
if not os.getenv('SECRET_KEY') or 'insecure' in os.getenv('SECRET_KEY', ''):
    raise ImproperlyConfigured("SECRET_KEY must be set and secure")
```

---

## Data Parity

### Database Schema Parity ✅

**Strategy**: Migrations ensure identical schema

```bash
# Development
python manage.py migrate

# Staging
kubectl exec -it backend-pod -- python manage.py migrate

# Production (with backup)
./scripts/backup_databases.sh
kubectl exec -it backend-pod -- python manage.py migrate
```

**Verification**:
```sql
-- Compare schema checksums
SELECT md5(array_agg(md5((t.*)::text))::text)
FROM (
  SELECT * FROM information_schema.columns
  ORDER BY table_name, ordinal_position
) t;
```

### Test Data Strategy

| Environment | Data Source | Volume | Strategy |
|-------------|-------------|--------|----------|
| Development | Fixtures | ~1000 records | `python manage.py loaddata` |
| Staging | Anonymized prod | ~10% of prod | Automated sync weekly |
| Production | Real data | Full | N/A |

**Anonymization script**:
```python
# scripts/anonymize_data.py
from faker import Faker
fake = Faker()

# Anonymize user data
for user in User.objects.all():
    user.email = fake.email()
    user.first_name = fake.first_name()
    user.last_name = fake.last_name()
    user.save()
```

---

## Monitoring Parity

### Metrics Collection ✅

**Same stack across all environments**:

```yaml
# docker-compose.yaml (dev)
prometheus:
  image: prom/prometheus:v2.48.0

# kubernetes (staging/prod)
apiVersion: v1
kind: Pod
spec:
  containers:
    - name: prometheus
      image: prom/prometheus:v2.48.0  # Same version
```

### Logging Parity ✅

**Structured JSON logs in all environments**:

```python
# Same logging config
from shared.json_logger import setup_json_logging

setup_json_logging(
    service_name=os.getenv("SERVICE_NAME"),
    environment=os.getenv("ENVIRONMENT"),  # dev/staging/prod
    log_level=os.getenv("LOG_LEVEL", "INFO")
)
```

**Collection**:
- Development: Docker logs
- Staging: Loki + Grafana
- Production: Loki + Grafana

---

## Gap Analysis

### Critical Gaps (Must Fix)

1. **Kubernetes Parity** ⚠️
   - **Gap**: Development uses Docker Compose, production uses Kubernetes
   - **Impact**: K8s-specific issues not caught in development
   - **Solution**: Use `kind` or `minikube` for local K8s development
   - **Timeline**: Q1 2025

2. **Secret Management** ⚠️
   - **Gap**: Development uses `.env` files, production uses K8s secrets
   - **Impact**: Different secret injection mechanisms
   - **Solution**: Use `external-secrets-operator` locally
   - **Timeline**: Q1 2025

### Minor Gaps (Nice to Have)

3. **Storage Backend**
   - **Gap**: Development uses local volumes, production uses EBS
   - **Impact**: Low (handled by abstraction layers)
   - **Solution**: Use MinIO for S3-compatible local storage (already implemented)

4. **Load Balancing**
   - **Gap**: Development has no load balancer, production uses ALB
   - **Impact**: Can't test load balancer behavior locally
   - **Solution**: Add HAProxy to development stack (optional)

5. **Auto-scaling**
   - **Gap**: Development runs single instance, production auto-scales
   - **Impact**: Can't test scaling behavior locally
   - **Solution**: Manual scaling tests in staging (acceptable)

---

## Migration Plan

### Phase 1: Immediate Improvements (Dec 2024)

- [x] Document current parity status (this document)
- [x] Standardize environment variable names
- [x] Implement startup validation in production
- [x] Use same Docker images across environments
- [ ] Create anonymization script for staging data

### Phase 2: Kubernetes Alignment (Q1 2025)

- [ ] Set up local Kubernetes with `kind`
- [ ] Migrate development to K8s manifests
- [ ] Implement `external-secrets-operator`
- [ ] Test deployments locally before staging

### Phase 3: Full Parity (Q2 2025)

- [ ] Achieve 95%+ parity score
- [ ] Automated parity verification in CI
- [ ] Quarterly parity audits
- [ ] Update this document with findings

---

## Verification Checklist

Use this checklist before each release:

### Pre-Deployment Checklist

- [ ] Same Docker image built from same commit
- [ ] Environment variables documented in `.env.example`
- [ ] Database migrations tested in staging
- [ ] Configuration validated (no default secrets)
- [ ] Health checks pass in all environments
- [ ] Monitoring dashboards updated
- [ ] Log aggregation working
- [ ] Backup/restore tested

### Post-Deployment Verification

```bash
# 1. Verify image version matches
kubectl get pods -o jsonpath='{.items[*].spec.containers[*].image}'

# 2. Check environment variables loaded
kubectl exec -it backend-pod -- env | grep DATABASE_URL

# 3. Verify database migrations applied
kubectl exec -it backend-pod -- python manage.py showmigrations

# 4. Test health endpoints
curl https://api.example.com/health

# 5. Check logs for errors
kubectl logs -l app=backend --tail=100
```

---

## Best Practices

### 1. Feature Flags

Use feature flags for environment-specific behavior:

```python
# settings.py
FEATURE_FLAGS = {
    'USE_REDIS_CACHE': os.getenv('USE_REDIS_CACHE', 'true').lower() == 'true',
    'ENABLE_DEBUG_TOOLBAR': os.getenv('DEBUG', 'false').lower() == 'true',
    'USE_S3_STORAGE': os.getenv('USE_S3_STORAGE', 'false').lower() == 'true',
}
```

### 2. Smoke Tests

Run smoke tests after deployment:

```python
# tests/smoke/test_production.py
def test_health_endpoint():
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200

def test_database_connection():
    # Verify migrations applied
    response = requests.get(f"{BASE_URL}/health/db")
    assert response.json()["status"] == "healthy"
```

### 3. Configuration Validation

Validate configuration at startup:

```python
# config/settings/production.py
REQUIRED_SETTINGS = [
    'SECRET_KEY',
    'DATABASE_URL',
    'ALLOWED_HOSTS',
    'SERVICE_AUTH_SECRET_DJANGO_BACKEND',
]

for setting in REQUIRED_SETTINGS:
    if not os.getenv(setting):
        raise ImproperlyConfigured(f"{setting} must be set")
```

---

## References

- [The Twelve-Factor App](https://12factor.net/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Kubernetes Production Best Practices](https://kubernetes.io/docs/setup/best-practices/)
- [Environment Variables Best Practices](https://www.doppler.com/blog/environment-variables-best-practices)

---

**Maintained By**: DevOps Team
**Review Schedule**: Quarterly
**Next Review**: 2025-03-04
**Parity Target**: 95%+
