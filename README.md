# E-Commerce Backend API (Django / DRF)

Production-ready Django REST Framework backend for an e-commerce platform, deployed on Render.

This service exposes a secure, observable API with health checks, metrics, JWT authentication, and background processing.

## Recruiter Quick Start (2 minutes)

Open the live API documentation:
- Swagger UI: https://ecommerce-system-8701.onrender.com/api/docs/

Authenticate (JWT) and explore endpoints under /api/

Verify production health:
```bash
curl -s https://ecommerce-system-8701.onrender.com/health/ready/
```

## Live Production Endpoints

- API Base URL  
  https://ecommerce-system-8701.onrender.com
- Swagger UI (OpenAPI)  
  https://ecommerce-system-8701.onrender.com/api/docs/
- OpenAPI Schema (JSON)  
  https://ecommerce-system-8701.onrender.com/api/schema/

### Health Checks

- General: /health/
- Liveness: /health/live/
- Readiness: /health/ready/
- Metrics (Prometheus): /metrics
- JWT JWKS Endpoint: /.well-known/jwks.json

## Core Capabilities

- RESTful API built with Django + DRF
- JWT authentication with JWKS support
- PostgreSQL persistence
- Redis caching and message brokering
- Celery for background and async tasks
- Production health, readiness, and liveness probes
- Prometheus-compatible metrics endpoint
- Dockerized local development and deployment

## Architecture Overview

- Framework: Django + Django REST Framework
- Database: PostgreSQL
- Cache / Broker: Redis
- Async Tasks: Celery
- Auth: JWT (SimpleJWT) with JWKS exposure
- Observability: Health checks + Prometheus metrics
- Deployment: Docker + Render

The backend is designed with production patterns commonly used in distributed systems and cloud environments.

## Local Development (Docker)

Run the full backend stack locally using Docker Compose:
```bash
docker compose \
  -f deploy/docker/compose/base.yml \
  -f deploy/docker/compose/development.yml \
  up -d
```

- API: http://localhost:8000
- Docs: http://localhost:8000/api/docs/

## Local Development (Virtual Environment)

```bash
cd services/backend
python -m venv .venv
source .venv/bin/activate

pip install -r requirements/dev.txt
cp .env.example .env

python manage.py migrate
python manage.py runserver
```

## Required Production Environment Variables

### Django / Core

- SECRET_KEY
- ALLOWED_HOSTS
- DATABASE_URL

### Caching & Background Jobs

- REDIS_URL
- CELERY_BROKER_URL
- CELERY_RESULT_BACKEND

### Internal Service Authentication

- SERVICE_AUTH_SECRET_DJANGO_BACKEND
- SERVICE_AUTH_SECRET_API_GATEWAY
- SERVICE_AUTH_SECRET_CELERY_WORKER

## Repository Structure (Monorepo)

```
services/
  backend/        # Django + DRF API (deployed service)
  gateway/        # Optional API gateway(not deployed)
  ai/             # Optional AI microservices(not deployed)
  shared/         # Shared utilities

deploy/
  docker/compose/ # Docker Compose configurations
```

## Notes for Interviewers

- The backend is deployed and publicly accessible.
- Health, readiness, and metrics endpoints are production-grade.
- JWT authentication is stateless and compatible with service-to-service usage.
- Docker Compose mirrors production dependencies locally.
- Codebase emphasizes clarity, maintainability, and operational awareness.
