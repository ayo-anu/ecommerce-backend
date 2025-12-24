# Disaster Recovery Plan

**Version**: 2.0
**Last Updated**: 2025-12-24
**Classification**: CONFIDENTIAL
**Owner**: Platform Team
**Deployment Architecture**: Docker Compose (No Kubernetes)

---

## Executive Summary

This document outlines the disaster recovery (DR) procedures for the e-commerce platform using Docker-based deployment. It includes Recovery Time Objective (RTO), Recovery Point Objective (RPO), and detailed step-by-step recovery procedures for all disaster scenarios.

**Infrastructure**: Docker Compose with containerized services
**Backup Strategy**: Automated daily backups with S3 offsite storage
**Primary Recovery Method**: Blue-green deployment with automated failover

## Recovery Objectives

| Component | RTO | RPO | Backup Frequency | Priority |
|-----------|-----|-----|------------------|----------|
| PostgreSQL (Main) | 30 minutes | 15 minutes | Every 6 hours | P0 - Critical |
| PostgreSQL (AI) | 30 minutes | 15 minutes | Every 6 hours | P0 - Critical |
| Backend Service | 15 minutes | 0 (stateless) | N/A | P0 - Critical |
| API Gateway | 15 minutes | 0 (stateless) | N/A | P0 - Critical |
| Redis Cache | 15 minutes | 1 hour | Daily | P1 - High |
| AI Services | 20 minutes | 0 (stateless) | N/A | P1 - High |
| Nginx/Reverse Proxy | 10 minutes | 0 (stateless) | N/A | P0 - Critical |
| Media Files (Volume) | 4 hours | 24 hours | Daily | P2 - Medium |
| Monitoring Stack | 30 minutes | 24 hours | Weekly | P2 - Medium |

## Disaster Scenarios

### Scenario 1: Database Container Failure

**Detection**:
- Alert: `DatabaseDown` from Prometheus
- Health checks failing: `docker ps` shows unhealthy postgres container
- Application logs show database connection errors

**Recovery Procedure**:

```bash
# 1. Verify failure
docker ps -a | grep postgres
docker logs ecommerce_postgres --tail 100

# 2. Check if container is running but unhealthy
POSTGRES_STATUS=$(docker inspect --format='{{.State.Health.Status}}' ecommerce_postgres 2>/dev/null || echo "not-found")

if [ "$POSTGRES_STATUS" != "healthy" ]; then
    echo "Database is $POSTGRES_STATUS"
fi

# 3. Attempt container restart
echo "Attempting container restart..."
docker-compose -f deploy/docker/compose/base.yml \
               -f deploy/docker/compose/production.yml \
               restart postgres

# 4. Wait for health check (30 seconds timeout)
timeout 30 bash -c 'until docker exec ecommerce_postgres pg_isready -U postgres; do sleep 2; done'

# 5. If restart fails, restore from backup
if [ $? -ne 0 ]; then
    echo "Restart failed. Restoring from backup..."

    # Stop the failed container
    docker-compose -f deploy/docker/compose/base.yml \
                   -f deploy/docker/compose/production.yml \
                   stop postgres

    # Restore from latest backup
    ./scripts/backup/restore-database.sh --latest --database main

    # Start container
    docker-compose -f deploy/docker/compose/base.yml \
                   -f deploy/docker/compose/production.yml \
                   up -d postgres
fi

# 6. Verify connectivity from backend
docker exec ecommerce_backend python manage.py dbshell <<< "SELECT 1;" || {
    echo "ERROR: Backend cannot connect to database"
    exit 1
}

# 7. Run data integrity checks
./scripts/deployment/verify-data-integrity.sh

# 8. Monitor for 5 minutes
echo "Monitoring database health for 5 minutes..."
for i in {1..30}; do
    docker exec ecommerce_postgres pg_isready -U postgres
    sleep 10
done

echo "✅ Database recovery complete"
```

**Time to Recovery**: ~15-30 minutes (depending on backup size)
**Data Loss**: Maximum 15 minutes (RPO)

### Scenario 2: Complete Server/Host Failure

