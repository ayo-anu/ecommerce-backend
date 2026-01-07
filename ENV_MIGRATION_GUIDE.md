# Environment Variables Migration Guide

## Overview

Your project now uses **service-specific .env files** instead of a single root .env file. Each service (Backend, Gateway, and 7 AI microservices) has its own `.env` file with only the variables it needs.

## New Structure

```
ecommerce-project/
├── .env.infrastructure          # Shared infrastructure credentials
├── .env.infrastructure.example  # Template for infrastructure
├── services/
│   ├── backend/
│   │   ├── .env                 # Backend-specific variables
│   │   └── .env.example         # Backend template
│   ├── gateway/
│   │   ├── .env                 # Gateway-specific variables
│   │   └── .env.example         # Gateway template
│   └── ai/services/
│       ├── recommendation_engine/
│       │   ├── .env
│       │   └── .env.example
│       ├── search_engine/
│       │   ├── .env
│       │   └── .env.example
│       ├── pricing_engine/
│       │   ├── .env
│       │   └── .env.example
│       ├── chatbot_rag/
│       │   ├── .env
│       │   └── .env.example
│       ├── fraud_detection/
│       │   ├── .env
│       │   └── .env.example
│       ├── demand_forecasting/
│       │   ├── .env
│       │   └── .env.example
│       └── visual_recognition/
│           ├── .env
│           └── .env.example
```

## Environment File Hierarchy

### 1. Infrastructure (.env.infrastructure)
**Shared by all services**

Contains:
- PostgreSQL credentials
- Redis password
- RabbitMQ credentials
- Grafana credentials
- General settings (ENVIRONMENT, DEBUG, LOG_LEVEL)

### 2. Backend (services/backend/.env)
**Used by Backend, Celery Worker, Celery Beat**

Contains:
- Django SECRET_KEY, ALLOWED_HOSTS
- Database/Redis URLs (constructed from infrastructure)
- Stripe payment credentials
- AWS S3 credentials
- Email SMTP settings
- Monitoring (Sentry, OpenTelemetry)

### 3. Gateway (services/gateway/.env)
**Used by API Gateway**

Contains:
- Gateway server settings
- Security & JWT configuration
- CORS settings
- All AI service URLs
- Rate limiting & circuit breaker settings
- External API keys (OpenAI, HuggingFace, Anthropic)
- Feature flags

### 4. AI Services (services/ai/services/*/...env)
**Each AI service has its own .env**

Each contains:
- Service name
- Redis URL (unique DB index per service)
- Model path
- Service-specific settings (e.g., QDRANT_URL, OPENAI_API_KEY)

## Docker Compose Integration

### How It Works

Docker Compose now uses `env_file` directives to load environment variables:

```yaml
# Example: Backend service
backend:
  env_file:
    - ../../../.env.infrastructure      # Loaded first
    - ../../../services/backend/.env    # Loaded second (can override)
```

### Variable Precedence

1. **environment:** block (highest priority)
2. **env_file:** (second file overrides first)
3. Shell environment variables
4. Defaults in code

## Quick Start Guide

### For Development

1. **Review infrastructure settings**:
   ```bash
   cat .env.infrastructure
   ```
   The default development values are already set.

2. **Update service-specific secrets**:
   ```bash
   # Backend
   nano services/backend/.env
   # Update: STRIPE_SECRET_KEY, AWS credentials, EMAIL settings

   # Gateway
   nano services/gateway/.env
   # Update: SECRET_KEY, OPENAI_API_KEY (if using chatbot)

   # Chatbot (if using OpenAI)
   nano services/ai/services/chatbot_rag/.env
   # Update: OPENAI_API_KEY
   ```

3. **Start services**:
   ```bash
   cd deploy/docker/compose
   docker-compose -f base.yml -f development.yml up -d
   ```

### For Production

1. **Copy example files**:
   ```bash
   cp .env.infrastructure.example .env.infrastructure
   cp services/backend/.env.example services/backend/.env
   cp services/gateway/.env.example services/gateway/.env
   # ... copy for all AI services
   ```

2. **Update all credentials**:
   - Replace all `your-*-here` placeholders
   - Use strong, unique passwords
   - Set `DEBUG=False`
   - Set `ENVIRONMENT=production`

3. **Secure the files**:
   ```bash
   chmod 600 .env.infrastructure
   chmod 600 services/*/....env
   chmod 600 services/ai/services/*/.env
   ```

## Redis DB Index Allocation

Each service uses a dedicated Redis database:

| DB Index | Service                |
|----------|------------------------|
| 0        | Backend cache          |
| 1        | Celery results         |
| 2        | API Gateway cache      |
| 3        | Recommendation Engine  |
| 4        | Search Engine          |
| 5        | Pricing Engine         |
| 6        | Chatbot RAG            |
| 7        | Fraud Detection        |
| 8        | Demand Forecasting     |
| 9        | Visual Recognition     |

## Migration Checklist

- [x] Infrastructure .env created with development defaults
- [x] Backend .env created
- [x] Gateway .env created
- [x] All 7 AI services .env files created
- [x] Docker Compose updated to use env_file directives
- [x] .gitignore updated to exclude .env files (but keep .env.example)
- [ ] Review and update service-specific secrets
- [ ] Test docker-compose startup
- [ ] Verify all services can connect to infrastructure

## Testing Your Setup

```bash
# 1. Validate docker-compose configuration
cd deploy/docker/compose
docker-compose -f base.yml config

# 2. Check which env files are loaded per service
docker-compose -f base.yml config | grep -A2 "env_file"

# 3. Start and check logs
docker-compose -f base.yml -f development.yml up -d
docker-compose logs -f backend
docker-compose logs -f api_gateway
docker-compose logs -f recommender

# 4. Verify services can connect
docker-compose exec backend python manage.py check
curl http://localhost:8080/health  # Gateway
curl http://localhost:8001/health  # Recommendation engine
```

## Troubleshooting

### Service can't find environment variable

**Problem**: Service logs show "Environment variable X not found"

**Solution**:
1. Check the variable exists in the correct .env file
2. Verify docker-compose env_file paths are correct
3. Restart the service: `docker-compose restart <service_name>`

### Database connection fails

**Problem**: "could not connect to server"

**Solution**:
1. Verify infrastructure credentials in `.env.infrastructure`
2. Check the constructed DATABASE_URL in service .env
3. Ensure PostgreSQL container is healthy: `docker-compose ps postgres`

### Redis authentication fails

**Problem**: "NOAUTH Authentication required"

**Solution**:
1. Verify REDIS_PASSWORD in `.env.infrastructure` matches Redis container
2. Check REDIS_URL format includes password: `redis://:password@redis:6379/0`

## Security Best Practices

1. **Never commit .env files to git**
   - Only commit .env.example files
   - The .gitignore is already configured

2. **Use strong credentials in production**
   - Generate secrets: `openssl rand -base64 32`
   - Rotate credentials regularly

3. **Restrict file permissions**
   ```bash
   chmod 600 .env.infrastructure
   chmod 600 services/*/.env
   ```

4. **Consider using Vault for production**
   - The project supports HashiCorp Vault
   - See `.env` (Vault example) for configuration

## Need Help?

- Check docker-compose logs: `docker-compose logs <service>`
- Verify environment loading: `docker-compose config`
- Review service health: `docker-compose ps`

---

**Note**: Development .env files are already created with working defaults. For production, copy from .env.example files and update with real credentials.
