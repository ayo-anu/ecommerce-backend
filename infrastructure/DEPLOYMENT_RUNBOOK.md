# Production Deployment Runbook

## Overview

This runbook provides step-by-step procedures for deploying, managing, and rolling back the e-commerce platform in production using Docker containers.

## Prerequisites

- Docker 20.10+ installed
- Docker Compose 2.0+ installed
- Access to production environment variables
- Vault credentials (if using Vault integration)
- Database backup tools

---

## 1. Building Production Images

### 1.1 Build Backend Image

```bash
# Navigate to project root
cd /path/to/ecommerce-project

# Build backend image
docker build -t ecommerce-backend:latest -f backend/Dockerfile backend/

# Tag with version
docker tag ecommerce-backend:latest ecommerce-backend:v1.0.0
```

### 1.2 Verify Image Security

```bash
# Check image history for secrets (should see no sensitive data)
docker history ecommerce-backend:latest

# Verify non-root user
docker run --rm ecommerce-backend:latest id
# Expected output: uid=1000(appuser) gid=1000(appuser) groups=1000(appuser)

# Check image size
docker images ecommerce-backend:latest
```

### 1.3 Build AI Services

```bash
# Build recommendation engine
cd ai-services
docker build -t ecommerce-recommendation:latest \
  -f services/recommendation_engine/Dockerfile .

# Repeat for other services as needed
```

---

## 2. Running Production Containers

### 2.1 Prepare Environment

```bash
# Copy and configure environment file
cp infrastructure/env/.env.vault.template .env.production

# Edit with production values
vim .env.production

# Set required variables:
# - SECRET_KEY
# - ALLOWED_HOSTS
# - DATABASE_URL
# - DB_PASSWORD
# - VAULT_TOKEN (if using Vault)

# Secure the file
chmod 600 .env.production
```

### 2.2 Start Services with Docker Compose

```bash
# Start all production services
docker-compose -f docker-compose.production.yml --env-file .env.production up -d

# Check service health
docker-compose -f docker-compose.production.yml ps

# View logs
docker-compose -f docker-compose.production.yml logs -f backend
```

### 2.3 Verify Deployment

```bash
# Check health endpoints
curl http://localhost:8000/health/
curl http://localhost:8000/health/ready/
curl http://localhost:8000/health/live/

# Expected response: {"status": "healthy", ...}

# Verify database connection
docker-compose -f docker-compose.production.yml exec backend \
  python manage.py dbshell --command="SELECT 1;"

# Check running processes
docker-compose -f docker-compose.production.yml top
```

---

## 3. Running Standalone Container

### 3.1 Run Backend Container

```bash
# Start backend with environment variables
docker run -d \
  --name ecommerce-backend \
  --restart unless-stopped \
  -p 8000:8000 \
  -e DJANGO_SETTINGS_MODULE=config.settings.production \
  -e PRODUCTION=true \
  -e SECRET_KEY="${SECRET_KEY}" \
  -e ALLOWED_HOSTS="${ALLOWED_HOSTS}" \
  -e DATABASE_URL="${DATABASE_URL}" \
  -e REDIS_URL="${REDIS_URL}" \
  -e USE_VAULT="${USE_VAULT:-false}" \
  -e VAULT_ADDR="${VAULT_ADDR}" \
  -e VAULT_TOKEN="${VAULT_TOKEN}" \
  --health-cmd="curl -f http://localhost:8000/health/ || exit 1" \
  --health-interval=30s \
  --health-timeout=5s \
  --health-retries=3 \
  --health-start-period=40s \
  ecommerce-backend:latest

# Check health status
docker ps --filter name=ecommerce-backend

# View logs
docker logs -f ecommerce-backend
```

### 3.2 Mount Vault Configuration

```bash
# Option 1: Mount .env.vault file
docker run -d \
  --name ecommerce-backend \
  -p 8000:8000 \
  -v $(pwd)/.env.vault:/app/.env.vault:ro \
  -e USE_VAULT=true \
  ecommerce-backend:latest

# Option 2: Use Docker secrets (Swarm)
echo "${VAULT_TOKEN}" | docker secret create vault_token -
docker service create \
  --name ecommerce-backend \
  --secret vault_token \
  -e VAULT_TOKEN_FILE=/run/secrets/vault_token \
  ecommerce-backend:latest
```