**Detection**:
- All Docker containers down
- Cannot SSH to server
- No response from any service endpoints
- Monitoring shows all services offline

**Recovery Procedure**:

```bash
# ====================================================================
# EXECUTE FROM DR/BACKUP SERVER OR LOCAL WORKSTATION
# ====================================================================

# 1. Verify primary server is down
ping production-server.example.com
ssh -o ConnectTimeout=5 production-server.example.com "echo test" || {
    echo "❌ Primary server is unreachable"
}

# 2. Prepare secondary/DR server
ssh dr-server.example.com

# 3. On DR server: Pull latest application code
cd /opt/ecommerce-platform
git fetch origin
git checkout main
git pull origin main

# 4. Restore database from latest S3 backup
./scripts/backup/restore-database.sh \
    --from-s3 \
    --s3-bucket ecommerce-backups-production \
    --database main \
    --latest

./scripts/backup/restore-database.sh \
    --from-s3 \
    --s3-bucket ecommerce-backups-production \
    --database ai \
    --latest

# 5. Restore Redis backup
./scripts/backup/restore-redis.sh --from-s3 --latest

# 6. Load environment configuration
cp config/environments/production.env .env
# Verify all secrets are properly configured
source .env

# 7. Start all services
docker-compose -f deploy/docker/compose/base.yml \
               -f deploy/docker/compose/production.yml \
               up -d

# 8. Wait for all services to be healthy
echo "Waiting for services to become healthy..."
timeout 300 bash -c 'until docker ps | grep -q "(healthy)"; do sleep 5; done'

# 9. Verify all services are running
docker ps --format "table {{.Names}}\t{{.Status}}"

# 10. Update DNS to point to DR server
# Option A: Update DNS A record
aws route53 change-resource-record-sets \
    --hosted-zone-id Z1234567890ABC \
    --change-batch '{
      "Changes": [{
        "Action": "UPSERT",
        "ResourceRecordSet": {
          "Name": "api.example.com",
          "Type": "A",
          "TTL": 60,
          "ResourceRecords": [{"Value": "DR_SERVER_IP"}]
        }
      }]
    }'

# Option B: Update load balancer target
# (If using load balancer, update target to DR server)

# 11. Run smoke tests
./scripts/deployment/smoke-tests.sh https://api.example.com

# 12. Verify data integrity
./scripts/deployment/verify-data-integrity.sh

# 13. Monitor all services closely
./scripts/monitoring/health-check-loop.sh

echo "✅ Failover to DR server complete"
echo "⚠️  Remember to schedule post-incident review"
```

**Time to Recovery**: ~45-90 minutes (depending on backup size and DNS propagation)
**Data Loss**: Maximum 6 hours (backup frequency)

### Scenario 3: Ransomware/Data Corruption

**Detection**:
- Unusual database modifications detected by monitoring
- Corrupted data reported by users or automated checks
- Security alerts from intrusion detection system
- Suspicious file encryption or ransom notes
- Unusual container behavior (high CPU, network activity)

**Recovery Procedure**:

