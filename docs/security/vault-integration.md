# HashiCorp Vault Integration Guide

## Overview

This document describes the HashiCorp Vault integration for the E-Commerce Platform, providing centralized secrets management with AppRole authentication.

## Table of Contents

1. [Architecture](#architecture)
2. [Quick Start](#quick-start)
3. [Configuration](#configuration)
4. [Usage](#usage)
5. [Maintenance](#maintenance)
6. [Troubleshooting](#troubleshooting)
7. [Security Best Practices](#security-best-practices)

---

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Services                      │
├──────────────┬──────────────┬──────────────┬────────────────┤
│   Backend    │ API Gateway  │ AI Services  │ Celery Workers │
└──────┬───────┴──────┬───────┴──────┬───────┴───────┬────────┘
       │              │              │               │
       │ AppRole      │ AppRole      │ AppRole       │ AppRole
       │ Auth         │ Auth         │ Auth          │ Auth
       │              │              │               │
       └──────────────┴──────────────┴───────────────┘
                              │
                      ┌───────▼────────┐
                      │  Vault Server  │
                      │  (Port 8200)   │
                      └───────┬────────┘
                              │
               ┌──────────────┼──────────────┐
               │              │              │
       ┌───────▼────┐  ┌──────▼──────┐  ┌───▼─────┐
       │  Secrets   │  │   Policies   │  │  Audit  │
       │   Engine   │  │   (RBAC)     │  │  Logs   │
       └────────────┘  └──────────────┘  └─────────┘
```

### Secret Organization

Secrets are organized in a KV v2 secrets engine mounted at `ecommerce/`:

```
ecommerce/
├── backend/
│   ├── django/          # Django SECRET_KEY, DEBUG, etc.
│   ├── database/        # Database credentials
│   ├── redis/           # Redis password
│   └── celery/          # Celery broker URLs
├── gateway/
│   └── api/             # API Gateway secrets
├── ai/
│   ├── openai/          # OpenAI API keys
│   ├── anthropic/       # Anthropic API keys
│   └── huggingface/     # HuggingFace tokens
└── shared/
    ├── stripe/          # Payment gateway credentials
    ├── aws/             # AWS access keys
    ├── email/           # SMTP credentials
    └── monitoring/      # Grafana, Sentry, etc.
```

### Authentication Flow

1. **Service Startup**: Service reads `VAULT_ROLE_ID` and `VAULT_SECRET_ID` from environment
2. **AppRole Login**: Service authenticates with Vault using AppRole
3. **Token Received**: Vault returns a client token (TTL: 1 hour)
4. **Secret Access**: Service uses token to read secrets
5. **Token Renewal**: Token is automatically renewed before expiration
6. **Re-authentication**: If renewal fails, service re-authenticates

---

## Quick Start

### 1. Start Vault

```bash
# Start Vault service
docker-compose -f deploy/docker/compose/base.yml \
               -f deploy/docker/compose/vault.yml up -d vault

# Wait for Vault to be ready
sleep 5
```

### 2. Initialize Vault

```bash
# Initialize Vault (creates unseal keys and root token)
./scripts/security/init-vault.sh
```

**IMPORTANT**: Save the unseal keys and root token securely! You will need them to unseal Vault after restarts.

### 3. Migrate Secrets

```bash
# Migrate secrets from .env to Vault
./scripts/security/migrate-secrets.sh .env
```

This creates:
- Backup of original `.env` file
- `.env.vault` with Vault configuration

### 4. Configure Services

Update your `.env` file with Vault credentials:

```bash
# Backend AppRole credentials
VAULT_ROLE_ID=$(cat vault-data/backend-role-id)
VAULT_SECRET_ID=$(cat vault-data/backend-secret-id)

# Enable Vault
USE_VAULT=true
VAULT_ADDR=http://vault:8200
```

### 5. Restart Services

```bash
docker-compose restart backend api_gateway celery_worker
```

---

## Configuration

### Environment Variables

#### Common Variables (All Services)

```bash
# Enable Vault integration
USE_VAULT=true

# Vault server address
VAULT_ADDR=http://vault:8200

# Vault namespace (if using Vault Enterprise)
VAULT_NAMESPACE=

# Vault secrets mount point
VAULT_MOUNT_POINT=ecommerce
```

#### Service-Specific Variables

**Backend Services** (backend, celery_worker, celery_beat):
```bash
VAULT_ROLE_ID=<backend-role-id>
VAULT_SECRET_ID=<backend-secret-id>
```

**AI Services** (recommender, search, pricing, chatbot, fraud, forecasting, vision):
```bash
VAULT_ROLE_ID=<ai-services-role-id>
VAULT_SECRET_ID=<ai-services-secret-id>
```

**API Gateway**:
```bash
VAULT_ROLE_ID=<api-gateway-role-id>
VAULT_SECRET_ID=<api-gateway-secret-id>
```

### Docker Compose Integration

Add Vault service dependency to your services:

```yaml
services:
  backend:
    depends_on:
      - vault
    environment:
      - USE_VAULT=true
      - VAULT_ADDR=http://vault:8200
      - VAULT_ROLE_ID=${VAULT_ROLE_ID}
      - VAULT_SECRET_ID=${VAULT_SECRET_ID}
```

---

## Usage

### Accessing Secrets in Code

#### Django Settings

```python
from core.vault_client import get_vault_secret

# Get Django SECRET_KEY
SECRET_KEY = get_vault_secret(
    env_var_name='SECRET_KEY',
    vault_path='backend/django',
    vault_key='SECRET_KEY'
)

# Get database password
DB_PASSWORD = get_vault_secret(
    env_var_name='DB_PASSWORD',
    vault_path='backend/database',
    vault_key='DB_PASSWORD'
)

# Get Stripe secret key
STRIPE_SECRET_KEY = get_vault_secret(
    env_var_name='STRIPE_SECRET_KEY',
    vault_path='shared/stripe',
    vault_key='STRIPE_SECRET_KEY'
)
```

#### Direct Vault Client Usage

```python
from core.vault_client import VaultClient

# Create Vault client
vault = VaultClient()

# Authenticate
if vault.authenticate():
    # Get a single secret
    api_key = vault.get_secret('ai/openai', 'OPENAI_API_KEY')

    # Get all secrets from a path
    all_django_secrets = vault.get_secret('backend/django')

    # Use cached secrets (recommended for frequently accessed secrets)
    db_password = vault.get_secret_cached('backend/database', 'DB_PASSWORD')
```

### Vault CLI Commands

#### List Secrets

```bash
# Set Vault address and token
export VAULT_ADDR=http://localhost:8200
export VAULT_TOKEN=$(cat vault-data/init.json | jq -r '.root_token')

# List all secret paths
vault kv list ecommerce/

# List backend secrets
vault kv list ecommerce/backend/

# List shared secrets
vault kv list ecommerce/shared/
```

#### Read Secrets

```bash
# Read Django secrets
vault kv get ecommerce/backend/django

# Read specific field
vault kv get -field=SECRET_KEY ecommerce/backend/django

# Read database secrets
vault kv get ecommerce/backend/database
```

#### Write Secrets

```bash
# Add a new secret
vault kv put ecommerce/backend/django \
  SECRET_KEY="new-secret-key" \
  DEBUG="False"

# Update a single field
vault kv patch ecommerce/backend/django DEBUG="True"
```

#### Delete Secrets

```bash
# Soft delete (can be undeleted)
vault kv delete ecommerce/backend/test-secret

# Permanently delete
vault kv destroy -versions=1 ecommerce/backend/test-secret

# Undelete
vault kv undelete -versions=1 ecommerce/backend/test-secret
```

---

## Maintenance

### Unsealing Vault

Vault must be unsealed after every restart:

```bash
./scripts/security/unseal-vault.sh
```

This script uses the unseal keys from `vault-data/init.json` to unseal Vault.

### Rotating AppRole Secret IDs

Secret IDs should be rotated regularly (recommended: monthly):

```bash
# Generate new secret ID for backend
export VAULT_TOKEN=$(cat vault-data/init.json | jq -r '.root_token')

curl -s \
  -H "X-Vault-Token: ${VAULT_TOKEN}" \
  --request POST \
  http://localhost:8200/v1/auth/approle/role/backend/secret-id \
  | jq -r '.data.secret_id' > vault-data/backend-secret-id-new

# Update .env with new secret ID
# Then restart services
docker-compose restart backend
```

### Rotating Secrets

```bash
# Rotate database password
./scripts/security/rotate-secrets.sh database

# Rotate Redis password
./scripts/security/rotate-secrets.sh redis

# Rotate all secrets
./scripts/security/rotate-secrets.sh all
```

### Monitoring Vault

#### Health Check

```bash
curl http://localhost:8200/v1/sys/health | jq
```

#### Seal Status

```bash
curl http://localhost:8200/v1/sys/seal-status | jq
```

#### Audit Logs

```bash
docker-compose exec vault cat /vault/logs/audit.log | tail -n 20
```

### Backup and Recovery

#### Backup Vault Data

```bash
# Backup Vault data directory
docker-compose exec vault tar czf /vault/backup.tar.gz /vault/data

# Copy backup to host
docker cp ecommerce_vault:/vault/backup.tar.gz ./vault-backup-$(date +%Y%m%d).tar.gz
```

#### Backup Unseal Keys

```bash
# CRITICAL: Keep multiple copies in secure locations
cp vault-data/init.json vault-backups/init-$(date +%Y%m%d).json
```

#### Recovery

1. Restore Vault data from backup
2. Start Vault service
3. Unseal Vault using stored unseal keys
4. Verify secrets are accessible

---

## Troubleshooting

### Vault is Sealed

**Symptom**: Services cannot connect to Vault

**Solution**:
```bash
./scripts/security/unseal-vault.sh
```

### Authentication Failed

**Symptom**: `Vault authentication failed: 400` in logs

**Possible Causes**:
1. Invalid `VAULT_ROLE_ID` or `VAULT_SECRET_ID`
2. AppRole not configured
3. Policies not attached to AppRole

**Solution**:
```bash
# Verify AppRole exists
export VAULT_TOKEN=$(cat vault-data/init.json | jq -r '.root_token')
curl -H "X-Vault-Token: ${VAULT_TOKEN}" http://localhost:8200/v1/auth/approle/role/backend | jq

# Re-run initialization if needed
./scripts/security/init-vault.sh
```

### Secret Not Found

**Symptom**: `Secret not found at path: backend/django`

**Solution**:
```bash
# List available secrets
vault kv list ecommerce/backend/

# Verify secret exists
vault kv get ecommerce/backend/django

# If missing, migrate secrets again
./scripts/security/migrate-secrets.sh
```

### Token Expired

**Symptom**: `403 Forbidden` errors after service runs for >1 hour

**Cause**: Token not being renewed

**Solution**: The VaultClient automatically renews tokens. Check logs for renewal errors.

### Vault Connection Refused

**Symptom**: `Connection refused` when connecting to Vault

**Solution**:
```bash
# Verify Vault is running
docker-compose ps vault

# Check Vault logs
docker-compose logs vault

# Restart Vault
docker-compose restart vault
```

---

## Security Best Practices

### 1. Protect Unseal Keys

- Store unseal keys in multiple secure locations
- Use Shamir's Secret Sharing (5 keys, threshold 3)
- Never store all keys in one location
- Consider using cloud KMS for auto-unseal in production

### 2. Limit Root Token Usage

- Use root token only for initial setup and emergencies
- Create specific policies for administrators
- Revoke root token after initial setup (optional)
- Generate new root token only when needed

### 3. Use AppRole for Services

- Never use root token in application code
- Each service should have its own AppRole
- Use separate policies for different service types
- Rotate secret IDs regularly

### 4. Enable Audit Logging

- Audit logs track all Vault access
- Store audit logs in a centralized logging system
- Monitor audit logs for suspicious activity
- Retain logs for compliance requirements

### 5. Implement Secrets Rotation

- Rotate secrets regularly (weekly/monthly)
- Automate rotation where possible
- Test rotation process before deploying
- Have rollback plan ready

### 6. Use TLS in Production

- Always use HTTPS for Vault in production
- Use valid SSL certificates (not self-signed)
- Enable TLS verification in clients
- Use strong cipher suites only

### 7. Implement High Availability

- Deploy Vault in HA mode for production
- Use Consul or integrated storage (Raft)
- Test failover procedures
- Monitor Vault cluster health

### 8. Backup Regularly

- Backup Vault data daily
- Store backups in multiple locations
- Test backup restoration procedures
- Encrypt backups at rest

### 9. Monitor and Alert

- Monitor Vault seal status
- Alert on authentication failures
- Track secret access patterns
- Set up health checks

### 10. Follow Least Privilege

- Grant minimum required permissions
- Use separate policies for each service
- Regularly review and audit policies
- Revoke unused AppRoles

---

## Production Deployment

### Auto-Unseal Setup

For production, implement auto-unseal to avoid manual unsealing:

#### AWS KMS Auto-Unseal

```hcl
seal "awskms" {
  region     = "us-east-1"
  kms_key_id = "your-kms-key-id"
}
```

#### Azure Key Vault Auto-Unseal

```hcl
seal "azurekeyvault" {
  tenant_id      = "your-tenant-id"
  client_id      = "your-client-id"
  client_secret  = "your-client-secret"
  vault_name     = "your-vault-name"
  key_name       = "your-key-name"
}
```

### High Availability Setup

1. Deploy 3+ Vault nodes
2. Configure integrated storage (Raft)
3. Set up load balancer
4. Enable auto-unseal
5. Monitor cluster health

### Disaster Recovery

1. Regular backups (daily minimum)
2. Document recovery procedures
3. Test recovery quarterly
4. Maintain offline backup copy
5. Have emergency contacts ready

---

## References

- [HashiCorp Vault Documentation](https://www.vaultproject.io/docs)
- [AppRole Auth Method](https://www.vaultproject.io/docs/auth/approle)
- [KV Secrets Engine v2](https://www.vaultproject.io/docs/secrets/kv/kv-v2)
- [Vault Security Model](https://www.vaultproject.io/docs/internals/security)
- [Production Hardening](https://learn.hashicorp.com/tutorials/vault/production-hardening)

---

**Document Version**: 1.0
**Last Updated**: 2025-12-18
**Maintained By**: Platform Engineering Team
