# AI Services (optional)

These services support recommendations, search, pricing, chatbot, fraud, forecasting, and vision.
They are not deployed for the recruiter demo.

For evaluation, focus on the Django REST API in `services/backend/`.

Local run (Compose):
- `docker-compose -f deploy/docker/compose/base.yml -f deploy/docker/compose/development.yml up -d recommender search pricing chatbot fraud forecasting vision`