```bash
# ====================================================================
# CRITICAL: IMMEDIATE ISOLATION REQUIRED
# ====================================================================

# 1. IMMEDIATELY isolate all affected services
echo "🚨 SECURITY INCIDENT: Isolating affected systems..."

# Stop all backend services to prevent further damage
docker-compose -f deploy/docker/compose/base.yml \
               -f deploy/docker/compose/production.yml \
               stop backend api_gateway

# Block all external traffic via firewall
sudo iptables -A INPUT -p tcp --dport 80 -j DROP
sudo iptables -A INPUT -p tcp --dport 443 -j DROP

# Preserve current state for forensics
INCIDENT_ID="incident-$(date +%Y%m%d-%H%M%S)"
mkdir -p /var/forensics/$INCIDENT_ID

# 2. Create forensic snapshots
echo "📸 Creating forensic snapshots..."
docker commit ecommerce_postgres forensic-postgres-$INCIDENT_ID
docker commit ecommerce_backend forensic-backend-$INCIDENT_ID
docker save forensic-postgres-$INCIDENT_ID -o /var/forensics/$INCIDENT_ID/postgres.tar
docker save forensic-backend-$INCIDENT_ID -o /var/forensics/$INCIDENT_ID/backend.tar

# Export database for analysis
docker exec ecommerce_postgres pg_dumpall -U postgres | gzip > \
    /var/forensics/$INCIDENT_ID/compromised-db-dump.sql.gz

# Collect logs
docker logs ecommerce_postgres &> /var/forensics/$INCIDENT_ID/postgres.log
docker logs ecommerce_backend &> /var/forensics/$INCIDENT_ID/backend.log

# 3. Identify last known good backup
echo "🔍 Finding last known good backup..."
ls -lth /backups/postgres/ | head -20

# List S3 backups
aws s3 ls s3://ecommerce-backups-production/postgres/ --recursive | \
    grep "sql.gz" | sort -r | head -10

# 4. Determine safe restore point (before compromise)
SAFE_RESTORE_TIME="2025-12-24T02:00:00"  # ADJUST THIS
echo "Restore point set to: $SAFE_RESTORE_TIME"

# 5. Find backup closest to safe time
RESTORE_BACKUP=$(find /backups/postgres -name "main_db_*.sql.gz" \
    -newermt "$SAFE_RESTORE_TIME" -print -quit)

if [ -z "$RESTORE_BACKUP" ]; then
    echo "⚠️  No local backup found. Downloading from S3..."
    aws s3 cp s3://ecommerce-backups-production/postgres/20251224/main_db_*.sql.gz \
        /tmp/restore-backup.sql.gz
    RESTORE_BACKUP="/tmp/restore-backup.sql.gz"
fi

# 6. Verify backup integrity
echo "✓ Verifying backup integrity..."
gunzip -t "$RESTORE_BACKUP" || {
    echo "❌ Backup file is corrupted!"
    exit 1
}

# 7. Stop and remove compromised database
docker-compose -f deploy/docker/compose/base.yml \
               -f deploy/docker/compose/production.yml \
               stop postgres

# Rename compromised data volume for forensics
docker volume create forensic-postgres-data-$INCIDENT_ID
docker run --rm -v ecommerce_postgres_data:/source \
    -v forensic-postgres-data-$INCIDENT_ID:/dest \
    alpine sh -c "cp -a /source/. /dest/"

# Remove compromised volume
docker volume rm ecommerce_postgres_data

# 8. Create fresh database container and restore clean data
docker volume create ecommerce_postgres_data

docker-compose -f deploy/docker/compose/base.yml \
               -f deploy/docker/compose/production.yml \
               up -d postgres

# Wait for database to be ready
timeout 60 bash -c 'until docker exec ecommerce_postgres pg_isready; do sleep 2; done'

# Restore clean data
gunzip -c "$RESTORE_BACKUP" | \
    docker exec -i ecommerce_postgres psql -U postgres

# 9. Verify restored data
echo "✓ Verifying restored data..."
docker exec ecommerce_postgres psql -U postgres -d ecommerce_db <<EOF
SELECT COUNT(*) FROM products;
SELECT COUNT(*) FROM orders;
SELECT MAX(created_at) FROM orders;
EOF

# 10. Rebuild application containers from clean images
docker-compose -f deploy/docker/compose/base.yml \
               -f deploy/docker/compose/production.yml \
               pull

docker-compose -f deploy/docker/compose/base.yml \
               -f deploy/docker/compose/production.yml \
               up -d --force-recreate backend api_gateway

# 11. Run comprehensive security scan
./scripts/security/scan-all-containers.sh

# 12. Restore firewall rules
sudo iptables -D INPUT -p tcp --dport 80 -j DROP
sudo iptables -D INPUT -p tcp --dport 443 -j DROP

# 13. Verify services are healthy
./scripts/deployment/smoke-tests.sh

# 14. Notify security team and stakeholders
echo "📧 Notifying security team..."
./scripts/security/notify-incident.sh \
    --severity critical \
    --type ransomware \
    --incident-id $INCIDENT_ID

echo "✅ System restored from clean backup"
echo "⚠️  NEXT STEPS:"
echo "   1. Review forensic data in /var/forensics/$INCIDENT_ID"
echo "   2. Conduct root cause analysis"
echo "   3. Schedule post-incident review within 24 hours"
echo "   4. Update security controls based on findings"
```

