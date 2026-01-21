# E-Commerce Platform API (Django/DRF)

## Recruiter Quick Start
_Replace placeholders (`<RENDER_API_BASE_URL>`, `<RENDER_API_DOCS_URL>`) with the deployed Render URL._
- Live API base URL (Render): <RENDER_API_BASE_URL>
- API docs (Swagger UI): <RENDER_API_DOCS_URL>
  - Schema: `<RENDER_API_BASE_URL>/api/schema/`
  - Redoc: `<RENDER_API_BASE_URL>/api/docs/redoc/`
- API base prefix: `/api/`
- Health endpoints:
  - `GET <RENDER_API_BASE_URL>/health/live/`
  - `GET <RENDER_API_BASE_URL>/health/ready/`
  - `GET <RENDER_API_BASE_URL>/health/`
  - Example: `curl -s <RENDER_API_BASE_URL>/health/ready/`
- Metrics and JWKS:
  - `GET <RENDER_API_BASE_URL>/metrics/` (Prometheus)
  - `GET <RENDER_API_BASE_URL>/.well-known/jwks.json`
- Code to review: `services/backend/`

Happy path (recruiter flow):
1) Register a user
2) Log in (receive JWT)
3) Browse products
4) List orders (authenticated)

### Copy/paste curl examples
```bash
# Register
curl -X POST <RENDER_API_BASE_URL>/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"email":"<DEMO_EMAIL>","username":"<DEMO_USERNAME>","password":"<DEMO_PASSWORD>","password2":"<DEMO_PASSWORD>"}'

# Login
curl -X POST <RENDER_API_BASE_URL>/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"<DEMO_EMAIL>","password":"<DEMO_PASSWORD>"}'

# Public browsing
curl <RENDER_API_BASE_URL>/api/products/

# Authenticated endpoints
curl -H "Authorization: Bearer <ACCESS_TOKEN>" <RENDER_API_BASE_URL>/api/orders/

curl -H "Authorization: Bearer <ACCESS_TOKEN>" <RENDER_API_BASE_URL>/api/payments/

curl -H "Authorization: Bearer <ACCESS_TOKEN>" <RENDER_API_BASE_URL>/api/notifications/

curl -H "Authorization: Bearer <ACCESS_TOKEN>" <RENDER_API_BASE_URL>/api/analytics/dashboard/
```

## Monorepo map
- `services/backend/` — Django REST Framework API (deployed on Render)
- `services/gateway/` — Optional gateway (not deployed as part of the recruiter demo)
- `services/ai/` — Optional AI services (not deployed for recruiter demo)
- `services/shared/` — Shared utilities
- `deploy/docker/compose/` — Docker Compose files

## Local run (backend only)
```bash
docker compose -f deploy/docker/compose/base.yml -f deploy/docker/compose/development.yml up -d
```
- Brings up backend + required infrastructure (PostgreSQL, Redis, Elasticsearch/OpenSearch)
- API: http://localhost:8000
- Docs: http://localhost:8000/api/docs/

Local venv (optional):
```bash
cd services/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements/dev.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

## Tests
- `make test-backend`
- `docker compose -f deploy/docker/compose/base.yml -f deploy/docker/compose/development.yml exec backend pytest`

## Deployment (Render)
High-level:
- Deploy `services/backend/` using `services/backend/Dockerfile`.
- Set `DJANGO_SETTINGS_MODULE=config.settings.production` and `PRODUCTION=true`.
- Required env vars: `SECRET_KEY`, `ALLOWED_HOSTS`, `DATABASE_URL`, `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`.

Notes:
- Celery env vars are required for settings import even if workers are not deployed.
- `/internal/*` routes are service-only; recruiters should focus on `/api/*`.
