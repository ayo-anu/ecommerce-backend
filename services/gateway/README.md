# API Gateway (optional)

This gateway fronts the AI services when running locally. It is not deployed for the recruiter demo.

For evaluation, focus on the Django REST API in `services/backend/`.

Local run (Compose):
- `docker-compose -f deploy/docker/compose/base.yml -f deploy/docker/compose/development.yml up -d api_gateway`
- Health: `http://localhost:8080/health`