**Time to Recovery**: ~60-90 minutes
**Data Loss**: Time between last backup and incident detection (up to 6 hours)
**Critical**: Preserve all forensic evidence for investigation

### Scenario 4: Docker Engine Failure

**Detection**:
- Docker daemon unresponsive
- Cannot run `docker ps`
- Container management commands timeout
- Systemd shows docker.service failed

**Recovery Procedure**:

```bash
# 1. Check Docker service status
systemctl status docker
journalctl -u docker -n 100 --no-pager

# 2. Attempt to restart Docker daemon
sudo systemctl restart docker

# 3. If restart fails, check for issues
# Check disk space
df -h
# Check if containerd is running
systemctl status containerd

# 4. If disk full, clean up Docker resources
docker system prune -af --volumes
# Or manually remove old images
docker image prune -a

# 5. Restart Docker with increased logging
sudo systemctl stop docker
sudo dockerd --debug --log-level=debug &
# Review logs for errors

# 6. If Docker engine is corrupted, reinstall
sudo apt-get update
sudo apt-get install --reinstall docker-ce docker-ce-cli containerd.io

# 7. Restart Docker service
sudo systemctl daemon-reload
sudo systemctl start docker
sudo systemctl enable docker

# 8. Verify Docker is working
docker version
docker ps -a

# 9. Restore all services
cd /opt/ecommerce-platform
docker-compose -f deploy/docker/compose/base.yml \
               -f deploy/docker/compose/production.yml \
               up -d

# 10. Verify all containers are running
docker ps --format "table {{.Names}}\t{{.Status}}"

# 11. Check logs for any issues
docker-compose -f deploy/docker/compose/base.yml \
               -f deploy/docker/compose/production.yml \
               logs --tail=100

# 12. Run health checks
./scripts/deployment/health-check-all.sh

echo "✅ Docker engine restored"
```

**Time to Recovery**: ~15-30 minutes
**Data Loss**: None (data persists in volumes)

### Scenario 5: Docker Volume Corruption

**Detection**:
- Database reports data corruption
- Volume mount failures in container logs
- I/O errors in system logs
- File system errors

**Recovery Procedure**:

```bash
# 1. Identify corrupted volume
docker volume ls
docker volume inspect ecommerce_postgres_data

# 2. Stop affected services immediately
docker-compose -f deploy/docker/compose/base.yml \
               -f deploy/docker/compose/production.yml \
               stop postgres

# 3. Attempt file system check (if possible)
# Mount volume to temporary container
docker run --rm -v ecommerce_postgres_data:/data \
    alpine sh -c "ls -la /data"

# 4. If corruption confirmed, backup current state
docker run --rm -v ecommerce_postgres_data:/source \
    -v /backups/emergency:/dest \
    alpine tar czf /dest/corrupted-volume-$(date +%Y%m%d-%H%M%S).tar.gz -C /source .

# 5. Create new volume
docker volume create ecommerce_postgres_data_new

# 6. Restore from latest known good backup
./scripts/backup/restore-database.sh \
    --target-volume ecommerce_postgres_data_new \
    --latest

# 7. Update docker-compose to use new volume
# (or rename volumes)
docker volume rm ecommerce_postgres_data
docker volume create ecommerce_postgres_data

# Restore data to recreated volume
./scripts/backup/restore-database.sh --latest

# 8. Start services
docker-compose -f deploy/docker/compose/base.yml \
               -f deploy/docker/compose/production.yml \
               up -d postgres

# 9. Verify data integrity
docker exec ecommerce_postgres psql -U postgres -c "
    SELECT pg_database.datname,
           pg_size_pretty(pg_database_size(pg_database.datname)) AS size
    FROM pg_database;
"

# 10. Run data validation
./scripts/deployment/verify-data-integrity.sh

# 11. Monitor for additional issues
journalctl -f | grep -i "i/o error"

echo "✅ Volume restored from backup"
```

