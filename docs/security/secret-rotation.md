# Secrets Rotation Guide

## Overview

This document describes the automated secrets rotation system for the E-Commerce Platform, which regularly rotates sensitive credentials to minimize the impact of potential security breaches.

## Table of Contents

1. [Rotation Schedule](#rotation-schedule)
2. [Automated Rotation](#automated-rotation)
3. [Manual Rotation](#manual-rotation)
4. [Testing Rotation](#testing-rotation)
5. [Rollback Procedures](#rollback-procedures)
6. [Monitoring](#monitoring)
7. [Troubleshooting](#troubleshooting)

---

## Rotation Schedule

### Weekly Rotation (Sunday 2:00 AM)

**Database Passwords:**
- PostgreSQL password for `ecommerce_user`
- Updated in both Vault and PostgreSQL
- Backend and Celery services restarted

**Redis Password:**
- Redis authentication password
- Updated in both Vault and Redis server
- Backend, API Gateway, and Celery restarted

### Monthly Rotation (1st of Month 2:00 AM)

**JWT Secrets:**
- JWT signing secret
- Updated in Vault
- All existing JWT tokens invalidated
- Backend and API Gateway restarted

### Quarterly Rotation (Manual)

**Encryption Keys:**
- Requires manual intervention
- Coordinate with security team
- Plan maintenance window

**API Keys (External Services):**
- Stripe API keys
- AWS access keys
- OpenAI API keys
- Coordinate with service providers

---

## Automated Rotation

### Setup

Install the cron job for automated rotation:

```bash
# Install cron job
./scripts/security/setup-rotation-cron.sh

# Verify installation
crontab -l | grep rotate-secrets

# Remove cron job (if needed)
./scripts/security/setup-rotation-cron.sh --remove
```

The cron job will:
- Run every Sunday at 2:00 AM
- Automatically determine which secrets to rotate based on schedule
- Log all activities to `/var/log/ecommerce/secret-rotation.log`
- Send Slack notifications on completion/failure

### Configuration

Set up environment variables for automated rotation:

```bash
# Vault configuration
export VAULT_ADDR="http://vault:8200"
export VAULT_TOKEN="your-vault-token"

# Optional: Slack notifications
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

# Optional: Custom health check URL
export HEALTH_CHECK_URL="http://localhost:8000/health/"
```

### Rotation Process

Each rotation follows this workflow:

1. **Pre-checks:**
   - Verify Vault is accessible and unsealed
   - Retrieve current secret from Vault
   - Store current value for rollback

2. **Update Vault:**
   - Generate new strong random secret
   - Store new secret in Vault with metadata
   - Add rotation timestamp and automation tag

3. **Update Service:**
   - Update secret in target service (DB, Redis, etc.)
   - If update fails, rollback Vault immediately

4. **Restart Services:**
   - Restart affected services
   - Wait for services to stabilize

5. **Health Check:**
   - Verify services are healthy
   - If health check fails, log error for manual intervention

6. **Notification:**
   - Send success/failure notification
   - Log results with timestamp

---

## Manual Rotation

### Rotate Specific Secret

```bash
# Rotate database password only
./scripts/security/rotate-secrets.sh database

# Rotate Redis password only
./scripts/security/rotate-secrets.sh redis

# Rotate JWT secret only
./scripts/security/rotate-secrets.sh jwt

# Rotate all secrets
./scripts/security/rotate-secrets.sh all
```

### Emergency Rotation

If a secret is compromised:

```bash
# 1. Immediately rotate the compromised secret
./scripts/security/rotate-secrets.sh [database|redis|jwt]

# 2. Verify rotation succeeded
tail -f /var/log/ecommerce/secret-rotation.log

# 3. Check service health
curl http://localhost:8000/health/

# 4. Review audit logs for unauthorized access
docker-compose exec vault cat /vault/logs/audit.log | grep -A 5 -B 5 "DB_PASSWORD"
```

### Rotation During Maintenance Window

For planned rotations that require coordination:

```bash
# 1. Announce maintenance window
# 2. Put application in maintenance mode
# 3. Run rotation
./scripts/security/rotate-secrets.sh all

# 4. Verify all services
./scripts/security/test-rotation.sh all

# 5. Exit maintenance mode
```

---

## Testing Rotation

### Pre-Rotation Testing

Always test before running actual rotation:

```bash
# Test all rotation checks
./scripts/security/test-rotation.sh all

# Test specific service rotation
./scripts/security/test-rotation.sh database
./scripts/security/test-rotation.sh redis
./scripts/security/test-rotation.sh jwt
```

The test script checks:
- Vault connectivity and authentication
- Secret existence in Vault
- Service health and connectivity
- Required tools availability
- Password generation
- Simulated rotation workflow

### Expected Test Output

```
============================================================
  Secrets Rotation Test Suite
  Mode: Safe Testing (No Actual Changes)
============================================================

[PASS] curl is installed
[PASS] jq is installed
[PASS] openssl is installed
[PASS] docker-compose is installed
[PASS] Vault is accessible
[PASS] Vault is unsealed
[PASS] Vault authentication valid
[PASS] Database password exists in Vault
[PASS] Can retrieve current database password
[PASS] PostgreSQL is accepting connections
...

Test Results Summary:
  Passed: 15
  Failed: 0
  Total:  15

All tests passed! Rotation should work correctly.
```

---

## Rollback Procedures

### Automatic Rollback

The rotation script includes automatic rollback:

- If Vault update fails, rotation stops (no service impact)
- If service update fails, Vault is rolled back to previous value
- If health check fails, error is logged for manual intervention

### Manual Rollback

If rotation succeeds but causes issues:

```bash
# 1. Check Vault history for previous secret
export VAULT_TOKEN="your-vault-token"

# View secret versions
vault kv metadata ecommerce/backend/database

# Retrieve previous version
vault kv get -version=1 ecommerce/backend/database

# 2. Manually set old password in service
# Database example:
docker-compose exec -T postgres psql -U postgres -c \
  "ALTER USER ecommerce_user WITH PASSWORD 'old-password';"

# Redis example:
docker-compose exec -T redis redis-cli CONFIG SET requirepass "old-password"

# 3. Update Vault back to old value
vault kv put ecommerce/backend/database \
  DB_PASSWORD="old-password"

# 4. Restart services
docker-compose restart backend celery_worker
```

### Rollback Checklist

- [ ] Identify which secret was rotated
- [ ] Retrieve previous version from Vault
- [ ] Update service with old secret
- [ ] Update Vault with old secret
- [ ] Restart affected services
- [ ] Verify health checks pass
- [ ] Document incident
- [ ] Review rotation logs

---

## Monitoring

### Log Files

**Rotation Logs:**
```bash
# View rotation log
tail -f /var/log/ecommerce/secret-rotation.log

# View cron output
tail -f /var/log/ecommerce/rotation-cron.log

# Search for failures
grep "ERROR" /var/log/ecommerce/secret-rotation.log

# Search for specific rotation
grep "Database password" /var/log/ecommerce/secret-rotation.log
```

**Vault Audit Logs:**
```bash
# View recent Vault access
docker-compose exec vault cat /vault/logs/audit.log | tail -n 50

# Search for rotation activity
docker-compose exec vault cat /vault/logs/audit.log | grep "rotated_at"
```

### Notifications

Configure Slack webhook for automated notifications:

```bash
# Set webhook URL
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

# Test notification
curl -X POST "$SLACK_WEBHOOK_URL" \
  -H 'Content-Type: application/json' \
  -d '{"text": "Test notification from secrets rotation"}'
```

Notifications are sent for:
- Successful rotation completion
- Rotation failures
- Health check failures

### Health Checks

Monitor service health after rotation:

```bash
# Backend health
curl http://localhost:8000/health/

# Database connectivity
docker-compose exec -T postgres pg_isready

# Redis connectivity
docker-compose exec -T redis redis-cli ping

# All services
docker-compose ps
```

### Metrics to Monitor

- **Rotation Success Rate:** Percentage of successful rotations
- **Rotation Duration:** Time taken for each rotation
- **Service Downtime:** Time services are unavailable during rotation
- **Health Check Failures:** Number of failed health checks post-rotation
- **Rollback Frequency:** Number of rollbacks required

---

## Troubleshooting

### Rotation Failed: Vault Sealed

**Symptom:** Rotation fails with "Vault is sealed"

**Solution:**
```bash
./scripts/security/unseal-vault.sh
./scripts/security/rotate-secrets.sh [service]
```

### Rotation Failed: Authentication Error

**Symptom:** "Vault authentication failed"

**Solution:**
```bash
# Get valid token
export VAULT_TOKEN=$(cat vault-data/init.json | jq -r '.root_token')

# Or authenticate with AppRole
export VAULT_ROLE_ID=$(cat vault-data/backend-role-id)
export VAULT_SECRET_ID=$(cat vault-data/backend-secret-id)

# Retry rotation
./scripts/security/rotate-secrets.sh [service]
```

### Health Check Failed After Rotation

**Symptom:** Services don't pass health check after rotation

**Investigation:**
```bash
# Check service logs
docker-compose logs backend

# Verify secret in Vault
vault kv get ecommerce/backend/database

# Test database connection manually
docker-compose exec backend python manage.py check --database default

# Check if service picked up new secret
docker-compose exec backend env | grep DB_PASSWORD
```

**Solution:**
- Verify services restarted successfully
- Check if services are pulling from Vault
- Manually restart services if needed
- Consider rollback if issue persists

### Database Password Update Failed

**Symptom:** PostgreSQL password update fails

**Investigation:**
```bash
# Check PostgreSQL logs
docker-compose logs postgres

# Verify user exists
docker-compose exec postgres psql -U postgres -c "\du"

# Test connection with old password
docker-compose exec backend python manage.py check --database default
```

**Solution:**
```bash
# Manually update password
docker-compose exec -T postgres psql -U postgres -c \
  "ALTER USER ecommerce_user WITH PASSWORD 'new-password';"

# Update Vault
vault kv put ecommerce/backend/database DB_PASSWORD="new-password"

# Restart services
docker-compose restart backend
```

### Redis Password Update Failed

**Symptom:** Redis password update fails

**Investigation:**
```bash
# Check Redis logs
docker-compose logs redis

# Test current password
docker-compose exec redis redis-cli -a "current-password" ping
```

**Solution:**
```bash
# Manually set password
docker-compose exec -T redis redis-cli CONFIG SET requirepass "new-password"

# Update Vault
vault kv put ecommerce/backend/redis REDIS_PASSWORD="new-password"

# Restart services
docker-compose restart backend api_gateway
```

### Services Won't Start After Rotation

**Symptom:** Services fail to start after rotation

**Investigation:**
```bash
# Check if Vault is accessible
curl http://vault:8200/v1/sys/health

# Verify services can authenticate
docker-compose logs backend | grep -i vault

# Check environment variables
docker-compose exec backend env | grep VAULT
```

**Solution:**
```bash
# Verify Vault AppRole credentials
echo $VAULT_ROLE_ID
echo $VAULT_SECRET_ID

# Test Vault authentication manually
curl --request POST \
  --data "{\"role_id\": \"$VAULT_ROLE_ID\", \"secret_id\": \"$VAULT_SECRET_ID\"}" \
  http://vault:8200/v1/auth/approle/login

# Restart services
docker-compose restart backend
```

---

## Best Practices

### Before Rotation

1. **Test in Staging:** Always test rotation in staging environment first
2. **Check Health:** Verify all services are healthy before starting
3. **Review Logs:** Check recent logs for any issues
4. **Notify Team:** Inform team of upcoming rotation
5. **Backup Data:** Ensure recent backups exist

### During Rotation

1. **Monitor Logs:** Watch rotation logs in real-time
2. **Track Time:** Note rotation start and completion times
3. **Verify Steps:** Confirm each step completes successfully
4. **Be Ready:** Have rollback procedure ready if needed

### After Rotation

1. **Verify Health:** Check all services are healthy
2. **Test Functionality:** Perform smoke tests
3. **Review Logs:** Check for any errors or warnings
4. **Update Documentation:** Record any issues encountered
5. **Notify Team:** Confirm rotation completed successfully

### Security Considerations

1. **Minimum Rotation Frequency:**
   - Critical secrets: Weekly
   - Standard secrets: Monthly
   - External API keys: Quarterly

2. **Secret Strength:**
   - Passwords: 32+ characters, random alphanumeric
   - JWT secrets: 64+ characters, base64 encoded
   - Use cryptographically secure random generation

3. **Access Control:**
   - Limit who can trigger manual rotation
   - Audit all rotation activities
   - Monitor for unauthorized rotation attempts

4. **Incident Response:**
   - Have emergency rotation procedure ready
   - Know how to rotate all secrets quickly
   - Document escalation paths

---

## Reference

### Quick Commands

```bash
# Test rotation readiness
./scripts/security/test-rotation.sh all

# Rotate all secrets
./scripts/security/rotate-secrets.sh all

# Rotate specific secret
./scripts/security/rotate-secrets.sh database

# Setup automated rotation
./scripts/security/setup-rotation-cron.sh

# View rotation logs
tail -f /var/log/ecommerce/secret-rotation.log

# Check Vault audit log
docker-compose exec vault cat /vault/logs/audit.log | grep rotated_at
```

### Files

- `scripts/security/rotate-secrets.sh` - Main rotation script
- `scripts/security/test-rotation.sh` - Test rotation
- `scripts/security/setup-rotation-cron.sh` - Cron setup
- `/var/log/ecommerce/secret-rotation.log` - Rotation log
- `/vault/logs/audit.log` - Vault audit log

### Related Documentation

- [Vault Integration Guide](vault-integration.md)
- [Phase 3 Execution Plan](../PHASE_3_EXECUTION_PLAN.md)
- [Security Policies](../policies/)

---

**Document Version:** 1.0
**Last Updated:** 2025-12-18
**Maintained By:** Platform Engineering Team