---

## 4. Database Migrations

### 4.1 Run Migrations

```bash
# Migrations run automatically via entrypoint.sh
# To run manually:
docker-compose -f docker-compose.production.yml exec backend \
  python manage.py migrate --settings=config.settings.production

# Check migration status
docker-compose -f docker-compose.production.yml exec backend \
  python manage.py showmigrations --settings=config.settings.production
```

### 4.2 Disable Auto-Migrations

```bash
# Set RUN_MIGRATIONS=false to skip auto-migrations on startup
docker run -d \
  -e RUN_MIGRATIONS=false \
  ecommerce-backend:latest
```

---

## 5. Monitoring & Health Checks

### 5.1 Check Container Health

```bash
# View health status
docker ps

# Inspect detailed health
docker inspect --format='{{json .State.Health}}' ecommerce-backend | jq

# View health check logs
docker inspect ecommerce-backend | jq '.[0].State.Health.Log'
```

### 5.2 Monitor Resources

```bash
# Check resource usage
docker stats ecommerce-backend

# View resource limits
docker inspect ecommerce-backend | jq '.[0].HostConfig.Memory'
docker inspect ecommerce-backend | jq '.[0].HostConfig.NanoCpus'
```

### 5.3 Application Logs

```bash
# Follow logs
docker-compose -f docker-compose.production.yml logs -f

# View last 100 lines
docker logs --tail 100 ecommerce-backend

# JSON log parsing (production uses JSON logs)
docker logs ecommerce-backend | jq -r 'select(.level=="ERROR")'
```

---

## 6. Scaling Services

### 6.1 Scale with Docker Compose

```bash
# Scale celery workers
docker-compose -f docker-compose.production.yml up -d --scale celery_worker=3

# Verify
docker-compose -f docker-compose.production.yml ps celery_worker
```

### 6.2 Scale with Docker Swarm

```bash
# Initialize swarm (if not already)
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.production.yml ecommerce

# Scale service
docker service scale ecommerce_backend=3
docker service scale ecommerce_celery_worker=5

# Check status
docker service ls
docker service ps ecommerce_backend
```

---

## 7. Rollback Procedures

### 7.1 Quick Rollback

```bash
# Stop current version
docker-compose -f docker-compose.production.yml down

# Rollback to previous image
docker tag ecommerce-backend:v1.0.0 ecommerce-backend:latest

# Restart services
docker-compose -f docker-compose.production.yml up -d

# Verify
curl http://localhost:8000/health/
```

### 7.2 Database Rollback

```bash
# Restore database backup (prepare backup first!)
# Stop services
docker-compose -f docker-compose.production.yml stop backend celery_worker

# Restore database
docker-compose -f docker-compose.production.yml exec postgres \
  psql -U postgres -d ecommerce < /backups/ecommerce_backup_YYYYMMDD.sql

# Restart services
docker-compose -f docker-compose.production.yml start backend celery_worker
```

### 7.3 Emergency Stop

```bash
# Stop all services immediately
docker-compose -f docker-compose.production.yml down

# Or stop individual service
docker stop ecommerce-backend

# Force stop if needed
docker kill ecommerce-backend
```

---

## 8. Troubleshooting

### 8.1 Container Won't Start

```bash
# Check logs
docker logs ecommerce-backend

# Check for port conflicts
netstat -tulpn | grep 8000

# Inspect container
docker inspect ecommerce-backend

# Run container interactively
docker run -it --rm --entrypoint /bin/bash ecommerce-backend:latest
```

### 8.2 Health Check Failing

```bash
# Test health endpoint manually
docker exec ecommerce-backend curl -f http://localhost:8000/health/

# Check application logs
docker logs --tail 50 ecommerce-backend

# Verify database connectivity
docker exec ecommerce-backend pg_isready -h postgres -U postgres

# Check Redis
docker exec ecommerce-backend redis-cli -h redis ping
```

### 8.3 Database Connection Issues

```bash
# Test database from container
docker-compose -f docker-compose.production.yml exec backend \
  python manage.py dbshell

# Check network
docker network inspect docker-compose_backend

# Verify DATABASE_URL
docker exec ecommerce-backend printenv DATABASE_URL
```