**Time to Recovery**: ~30-60 minutes
**Data Loss**: Up to 6 hours (last backup)

## Backup Strategy

### Automated Backups

The platform implements a comprehensive 3-2-1 backup strategy:
- **3** copies of data (production + 2 backups)
- **2** different storage types (local disk + S3)
- **1** offsite copy (S3 in different region)

```yaml
# PostgreSQL Databases (Main + AI)
- Frequency: Every 6 hours
- Retention: Local 7 days, S3 30 days
- Method: pg_dumpall with gzip compression
- Encryption: GPG encrypted before S3 upload
- Location: /backups/postgres + s3://ecommerce-backups-production/postgres/

# Redis Cache
- Frequency: Daily (4:00 AM UTC)
- Retention: Local 7 days, S3 14 days
- Method: RDB snapshot
- Location: /backups/redis + s3://ecommerce-backups-production/redis/

# Media Files (User uploads)
- Frequency: Daily (2:00 AM UTC)
- Retention: 90 days with S3 lifecycle policy
- Method: rsync to S3 with versioning
- Location: Docker volume → s3://ecommerce-media-backups/

# Docker Configuration
- Frequency: On each deployment
- Retention: Last 10 configurations
- Method: Git + docker-compose files
- Location: Git repository + S3

# Monitoring Data (Prometheus/Grafana)
- Frequency: Weekly
- Retention: 30 days
- Method: Volume snapshots
- Location: /backups/monitoring + S3
```

### Backup Scripts

The platform includes automated backup scripts in `scripts/backup/`:

#### Primary Backup Script

**Location**: `scripts/backup/backup-databases.sh`

**Features**:
- Backs up PostgreSQL (main + AI databases)
- Backs up Redis RDB file
- GPG encryption support
- S3 upload with lifecycle management
- Automatic cleanup of old backups
- Backup verification
- Email notifications on failure

**Usage**:
```bash
# Local backup only
./scripts/backup/backup-databases.sh

# With encryption and S3 upload
./scripts/backup/backup-databases.sh \
    --encrypt \
    --s3-upload \
    --s3-bucket ecommerce-backups-production

# Custom retention
./scripts/backup/backup-databases.sh \
    --retention-days 14 \
    --output-dir /custom/backup/path
```

#### Automated Backup Schedule (Cron)

```bash
# File: /etc/cron.d/ecommerce-backups

# PostgreSQL backup every 6 hours
0 */6 * * * root /opt/ecommerce-platform/scripts/backup/backup-databases.sh --s3-upload --s3-bucket ecommerce-backups-production >> /var/log/ecommerce/backup.log 2>&1

# Redis backup daily at 4 AM
0 4 * * * root /opt/ecommerce-platform/scripts/backup/backup-redis.sh --s3-upload >> /var/log/ecommerce/backup.log 2>&1

# Media files backup daily at 2 AM
0 2 * * * root /opt/ecommerce-platform/scripts/backup/backup-media.sh --s3-upload >> /var/log/ecommerce/backup.log 2>&1

# Backup verification weekly on Sundays at 3 AM
0 3 * * 0 root /opt/ecommerce-platform/scripts/backup/verify-backup.sh --all >> /var/log/ecommerce/backup.log 2>&1
```

#### Setup Automated Backups

```bash
# Install cron jobs
sudo ./scripts/backup/setup-backup-cron.sh

# Verify cron is configured
sudo crontab -l
```

## Recovery Testing

### Backup Verification

All backups must be tested regularly to ensure they can be restored successfully.

#### Automated Verification Script

**Location**: `scripts/backup/verify-backup.sh`

