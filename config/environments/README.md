# Environment Configuration Guide

This directory contains all environment configuration templates for the e-commerce platform.

## Structure

```
config/environments/
├── .env.example                    # Main template with all variables
├── development.env.template        # Development environment
├── staging.env.template            # Staging environment
├── production.env.template         # Production environment
├── backend.env.template            # Backend service specific
├── ai-gateway.env.template         # AI Gateway specific
├── services/                       # AI microservice templates
│   ├── chatbot.env.template
│   ├── fraud-detection.env.template
│   ├── pricing.env.template
│   ├── recommendation.env.template
│   ├── search.env.template
│   └── visual-recognition.env.template
└── README.md                       # This file
```

## Usage

### Local Development

1. Copy the development template:
   ```bash
   cp config/environments/development.env.template .env
   ```

2. Edit `.env` with your local values:
   ```bash
   nano .env
   ```

3. Start services:
   ```bash
   docker-compose -f deploy/docker/compose/base.yml \
                  -f deploy/docker/compose/development.yml up
   ```

### Production Deployment

**⚠️ IMPORTANT: Never commit actual `.env` files to git!**

1. Copy the production template:
   ```bash
   cp config/environments/production.env.template .env.production
   ```

2. **Use Vault for secrets** (recommended):
   ```bash
   # Initialize Vault
   bash scripts/security/init-vault.sh

   # Secrets are fetched automatically from Vault
   # See config/secrets/vault-policies/ for access policies
   ```

3. Or manually set production values:
   ```bash
   nano .env.production
   ```

4. Deploy:
   ```bash
   docker-compose -f deploy/docker/compose/base.yml \
                  -f deploy/docker/compose/production.yml \
                  --env-file .env.production up -d
   ```

## Environment Variables

### Core Variables

All environments require these core variables:

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `DJANGO_SETTINGS_MODULE` | Django settings module | `config.settings.production` | Yes |
| `SECRET_KEY` | Django secret key | `random-50-char-string` | Yes |
| `DEBUG` | Debug mode | `False` (production) | Yes |
| `ALLOWED_HOSTS` | Allowed hostnames | `api.example.com,localhost` | Yes |

### Database

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host:5432/db` | Yes |
| `DB_NAME` | Database name | `ecommerce_prod` | Yes |
| `DB_USER` | Database user | `ecommerce_user` | Yes |
| `DB_PASSWORD` | Database password | `strong-password` | Yes |
| `DB_HOST` | Database host | `postgres` | Yes |
| `DB_PORT` | Database port | `5432` | Yes |

### Redis

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `REDIS_URL` | Redis connection string | `redis://redis:6379/0` | Yes |
| `REDIS_PASSWORD` | Redis password | `redis-password` | Yes (prod) |
| `CELERY_BROKER_URL` | Celery broker | `redis://redis:6379/1` | Yes |

### Security

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `USE_VAULT` | Enable HashiCorp Vault | `true` | Yes (prod) |
| `VAULT_ADDR` | Vault server address | `http://vault:8200` | If Vault enabled |
| `VAULT_TOKEN` | Vault access token | `hvs.xxx` | If Vault enabled |
| `VAULT_NAMESPACE` | Vault namespace | `ecommerce` | If Vault enabled |

### AWS (Optional)

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `AWS_ACCESS_KEY_ID` | AWS access key | `AKIA...` | If using S3 |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | `xxx` | If using S3 |
| `AWS_STORAGE_BUCKET_NAME` | S3 bucket | `ecommerce-media` | If using S3 |
| `AWS_S3_REGION_NAME` | AWS region | `us-east-1` | If using S3 |

### Stripe (Payment Processing)

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `STRIPE_PUBLIC_KEY` | Stripe publishable key | `pk_test_...` | If payments enabled |
| `STRIPE_SECRET_KEY` | Stripe secret key | `sk_test_...` | If payments enabled |
| `STRIPE_WEBHOOK_SECRET` | Webhook secret | `whsec_...` | If payments enabled |

### AI Services

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `AI_GATEWAY_URL` | AI Gateway URL | `http://api-gateway:8080` | Yes |
| `AI_GATEWAY_API_KEY` | Gateway API key | `xxx` | Yes |
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` | If using ChatGPT |
| `ANTHROPIC_API_KEY` | Anthropic API key | `xxx` | If using Claude |

### Monitoring

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `PROMETHEUS_URL` | Prometheus URL | `http://prometheus:9090` | No |
| `GRAFANA_URL` | Grafana URL | `http://grafana:3000` | No |
| `JAEGER_AGENT_HOST` | Jaeger agent | `jaeger` | No |
| `JAEGER_AGENT_PORT` | Jaeger port | `6831` | No |

## Best Practices

### Security

1. **Never commit `.env` files**
   - Only commit `.env.example` and `*.env.template` files
   - Add `.env` to `.gitignore`

