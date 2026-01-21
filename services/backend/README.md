# Django REST API (Backend)

This is the only deployed service on Render. The gateway and AI services are optional and not part of the recruiter demo.

## Project structure
- `services/backend/config/` - Django project, URLs, ASGI/WSGI, Celery app
- `services/backend/config/settings/` - settings split by environment (base, development, staging, production, tests, e2e_test)
- `services/backend/apps/` - domain apps: accounts, products, orders, payments, notifications, analytics, health, core
- `services/backend/core/` - shared middleware, logging, tracing, service auth, JWKS, celery tuning

## Settings selection
- `config/settings/__init__.py` selects settings by `ENVIRONMENT` (production, staging, or development).
- You can also set `DJANGO_SETTINGS_MODULE` directly (for example `config.settings.production`).
- Defaults:
  - `manage.py` uses `config.settings.development`
  - `asgi.py` uses `config.settings` (ENVIRONMENT-driven)
  - `wsgi.py` uses `config.settings.production`

## Environment variables
The settings load with `python-decouple`, so a `.env` file in `services/backend/` works for local dev.

Minimum local dev (example placeholders):
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

Notes:
- `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` are read in `config/settings/base.py` with no defaults. They must exist in every environment, even local dev.
- Production hard-fails without `SECRET_KEY`, `ALLOWED_HOSTS`, `DATABASE_URL` (or DB_*), and the service auth secrets.

Required in production:
- `SECRET_KEY`, `ALLOWED_HOSTS`
- `DATABASE_URL` (preferred) or `DB_ENGINE/DB_NAME/DB_USER/DB_PASSWORD/DB_HOST/DB_PORT`
- `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`
- `REDIS_URL`
- `SERVICE_AUTH_SECRET_DJANGO_BACKEND`, `SERVICE_AUTH_SECRET_API_GATEWAY`, `SERVICE_AUTH_SECRET_CELERY_WORKER`
- `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS` (if you serve a frontend)

Optional integrations:
- Stripe: `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET`
- OpenSearch: `ELASTICSEARCH_URL`
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
- Queue tuning lives in `services/backend/core/celery_config.py` (prefetch, timeouts, priority queues, task routing).

## Internal service auth
- `core/middleware/service_auth.py` guards `/internal` and `/api/internal` routes.
- Requests must send `X-Service-Token` with a JWT generated via `core/service_tokens.py`.
- JWKS endpoint: `/.well-known/jwks.json` (only returns keys for asymmetric algorithms).
- For local/dev, set `SERVICE_AUTH_SECRET_DJANGO_BACKEND`, `SERVICE_AUTH_SECRET_API_GATEWAY`, and `SERVICE_AUTH_SECRET_CELERY_WORKER` to random 32+ char values and generate tokens with `ServiceTokenManager`.

## Observability
- Prometheus metrics via `django_prometheus` at `/metrics/`.
- JSON logging in production (`core/logging.py`).
- Optional Sentry (`SENTRY_DSN`) and Jaeger/OpenTelemetry (`JAEGER_AGENT_HOST`).

## Health checks
- `/health/live/` - liveness
- `/health/ready/` - readiness (DB, cache, OpenSearch)
- `/health/` - detailed dependency report (DB, cache, OpenSearch, Vault)

## Integrations
- Stripe payments and webhooks (`/api/payments/` and `/api/payments/webhook/`)
- OpenSearch product search (via `django_opensearch_dsl`)
- Optional S3/CDN storage for static/media
- SMTP email via Django email backend

## Render deployment notes
- Entry point reads `PRODUCTION`, `RUN_MIGRATIONS`, `COLLECT_STATIC` in `services/backend/entrypoint.sh`.
- Use `DJANGO_SETTINGS_MODULE=config.settings.production` or `ENVIRONMENT=production`.
- Set `ALLOWED_HOSTS`, `SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`, and the Celery and service auth vars.

## Troubleshooting
- Missing `CELERY_BROKER_URL` or `CELERY_RESULT_BACKEND` will break settings import.
- Production settings block startup if `SECRET_KEY`, `ALLOWED_HOSTS`, `DATABASE_URL`, or service auth secrets are missing.
- Vault uses AppRole (`VAULT_ROLE_ID`/`VAULT_SECRET_ID`); the entrypoint `VAULT_TOKEN` check does not satisfy the client.