```bash
#!/bin/bash
# Automated backup verification
# Restores latest backup to test environment and validates data

set -e

BACKUP_DIR="/backups/postgres"
TEST_DB_CONTAINER="ecommerce_postgres_test"

echo "🔍 Starting backup verification..."

# 1. Find latest backup
LATEST_BACKUP=$(ls -t $BACKUP_DIR/main_db_*.sql.gz | head -1)
echo "Testing backup: $LATEST_BACKUP"

# 2. Create test database container
docker run -d \
    --name $TEST_DB_CONTAINER \
    -e POSTGRES_PASSWORD=test \
    postgres:15-alpine

sleep 10

# 3. Restore backup to test container
gunzip -c "$LATEST_BACKUP" | \
    docker exec -i $TEST_DB_CONTAINER psql -U postgres

# 4. Verify data integrity
echo "Running data integrity checks..."
docker exec $TEST_DB_CONTAINER psql -U postgres -d ecommerce_db <<EOF
-- Check table counts
SELECT 'users' as table_name, COUNT(*) FROM users
UNION ALL
SELECT 'products', COUNT(*) FROM products
UNION ALL
SELECT 'orders', COUNT(*) FROM orders;

-- Verify foreign key constraints
SELECT conname, conrelid::regclass, confrelid::regclass
FROM pg_constraint
WHERE contype = 'f';
EOF

# 5. Cleanup test container
docker stop $TEST_DB_CONTAINER
docker rm $TEST_DB_CONTAINER

echo "✅ Backup verification complete - backup is valid"
```

### Monthly DR Drill

**Purpose**: Validate complete disaster recovery procedures

```bash
#!/bin/bash
# File: scripts/dr/dr-drill.sh
#
# Monthly disaster recovery drill
# Tests full recovery to DR environment

set -e

START_TIME=$(date +%s)
DR_HOST="dr-server.example.com"

echo "=========================================="
echo "  Disaster Recovery Drill"
echo "  Date: $(date)"
echo "=========================================="

# 1. Prepare DR environment
echo "📋 Step 1: Preparing DR environment..."
ssh $DR_HOST "cd /opt/ecommerce-platform && git pull"

# 2. Restore databases from S3
echo "💾 Step 2: Restoring databases..."
ssh $DR_HOST "/opt/ecommerce-platform/scripts/backup/restore-database.sh \
    --from-s3 \
    --s3-bucket ecommerce-backups-production \
    --latest \
    --database main"

ssh $DR_HOST "/opt/ecommerce-platform/scripts/backup/restore-database.sh \
    --from-s3 \
    --s3-bucket ecommerce-backups-production \
    --latest \
    --database ai"

# 3. Start all services
echo "🚀 Step 3: Starting services..."
ssh $DR_HOST "cd /opt/ecommerce-platform && \
    docker-compose -f deploy/docker/compose/base.yml \
                   -f deploy/docker/compose/production.yml \
                   up -d"

# 4. Wait for health checks
echo "⏳ Step 4: Waiting for health checks..."
sleep 60

# 5. Run smoke tests
echo "🧪 Step 5: Running smoke tests..."
ssh $DR_HOST "/opt/ecommerce-platform/scripts/deployment/smoke-tests.sh"

# 6. Verify data integrity
echo "✓ Step 6: Verifying data integrity..."
ssh $DR_HOST "/opt/ecommerce-platform/scripts/deployment/verify-data-integrity.sh"

# 7. Measure recovery time
END_TIME=$(date +%s)
RECOVERY_TIME=$(( ($END_TIME - $START_TIME) / 60 ))

echo "=========================================="
echo "✅ DR Drill Complete"
echo "Recovery Time: $RECOVERY_TIME minutes"
echo "RTO Target: 60 minutes"
echo "Status: $( [ $RECOVERY_TIME -lt 60 ] && echo 'PASSED' || echo 'FAILED' )"
echo "=========================================="

# 8. Generate report
cat > /tmp/dr-drill-report-$(date +%Y%m%d).txt <<EOF
Disaster Recovery Drill Report
==============================
Date: $(date)
Recovery Time: $RECOVERY_TIME minutes
RTO Target: 60 minutes
Status: $( [ $RECOVERY_TIME -lt 60 ] && echo 'PASSED ✅' || echo 'FAILED ❌' )

Services Verified:
- PostgreSQL (main): ✅
- PostgreSQL (AI): ✅
- Backend API: ✅
- API Gateway: ✅
- Redis: ✅

Next Drill: $(date -d "+1 month" +%Y-%m-%d)
EOF

echo "📄 Report saved to /tmp/dr-drill-report-$(date +%Y%m%d).txt"

# 9. Cleanup DR environment
echo "🧹 Step 9: Cleaning up..."
ssh $DR_HOST "cd /opt/ecommerce-platform && \
    docker-compose -f deploy/docker/compose/base.yml \
                   -f deploy/docker/compose/production.yml \
                   down"

echo "✅ DR drill complete"
```

