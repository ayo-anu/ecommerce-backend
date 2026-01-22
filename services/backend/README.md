# Django REST API (Backend)

This service is deployed on Render. The gateway and AI services are optional.

## Live URLs
- Base: https://ecommerce-system-8701.onrender.com
- Swagger UI: https://ecommerce-system-8701.onrender.com/api/docs/
- Schema JSON: https://ecommerce-system-8701.onrender.com/api/schema/
- Schema UI: https://ecommerce-system-8701.onrender.com/api/docs/#/schema/schema_retrieve
- Health: https://ecommerce-system-8701.onrender.com/health/
- Liveness: https://ecommerce-system-8701.onrender.com/health/live/
- Readiness: https://ecommerce-system-8701.onrender.com/health/ready/
- Metrics: https://ecommerce-system-8701.onrender.com/metrics

## Structure
- `services/backend/config/` — Django project, URLs, ASGI/WSGI, Celery app
- `services/backend/config/settings/` — environment settings
- `services/backend/apps/` — domain apps
- `services/backend/core/` — middleware, logging, tracing, auth, JWKS, Celery tuning

## Settings selection
- `config/settings/__init__.py` picks settings by `ENVIRONMENT`.
- You can set `DJANGO_SETTINGS_MODULE` directly (ex: `config.settings.production`).

## Environment variables
Local dev can use `services/backend/.env` via `python-decouple`.

Minimal local dev:
```
SECRET_KEY=<LOCAL_SECRET_KEY>
ALLOWED_HOSTS=localhost,127.0.0.1
DB_ENGINE=django.db.backends.postgresql
DB_NAME=ecommerce
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=127.0.0.1
DB_PORT=5432
REDIS_URL=redis://:redis_password@127.0.0.1:6379/0
CELERY_BROKER_URL=redis://:redis_password@127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://:redis_password@127.0.0.1:6379/1
ELASTICSEARCH_URL=http://127.0.0.1:9200
```

Required in production:
- `SECRET_KEY`, `ALLOWED_HOSTS`
- `DATABASE_URL` (or `DB_*`)
- `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`
- `SERVICE_AUTH_SECRET_DJANGO_BACKEND`, `SERVICE_AUTH_SECRET_API_GATEWAY`, `SERVICE_AUTH_SECRET_CELERY_WORKER`
- `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS` (if you serve a frontend)

Optional integrations:
- OpenSearch: `ELASTICSEARCH_URL`
- Stripe: `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET`
- S3/CDN: `USE_S3`, `USE_CDN`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_REGION_NAME`, `CDN_DOMAIN`
- Email: `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`
- Observability: `SENTRY_DSN`, `JAEGER_AGENT_HOST`, `JAEGER_AGENT_PORT`, `OTEL_SERVICE_NAME`
- Vault: `USE_VAULT`, `VAULT_ROLE_ID`, `VAULT_SECRET_ID`, `VAULT_ADDR`

## Run locally
Docker Compose (backend only):
- `docker-compose -f deploy/docker/compose/base.yml -f deploy/docker/compose/development.yml up -d postgres redis elasticsearch backend`
- API: `http://localhost:8000` (docs at `http://localhost:8000/api/docs/`)

Local venv:
- `cd services/backend`
- `python -m venv .venv && source .venv/bin/activate`
- `pip install -r requirements/dev.txt`
- Copy `services/backend/.env.example` to `services/backend/.env` and set required vars
- `python manage.py migrate`
- `python manage.py runserver`

## Celery
- Worker: `celery -A config worker -l info --concurrency=4`
- Beat: `celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler`

## Internal service auth
- `core/middleware/service_auth.py` guards `/internal` and `/api/internal` routes.
- Requests must send `X-Service-Token` with a JWT generated via `core/service_tokens.py`.
- JWKS endpoint: `/.well-known/jwks.json`.

## Observability
- Prometheus metrics at `/metrics`.
- JSON logging in production (`core/logging.py`).
- Optional Sentry (`SENTRY_DSN`) and Jaeger/OpenTelemetry (`JAEGER_AGENT_HOST`).

## Integrations
- Stripe payments and webhooks (`/api/payments/` and `/api/payments/webhook/`)
- OpenSearch product search (via `django_opensearch_dsl`)
- Optional S3/CDN storage
- SMTP email

## Render deployment notes
- Entry point reads `PRODUCTION`, `RUN_MIGRATIONS`, `COLLECT_STATIC` in `services/backend/entrypoint.sh`.
- Use `DJANGO_SETTINGS_MODULE=config.settings.production` or `ENVIRONMENT=production`.