2. **Use strong secrets**
   ```bash
   # Generate Django SECRET_KEY
   python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

   # Generate random password
   openssl rand -base64 32
   ```

3. **Use Vault in production**
   - Store all secrets in HashiCorp Vault
   - Rotate secrets regularly (weekly recommended)
   - Use Vault policies to limit access

4. **Rotate credentials**
   ```bash
   # Automated rotation
   bash scripts/security/rotate-secrets.sh
   ```

### Environment-Specific Values

#### Development
- `DEBUG=True`
- `LOG_LEVEL=DEBUG`
- `WORKERS=1` (single worker for debugging)
- Local database, Redis
- Dummy Stripe keys (test mode)

#### Staging
- `DEBUG=False`
- `LOG_LEVEL=INFO`
- `WORKERS=2`
- Staging database
- Test Stripe keys
- Similar to production but with test data

#### Production
- `DEBUG=False`
- `LOG_LEVEL=WARNING`
- `WORKERS=4+` (based on CPU cores)
- Production database with replicas
- Live Stripe keys
- All monitoring enabled
- Vault for secrets
- HTTPS only

## Validation

### Check Environment

Run validation script:
```bash
python scripts/development/validate-env.sh
```

### Test Configuration

```bash
# Test Django config
cd services/backend
python manage.py check --deploy

# Test database connection
python manage.py dbshell

# Test Redis connection
python manage.py shell -c "from django.core.cache import cache; cache.set('test', 'ok'); print(cache.get('test'))"
```

## Troubleshooting

### Issue: Missing required variables

**Error:**
```
django.core.exceptions.ImproperlyConfigured: Set the SECRET_KEY environment variable
```

**Solution:**
- Check your `.env` file exists
- Ensure all required variables are set
- Verify docker-compose is loading the env file:
  ```yaml
  env_file:
    - .env
  ```

### Issue: Database connection fails

**Error:**
```
psycopg2.OperationalError: could not connect to server
```

**Solution:**
1. Check `DATABASE_URL` format:
   ```
   postgresql://user:password@host:port/database
   ```

2. Verify database is running:
   ```bash
   docker-compose ps postgres
   ```

3. Test connection:
   ```bash
   docker-compose exec postgres psql -U ecommerce_user -d ecommerce_db
   ```

### Issue: Vault connection fails

**Error:**
```
VaultError: Vault is sealed
```

**Solution:**
1. Unseal Vault:
   ```bash
   bash scripts/security/unseal-vault.sh
   ```

2. Check Vault status:
   ```bash
   docker-compose exec vault vault status
   ```

## Migration from Old Structure

If migrating from the old environment file structure:

```bash
# Old locations (before Phase 1)
.env.example                          → config/environments/.env.example
backend/.env.example                  → config/environments/backend.env.template
ai-services/.env.example              → config/environments/ai-gateway.env.template
infrastructure/env/.env.development   → config/environments/development.env.template
infrastructure/env/.env.production    → config/environments/production.env.template
```

**Important:** After migration, update docker-compose env_file paths:
```yaml
# Old
env_file: .env

# New
env_file: ../../../config/environments/.env
```

## Templates

### Minimal .env (Development)

```bash
# Core
DJANGO_SETTINGS_MODULE=config.settings.development
SECRET_KEY=dev-secret-key-change-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=postgresql://ecommerce:ecommerce@postgres:5432/ecommerce_dev

# Redis
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1

# Vault (disabled in dev)
USE_VAULT=False
```

### Production .env Template

```bash
# Core
DJANGO_SETTINGS_MODULE=config.settings.production
SECRET_KEY=${VAULT_SECRET:secret_key}
DEBUG=False
ALLOWED_HOSTS=api.example.com

# Database
DATABASE_URL=${VAULT_SECRET:database_url}

# Redis
REDIS_URL=${VAULT_SECRET:redis_url}
REDIS_PASSWORD=${VAULT_SECRET:redis_password}

# Vault
USE_VAULT=True
VAULT_ADDR=https://vault.example.com
VAULT_TOKEN=${VAULT_TOKEN}

# AWS
AWS_ACCESS_KEY_ID=${VAULT_SECRET:aws_access_key}
AWS_SECRET_ACCESS_KEY=${VAULT_SECRET:aws_secret_key}

# Stripe
STRIPE_SECRET_KEY=${VAULT_SECRET:stripe_secret_key}

# Monitoring
SENTRY_DSN=${VAULT_SECRET:sentry_dsn}
```

## See Also

- [Vault Integration Guide](../../docs/security/vault-integration.md)
- [Production Deployment Checklist](../../docs/deployment/production-checklist.md)
- [Security Best Practices](../../docs/security/security-checklist.md)
- [Secrets Rotation](../../docs/operations/runbooks/rotate-secrets.md)