### Testing Schedule

| Frequency | Test Type | Duration | Responsible | Success Criteria |
|-----------|-----------|----------|-------------|------------------|
| **Daily** | Automated backup verification | 10 min | Automated (cron) | Backup restores successfully |
| **Weekly** | Manual restore to staging | 30 min | DevOps Engineer | Data integrity verified |
| **Monthly** | Full DR drill | 60 min | Platform Team | RTO < 60 minutes |
| **Quarterly** | Failover simulation | 90 min | SRE Team + Management | Complete failover successful |
| **Annually** | Third-party DR audit | 1 day | External Auditor | All procedures validated |

### DR Drill Checklist

```markdown
# Monthly DR Drill Checklist

## Pre-Drill (Day Before)
- [ ] Notify team of drill schedule
- [ ] Verify DR environment is available
- [ ] Confirm latest backups are in S3
- [ ] Review DR procedures
- [ ] Assign roles (IC, Ops Lead, Comms Lead)

## During Drill
- [ ] Start timer when drill begins
- [ ] Document each step and timestamp
- [ ] Note any issues or delays
- [ ] Test all communication channels
- [ ] Verify monitoring/alerting works

## Post-Drill
- [ ] Calculate total recovery time
- [ ] Compare against RTO target
- [ ] Document lessons learned
- [ ] Update runbooks if needed
- [ ] Schedule follow-up for issues
- [ ] Archive drill report

## Success Criteria
- [ ] RTO < 60 minutes achieved
- [ ] All services healthy
- [ ] Data integrity verified
- [ ] No data loss beyond RPO
- [ ] Team followed procedures correctly
```

## Communication Plan

### Incident Severity Levels

**SEV-1 (Critical)**:
- Complete service outage
- Data loss risk
- Security breach

**Response**: Immediate page-out, war room

**SEV-2 (High)**:
- Partial service degradation
- Single region failure

**Response**: On-call engineer + manager

### Contact Tree

```
Incident Commander (IC)
├── Operations Lead
│   ├── Database Admin
│   ├── DevOps Engineer
│   └── Network Engineer
├── Engineering Lead
│   ├── Backend Engineers
│   └── Frontend Engineers
├── Communications Lead
│   ├── Customer Support
│   └── PR/Marketing
└── Executive Sponsor
    └── CTO/VP Engineering
```

### Status Page Updates

```bash
# Update status page
curl -X POST "https://api.statuspage.io/v1/pages/PAGE_ID/incidents" \
  -H "Authorization: OAuth YOUR_API_KEY" \
  -d '{
    "incident": {
      "name": "Database Restoration in Progress",
      "status": "investigating",
      "impact_override": "major",
      "body": "We are experiencing database issues and are working to restore service."
    }
  }'
```

## Post-Incident

### 1. Post-Mortem Template

```markdown
# Post-Incident Review

**Date**: 2025-12-04
**Duration**: 2 hours 15 minutes
**Severity**: SEV-1

## Timeline
- 14:00 UTC: First alert received
- 14:05 UTC: Incident declared
- 14:30 UTC: Root cause identified
- 16:15 UTC: Service restored

## Root Cause
[Detailed explanation]

## Impact
- Users affected: 10,000
- Revenue loss: $50,000
- Reputation impact: High

## What Went Well
- Quick detection
- Effective communication
- Backup restored successfully

## What Went Wrong
- Backup was 2 hours old (should be 15 min)
- Alert took 5 minutes to page (should be immediate)

## Action Items
1. [ ] Increase backup frequency (Owner: DBA, Due: 2025-12-10)
2. [ ] Fix alert routing (Owner: DevOps, Due: 2025-12-07)
3. [ ] Update runbook (Owner: Platform, Due: 2025-12-08)
```