### 8.4 Vault Integration Issues

```bash
# Check Vault configuration
docker exec ecommerce-backend printenv | grep VAULT

# Test Vault connectivity
docker exec ecommerce-backend curl -v ${VAULT_ADDR}/v1/sys/health

# Check Vault health from Django
docker-compose -f docker-compose.production.yml exec backend \
  python -c "from core.vault_client import vault_health_check; print(vault_health_check())"
```

---

## 9. Security Checks

### 9.1 Verify No Secrets in Images

```bash
# Check image layers
docker history --no-trunc ecommerce-backend:latest | grep -i secret
docker history --no-trunc ecommerce-backend:latest | grep -i password
docker history --no-trunc ecommerce-backend:latest | grep -i token

# Expected: No matches

# Export and scan image
docker save ecommerce-backend:latest | tar -x
grep -r "SECRET_KEY\|VAULT_TOKEN" */layer.tar
# Expected: No matches
```

### 9.2 Verify Non-Root User

```bash
# Check running user
docker exec ecommerce-backend id
# Expected: uid=1000(appuser)

# Verify file permissions
docker exec ecommerce-backend ls -la /app
```

### 9.3 Security Scan

```bash
# Install trivy (if not installed)
# https://github.com/aquasecurity/trivy

# Scan image for vulnerabilities
trivy image ecommerce-backend:latest

# Scan for misconfigurations
trivy config docker-compose.production.yml
```

---

## 10. Backup & Restore

### 10.1 Database Backup

```bash
# Create backup
docker-compose -f docker-compose.production.yml exec postgres \
  pg_dump -U postgres ecommerce > backup_$(date +%Y%m%d_%H%M%S).sql

# Verify backup
ls -lh backup_*.sql
```

### 10.2 Volume Backup

```bash
# Backup postgres data volume
docker run --rm \
  -v ecommerce_postgres_data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/postgres_data_$(date +%Y%m%d).tar.gz /data

# Backup media files
docker run --rm \
  -v ecommerce_media_files:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/media_files_$(date +%Y%m%d).tar.gz /data
```

---

## 11. CI/CD Integration

### 11.1 Automated Build

```bash
# Example GitHub Actions / CI script
docker build -t ecommerce-backend:${CI_COMMIT_SHA} backend/
docker tag ecommerce-backend:${CI_COMMIT_SHA} ecommerce-backend:latest

# Run tests
docker run --rm ecommerce-backend:${CI_COMMIT_SHA} \
  python manage.py test --settings=config.settings.test

# Security scan
trivy image --exit-code 1 --severity HIGH,CRITICAL \
  ecommerce-backend:${CI_COMMIT_SHA}

# Push to registry
docker push ecommerce-backend:${CI_COMMIT_SHA}
docker push ecommerce-backend:latest
```

---

## 12. Quick Reference

### Common Commands

```bash
# Start services
docker-compose -f docker-compose.production.yml up -d

# Stop services
docker-compose -f docker-compose.production.yml down

# Restart service
docker-compose -f docker-compose.production.yml restart backend

# View logs
docker-compose -f docker-compose.production.yml logs -f backend

# Execute command
docker-compose -f docker-compose.production.yml exec backend python manage.py shell

# Check health
curl http://localhost:8000/health/
```

### Emergency Contacts

- **On-Call Engineer**: [Contact info]
- **Database Admin**: [Contact info]
- **Security Team**: [Contact info]

---

## Appendix: Environment Variables

### Required Variables

- `SECRET_KEY`: Django secret key (50+ characters)
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
- `DATABASE_URL`: PostgreSQL connection string
- `DB_PASSWORD`: Database password

### Optional Variables

- `USE_VAULT`: Enable Vault integration (default: false)
- `VAULT_ADDR`: Vault server address
- `VAULT_TOKEN`: Vault authentication token
- `SENTRY_DSN`: Sentry error tracking DSN
- `RUN_MIGRATIONS`: Run migrations on startup (default: true)
- `COLLECT_STATIC`: Collect static files (default: true)

---

**Last Updated**: 2025-12-11
**Version**: 1.0.0
**Maintained By**: DevOps Team
