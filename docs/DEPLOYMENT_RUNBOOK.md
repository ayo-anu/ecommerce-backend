# Production Deployment Runbook

**Last Updated**: 2025-12-04
**Version**: 1.0
**Owner**: Platform Team
**On-Call**: See PagerDuty rotation

---

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Deployment Steps](#deployment-steps)
3. [Rollback Procedures](#rollback-procedures)
4. [Health Check Verification](#health-check-verification)
5. [Common Issues and Troubleshooting](#common-issues-and-troubleshooting)
6. [Emergency Contacts](#emergency-contacts)

---

## Pre-Deployment Checklist

### 1. Code Quality Verification

- [ ] All CI/CD pipelines passing
- [ ] Security scans completed (no CRITICAL/HIGH vulnerabilities)
- [ ] Code review approved by at least 2 engineers
- [ ] Unit tests passing with >70% coverage
- [ ] Integration tests passing

### 2. Database Migrations

- [ ] Database migrations reviewed and tested in staging
- [ ] Backup verification completed
- [ ] Rollback migrations prepared
- [ ] Migration downtime estimated and communicated

### 3. Configuration and Secrets

- [ ] All required environment variables set
- [ ] Service auth keys rotated if needed
- [ ] SSL/TLS certificates valid (>30 days remaining)
- [ ] DNS records configured
- [ ] Load balancer health checks configured

### 4. Dependencies

- [ ] All third-party service status verified
- [ ] API rate limits checked
- [ ] External service SLAs reviewed

### 5. Communication

- [ ] Deployment scheduled and communicated to team
- [ ] Status page updated (if maintenance window)
- [ ] Customer support team notified
- [ ] Stakeholders informed

### 6. Monitoring

- [ ] Grafana dashboards accessible
- [ ] Alert routing configured
- [ ] PagerDuty schedules verified
- [ ] Log aggregation working

---

## Deployment Steps

### Phase 1: Pre-Deployment (30 minutes before)

#### 1.1 Verify System Status

```bash
# Check all services are healthy
curl https://api.production.example.com/health

# Check database connections
docker exec backend python manage.py dbshell -c "SELECT 1;"

# Check Redis
docker exec redis redis-cli PING

# Check Celery workers
docker exec celery-worker celery -A config inspect active
```

#### 1.2 Create Backup

```bash
# Backup databases
./scripts/backup_databases.sh --verify

# Backup volumes
docker run --rm -v postgres_data:/data -v /backup:/backup \
  ubuntu tar czf /backup/postgres-$(date +%Y%m%d-%H%M%S).tar.gz /data

# Backup configuration
cp -r /etc/ecommerce /backup/config-$(date +%Y%m%d-%H%M%S)
```

#### 1.3 Tag Release

```bash
# Tag the release
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0

# Build and tag Docker images
docker build -t ecommerce-backend:v1.0.0 backend/
docker build -t ecommerce-api-gateway:v1.0.0 ai-services/api_gateway/
```

### Phase 2: Database Migrations (if applicable)

#### 2.1 Put Application in Maintenance Mode (if needed)

```bash
# Enable maintenance mode
docker exec nginx sh -c 'echo "maintenance" > /usr/share/nginx/html/status'

# Or update Nginx config
# Location: infrastructure/nginx/maintenance.html
```

#### 2.2 Run Database Migrations

```bash
# Dry run first
docker exec backend python manage.py migrate --plan

# Run migrations
docker exec backend python manage.py migrate

# Verify migrations
docker exec backend python manage.py showmigrations
```

#### 2.3 Verify Data Integrity

```bash
# Run data integrity checks
docker exec backend python manage.py check --database default

# Test critical queries
docker exec backend python manage.py shell
>>> from apps.products.models import Product
>>> Product.objects.count()
```

### Phase 3: Deployment

#### 3.1 Pull Latest Code

```bash
# On production server
cd /opt/ecommerce-platform
git fetch --all
git checkout v1.0.0

# Verify correct version
git describe --tags
```

#### 3.2 Update Environment Variables

```bash
# Update .env file
nano /opt/ecommerce-platform/.env

# Source environment
export $(cat .env | xargs)

# Verify critical variables
echo $SECRET_KEY | wc -c  # Should be >50
echo $ALLOWED_HOSTS
echo $DATABASE_URL
```

#### 3.3 Deploy Services

**Option A: Docker Compose (Small/Medium deployments)**

```bash
# Build images
docker-compose -f infrastructure/docker-compose.yaml \
  -f infrastructure/docker-compose.prod.yaml \
  build

# Pull dependencies
docker-compose pull

# Deploy with zero-downtime
docker-compose up -d --no-deps --build backend

# Wait for health check
sleep 10
curl http://localhost:8000/health

# Deploy remaining services
docker-compose up -d --no-deps --build api-gateway
docker-compose up -d --no-deps --build celery-worker
docker-compose up -d --no-deps --build celery-beat

# Restart Nginx (last)
docker-compose up -d --no-deps nginx
```

**Option B: Kubernetes (Large deployments)**

```bash
# Apply configurations
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/configmaps.yaml

# Deploy backend
kubectl set image deployment/backend \
  backend=ecommerce-backend:v1.0.0 \
  --record

# Wait for rollout
kubectl rollout status deployment/backend

# Deploy remaining services
kubectl set image deployment/api-gateway \
  api-gateway=ecommerce-api-gateway:v1.0.0 \
  --record

kubectl rollout status deployment/api-gateway
```

#### 3.4 Verify Deployment

```bash
# Check running containers
docker ps

# Check logs for errors
docker-compose logs --tail=100 backend
docker-compose logs --tail=100 api-gateway

# Verify health endpoints
curl http://localhost:8000/health
curl http://localhost:8080/health

# Check metrics
curl http://localhost:8000/metrics
```

### Phase 4: Post-Deployment Verification

#### 4.1 Smoke Tests

```bash
# Test authentication
curl -X POST https://api.production.example.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}'

# Test key endpoints
curl https://api.production.example.com/api/v1/products/
curl https://api.production.example.com/api/v1/orders/

# Test AI services
curl https://api.production.example.com/api/v1/recommendations/test-user
```

#### 4.2 Monitor Metrics (30 minutes)

```bash
# Watch error rates
watch -n 5 'curl -s http://localhost:9090/api/v1/query?query=rate(http_requests_total{status=~\"5..\"}[5m])'

# Watch latency
watch -n 5 'curl -s http://localhost:9090/api/v1/query?query=histogram_quantile(0.95,rate(http_request_duration_seconds_bucket[5m]))'

# Watch service health
watch -n 5 'curl -s http://localhost:8000/health | jq'
```

#### 4.3 Verify Monitoring

- [ ] Check Grafana dashboards
- [ ] Verify metrics are being collected
- [ ] Ensure alerts are not firing
- [ ] Check log aggregation
- [ ] Verify distributed tracing

#### 4.4 Performance Testing

```bash
# Run load test
ab -n 1000 -c 10 https://api.production.example.com/api/v1/products/

# Or use k6
k6 run --vus 10 --duration 30s tests/load-test.js
```

### Phase 5: Enable Traffic

#### 5.1 Disable Maintenance Mode

```bash
# Remove maintenance page
docker exec nginx rm -f /usr/share/nginx/html/status

# Reload Nginx
docker exec nginx nginx -s reload
```

#### 5.2 Gradual Traffic Ramp (if using canary deployment)

```bash
# Route 10% of traffic to new version
kubectl set image deployment/backend backend=ecommerce-backend:v1.0.0 \
  --record

# Monitor for 10 minutes, then increase
kubectl scale deployment/backend --replicas=5

# Continue monitoring and scale up
```

### Phase 6: Post-Deployment Tasks

#### 6.1 Update Documentation

- [ ] Update CHANGELOG.md
- [ ] Update API documentation
- [ ] Update deployment notes

#### 6.2 Cleanup

```bash
# Remove old Docker images
docker image prune -a --filter "until=24h" --force

# Clean build artifacts
docker builder prune --force

# Archive old logs
find /var/log/ecommerce -name "*.log" -mtime +7 -exec gzip {} \;
```

#### 6.3 Communication

- [ ] Update status page (deployment complete)
- [ ] Send deployment summary to team
- [ ] Notify stakeholders
- [ ] Update on-call documentation

---

## Rollback Procedures

### When to Rollback

Rollback immediately if:
- Error rate > 5%
- P95 latency > 2x baseline
- Critical functionality broken
- Data corruption detected
- Security vulnerability introduced

### Rollback Steps

#### 1. Quick Rollback (Docker Compose)

```bash
# Stop current version
docker-compose down

# Checkout previous version
git checkout v0.9.9

# Deploy previous version
docker-compose up -d

# Verify
curl http://localhost:8000/health
```

#### 2. Kubernetes Rollback

```bash
# Rollback to previous revision
kubectl rollout undo deployment/backend

# Or rollback to specific revision
kubectl rollout undo deployment/backend --to-revision=2

# Watch rollback
kubectl rollout status deployment/backend
```

#### 3. Database Rollback (if migrations applied)

```bash
# List migrations
docker exec backend python manage.py showmigrations

# Rollback to previous migration
docker exec backend python manage.py migrate app_name 0042_previous_migration

# Verify
docker exec backend python manage.py showmigrations
```

#### 4. Restore from Backup (last resort)

```bash
# Stop services
docker-compose down

# Restore database
./scripts/restore_database.sh /backup/postgres-20250104-020000.tar.gz

# Restore volumes
docker run --rm -v postgres_data:/data -v /backup:/backup \
  ubuntu tar xzf /backup/postgres-20250104-020000.tar.gz -C /

# Restart services
docker-compose up -d
```

---

## Health Check Verification

### Service Health Endpoints

| Service | Endpoint | Expected Response |
|---------|----------|-------------------|
| Backend | `http://backend:8000/health` | `{"status": "healthy"}` |
| API Gateway | `http://api-gateway:8080/health` | `{"status": "healthy"}` |
| Celery Worker | `celery inspect ping` | `pong` |
| PostgreSQL | `pg_isready` | `accepting connections` |
| Redis | `redis-cli PING` | `PONG` |

### Automated Health Check Script

```bash
#!/bin/bash
# File: scripts/verify_deployment.sh

set -e

echo "🔍 Verifying deployment..."

# Backend
echo "Checking backend..."
curl -f http://localhost:8000/health || exit 1

# API Gateway
echo "Checking API gateway..."
curl -f http://localhost:8080/health || exit 1

# Database
echo "Checking database..."
docker exec postgres pg_isready || exit 1

# Redis
echo "Checking Redis..."
docker exec redis redis-cli PING || exit 1

# Celery
echo "Checking Celery..."
docker exec celery-worker celery -A config inspect ping || exit 1

echo "✅ All services healthy"
```

---

## Common Issues and Troubleshooting

### Issue 1: Service Won't Start

**Symptoms**: Container exits immediately

**Diagnosis**:
```bash
# Check logs
docker logs backend --tail=100

# Check exit code
docker inspect backend --format='{{.State.ExitCode}}'

# Check resource limits
docker stats
```

**Solutions**:
- Check environment variables
- Verify port availability
- Check disk space
- Review recent configuration changes

### Issue 2: Database Connection Errors

**Symptoms**: `OperationalError: could not connect to server`

**Diagnosis**:
```bash
# Test connection
docker exec backend python manage.py dbshell

# Check database status
docker exec postgres pg_isready

# Check network
docker exec backend ping postgres
```

**Solutions**:
- Verify `DATABASE_URL`
- Check database container running
- Verify network connectivity
- Check connection pool settings

### Issue 3: High Memory Usage

**Symptoms**: Services crashing, OOM errors

**Diagnosis**:
```bash
# Check memory usage
docker stats

# Check system memory
free -h

# Check for memory leaks
docker exec backend python manage.py shell
>>> import resource
>>> resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
```

**Solutions**:
- Increase memory limits
- Check for memory leaks
- Reduce worker concurrency
- Implement memory limits in Docker

### Issue 4: Slow Response Times

**Symptoms**: Latency spikes, timeouts

**Diagnosis**:
```bash
# Check metrics
curl http://localhost:9090/api/v1/query?query=http_request_duration_seconds

# Check database queries
docker exec backend python manage.py check --database default

# Check Celery queue size
docker exec celery-worker celery -A config inspect active_queues
```

**Solutions**:
- Scale workers
- Optimize database queries
- Check cache hit rate
- Review external API calls

---

## Emergency Contacts

### On-Call Rotation
- PagerDuty: https://example.pagerduty.com
- Phone: +1-XXX-XXX-XXXX

### Key Personnel

| Role | Name | Contact |
|------|------|---------|
| Platform Lead | [Name] | [Email/Phone] |
| Database Admin | [Name] | [Email/Phone] |
| DevOps Lead | [Name] | [Email/Phone] |
| Security Lead | [Name] | [Email/Phone] |

### Escalation Path

1. On-call engineer (PagerDuty)
2. Platform Lead
3. Engineering Manager
4. VP Engineering
5. CTO

---

## Appendix

### Useful Commands

```bash
# Quick health check all services
docker-compose ps

# View logs for all services
docker-compose logs -f --tail=100

# Restart specific service
docker-compose restart backend

# Scale workers
docker-compose up -d --scale celery-worker=5

# Execute Django management command
docker exec backend python manage.py <command>

# Database backup
./scripts/backup_databases.sh

# Generate service keys
python scripts/generate_service_keys.py
```

### Links

- Grafana: https://grafana.production.example.com
- Prometheus: https://prometheus.production.example.com
- Kibana: https://kibana.production.example.com
- Sentry: https://sentry.io/ecommerce-platform
- Status Page: https://status.example.com

---

**Document Version**: 1.0
**Last Deployment**: [Date]
**Next Review**: 2025-03-04
