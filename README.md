# E-Commerce Platform

Django REST backend for a full e-commerce workflow (auth, catalog, cart, orders, payments). The API is the core of the repo; the gateway and AI services are optional and still evolving.

## What runs today
- Django + DRF backend with JWT auth
- PostgreSQL, Redis, RabbitMQ, Elasticsearch
- Stripe integration for payments
- Celery for async tasks
- End-to-end tests for the main user flows

## Repo layout
```
services/backend/   Django API and apps
services/gateway/   FastAPI gateway (optional)
services/ai/        AI microservices (optional)
services/shared/    Shared utilities

deploy/docker/compose/   Compose files
infrastructure/          Nginx + DB init
monitoring/              Prometheus/Grafana
```

## Quick start (dev)
Use the Docker Compose files under `deploy/docker/compose/` for local development. The backend lives in `services/backend/`.

## Notes
- AI services and the gateway are not required to run the core API.
- Keep production settings separate from local overrides.
