# Ecommerce Backend API

Django/DRF backend deployed on Render.

## Live URLs
- Base: https://ecommerce-system-8701.onrender.com
- Swagger UI: https://ecommerce-system-8701.onrender.com/api/docs/
- Schema JSON: https://ecommerce-system-8701.onrender.com/api/schema/
- Schema UI: https://ecommerce-system-8701.onrender.com/api/docs/#/schema/schema_retrieve
- Health: https://ecommerce-system-8701.onrender.com/health/
- Liveness: https://ecommerce-system-8701.onrender.com/health/live/
- Readiness: https://ecommerce-system-8701.onrender.com/health/ready/
- Metrics: https://ecommerce-system-8701.onrender.com/metrics
- JWKS: https://ecommerce-system-8701.onrender.com/.well-known/jwks.json

## Quick checks
```bash
curl -s https://ecommerce-system-8701.onrender.com/health/ready/
curl -s https://ecommerce-system-8701.onrender.com/api/schema/ | head
```

## Local backend
```bash
docker compose -f deploy/docker/compose/base.yml -f deploy/docker/compose/development.yml up -d
```
- API: http://localhost:8000
- Docs: http://localhost:8000/api/docs/

Local venv:
```bash
cd services/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements/dev.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

## Required production env
- `SECRET_KEY`, `ALLOWED_HOSTS`
- `DATABASE_URL`
- `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`
- `SERVICE_AUTH_SECRET_DJANGO_BACKEND`, `SERVICE_AUTH_SECRET_API_GATEWAY`, `SERVICE_AUTH_SECRET_CELERY_WORKER`

## Monorepo map
- `services/backend/` — Django API (deployed)
- `services/gateway/` — Optional gateway
- `services/ai/` — Optional AI services
- `services/shared/` — Shared utilities
- `deploy/docker/compose/` — Compose files
