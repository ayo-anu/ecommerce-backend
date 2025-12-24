# E-Commerce Platform Operations Manual

**Version**: 1.0
**Last Updated**: 2025-12-24
**Owner**: Platform Operations Team
**Classification**: Internal Use Only

---

## Table of Contents

1. [Introduction](#introduction)
2. [System Overview](#system-overview)
3. [Operations Team Structure](#operations-team-structure)
4. [Daily Operations](#daily-operations)
5. [Monitoring and Alerting](#monitoring-and-alerting)
6. [Incident Management](#incident-management)
7. [Deployment Procedures](#deployment-procedures)
8. [Disaster Recovery](#disaster-recovery)
9. [Maintenance Procedures](#maintenance-procedures)
10. [Security Operations](#security-operations)
11. [Performance Management](#performance-management)
12. [Runbooks and Procedures](#runbooks-and-procedures)
13. [Tools and Access](#tools-and-access)
14. [Escalation and Contacts](#escalation-and-contacts)
15. [Appendices](#appendices)

---

## Introduction

### Purpose

This operations manual serves as the definitive guide for operating, maintaining, and supporting the E-Commerce platform. It consolidates all operational procedures, runbooks, and best practices required for day-to-day operations and incident response.

### Audience

- Platform Operations Engineers
- Site Reliability Engineers (SRE)
- DevOps Engineers
- On-call Engineers
- Platform Leadership
- New team members during onboarding

### Document Scope

This manual covers:
- System architecture and components
- Daily operational procedures
- Monitoring and incident response
- Deployment and rollback procedures
- Disaster recovery and business continuity
- Maintenance and security operations
- Performance optimization
- Troubleshooting and runbooks

### Related Documentation

| Document | Location | Purpose |
|----------|----------|---------|
| Disaster Recovery Plan | [disaster-recovery.md](disaster-recovery.md) | DR procedures and RTO/RPO |
| Dependency Management | [../maintenance/dependency-management.md](../maintenance/dependency-management.md) | Automated dependency updates |
| Deployment Guide | [../deployment/production-guide.md](../deployment/production-guide.md) | Production deployment procedures |
| Architecture Overview | [../architecture/system-architecture.md](../architecture/system-architecture.md) | System design and components |
| Security Policies | [../security/](../security/) | Security procedures and policies |

---

## System Overview

### Architecture

The E-Commerce platform is a **microservices-based** system deployed using **Docker Compose** (no Kubernetes).

#### Components

```
┌─────────────────────────────────────────────────────────────┐
│                         Internet                             │
└─────────────────┬───────────────────────────────────────────┘
                  │
          ┌───────▼────────┐
          │  Nginx Proxy   │ (Port 80/443)
          │  + SSL/TLS     │
          └───────┬────────┘
                  │
     ┌────────────┴────────────┐
     │                         │
┌────▼──────┐         ┌────────▼────────┐
│  Backend  │         │  AI API Gateway │
│  (Django) │         │  (FastAPI)      │
└────┬──────┘         └────────┬────────┘
     │                         │
     │              ┌──────────┴─────────────┐
     │              │  AI Microservices      │
     │              ├────────────────────────┤
     │              │ - Recommendation       │
     │              │ - Fraud Detection      │
┌────▼────────┐     │ - Search Engine       │
│ PostgreSQL  │     │ - Chatbot RAG         │
│ (Main + AI) │     │ - Pricing Engine      │
└─────────────┘     │ - Demand Forecasting  │
                    │ - Visual Recognition  │
┌─────────────┐     └───────────────────────┘
│   Redis     │
│   Cache     │
└─────────────┘
```

#### Technology Stack

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Backend | Django | 4.2.x | Main application logic |
| API Gateway | FastAPI | 0.109.x | AI services routing |
| Database | PostgreSQL | 15.x | Primary data store |
| AI Database | PostgreSQL | 15.x | AI/ML data store |
| Cache | Redis | 7.x | Session & data caching |
| Proxy | Nginx | 1.25.x | Reverse proxy & SSL |
| Container Runtime | Docker | 24.x | Application containers |
| Orchestration | Docker Compose | 2.x | Service orchestration |
| Monitoring | Prometheus | 2.x | Metrics collection |
| Visualization | Grafana | 10.x | Metrics visualization |
| Connection Pooling | PgBouncer | 1.21.x | Database connection pooling |

### Infrastructure

**Deployment Model**: Single-server Docker Compose (no cloud-native orchestration)

**Environment Tiers**:
1. **Production** - Live customer-facing environment
2. **Staging** - Pre-production testing
3. **Development** - Local development

**Backup Strategy**: 3-2-1 approach
- 3 copies of data (production + local backup + S3)
- 2 different storage types (local disk + S3)
- 1 offsite copy (S3 in different region)

### Service Inventory

| Service | Container Name | Port | Health Check | Critical |
|---------|---------------|------|--------------|----------|
| Backend | `ecommerce_backend` | 8000 | `/health/` | ✅ Yes |
| AI Gateway | `ecommerce_ai_gateway` | 8001 | `/health` | ✅ Yes |
| Recommendation | `ecommerce_recommendation` | 8002 | `/health` | ⚠️ High |
| Fraud Detection | `ecommerce_fraud` | 8003 | `/health` | ✅ Yes |
| Search Engine | `ecommerce_search` | 8004 | `/health` | ⚠️ High |
| Chatbot | `ecommerce_chatbot` | 8005 | `/health` | ⚠️ Medium |
| Pricing | `ecommerce_pricing` | 8006 | `/health` | ⚠️ High |
| Forecasting | `ecommerce_forecasting` | 8007 | `/health` | ⚠️ Medium |
| Visual Recognition | `ecommerce_vision` | 8008 | `/health` | ⚠️ Medium |
| PostgreSQL (Main) | `ecommerce_postgres` | 5432 | `pg_isready` | ✅ Yes |
| PostgreSQL (AI) | `ecommerce_postgres_ai` | 5433 | `pg_isready` | ✅ Yes |
| Redis | `ecommerce_redis` | 6379 | `redis-cli ping` | ✅ Yes |
| PgBouncer | `ecommerce_pgbouncer` | 6432 | Port check | ✅ Yes |
| Nginx | `ecommerce_nginx` | 80/443 | HTTP 200 | ✅ Yes |
| Prometheus | `ecommerce_prometheus` | 9090 | `/-/healthy` | ⚠️ High |
| Grafana | `ecommerce_grafana` | 3000 | `/api/health` | ⚠️ High |

---

## Operations Team Structure

### Roles and Responsibilities

#### Platform Lead
- Overall system health and performance
- Capacity planning
- Architecture decisions
- Budget and resource allocation

#### Site Reliability Engineer (SRE)
- System reliability and uptime
- Incident response and resolution
- Performance optimization
- Automation and tooling

#### DevOps Engineer
- CI/CD pipeline maintenance
- Infrastructure automation
- Deployment procedures
- Configuration management

#### Database Administrator (DBA)
- Database performance tuning
- Backup and recovery
- Schema changes
- Query optimization

#### Security Engineer
- Security monitoring
- Vulnerability management
- Access control
- Compliance

### On-Call Rotation

**Schedule**: 24/7 coverage with weekly rotation

**Primary On-Call**:
- First responder for incidents
- Triages and escalates as needed
- Documents incidents
- Handoff to next shift

**Secondary On-Call**:
- Backup for primary
- Specialized expertise escalation
- Major incident support

**On-Call Expectations**:
- Response time: 15 minutes for P0/P1
- Laptop with VPN access
- Access to all systems
- PagerDuty app installed
- Escalation contacts handy

---

## Daily Operations

### Morning Checklist (09:00 UTC)

**Duration**: ~30 minutes

```bash
#!/bin/bash
# Daily morning health check routine

echo "=== Daily Morning Operations Checklist ==="

# 1. Check all container health
echo "□ Checking container health..."
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.State}}"

# 2. Check system resources
echo "□ Checking system resources..."
df -h | grep -E '(Filesystem|/dev/)'
free -h

# 3. Check database connections
echo "□ Checking database health..."
docker exec ecommerce_postgres pg_isready -U postgres
docker exec ecommerce_postgres_ai pg_isready -U postgres

# 4. Check Redis
echo "□ Checking Redis..."
docker exec ecommerce_redis redis-cli ping

# 5. Review overnight logs
echo "□ Checking for errors in last 24h..."
docker-compose -f deploy/docker/compose/base.yml \
               -f deploy/docker/compose/production.yml \
               logs --since=24h | grep -i error | wc -l

# 6. Check backup status
echo "□ Verifying backups exist..."
find /backups/postgres -name "*.sql.gz" -mtime -1 | wc -l

# 7. Check monitoring dashboards
echo "□ Opening Grafana dashboard..."
echo "   URL: https://grafana.example.com"

# 8. Review PagerDuty incidents
echo "□ Check PagerDuty for overnight incidents..."

# 9. Check Dependabot PRs
echo "□ Review dependency updates..."
gh pr list --author "app/dependabot" --state open

# 10. Review deployment schedule
echo "□ Check deployment calendar for today..."

echo "=== Checklist Complete ==="
```

**Action Items**:
- [ ] All containers healthy
- [ ] Disk usage < 80%
- [ ] Memory usage < 85%
- [ ] No critical errors in logs
- [ ] Backups completed successfully
- [ ] No P0/P1 incidents overnight
- [ ] Security updates reviewed
- [ ] Team standup prepared

### Afternoon Checklist (15:00 UTC)

**Duration**: ~15 minutes

- [ ] Review current system load
- [ ] Check for any performance degradation
- [ ] Verify scheduled jobs completed
- [ ] Review deployment queue
- [ ] Update incident tickets
- [ ] Prepare handoff notes for next shift

### End of Day Checklist (18:00 UTC)

**Duration**: ~20 minutes

- [ ] Document any incidents or changes
- [ ] Update runbooks if needed
- [ ] Review tomorrow's deployment schedule
- [ ] Handoff notes to on-call engineer
- [ ] Update team communication channels
- [ ] Close completed tickets

### Weekly Tasks

**Monday**:
- Dependency review meeting (10:00 UTC)
- Review last week's incidents
- Plan week's deployments

**Wednesday**:
- Performance review
- Capacity planning check
- Security updates review

**Friday**:
- Backup verification report
- Incident metrics review
- On-call rotation handoff

### Monthly Tasks

- DR drill execution
- Dependency audit
- Security compliance review
- Performance trending analysis
- Capacity planning update
- Documentation review

---

## Monitoring and Alerting

### Monitoring Stack

**Prometheus** - Metrics collection
- **URL**: `https://prometheus.example.com`
- **Retention**: 15 days
- **Scrape Interval**: 15 seconds

**Grafana** - Visualization
- **URL**: `https://grafana.example.com`
- **Dashboards**:
  - System Overview
  - Service Health
  - Database Performance
  - AI Services Metrics
  - Business Metrics

**PagerDuty** - Incident management
- **URL**: `https://example.pagerduty.com`
- **Escalation Policy**: Auto-escalate after 15 minutes

### Key Metrics

#### Service Health Metrics

| Metric | Threshold | Alert Level |
|--------|-----------|-------------|
| Service Uptime | < 99.9% | P1 |
| Response Time (p95) | > 500ms | P2 |
| Response Time (p99) | > 1000ms | P1 |
| Error Rate | > 1% | P1 |
| Request Rate Drop | > 50% | P0 |

#### Infrastructure Metrics

| Metric | Warning | Critical |
|--------|---------|----------|
| CPU Usage | > 75% | > 90% |
| Memory Usage | > 80% | > 95% |
| Disk Usage | > 75% | > 90% |
| Database Connections | > 80% pool | > 95% pool |
| Redis Memory | > 75% | > 90% |

#### Business Metrics

| Metric | Threshold | Alert Level |
|--------|-----------|-------------|
| Order Completion Rate | < 95% | P2 |
| Payment Success Rate | < 98% | P1 |
| Search Query Success | < 99% | P2 |
| API Gateway Success | < 99.5% | P1 |

### Alert Routing

```
Alert Triggered
    │
    ├─ P0 (Critical)
    │   ├─ PagerDuty → Primary On-Call (immediate)
    │   ├─ SMS + Phone Call
    │   ├─ Slack #incidents (immediate)
    │   └─ Auto-escalate to Secondary after 5 min
    │
    ├─ P1 (High)
    │   ├─ PagerDuty → Primary On-Call (15 min)
    │   ├─ Slack #alerts
    │   └─ Auto-escalate to Secondary after 15 min
    │
    ├─ P2 (Medium)
    │   ├─ Slack #alerts
    │   └─ Email to ops-team
    │
    └─ P3 (Low)
        └─ Email to ops-team (batched)
```

### Common Alerts

#### DatabaseDown
**Severity**: P0
**Trigger**: PostgreSQL health check fails
**Runbook**: [Database Failure Recovery](disaster-recovery.md#scenario-1-database-container-failure)

#### HighErrorRate
**Severity**: P1
**Trigger**: Error rate > 1% for 5 minutes
**Runbook**: [Error Rate Investigation](runbooks/high-error-rate.md)

#### DiskSpaceLow
**Severity**: P2
**Trigger**: Disk usage > 85%
**Runbook**: [Disk Cleanup](runbooks/disk-cleanup.md)

#### BackupFailed
**Severity**: P1
**Trigger**: Backup script exits with error
**Runbook**: [Backup Troubleshooting](../backup/README.md#troubleshooting)

---

## Incident Management

### Incident Severity Levels

#### P0 - Critical

**Definition**: Complete service outage or data loss risk

**Examples**:
- Production site is down
- Database corruption or loss
- Security breach
- Payment processing completely broken

**Response**:
- **Response Time**: Immediate (< 5 minutes)
- **Resolution Target**: < 1 hour
- **Team**: All hands on deck
- **Communication**: Every 15 minutes
- **Post-Mortem**: Required within 24 hours

#### P1 - High

**Definition**: Major feature broken or severe degradation

**Examples**:
- Search not working
- Checkout flow broken for some users
- Single microservice down
- Database performance degraded

**Response**:
- **Response Time**: 15 minutes
- **Resolution Target**: < 4 hours
- **Team**: On-call + relevant specialists
- **Communication**: Every 30 minutes
- **Post-Mortem**: Required within 48 hours

#### P2 - Medium

**Definition**: Minor feature broken or performance issue

**Examples**:
- Recommendation engine degraded
- Slow page loads
- Non-critical API errors
- Monitoring alerts

**Response**:
- **Response Time**: 1 hour
- **Resolution Target**: < 24 hours
- **Team**: On-call engineer
- **Communication**: As needed
- **Post-Mortem**: Optional

#### P3 - Low

**Definition**: Cosmetic issues or minor bugs

**Examples**:
- UI glitches
- Non-critical logs
- Documentation issues

**Response**:
- **Response Time**: Next business day
- **Resolution Target**: < 1 week
- **Team**: Assigned engineer
- **Post-Mortem**: Not required

### Incident Response Process

```
┌──────────────────┐
│  Alert Received  │
└────────┬─────────┘
         │
    ┌────▼─────┐
    │ Acknow-  │
    │ ledge    │
    └────┬─────┘
         │
    ┌────▼──────┐
    │ Triage &  │
    │ Assess    │
    └────┬──────┘
         │
    ┌────▼──────────┐
    │ Create        │
    │ Incident      │
    │ Ticket        │
    └────┬──────────┘
         │
    ┌────▼──────────┐
    │ Investigate & │
    │ Diagnose      │
    └────┬──────────┘
         │
    ┌────▼──────────┐
    │ Implement     │
    │ Fix           │
    └────┬──────────┘
         │
    ┌────▼──────────┐
    │ Verify        │
    │ Resolution    │
    └────┬──────────┘
         │
    ┌────▼──────────┐
    │ Communicate   │
    │ & Close       │
    └────┬──────────┘
         │
    ┌────▼──────────┐
    │ Post-Mortem   │
    │ (if required) │
    └───────────────┘
```

### Incident Communication

**Status Page**: `https://status.example.com`

**Update Frequency**:
- P0: Every 15 minutes
- P1: Every 30 minutes
- P2: Hourly or as needed

**Communication Channels**:
- Internal: Slack #incidents
- External: Status page + Twitter
- Customers: Email (if major impact)

**Status Update Template**:
```markdown
**Incident**: [Title]
**Severity**: P0/P1/P2
**Started**: [Timestamp]
**Status**: Investigating / Identified / Monitoring / Resolved

**Summary**:
[Brief description of issue and user impact]

**Current Actions**:
[What we're doing to resolve]

**Next Update**: [Time]
```

### Post-Mortem Template

See full template in [Disaster Recovery Plan](disaster-recovery.md#post-incident)

**Required Sections**:
1. Timeline of events
2. Root cause analysis
3. Impact assessment
4. What went well
5. What went wrong
6. Action items with owners and due dates

---

## Deployment Procedures

### Deployment Windows

| Environment | Days | Time (UTC) | Approval Required |
|-------------|------|------------|-------------------|
| Development | Anytime | - | No |
| Staging | Mon-Fri | 08:00-18:00 | Team lead |
| Production | Tue-Thu | 10:00-16:00 | Platform lead + QA |

**Deployment Freeze**:
- Fridays after 12:00 UTC
- Weekends and holidays
- Major shopping events (Black Friday, etc.)
- Known high-traffic periods

### Deployment Process

**Standard Deployment** (Non-breaking changes)

See: [Production Deployment Guide](../deployment/production-guide.md)

1. **Pre-Deployment**
   - [ ] Code reviewed and approved
   - [ ] Tests passing in CI
   - [ ] Staging deployment successful
   - [ ] QA sign-off
   - [ ] Change request approved
   - [ ] Deployment window scheduled

2. **Deployment**
   ```bash
   # Pull latest code
   git pull origin main

   # Build new images
   docker-compose -f deploy/docker/compose/base.yml \
                  -f deploy/docker/compose/production.yml \
                  build

   # Deploy with zero downtime
   docker-compose -f deploy/docker/compose/base.yml \
                  -f deploy/docker/compose/production.yml \
                  up -d --no-deps --build backend
   ```

3. **Post-Deployment**
   - [ ] Health checks passing
   - [ ] Smoke tests successful
   - [ ] Monitoring shows normal metrics
   - [ ] No error spike in logs
   - [ ] Deployment documented

**Blue-Green Deployment** (Breaking changes)

See: [Blue-Green Deployment Guide](../deployment/blue-green-deployment.md)

**Rollback Procedure**

```bash
# Immediate rollback
git checkout <previous-version-tag>

docker-compose -f deploy/docker/compose/base.yml \
               -f deploy/docker/compose/production.yml \
               up -d --build

# Verify rollback successful
./scripts/deployment/smoke-tests.sh
```

**Rollback Decision Criteria**:
- Error rate > 5%
- Response time > 2x normal
- Any P0 incident within 30 minutes
- Health checks failing
- Database migration failure

---

## Disaster Recovery

For complete disaster recovery procedures, see: **[Disaster Recovery Plan](disaster-recovery.md)**

### Quick Reference

**RTO/RPO Summary**:

| Component | RTO | RPO |
|-----------|-----|-----|
| PostgreSQL | 30 min | 15 min |
| Backend Service | 15 min | 0 (stateless) |
| Redis Cache | 15 min | 1 hour |

**Emergency Contacts**:
- Incident Commander: [Name] [Phone]
- Database Admin: [Name] [Phone]
- AWS Support: enterprise-support@aws.com
- PagerDuty: +1-XXX-XXX-XXXX

**Critical Commands**:

```bash
# Check all services
docker ps --format "table {{.Names}}\t{{.Status}}"

# Stop all services immediately
docker-compose -f deploy/docker/compose/base.yml \
               -f deploy/docker/compose/production.yml \
               stop

# Restore from latest backup
./scripts/backup/restore-database.sh --latest --database main

# Failover to DR server
ssh dr-server.example.com
cd /opt/ecommerce-platform
./scripts/dr/failover-to-dr.sh
```

### DR Drill Schedule

- **Weekly**: Backup verification (automated)
- **Monthly**: Full DR drill
- **Quarterly**: Failover simulation
- **Annually**: External audit

---

## Maintenance Procedures

### Dependency Management

For complete dependency management procedures, see: **[Dependency Management Guide](../maintenance/dependency-management.md)**

**Automated Updates** (Dependabot):
- Backend/Gateway: Daily security updates
- AI Services: Weekly updates
- Docker Images: Weekly updates

**Manual Review Required**:
- Minor version updates (x.Y.0)
- Security updates with CVSS >= 7.0

**Weekly Dependency Review** (Mondays 10:00 UTC):
```bash
# List open Dependabot PRs
gh pr list --author "app/dependabot" --state open

# Review and merge security updates
gh pr view 123
gh pr checks 123
gh pr merge 123 --squash
```

**Quarterly Dependency Audit**:
```bash
./scripts/maintenance/audit-dependencies.sh
```

### Database Maintenance

**Weekly Tasks**:
- Vacuum and analyze (automated via cron)
- Index usage review
- Slow query analysis

**Monthly Tasks**:
- Table bloat check
- Connection pool tuning review
- Backup verification

**Quarterly Tasks**:
- Full database audit
- Index optimization
- Archive old data

**Database Vacuum** (Automated):
```bash
# Runs every Sunday 02:00 UTC
docker exec ecommerce_postgres \
    vacuumdb -U postgres -d ecommerce_db --analyze --verbose
```

**Slow Query Analysis**:
```bash
# Enable slow query log (> 100ms)
docker exec ecommerce_postgres psql -U postgres -c \
    "ALTER SYSTEM SET log_min_duration_statement = 100;"

# Review slow queries
docker exec ecommerce_postgres \
    tail -f /var/lib/postgresql/data/log/postgresql.log | grep "duration:"
```

### Log Management

**Log Rotation**:
- Docker logs: 10MB max, 3 files
- Application logs: Daily rotation, 30 days retention
- Nginx logs: Daily rotation, 90 days retention

**Log Analysis**:
```bash
# Search for errors in last 24h
docker-compose logs --since=24h | grep -i error

# Count errors by service
docker-compose logs --since=24h | grep -i error | \
    awk '{print $1}' | sort | uniq -c

# Tail live logs
docker-compose logs -f --tail=100 backend
```

### Certificate Management

**SSL Certificate Renewal** (Let's Encrypt):
- Automated via certbot
- Renewal: 30 days before expiry
- Monitoring: Certificate expiry alerts

```bash
# Check certificate expiry
echo | openssl s_client -servername example.com \
    -connect example.com:443 2>/dev/null | \
    openssl x509 -noout -dates

# Manual renewal
certbot renew --dry-run
certbot renew
```

---

## Security Operations

### Security Monitoring

**Daily Tasks**:
- Review security alerts
- Check failed login attempts
- Monitor unusual traffic patterns

**Weekly Tasks**:
- Security patch review
- Access audit
- Vulnerability scan results

**Monthly Tasks**:
- Security compliance review
- Permission audit
- Incident review

### Access Management

**SSH Access**:
- Key-based authentication only
- No password authentication
- Audit logs enabled

**Application Access**:
- MFA required for production
- Principle of least privilege
- Regular access reviews

**Database Access**:
- No direct production DB access
- Read-only replicas for queries
- All changes via migration scripts

### Vulnerability Management

**Security Update SLA**:
- Critical (CVSS >= 9.0): < 4 hours
- High (CVSS >= 7.0): < 24 hours
- Medium (CVSS >= 4.0): < 1 week
- Low (CVSS < 4.0): Next release

**Vulnerability Scanning**:
```bash
# Python dependencies
pip-audit

# Docker images
docker scan ecommerce_backend:latest

# Infrastructure
./scripts/security/scan-all-containers.sh
```

---

## Performance Management

### Performance Monitoring

**Key Performance Indicators**:

| Metric | Target | Warning | Critical |
|--------|--------|---------|----------|
| Homepage Load Time | < 2s | > 3s | > 5s |
| Search Response Time | < 300ms | > 500ms | > 1s |
| API Response Time (p95) | < 200ms | > 500ms | > 1s |
| Database Query Time (p95) | < 50ms | > 100ms | > 200ms |
| Cache Hit Rate | > 80% | < 70% | < 50% |

### Performance Optimization

**Database Optimization**:
```bash
# Connection pool tuning
./scripts/tune_connection_pools.sh

# Query analysis
docker exec ecommerce_postgres psql -U postgres -d ecommerce_db -c \
    "SELECT query, calls, total_time/calls as avg_time
     FROM pg_stat_statements
     ORDER BY total_time DESC
     LIMIT 20;"
```

**Cache Optimization**:
```bash
# Check Redis memory usage
docker exec ecommerce_redis redis-cli INFO memory

# Monitor cache hit rate
docker exec ecommerce_redis redis-cli INFO stats | grep hits
```

**Load Testing**:
```bash
# Run load tests (staging only)
./scripts/run_load_tests.sh --duration 300 --users 100
```

### Capacity Planning

**Monthly Review**:
- Resource utilization trends
- Growth projections
- Bottleneck identification

**Metrics to Track**:
- CPU utilization trending
- Memory usage growth
- Database size growth
- Request rate growth
- Storage consumption

**Scaling Triggers**:
- CPU > 70% sustained
- Memory > 80% sustained
- Database connections > 80% pool
- Response time degradation

---

## Runbooks and Procedures

### Available Runbooks

| Runbook | Location | Purpose |
|---------|----------|---------|
| Database Failure Recovery | [disaster-recovery.md#scenario-1](disaster-recovery.md#scenario-1-database-container-failure) | Database container failures |
| Server Failure Recovery | [disaster-recovery.md#scenario-2](disaster-recovery.md#scenario-2-complete-server-host-failure) | Complete server outage |
| Ransomware Recovery | [disaster-recovery.md#scenario-3](disaster-recovery.md#scenario-3-ransomware-data-corruption) | Security incident response |
| Docker Engine Failure | [disaster-recovery.md#scenario-4](disaster-recovery.md#scenario-4-docker-engine-failure) | Docker daemon issues |
| Volume Corruption | [disaster-recovery.md#scenario-5](disaster-recovery.md#scenario-5-docker-volume-corruption) | Data volume failures |
| CI/CD Troubleshooting | [runbooks/ci-troubleshooting.md](runbooks/ci-troubleshooting.md) | Pipeline failures |
| Deployment Rollback | [../deployment/production-guide.md](../deployment/production-guide.md) | Failed deployments |

### Quick Troubleshooting

**Service Won't Start**:
```bash
# Check logs
docker logs ecommerce_backend --tail 100

# Check configuration
docker inspect ecommerce_backend

# Restart service
docker-compose restart backend
```

**High CPU Usage**:
```bash
# Identify process
docker stats --no-stream

# Check application logs
docker logs ecommerce_backend | grep -i "performance\|slow"

# Profile application
docker exec ecommerce_backend py-spy top --pid 1
```

**Database Connection Issues**:
```bash
# Check PgBouncer
docker exec ecommerce_pgbouncer psql -p 6432 -U postgres -c "SHOW POOLS;"

# Check connection count
docker exec ecommerce_postgres psql -U postgres -c \
    "SELECT count(*) FROM pg_stat_activity;"

# Kill idle connections
docker exec ecommerce_postgres psql -U postgres -c \
    "SELECT pg_terminate_backend(pid)
     FROM pg_stat_activity
     WHERE state = 'idle' AND state_change < now() - interval '10 minutes';"
```

---

## Tools and Access

### Required Tools

**Local Development**:
- Docker Desktop / Docker Engine
- Git
- Python 3.11+
- VS Code or preferred IDE
- Postman or similar API client

**Operations**:
- SSH client
- VPN client
- AWS CLI
- GitHub CLI (`gh`)
- `jq` for JSON processing
- `kubectl` (if using Kubernetes)

**Monitoring**:
- Web browser (for Grafana, Prometheus)
- PagerDuty mobile app
- Slack desktop/mobile app

### Access Requirements

**Production Access**:
1. VPN connection required
2. MFA enabled
3. SSH keys registered
4. PagerDuty account
5. Slack workspace access

**Requesting Access**:
1. Submit ticket to platform-team
2. Manager approval required
3. Complete security training
4. Sign NDA and acceptable use policy
5. Access reviewed quarterly

### Critical URLs

| Service | URL | Access Required |
|---------|-----|-----------------|
| Production API | https://api.example.com | Public |
| Grafana | https://grafana.example.com | VPN + Auth |
| Prometheus | https://prometheus.example.com | VPN + Auth |
| Status Page | https://status.example.com | Public |
| PagerDuty | https://example.pagerduty.com | Account |
| GitHub Repo | https://github.com/org/ecommerce-platform | Org member |
| Documentation | https://docs.example.com | VPN |

---

## Escalation and Contacts

### Escalation Matrix

```
┌─────────────────┐
│  On-Call Eng    │ (First Responder)
└────────┬────────┘
         │ If unable to resolve in 30 min
         ▼
┌─────────────────┐
│  Team Lead      │ (Technical Escalation)
└────────┬────────┘
         │ If P0 or needs resources
         ▼
┌─────────────────┐
│  Platform Lead  │ (Management Escalation)
└────────┬────────┘
         │ If business impact or external
         ▼
┌─────────────────┐
│  VP Engineering │ (Executive Escalation)
└─────────────────┘
```

### Contact Information

#### Operations Team

| Role | Name | Email | Phone | Slack |
|------|------|-------|-------|-------|
| Platform Lead | [Name] | [Email] | [Phone] | @platform-lead |
| SRE Lead | [Name] | [Email] | [Phone] | @sre-lead |
| DBA | [Name] | [Email] | [Phone] | @dba |
| Security Lead | [Name] | [Email] | [Phone] | @security-lead |
| DevOps Lead | [Name] | [Email] | [Phone] | @devops-lead |

#### External Contacts

| Service | Contact | Hours | SLA |
|---------|---------|-------|-----|
| AWS Support | enterprise-support@aws.com | 24/7 | < 1 hour |
| GitHub Support | support@github.com | 24/7 | < 4 hours |
| DNS Provider | [Contact] | 24/7 | < 2 hours |
| SSL Provider | [Contact] | Business hours | < 1 day |

### Communication Channels

**Slack Channels**:
- `#incidents` - Active incident coordination
- `#alerts` - Automated alerts (non-critical)
- `#deployments` - Deployment announcements
- `#platform-team` - General team communication
- `#on-call` - On-call coordination

**Email Lists**:
- `ops-team@example.com` - All operations engineers
- `platform-oncall@example.com` - Current on-call rotation
- `incidents@example.com` - Incident notifications

---

## Appendices

### Appendix A: Glossary

| Term | Definition |
|------|------------|
| RTO | Recovery Time Objective - Maximum acceptable downtime |
| RPO | Recovery Point Objective - Maximum acceptable data loss |
| SLA | Service Level Agreement - Committed uptime percentage |
| SLO | Service Level Objective - Internal uptime target |
| P0/P1/P2/P3 | Priority levels for incidents (P0 = Critical) |
| DR | Disaster Recovery |
| MTTR | Mean Time To Recovery |
| MTTD | Mean Time To Detection |

### Appendix B: Useful Commands

**System Health**:
```bash
# Quick health check
./scripts/health_check.py

# Detailed service status
docker-compose ps

# Resource usage
docker stats --no-stream
```

**Database**:
```bash
# Database size
docker exec ecommerce_postgres psql -U postgres -c "\l+"

# Active connections
docker exec ecommerce_postgres psql -U postgres -c \
    "SELECT count(*) FROM pg_stat_activity;"

# Backup status
ls -lh /backups/postgres/ | head -10
```

**Logs**:
```bash
# All services
docker-compose logs -f --tail=100

# Specific service
docker logs -f ecommerce_backend

# Error search
docker-compose logs --since=1h | grep -i error
```

### Appendix C: Compliance and Audit

**SOC 2 Requirements**:
- Change management process (documented)
- Incident response procedures (documented)
- Backup and recovery testing (automated)
- Access controls and reviews (quarterly)

**PCI-DSS Requirements**:
- Security patch management (automated)
- Access logging (enabled)
- Encryption in transit and at rest (enforced)
- Quarterly vulnerability scans (automated)

**GDPR Requirements**:
- Data breach notification (< 72 hours)
- Data backup and recovery (tested)
- Access controls (enforced)
- Data retention policies (documented)

### Appendix D: Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-24 | Platform Team | Initial release for Phase 6 |

---

## Document Maintenance

**Review Schedule**: Quarterly

**Next Review**: 2025-03-24

**Ownership**: Platform Operations Team

**Approval**: Platform Lead

**Distribution**: All operations and engineering staff

---

**End of Operations Manual**

For questions or updates, contact: platform-team@example.com