### 2. Lessons Learned

- Document what worked
- Update runbooks
- Improve monitoring
- Schedule follow-up drill

---

## Quick Reference

### Emergency Contacts

| Role | Name | Phone | Email |
|------|------|-------|-------|
| IC On-Call | [Name] | [Phone] | [Email] |
| Platform Lead | [Name] | [Phone] | [Email] |
| Database Admin | [Name] | [Phone] | [Email] |
| DevOps Engineer | [Name] | [Phone] | [Email] |
| Security Lead | [Name] | [Phone] | [Email] |
| AWS Support | - | - | enterprise-support@aws.com |
| PagerDuty | - | - | +1-XXX-XXX-XXXX |

### Critical URLs

- Production: https://api.example.com
- Status Page: https://status.example.com
- Grafana: https://grafana.example.com
- Prometheus: https://prometheus.example.com
- DR Server SSH: dr-server.example.com
- Backup S3 Bucket: s3://ecommerce-backups-production
- Runbooks: https://github.com/your-org/ecommerce-platform/tree/main/docs/operations/runbooks

### Key Commands

#### Service Health Checks
```bash
# Check all containers
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Check specific service health
docker inspect --format='{{.State.Health.Status}}' ecommerce_postgres
docker inspect --format='{{.State.Health.Status}}' ecommerce_backend

# View service logs
docker-compose -f deploy/docker/compose/base.yml \
               -f deploy/docker/compose/production.yml \
               logs --tail=100 [service_name]

# Check container resource usage
docker stats --no-stream
```

#### Database Operations
```bash
# Check database connectivity
docker exec ecommerce_postgres pg_isready -U postgres

# Connect to database
docker exec -it ecommerce_postgres psql -U postgres -d ecommerce_db

# Check database size
docker exec ecommerce_postgres psql -U postgres -c "\l+"

# Check active connections
docker exec ecommerce_postgres psql -U postgres -c \
    "SELECT count(*) FROM pg_stat_activity;"
```

#### Backup Operations
```bash
# Create manual backup
./scripts/backup/backup-databases.sh --s3-upload --s3-bucket ecommerce-backups-production

# List available backups
ls -lh /backups/postgres/
aws s3 ls s3://ecommerce-backups-production/postgres/ --recursive | tail -20

# Restore from backup
./scripts/backup/restore-database.sh --latest --database main

# Verify backup
./scripts/backup/verify-backup.sh
```

#### Emergency Operations
```bash
# Stop all services immediately
docker-compose -f deploy/docker/compose/base.yml \
               -f deploy/docker/compose/production.yml \
               stop

# Start all services
docker-compose -f deploy/docker/compose/base.yml \
               -f deploy/docker/compose/production.yml \
               up -d

# Restart specific service
docker-compose -f deploy/docker/compose/base.yml \
               -f deploy/docker/compose/production.yml \
               restart backend

# View system resources
df -h
free -h
top -bn1 | head -20
```

#### Failover to DR
```bash
# Full failover procedure
ssh dr-server.example.com
cd /opt/ecommerce-platform
./scripts/dr/failover-to-dr.sh

# Manual failover steps
./scripts/backup/restore-database.sh --from-s3 --latest
docker-compose -f deploy/docker/compose/base.yml \
               -f deploy/docker/compose/production.yml up -d
./scripts/deployment/smoke-tests.sh
```

#### Rollback
```bash
# Rollback to previous deployment
git checkout <previous-version-tag>
docker-compose -f deploy/docker/compose/base.yml \
               -f deploy/docker/compose/production.yml \
               up -d --build

# Or use blue-green deployment script
cd deploy/docker/scripts
./blue-green-deploy.sh --rollback
```

---

## Document Control

**Document Version**: 2.0
**Last Updated**: 2025-12-24
**Next DR Drill**: 2025-01-24
**Last Successful Recovery Test**: [To be conducted]
**Next Review**: 2025-03-24

**Change Log**:
- v2.0 (2025-12-24): Updated for Docker-based deployment, removed Kubernetes references
- v1.0 (2025-12-04): Initial version
