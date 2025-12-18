# PHASE 2 EXECUTION PLAN
## Docker Production Hardening (Week 3-4)

**Status:** Ready to Execute
**Prerequisites:** ✅ Phase 0 Complete, ✅ Phase 1 Complete
**Story Points:** 55
**Estimated Duration:** 1-2 weeks
**Priority:** High

---

## Table of Contents

1. [Overview](#overview)
2. [Task Breakdown](#task-breakdown)
3. [Execution Steps](#execution-steps)
4. [Testing Strategy](#testing-strategy)
5. [Rollback Plan](#rollback-plan)
6. [Success Criteria](#success-criteria)

---

## Overview

### Goals

Phase 2 transforms the Docker setup from development-ready to production-hardened with:

- **Zero-downtime deployments** via blue-green strategy
- **Production-grade Nginx** with TLS 1.3, rate limiting, and security headers
- **Network segmentation** for enhanced security
- **Comprehensive health checks** for all services
- **Structured logging** for production observability
- **Automated backups** to prevent data loss

### Success Metrics

| Metric | Current | Target | Impact |
|--------|---------|--------|--------|
| Deployment downtime | Manual, minutes | 0 seconds | Zero-downtime |
| SSL rating | N/A | A+ (SSL Labs) | Security compliance |
| Services with health checks | 2/12 | 12/12 | 100% coverage |
| Network isolation | None | Backend internal-only | Attack surface reduced |
| Backup automation | Manual | Daily automated | Data protection |
| Rate limiting | None | All endpoints | DDoS protection |

---

## Task Breakdown

### DOCKER-003: Blue-Green Deployment (13 SP)

**Priority:** High
**Description:** Implement zero-downtime deployment strategy

**What is Blue-Green Deployment:**
- Two identical production environments (blue and green)
- Traffic switches between them during deployment
- Instant rollback by switching traffic back
- No downtime for users

**Implementation:**
1. Create deployment script with health check integration
2. Configure nginx to switch between blue/green upstreams
3. Implement automated rollback on health check failure
4. Add smoke tests after deployment
5. Document deployment procedures

**Files to Create:**
- `deploy/docker/scripts/blue-green-deploy.sh` - Main deployment script
- `deploy/docker/scripts/rollback.sh` - Emergency rollback
- `deploy/docker/scripts/health-check.sh` - Health verification
- `deploy/docker/scripts/smoke-test.sh` - Post-deployment tests
- `deploy/nginx/conf.d/upstream.conf` - Nginx upstream config

**Acceptance Criteria:**
- ✅ Can deploy without downtime
- ✅ Automated health checks before traffic switch
- ✅ Rollback completes in < 30 seconds
- ✅ Smoke tests validate deployment
- ✅ Documentation complete

---

### DOCKER-004: Health Checks for All Services (5 SP)

**Priority:** High
**Description:** Add Docker health checks to all containers

**Current Coverage:** 2/12 services (backend, some AI services)
**Target:** 12/12 services

**Services Needing Health Checks:**
1. PostgreSQL
2. Redis
3. Nginx
4. Vault (if deployed)
5. PGBouncer (if deployed)
6. All AI services (7 services)
7. API Gateway
8. Monitoring services (Prometheus, Grafana)

**Implementation:**
1. Add HEALTHCHECK directives to all Dockerfiles
2. Create health check endpoints where missing
3. Configure health check intervals and timeouts
4. Update docker-compose with depends_on conditions
5. Test health check reliability

**Example Health Check:**
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1
```

**Acceptance Criteria:**
- ✅ All 12 services have HEALTHCHECK directives
- ✅ Health checks use appropriate intervals
- ✅ Services wait for dependencies to be healthy
- ✅ Failed health checks trigger restart
- ✅ Documentation updated

---

### DOCKER-005: Production Logging (5 SP)

**Priority:** Medium
**Description:** Implement structured JSON logging

**Current State:**
- Mixed logging formats
- Some logs to stdout, some to files
- No centralized aggregation
- Difficult to parse and search

**Target State:**
- All services log JSON to stdout
- Structured fields (timestamp, level, service, trace_id, etc.)
- Ready for aggregation (ELK, Loki, CloudWatch)
- Consistent format across all services

**Implementation:**
1. Update backend logging to structured JSON
2. Configure AI services for JSON logging
3. Add request ID propagation
4. Configure log rotation for file-based logs
5. Update docker-compose with logging drivers

**Logging Format:**
```json
{
  "timestamp": "2025-12-18T10:30:45.123Z",
  "level": "INFO",
  "service": "backend",
  "request_id": "abc-123-def",
  "message": "User login successful",
  "user_id": "12345",
  "duration_ms": 45
}
```

**Files to Update:**
- `services/backend/core/logging.py` - JSON formatter
- `services/ai/shared/logger.py` - AI services logger
- `deploy/docker/compose/production.yml` - Logging drivers
- `config/logging/fluent-bit.conf` - Log aggregation (optional)

**Acceptance Criteria:**
- ✅ All services log structured JSON
- ✅ Request IDs propagate across services
- ✅ Logs include service name and version
- ✅ Log levels configurable via environment
- ✅ Documentation updated

---

### NGINX-001: Production Nginx with TLS (8 SP)

**Priority:** High
**Description:** Production-hardened Nginx with TLS 1.3

**Current State:**
- Basic nginx configuration
- No TLS
- No security headers
- No rate limiting
- Single upstream

**Target State:**
- TLS 1.3 with strong ciphers
- A+ rating on SSL Labs
- Security headers (HSTS, CSP, etc.)
- Compression enabled
- Proper logging
- Blue-green upstream support

**Implementation:**
1. Create production Nginx Dockerfile
2. Configure TLS 1.3 with modern ciphers
3. Add security headers
4. Configure access/error logging
5. Set up compression (gzip/brotli)
6. Configure upstream health checks
7. Add rate limiting (separate task)

**Files to Create:**
- `deploy/docker/images/nginx/Dockerfile` - Production Nginx image
- `deploy/nginx/nginx.conf` - Main configuration
- `deploy/nginx/conf.d/api.conf` - API routing
- `deploy/nginx/conf.d/security.conf` - Security headers
- `deploy/nginx/conf.d/upstream.conf` - Blue-green upstreams
- `deploy/nginx/ssl/` - SSL certificates directory

**TLS Configuration:**
```nginx
# TLS 1.3 only with strong ciphers
ssl_protocols TLSv1.3;
ssl_ciphers TLS_AES_256_GCM_SHA384:TLS_AES_128_GCM_SHA256;
ssl_prefer_server_ciphers off;

# OCSP stapling
ssl_stapling on;
ssl_stapling_verify on;

# Session resumption
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;
```

**Security Headers:**
```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
add_header X-Frame-Options "DENY" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
```

**Acceptance Criteria:**
- ✅ SSL Labs A+ rating
- ✅ TLS 1.3 enabled
- ✅ All security headers present
- ✅ Compression working
- ✅ Access logs structured
- ✅ Blue-green upstream ready

---

### NGINX-002: Rate Limiting (5 SP)

**Priority:** Medium
**Description:** Implement rate limiting on all endpoints

**Purpose:**
- Protect against DDoS attacks
- Prevent API abuse
- Ensure fair usage
- Protect backend from overload

**Rate Limit Tiers:**
1. **Authentication endpoints:** 10 req/min per IP
2. **API endpoints:** 100 req/min per user
3. **Search/AI endpoints:** 30 req/min per user
4. **Static assets:** 1000 req/min per IP
5. **Health checks:** Unlimited (internal only)

**Implementation:**
1. Configure nginx rate limiting zones
2. Add rate limit directives to locations
3. Customize error responses
4. Add rate limit headers (X-RateLimit-*)
5. Document rate limits in API docs

**Nginx Configuration:**
```nginx
# Define rate limit zones
limit_req_zone $binary_remote_addr zone=auth:10m rate=10r/m;
limit_req_zone $http_x_user_id zone=api:10m rate=100r/m;
limit_req_zone $http_x_user_id zone=ai:10m rate=30r/m;

# Apply to locations
location /api/auth/ {
    limit_req zone=auth burst=5 nodelay;
    # ...
}

location /api/ {
    limit_req zone=api burst=20 nodelay;
    # ...
}
```

**Files to Update:**
- `deploy/nginx/conf.d/rate-limiting.conf` - Rate limit config
- `deploy/nginx/conf.d/api.conf` - Apply limits to locations
- `docs/api/rate-limits.md` - API documentation

**Acceptance Criteria:**
- ✅ Rate limits enforced on all endpoints
- ✅ Appropriate burst sizes configured
- ✅ Custom error responses for 429 status
- ✅ Rate limit headers in responses
- ✅ Documentation updated

---

### NET-001: Network Segmentation (8 SP)

**Priority:** High
**Description:** Isolate backend services from external access

**Current State:**
- All services on single network
- Backend accessible from external
- No network isolation
- Flat network topology

**Target State:**
- Frontend network (nginx, public-facing)
- Backend network (internal services only)
- Database network (database tier only)
- Services communicate via defined interfaces only

**Network Architecture:**
```
┌─────────────────────────────────────────┐
│          External Network               │
│                                         │
│  ┌──────────┐                          │
│  │  Nginx   │ (Port 80/443)            │
│  └────┬─────┘                          │
└───────┼──────────────────────────────────┘
        │
┌───────┼──────────────────────────────────┐
│       │      Frontend Network            │
│  ┌────┴─────┐    ┌──────────┐           │
│  │ Backend  │◄───│ AI Gateway│           │
│  └────┬─────┘    └──────────┘           │
└───────┼──────────────────────────────────┘
        │
┌───────┼──────────────────────────────────┐
│       │      Backend Network             │
│  ┌────┴─────┐    ┌──────────┐           │
│  │ Postgres │    │  Redis   │           │
│  └──────────┘    └──────────┘           │
└─────────────────────────────────────────┘
```

**Implementation:**
1. Define Docker networks in compose
2. Assign services to appropriate networks
3. Remove unnecessary network access
4. Configure service-to-service communication
5. Document network topology

**Docker Compose Networks:**
```yaml
networks:
  frontend:
    driver: bridge
    internal: false  # Connected to external
  backend:
    driver: bridge
    internal: true   # No external access
  database:
    driver: bridge
    internal: true   # No external access

services:
  nginx:
    networks:
      - frontend

  backend:
    networks:
      - frontend  # For nginx communication
      - backend   # For AI services
      - database  # For database access

  postgres:
    networks:
      - database  # Isolated
```

**Files to Update:**
- `deploy/docker/compose/production.yml` - Network definitions
- `deploy/docker/compose/network-policy.yml` - Specific policies
- `docs/architecture/network-topology.md` - Documentation

**Acceptance Criteria:**
- ✅ Backend not accessible from external
- ✅ Database isolated to backend only
- ✅ Services communicate via defined paths
- ✅ Network diagram documented
- ✅ Security tested

---

### COMPOSE-001: Production docker-compose.yml (8 SP)

**Priority:** High
**Description:** Production-ready docker-compose with all best practices

**Current State:**
- Development-focused compose files
- Missing production optimizations
- No resource limits (added in Phase 0, needs refinement)
- No restart policies in all services
- Missing health checks in compose

**Target State:**
- Production docker-compose with all best practices
- Resource limits on all services
- Proper restart policies
- Health check dependencies
- Security options enabled
- Read-only root filesystem where possible

**Best Practices to Implement:**
1. **Resource Limits:** CPU, memory, PIDs
2. **Restart Policies:** unless-stopped or on-failure
3. **Security Options:** no-new-privileges, read-only
4. **Health Checks:** With depends_on conditions
5. **Logging:** JSON driver with rotation
6. **Networks:** Proper segmentation
7. **Volumes:** Named volumes with options
8. **Environment:** From env files, not inline

**Example Service Configuration:**
```yaml
services:
  backend:
    image: backend:${VERSION:-latest}
    restart: unless-stopped

    # Resource limits
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
          pids: 100
        reservations:
          cpus: '0.5'
          memory: 512M

    # Security
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp:size=100M,mode=1777

    # Health check
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

    # Logging
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

    # Networks
    networks:
      - frontend
      - backend

    # Environment
    env_file:
      - ../../../config/environments/production.env
```

**Files to Update:**
- `deploy/docker/compose/production.yml` - Complete rewrite
- `deploy/docker/resource-limits.yaml` - Update limits
- `docs/deployment/production-guide.md` - Documentation

**Acceptance Criteria:**
- ✅ All services have resource limits
- ✅ Restart policies on all services
- ✅ Security options enabled
- ✅ Health checks with depends_on
- ✅ Proper network segmentation
- ✅ Logging configured
- ✅ No hardcoded secrets

---

### BACKUP-001: Automated Backup Scripts (3 SP)

**Priority:** Medium
**Description:** Automated daily backups to S3 or local storage

**What to Backup:**
1. PostgreSQL database
2. Redis data (if persistence enabled)
3. Uploaded media files
4. Configuration files
5. SSL certificates

**Backup Strategy:**
- **Frequency:** Daily at 2 AM
- **Retention:** 7 daily, 4 weekly, 12 monthly
- **Location:** S3 or local with sync
- **Encryption:** AES-256
- **Verification:** Weekly restore test

**Implementation:**
1. Create backup script for PostgreSQL
2. Create backup script for media files
3. Implement S3 upload with encryption
4. Set up cron job for automation
5. Create restore scripts
6. Implement backup verification

**Files to Create:**
- `scripts/backup/backup-databases.sh` - Database backup
- `scripts/backup/backup-media.sh` - Media files backup
- `scripts/backup/backup-to-s3.sh` - Upload to S3
- `scripts/backup/restore-database.sh` - Database restore
- `scripts/backup/verify-backup.sh` - Test restore
- `scripts/backup/setup-cron.sh` - Automate backups
- `docs/operations/backup-restore.md` - Documentation

**PostgreSQL Backup Script:**
```bash
#!/bin/bash
# backup-databases.sh

BACKUP_DIR="/backups/postgres"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/backup_$DATE.sql.gz"

# Create backup
docker-compose exec -T postgres pg_dumpall -U postgres | gzip > "$BACKUP_FILE"

# Encrypt
gpg --encrypt --recipient backup@example.com "$BACKUP_FILE"

# Upload to S3
aws s3 cp "$BACKUP_FILE.gpg" "s3://backups/postgres/$DATE/"

# Cleanup old backups (keep 7 days)
find "$BACKUP_DIR" -name "backup_*.sql.gz*" -mtime +7 -delete
```

**Acceptance Criteria:**
- ✅ Daily automated backups working
- ✅ Backups encrypted
- ✅ Uploaded to S3 successfully
- ✅ Retention policy enforced
- ✅ Restore tested weekly
- ✅ Documentation complete

---

## Execution Steps

### Week 1: Core Infrastructure

**Day 1-2: Health Checks & Logging**
1. Add health checks to all Dockerfiles (DOCKER-004)
2. Implement structured JSON logging (DOCKER-005)
3. Update docker-compose with health check dependencies
4. Test health check reliability

**Day 3-4: Nginx Production Setup**
1. Create production Nginx Dockerfile (NGINX-001)
2. Configure TLS 1.3 with strong ciphers
3. Add security headers
4. Implement rate limiting (NGINX-002)
5. Test SSL Labs rating

**Day 5: Network Segmentation**
1. Define Docker networks (NET-001)
2. Assign services to networks
3. Test service communication
4. Document network topology

### Week 2: Deployment & Automation

**Day 6-7: Blue-Green Deployment**
1. Create deployment scripts (DOCKER-003)
2. Configure nginx for blue-green
3. Implement health check integration
4. Test zero-downtime deployment
5. Create rollback procedures

**Day 8: Production Compose & Backups**
1. Finalize production docker-compose (COMPOSE-001)
2. Implement backup scripts (BACKUP-001)
3. Set up cron jobs
4. Test backup and restore

**Day 9-10: Testing & Documentation**
1. End-to-end testing of all Phase 2 features
2. Load testing with new setup
3. Security testing
4. Complete all documentation

---

## Testing Strategy

### Unit Tests
- Health check endpoints return correct status
- Logging produces valid JSON
- Rate limiting calculations correct

### Integration Tests
```bash
# Test health checks
docker-compose ps  # All services healthy

# Test blue-green deployment
bash deploy/docker/scripts/blue-green-deploy.sh
curl http://localhost/health  # No downtime

# Test rate limiting
for i in {1..100}; do curl http://localhost/api/products/; done
# Should see 429 responses

# Test network segmentation
docker network inspect ecommerce_backend
# Postgres should not be externally accessible

# Test backups
bash scripts/backup/backup-databases.sh
bash scripts/backup/restore-database.sh
# Restore should succeed
```

### Load Tests
- Deploy new version under load
- Verify zero downtime
- Test rate limiting under load
- Verify health checks don't impact performance

### Security Tests
```bash
# Test TLS configuration
testssl.sh localhost:443

# Test network isolation
nmap -p- backend-container  # Should timeout

# Test rate limiting bypass attempts
# Various attack patterns
```

---

## Rollback Plan

### Quick Rollback
```bash
# Rollback deployment
bash deploy/docker/scripts/rollback.sh

# Switch to previous version
docker-compose -f deploy/docker/compose/production.yml \
  up -d --scale backend=2 backend:previous-version
```

### Component Rollback
- **Nginx:** Revert config, reload
- **Networks:** Remove network, use single network temporarily
- **Health checks:** Disable in compose, restart services
- **Backups:** Restore from previous backup

### Emergency Procedures
1. Switch to maintenance mode
2. Roll back to Phase 1 state
3. Investigate issues
4. Fix and retry

---

## Success Criteria

### Must Have (Blocking)
- ✅ Zero-downtime deployment working
- ✅ SSL Labs A+ rating
- ✅ All 12 services have health checks
- ✅ Network segmentation functional
- ✅ Rate limiting operational
- ✅ Automated backups working
- ✅ All tests passing

### Should Have (Important)
- ✅ Structured JSON logging
- ✅ Production docker-compose optimized
- ✅ Backup verification automated
- ✅ Documentation complete
- ✅ Rollback procedures tested

### Nice to Have (Optional)
- ✅ Log aggregation configured
- ✅ Monitoring dashboards updated
- ✅ Performance benchmarks

---

## Risk Mitigation

### Risk 1: Downtime During Network Changes
**Mitigation:** Test network changes in staging first, have rollback ready

### Risk 2: SSL Certificate Issues
**Mitigation:** Use Let's Encrypt staging first, test certificate renewal

### Risk 3: Rate Limiting Too Aggressive
**Mitigation:** Start with generous limits, monitor, adjust gradually

### Risk 4: Backup Failures
**Mitigation:** Test restore weekly, have multiple backup locations

### Risk 5: Blue-Green Complexity
**Mitigation:** Start simple, add complexity gradually, document thoroughly

---

## Dependencies

**Phase 0:** ✅ Complete (security fixes, resource limits)
**Phase 1:** ✅ Complete (structure reorganization)
**External:**
- SSL certificates (Let's Encrypt or purchased)
- S3 bucket for backups (or local storage)
- Domain name configured

---

## Next Phase

After Phase 2 completion:
**Phase 3: CI/CD & Security (Week 5-6)**
- Complete production pipeline
- Vault secrets management
- Security automation
- Compliance documentation

---

**Document Version:** 1.0
**Last Updated:** 2025-12-18
**Status:** Ready for Execution
**Owner:** Platform Engineering Team
