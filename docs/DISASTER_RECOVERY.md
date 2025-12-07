# Disaster Recovery Plan

**Version**: 1.0
**Last Updated**: 2025-12-04
**Classification**: CONFIDENTIAL
**Owner**: Platform Team

---

## Executive Summary

This document outlines the disaster recovery (DR) procedures for the e-commerce platform, including Recovery Time Objective (RTO), Recovery Point Objective (RPO), and step-by-step recovery procedures.

## Recovery Objectives

| Component | RTO | RPO | Priority |
|-----------|-----|-----|----------|
| Database (PostgreSQL) | 1 hour | 15 minutes | P0 - Critical |
| Application (Backend/API) | 30 minutes | 0 (stateless) | P0 - Critical |
| Cache (Redis) | 15 minutes | 1 hour | P1 - High |
| Search (Elasticsearch) | 2 hours | 24 hours | P2 - Medium |
| AI Services | 1 hour | 0 (stateless) | P1 - High |
| Media Files (S3) | 4 hours | 24 hours | P2 - Medium |

## Disaster Scenarios

### Scenario 1: Database Failure

**Detection**:
- Alert: `DatabaseDown` from Prometheus
- Health checks failing
- Unable to connect to RDS

**Recovery Procedure**:

```bash
# 1. Verify failure
aws rds describe-db-instances --db-instance-identifier ecommerce-prod

# 2. Check automated snapshots
aws rds describe-db-snapshots \
    --db-instance-identifier ecommerce-prod \
    --snapshot-type automated \
    --query 'DBSnapshots[0]'

# 3. Restore from snapshot
aws rds restore-db-instance-from-db-snapshot \
    --db-instance-identifier ecommerce-prod-restored \
    --db-snapshot-identifier rds:ecommerce-prod-2025-12-04-03-00 \
    --db-instance-class db.r5.2xlarge \
    --multi-az

# 4. Wait for availability
aws rds wait db-instance-available \
    --db-instance-identifier ecommerce-prod-restored

# 5. Update DNS/connection strings
kubectl set env deployment/backend \
    DATABASE_URL=postgresql://user:pass@new-endpoint:5432/db \
    -n ecommerce-production

# 6. Verify connectivity
kubectl exec -it deployment/backend -n ecommerce-production -- \
    python manage.py dbshell -c "SELECT 1;"

# 7. Run data integrity checks
./scripts/verify_data_integrity.sh
```

**Time to Recovery**: ~45 minutes

### Scenario 2: Complete Region Failure

**Detection**:
- All services down in primary region
- AWS Service Health Dashboard shows region outage
- Unable to reach any resources

**Recovery Procedure**:

```bash
# 1. Activate DR region
export AWS_REGION=us-west-2  # DR region
export CLUSTER_NAME=ecommerce-dr

# 2. Verify DR infrastructure
terraform workspace select dr
terraform plan

# 3. Restore database from cross-region backup
aws rds restore-db-instance-from-db-snapshot \
    --db-instance-identifier ecommerce-dr \
    --db-snapshot-identifier arn:aws:rds:us-west-2:123456789:snapshot:ecommerce-prod-latest \
    --region us-west-2

# 4. Update Route 53 for failover
aws route53 change-resource-record-sets \
    --hosted-zone-id Z1234567890ABC \
    --change-batch file://dns-failover.json

# 5. Scale up DR cluster
kubectl scale deployment/backend --replicas=10 -n ecommerce-production
kubectl scale deployment/api-gateway --replicas=5 -n ecommerce-production

# 6. Verify services
./scripts/smoke-tests.sh https://api-dr.example.com

# 7. Monitor closely
# Open Grafana DR dashboard and watch for issues
```

**Time to Recovery**: ~2 hours (includes DNS propagation)

### Scenario 3: Ransomware/Data Corruption

**Detection**:
- Unusual database modifications
- Corrupted data reported by users
- Security alerts from intrusion detection

**Recovery Procedure**:

```bash
# 1. IMMEDIATELY isolate affected systems
kubectl scale deployment/backend --replicas=0 -n ecommerce-production

# 2. Identify last known good backup
aws rds describe-db-snapshots \
    --db-instance-identifier ecommerce-prod \
    --query 'DBSnapshots[*].[DBSnapshotIdentifier,SnapshotCreateTime]'

# 3. Restore to point-in-time BEFORE attack
aws rds restore-db-instance-to-point-in-time \
    --source-db-instance-identifier ecommerce-prod \
    --target-db-instance-identifier ecommerce-clean \
    --restore-time 2025-12-04T02:00:00Z

# 4. Verify clean data
psql -h ecommerce-clean.xxx.rds.amazonaws.com -U admin -d ecommerce \
    -c "SELECT COUNT(*) FROM products;"

# 5. Update application
kubectl set env deployment/backend \
    DATABASE_URL=postgresql://user:pass@ecommerce-clean:5432/db

# 6. Scale back up
kubectl scale deployment/backend --replicas=3 -n ecommerce-production

# 7. Forensics
# Preserve compromised instance for investigation
# Notify security team
```

### Scenario 4: Kubernetes Cluster Failure

**Detection**:
- Cannot connect to Kubernetes API
- All pods evicted or not running
- EKS control plane unresponsive

**Recovery Procedure**:

```bash
# 1. Check EKS cluster status
aws eks describe-cluster --name ecommerce-prod --region us-east-1

# 2. If cluster is down, create new cluster from Terraform
cd terraform/
terraform workspace select prod-backup
terraform apply -var="cluster_name=ecommerce-prod-recovery"

# 3. Restore from GitOps repository
git clone https://github.com/org/k8s-config
cd k8s-config/
kubectl apply -k overlays/production/

# 4. Restore secrets from AWS Secrets Manager
./scripts/restore-secrets.sh production

# 5. Wait for pods to be ready
kubectl wait --for=condition=ready pod -l app=backend --timeout=600s

# 6. Verify services
kubectl get pods -A
kubectl get svc -A

# 7. Run smoke tests
./tests/integration/smoke-tests.sh
```

### Scenario 5: Data Center / AZ Failure

**Detection**:
- Nodes in specific AZ are not ready
- Pods being evicted from AZ
- AWS reports AZ degradation

**Actions**:
- Kubernetes will automatically reschedule pods to healthy AZs
- Monitor pod rescheduling
- Verify no data loss

```bash
# Check pod distribution
kubectl get pods -o wide -n ecommerce-production | grep backend

# If needed, manually drain AZ
kubectl drain node-in-failed-az --ignore-daemonsets --delete-emptydir-data

# Verify services recovered
kubectl get pods -n ecommerce-production
```

## Backup Strategy

### Automated Backups

```yaml
# RDS Automated Backups
- Frequency: Every 6 hours
- Retention: 30 days
- Cross-Region: Yes (us-west-2)

# Application State (S3)
- Frequency: Daily
- Retention: 90 days with lifecycle
- Versioning: Enabled

# Kubernetes Etcd
- Frequency: Every 6 hours
- Retention: 7 days
- Tool: Velero

# ElastiCache Redis
- Frequency: Daily snapshots
- Retention: 7 days
```

### Backup Script

```bash
#!/bin/bash
# File: scripts/backup-all.sh

set -e

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_BUCKET="s3://ecommerce-backups"

echo "🔄 Starting comprehensive backup..."

# 1. RDS Snapshot
echo "📸 Creating RDS snapshot..."
aws rds create-db-snapshot \
    --db-instance-identifier ecommerce-prod \
    --db-snapshot-identifier manual-backup-$TIMESTAMP

# 2. Redis Snapshot
echo "📸 Creating Redis snapshot..."
aws elasticache create-snapshot \
    --replication-group-id ecommerce-redis \
    --snapshot-name manual-backup-$TIMESTAMP

# 3. Kubernetes Resources
echo "💾 Backing up Kubernetes resources..."
velero backup create backup-$TIMESTAMP \
    --include-namespaces ecommerce-production \
    --wait

# 4. Application Data
echo "💾 Backing up media files..."
aws s3 sync s3://ecommerce-media $BACKUP_BUCKET/media-$TIMESTAMP/ \
    --storage-class GLACIER

# 5. Configuration
echo "💾 Backing up configuration..."
kubectl get configmap,secret -n ecommerce-production -o yaml > \
    /tmp/k8s-config-$TIMESTAMP.yaml
aws s3 cp /tmp/k8s-config-$TIMESTAMP.yaml \
    $BACKUP_BUCKET/config/

echo "✅ Backup complete: $TIMESTAMP"
```

## Recovery Testing

### Monthly DR Drill

```bash
#!/bin/bash
# File: scripts/dr-drill.sh

echo "🧪 Starting DR drill..."

# 1. Restore to DR environment
terraform workspace select dr
terraform apply -auto-approve

# 2. Restore database
aws rds restore-db-instance-from-db-snapshot \
    --db-instance-identifier ecommerce-dr-test \
    --db-snapshot-identifier latest-automated

# 3. Deploy application
kubectl apply -k k8s/overlays/dr/

# 4. Run verification tests
./tests/integration/dr-tests.sh

# 5. Measure recovery time
echo "Recovery completed in: $(($SECONDS / 60)) minutes"

# 6. Cleanup
terraform destroy -auto-approve

echo "✅ DR drill complete"
```

### Testing Schedule

- **Weekly**: Backup verification (restore to non-prod)
- **Monthly**: Full DR drill
- **Quarterly**: Multi-region failover test
- **Annually**: Full disaster simulation with external auditor

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
| Database Admin | [Name] | [Phone] | [Email] |
| AWS Support | - | - | enterprise-support@aws.com |
| PagerDuty | - | - | +1-XXX-XXX-XXXX |

### Critical URLs

- Status Page: https://status.example.com
- Grafana DR: https://grafana-dr.example.com
- AWS Console: https://console.aws.amazon.com
- PagerDuty: https://example.pagerduty.com
- Runbooks: https://wiki.example.com/runbooks

### Key Commands

```bash
# Check cluster health
kubectl get nodes
kubectl get pods -A

# Check database
aws rds describe-db-instances

# Check backups
aws rds describe-db-snapshots --max-records 5

# Failover to DR
./scripts/failover-to-dr.sh

# Rollback
./scripts/rollback.sh
```

---

**Document Version**: 1.0
**Next DR Drill**: 2025-01-04
**Last Successful Recovery Test**: [Date]
**Next Review**: 2025-03-04
