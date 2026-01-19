# API Gateway

FastAPI gateway that fronts the AI services. It adds rate limiting, circuit breakers, and request logging. Optional for local dev.

## Endpoints
- `GET /health`
- `GET /metrics`
- `GET /circuit-breakers`

## Notes
- Configure via env vars in the compose files.
- The gateway only proxies the AI routes; it does not replace the Django API.
