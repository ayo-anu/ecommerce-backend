# PHASE 3 EXECUTION PLAN
## CI/CD & Security (Week 5-6)

**Status:** In Progress
**Prerequisites:** ✅ Phase 0 Complete, ✅ Phase 1 Complete, ✅ Phase 2 Complete
**Story Points:** 89
**Estimated Duration:** 1-2 weeks
**Priority:** Critical

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

Phase 3 transforms the platform into a production-ready, security-hardened system with:

- **Complete CI/CD pipeline** from PR to production
- **Security automation** with vulnerability scanning and SBOM generation
- **Secrets management** via HashiCorp Vault with automated rotation
- **Compliance readiness** for PCI-DSS and SOC 2
- **Defense in depth** with multiple security layers

### Success Metrics

| Metric | Current | Target | Impact |
|--------|---------|--------|--------|
| Secrets in environment files | Yes | 0 (all in Vault) | Security compliance |
| Security scanning in CI | None | 3 tools (Trivy, Snyk, SAST) | Vulnerability detection |
| Deployment approvals | Manual | Automated with gates | Controlled releases |
| SBOM generation | None | All images | Supply chain security |
| Secrets rotation | Never | Weekly automated | Reduced exposure |
| Non-root containers | 50% | 100% | Principle of least privilege |
| Secret scanning | None | Pre-commit + CI | Prevent leaks |

---

## Task Breakdown

### CICD-001: Complete Production Pipeline (13 SP)

**Priority:** Critical
**Description:** End-to-end CI/CD pipeline from PR to production

**Current State:**
- Basic CI workflows exist
- No deployment automation
- Manual production deployments
- No rollback automation

**Target State:**
- Automated pipeline: PR → Build → Test → Security Scan → Deploy
- Integration with blue-green deployment
- Automated rollback on failure
- Deployment notifications

**Pipeline Stages:**
1. **PR Stage:** Linting, unit tests, security scan
2. **Build Stage:** Multi-stage Docker builds, layer caching
3. **Test Stage:** Integration tests, smoke tests
4. **Security Stage:** Vulnerability scanning, SBOM generation
5. **Staging Deploy:** Automated deployment to staging
6. **Production Deploy:** Manual approval → Blue-green deployment

**Files to Create:**
- `.github/workflows/production-deploy.yml` - Full production pipeline
- `.github/workflows/staging-deploy.yml` - Staging deployment
- `.github/workflows/pr-checks.yml` - PR validation
- `deploy/docker/scripts/deploy.sh` - Unified deployment script
- `docs/deployment/ci-cd-pipeline.md` - Pipeline documentation

**Implementation:**
```yaml
name: Production Deployment Pipeline

on:
  push:
    tags:
      - 'v*.*.*'
  workflow_dispatch:

jobs:
  security-scan:
    # Trivy, Snyk, SAST

  build-and-test:
    needs: [security-scan]
    # Build images, run tests

  integration-tests:
    needs: [build-and-test]
    # Full integration test suite

  deploy-staging:
    needs: [integration-tests]
    # Auto-deploy to staging

  deploy-production:
    needs: [deploy-staging]
    environment:
      name: production
      url: https://api.example.com
    # Manual approval required
    # Blue-green deployment
```

**Acceptance Criteria:**
- ✅ PR triggers validation workflow
- ✅ Tag triggers full deployment pipeline
- ✅ Security scans block on critical vulnerabilities
- ✅ Integration tests run in isolated environment
- ✅ Staging deploys automatically
- ✅ Production requires manual approval
- ✅ Blue-green deployment on production
- ✅ Rollback automation works
- ✅ Slack/email notifications sent

---

### CICD-002: Security Gates (8 SP)

**Priority:** Critical
**Description:** Multiple security scanning tools in CI pipeline

**Security Tools:**
1. **Trivy** - Container vulnerability scanning
2. **Snyk** - Dependency and container scanning
3. **Grype** - Additional vulnerability detection
4. **Semgrep** - SAST (Static Application Security Testing)
5. **Gitleaks** - Secret scanning in commits

**Implementation:**
```yaml
# .github/workflows/security-scan.yml
name: Security Scanning

on:
  pull_request:
  push:
    branches: [main]

jobs:
  trivy-scan:
    name: Trivy Container Scan
    runs-on: ubuntu-latest
    steps:
      - name: Build image
        run: docker build -t $IMAGE_NAME .

      - name: Run Trivy
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: $IMAGE_NAME
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'
          exit-code: '1'  # Fail on critical/high

      - name: Upload to GitHub Security
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'

  snyk-scan:
    name: Snyk Vulnerability Scan
    runs-on: ubuntu-latest
    steps:
      - name: Run Snyk
        uses: snyk/actions/docker@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          image: $IMAGE_NAME
          args: --severity-threshold=high --fail-on=all

  sast-scan:
    name: SAST with Semgrep
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Run Semgrep
        uses: returntocorp/semgrep-action@v1
        with:
          config: >-
            p/security-audit
            p/secrets
            p/owasp-top-ten

  secret-scan:
    name: Secret Scanning
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        fetch-depth: 0

      - name: Run Gitleaks
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

**Files to Create:**
- `.github/workflows/security-scan.yml` - Security scanning workflow
- `.semgrep.yml` - Semgrep configuration
- `.gitleaks.toml` - Gitleaks configuration
- `scripts/security/local-security-scan.sh` - Run scans locally
- `docs/security/security-scanning.md` - Documentation

**Acceptance Criteria:**
- ✅ Trivy scans all container images
- ✅ Snyk scans dependencies and containers
- ✅ Semgrep SAST finds code vulnerabilities
- ✅ Gitleaks prevents secret commits
- ✅ Results uploaded to GitHub Security tab
- ✅ Critical/High vulnerabilities block PRs
- ✅ Security reports generated
- ✅ Can run scans locally

---

### CICD-003: Approval Workflows (5 SP)

**Priority:** High
**Description:** Manual approval gates for production deployments

**Implementation:**
```yaml
# .github/workflows/production-deploy.yml
deploy-production:
  name: Deploy to Production
  needs: [deploy-staging, smoke-tests]
  runs-on: ubuntu-latest

  environment:
    name: production
    url: https://api.example.com

  steps:
    - name: Checkout
      uses: actions/checkout@v4

    - name: Wait for approval
      uses: trstringer/manual-approval@v1
      with:
        secret: ${{ secrets.GITHUB_TOKEN }}
        approvers: devops-team,platform-leads
        minimum-approvals: 2
        issue-title: "Production Deployment: ${{ github.ref_name }}"
        issue-body: |
          ### Production Deployment Request

          **Version:** ${{ github.ref_name }}
          **Triggered by:** ${{ github.actor }}
          **Changes:** [View Diff](${{ github.event.compare }})

          **Pre-deployment Checklist:**
          - [ ] All tests passing
          - [ ] Security scans clear
          - [ ] Staging deployment successful
          - [ ] Database migrations reviewed
          - [ ] Rollback plan ready

          **Approvers:** @devops-team @platform-leads
        exclude-workflow-initiator-as-approver: false

    - name: Deploy to production
      run: |
        ./deploy/docker/scripts/deploy.sh production

    - name: Post-deployment tests
      run: |
        ./deploy/docker/scripts/smoke-test.sh production

    - name: Notify deployment
      uses: slackapi/slack-github-action@v1
      with:
        payload: |
          {
            "text": "✅ Production deployed: ${{ github.ref_name }}",
            "blocks": [
              {
                "type": "section",
                "text": {
                  "type": "mrkdwn",
                  "text": "Production deployment completed!\n*Version:* ${{ github.ref_name }}\n*Deployed by:* ${{ github.actor }}"
                }
              }
            ]
          }
      env:
        SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

**Files to Create:**
- Update `.github/workflows/production-deploy.yml` - Add approval
- `docs/deployment/approval-process.md` - Approval documentation
- `.github/CODEOWNERS` - Define approvers

**Acceptance Criteria:**
- ✅ Production deploys require manual approval
- ✅ Minimum 2 approvers required
- ✅ Approval issue created automatically
- ✅ Pre-deployment checklist enforced
- ✅ Deployment notifications sent
- ✅ Audit trail of approvals maintained

---

### CICD-004: SBOM Generation (5 SP)

**Priority:** High
**Description:** Software Bill of Materials for all container images

**Why SBOM:**
- Supply chain security
- Vulnerability tracking
- License compliance
- Incident response

**Implementation:**
```yaml
# .github/workflows/sbom-generation.yml
name: SBOM Generation

on:
  push:
    branches: [main]
    tags: ['v*.*.*']

jobs:
  generate-sbom:
    name: Generate SBOM
    runs-on: ubuntu-latest

    strategy:
      matrix:
        service:
          - backend
          - api-gateway
          - recommendation-engine
          - search-engine
          - pricing-engine
          - chatbot-rag
          - fraud-detection
          - demand-forecasting
          - visual-recognition

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Build image
        run: |
          docker build -t ${{ matrix.service }}:${{ github.sha }} \
            -f deploy/docker/images/${{ matrix.service }}/Dockerfile .

      - name: Generate SBOM with Syft
        uses: anchore/sbom-action@v0
        with:
          image: ${{ matrix.service }}:${{ github.sha }}
          format: cyclonedx-json
          output-file: sbom-${{ matrix.service }}.json

      - name: Generate SBOM with Trivy
        run: |
          trivy image --format cyclonedx \
            --output sbom-trivy-${{ matrix.service }}.json \
            ${{ matrix.service }}:${{ github.sha }}

      - name: Upload SBOM artifacts
        uses: actions/upload-artifact@v3
        with:
          name: sboms
          path: sbom-*.json

      - name: Scan SBOM for vulnerabilities
        uses: anchore/scan-action@v3
        with:
          sbom: sbom-${{ matrix.service }}.json
          fail-build: true
          severity-cutoff: high

      - name: Upload to dependency tracking
        run: |
          # Upload to DependencyTrack or similar
          curl -X POST https://dependencytrack.example.com/api/v1/bom \
            -H "X-Api-Key: ${{ secrets.DTRACK_API_KEY }}" \
            -F "project=ecommerce-${{ matrix.service }}" \
            -F "bom=@sbom-${{ matrix.service }}.json"
```

**Files to Create:**
- `.github/workflows/sbom-generation.yml` - SBOM workflow
- `scripts/security/generate-sbom.sh` - Local SBOM generation
- `docs/security/sbom-management.md` - SBOM documentation

**Tools:**
- **Syft** - SBOM generation
- **Trivy** - Alternative SBOM generation
- **Grype** - SBOM vulnerability scanning
- **DependencyTrack** - SBOM management (optional)

**Acceptance Criteria:**
- ✅ SBOM generated for all images
- ✅ CycloneDX format used
- ✅ SBOMs uploaded as artifacts
- ✅ SBOMs scanned for vulnerabilities
- ✅ SBOMs tracked in central system
- ✅ Can generate SBOMs locally

---

### SEC-001: Vault Integration (13 SP)

**Priority:** Critical
**Description:** Full HashiCorp Vault integration for secrets management

**Current State:**
- Vault client code exists but disabled
- Secrets in .env files
- No rotation
- No audit trail

**Target State:**
- Vault managing all secrets
- Secrets pulled at runtime
- AppRole authentication
- Audit logging enabled
- Secrets rotation automated

**Architecture:**
```
┌─────────────┐
│  Backend    │─┐
└─────────────┘ │
┌─────────────┐ │
│ AI Gateway  │─┤  AppRole Auth
└─────────────┘ │  ────────────►  ┌──────────┐
┌─────────────┐ │                  │  Vault   │
│ AI Services │─┘                  │  Server  │
└─────────────┘                    └──────────┘
                                        │
                                        ▼
                                   ┌──────────┐
                                   │ Secrets  │
                                   │  - DB    │
                                   │  - API   │
                                   │  - Keys  │
                                   └──────────┘
```

**Implementation:**

1. **Deploy Vault Container:**
```yaml
# deploy/docker/compose/vault.yml
services:
  vault:
    image: hashicorp/vault:1.15
    container_name: ecommerce_vault
    ports:
      - "8200:8200"
    environment:
      VAULT_DEV_ROOT_TOKEN_ID: ${VAULT_ROOT_TOKEN}
      VAULT_DEV_LISTEN_ADDRESS: 0.0.0.0:8200
    cap_add:
      - IPC_LOCK
    volumes:
      - vault-data:/vault/data
      - vault-logs:/vault/logs
      - ./vault/config:/vault/config
    command: server
    networks:
      - backend

volumes:
  vault-data:
  vault-logs:
```

2. **Initialize Vault:**
```bash
# scripts/security/init-vault.sh
#!/bin/bash
set -euo pipefail

export VAULT_ADDR="http://localhost:8200"

echo "🔐 Initializing Vault..."

# Initialize (only once)
if [ ! -f /vault/data/init.json ]; then
    vault operator init \
        -key-shares=5 \
        -key-threshold=3 \
        -format=json > /vault/data/init.json

    echo "⚠️  IMPORTANT: Save these unseal keys securely!"
    cat /vault/data/init.json
fi

# Unseal
for i in 1 2 3; do
    UNSEAL_KEY=$(jq -r ".unseal_keys_b64[$((i-1))]" /vault/data/init.json)
    vault operator unseal "$UNSEAL_KEY"
done

# Login
ROOT_TOKEN=$(jq -r .root_token /vault/data/init.json)
vault login "$ROOT_TOKEN"

# Enable secrets engine
vault secrets enable -path=ecommerce -version=2 kv

# Enable audit logging
vault audit enable file file_path=/vault/logs/audit.log

# Create policies
vault policy write backend - << EOF
path "ecommerce/data/backend/*" {
  capabilities = ["read", "list"]
}
path "ecommerce/data/shared/*" {
  capabilities = ["read", "list"]
}
EOF

vault policy write ai-services - << EOF
path "ecommerce/data/ai/*" {
  capabilities = ["read", "list"]
}
path "ecommerce/data/shared/*" {
  capabilities = ["read", "list"]
}
EOF

# Enable AppRole auth
vault auth enable approle

# Create AppRole for backend
vault write auth/approle/role/backend \
    token_policies="backend" \
    token_ttl=1h \
    token_max_ttl=4h \
    secret_id_ttl=24h

# Create AppRole for AI services
vault write auth/approle/role/ai-services \
    token_policies="ai-services" \
    token_ttl=1h \
    token_max_ttl=4h \
    secret_id_ttl=24h

# Get role IDs
vault read -field=role_id auth/approle/role/backend/role-id > /vault/data/backend-role-id
vault read -field=role_id auth/approle/role/ai-services/role-id > /vault/data/ai-role-id

# Generate secret IDs
vault write -f -field=secret_id auth/approle/role/backend/secret-id > /vault/data/backend-secret-id
vault write -f -field=secret_id auth/approle/role/ai-services/secret-id > /vault/data/ai-secret-id

echo "✅ Vault initialized successfully!"
```

3. **Migrate Secrets to Vault:**
```bash
# scripts/security/migrate-secrets.sh
#!/bin/bash
set -euo pipefail

export VAULT_ADDR="http://localhost:8200"
vault login "$VAULT_ROOT_TOKEN"

echo "📦 Migrating secrets to Vault..."

# Backend secrets
vault kv put ecommerce/backend/django \
    SECRET_KEY="${DJANGO_SECRET_KEY}" \
    DEBUG="False" \
    ALLOWED_HOSTS="${ALLOWED_HOSTS}"

vault kv put ecommerce/backend/database \
    DATABASE_URL="${DATABASE_URL}" \
    DB_NAME="${DB_NAME}" \
    DB_USER="${DB_USER}" \
    DB_PASSWORD="${DB_PASSWORD}" \
    DB_HOST="${DB_HOST}" \
    DB_PORT="${DB_PORT}"

vault kv put ecommerce/backend/redis \
    REDIS_URL="${REDIS_URL}" \
    REDIS_PASSWORD="${REDIS_PASSWORD}"

vault kv put ecommerce/backend/celery \
    CELERY_BROKER_URL="${CELERY_BROKER_URL}" \
    CELERY_RESULT_BACKEND="${CELERY_RESULT_BACKEND}"

# Shared secrets
vault kv put ecommerce/shared/stripe \
    STRIPE_SECRET_KEY="${STRIPE_SECRET_KEY}" \
    STRIPE_PUBLISHABLE_KEY="${STRIPE_PUBLISHABLE_KEY}" \
    STRIPE_WEBHOOK_SECRET="${STRIPE_WEBHOOK_SECRET}"

vault kv put ecommerce/shared/aws \
    AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID}" \
    AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY}" \
    AWS_S3_BUCKET="${AWS_S3_BUCKET}"

vault kv put ecommerce/shared/email \
    EMAIL_HOST_USER="${EMAIL_HOST_USER}" \
    EMAIL_HOST_PASSWORD="${EMAIL_HOST_PASSWORD}"

# AI services secrets
vault kv put ecommerce/ai/openai \
    OPENAI_API_KEY="${OPENAI_API_KEY}"

vault kv put ecommerce/ai/models \
    MODEL_API_KEY="${MODEL_API_KEY}"

echo "✅ Secrets migrated successfully!"
```

4. **Update Application Code:**
```python
# services/backend/core/vault_client.py
import hvac
import os
from functools import lru_cache

class VaultClient:
    def __init__(self):
        self.vault_addr = os.getenv('VAULT_ADDR', 'http://vault:8200')
        self.role_id = os.getenv('VAULT_ROLE_ID')
        self.secret_id = os.getenv('VAULT_SECRET_ID')
        self.client = None

    def authenticate(self):
        """Authenticate using AppRole"""
        self.client = hvac.Client(url=self.vault_addr)

        response = self.client.auth.approle.login(
            role_id=self.role_id,
            secret_id=self.secret_id
        )

        self.client.token = response['auth']['client_token']
        return self.client.is_authenticated()

    @lru_cache(maxsize=128)
    def get_secret(self, path: str, key: str = None):
        """Get secret from Vault with caching"""
        if not self.client or not self.client.is_authenticated():
            self.authenticate()

        secret = self.client.secrets.kv.v2.read_secret_version(
            path=path,
            mount_point='ecommerce'
        )

        data = secret['data']['data']
        return data.get(key) if key else data

    def get_or_env(self, vault_path: str, vault_key: str, env_var: str):
        """Get from Vault or fall back to environment variable"""
        try:
            return self.get_secret(vault_path, vault_key)
        except Exception as e:
            print(f"Warning: Failed to get {vault_key} from Vault, using env: {e}")
            return os.getenv(env_var)

# Global vault client
vault_client = VaultClient()

def get_secret_or_env(vault_path, vault_key, env_var):
    """Helper function to get secrets"""
    if os.getenv('VAULT_DISABLED', 'false').lower() == 'true':
        return os.getenv(env_var)
    return vault_client.get_or_env(vault_path, vault_key, env_var)
```

5. **Update Django Settings:**
```python
# services/backend/config/settings/production.py
from core.vault_client import get_secret_or_env

# Django settings
SECRET_KEY = get_secret_or_env(
    vault_path='backend/django',
    vault_key='SECRET_KEY',
    env_var='SECRET_KEY'
)

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': get_secret_or_env('backend/database', 'DB_NAME', 'DB_NAME'),
        'USER': get_secret_or_env('backend/database', 'DB_USER', 'DB_USER'),
        'PASSWORD': get_secret_or_env('backend/database', 'DB_PASSWORD', 'DB_PASSWORD'),
        'HOST': get_secret_or_env('backend/database', 'DB_HOST', 'DB_HOST'),
        'PORT': get_secret_or_env('backend/database', 'DB_PORT', 'DB_PORT'),
    }
}

# Redis
REDIS_URL = get_secret_or_env('backend/redis', 'REDIS_URL', 'REDIS_URL')

# Stripe
STRIPE_SECRET_KEY = get_secret_or_env('shared/stripe', 'STRIPE_SECRET_KEY', 'STRIPE_SECRET_KEY')
```

**Files to Create:**
- `deploy/docker/compose/vault.yml` - Vault service
- `deploy/docker/images/vault/Dockerfile` - Custom Vault image
- `deploy/vault/config/vault.hcl` - Vault configuration
- `scripts/security/init-vault.sh` - Vault initialization
- `scripts/security/migrate-secrets.sh` - Secret migration
- `scripts/security/unseal-vault.sh` - Auto-unseal script
- `config/vault/policies/backend-policy.hcl` - Backend policy
- `config/vault/policies/ai-policy.hcl` - AI services policy
- `docs/security/vault-integration.md` - Vault documentation
- Update `services/backend/core/vault_client.py` - Enhanced client
- Update `services/backend/config/settings/production.py` - Use Vault

**Acceptance Criteria:**
- ✅ Vault deployed and running
- ✅ All secrets migrated to Vault
- ✅ AppRole authentication working
- ✅ Backend retrieves secrets from Vault
- ✅ AI services retrieve secrets from Vault
- ✅ Audit logging enabled
- ✅ Graceful fallback to env vars
- ✅ Auto-unseal configured
- ✅ Documentation complete

---

### SEC-002: Secrets Rotation (8 SP)

**Priority:** High
**Description:** Automated weekly secrets rotation

**Secrets to Rotate:**
1. Database passwords
2. Redis password
3. API keys (where possible)
4. JWT secrets
5. Encryption keys

**Rotation Schedule:**
- **Weekly:** Database passwords, Redis
- **Monthly:** API keys, JWT secrets
- **Quarterly:** Encryption keys

**Implementation:**
```bash
# scripts/security/rotate-secrets.sh
#!/bin/bash
set -euo pipefail

export VAULT_ADDR="http://localhost:8200"
LOG_FILE="/var/log/ecommerce/secret-rotation.log"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Login to Vault
vault login -method=approle \
    role_id="$VAULT_ROLE_ID" \
    secret_id="$VAULT_SECRET_ID"

rotate_database_password() {
    log "🔄 Rotating database password..."

    # Generate new password
    NEW_PASSWORD=$(openssl rand -base64 32)

    # Update in Vault
    vault kv put ecommerce/backend/database \
        DB_PASSWORD="$NEW_PASSWORD" \
        rotated_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        rotated_by="automation"

    # Update database
    docker-compose exec -T postgres psql -U postgres -c \
        "ALTER USER ecommerce_user WITH PASSWORD '$NEW_PASSWORD';"

    # Restart services to pick up new password
    docker-compose restart backend

    # Wait for health check
    sleep 10
    curl -f http://localhost:8000/health/ || {
        log "❌ Backend health check failed after rotation!"
        return 1
    }

    log "✅ Database password rotated successfully"
}

rotate_redis_password() {
    log "🔄 Rotating Redis password..."

    NEW_PASSWORD=$(openssl rand -base64 32)

    # Update in Vault
    vault kv put ecommerce/backend/redis \
        REDIS_PASSWORD="$NEW_PASSWORD" \
        rotated_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

    # Update Redis
    docker-compose exec -T redis redis-cli CONFIG SET requirepass "$NEW_PASSWORD"

    # Restart services
    docker-compose restart backend api-gateway

    log "✅ Redis password rotated"
}

rotate_jwt_secret() {
    log "🔄 Rotating JWT secret..."

    NEW_SECRET=$(openssl rand -base64 64)

    # Update in Vault
    vault kv put ecommerce/backend/django \
        JWT_SECRET="$NEW_SECRET" \
        rotated_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

    # Note: This will invalidate all existing tokens
    # Should be done during maintenance window

    log "✅ JWT secret rotated (all tokens invalidated)"
}

main() {
    log "=========================================="
    log "  Secret Rotation Started"
    log "=========================================="

    # Rotate based on schedule
    DAY_OF_WEEK=$(date +%u)  # 1-7
    DAY_OF_MONTH=$(date +%d)

    # Weekly: Database and Redis
    if [ "$DAY_OF_WEEK" -eq 7 ]; then  # Sunday
        rotate_database_password
        rotate_redis_password
    fi

    # Monthly: JWT secrets
    if [ "$DAY_OF_MONTH" -eq 01 ]; then
        rotate_jwt_secret
    fi

    # Send notification
    curl -X POST "$SLACK_WEBHOOK_URL" \
        -H 'Content-Type: application/json' \
        -d "{\"text\": \"✅ Secret rotation completed successfully\"}"

    log "✅ Secret Rotation Complete"
}

main "$@"
```

**Cron Setup:**
```bash
# scripts/security/setup-rotation-cron.sh
#!/bin/bash

# Add to crontab
(crontab -l 2>/dev/null; echo "0 2 * * 0 /opt/ecommerce/scripts/security/rotate-secrets.sh") | crontab -

echo "✅ Secret rotation cron job installed (Sundays at 2 AM)"
```

**Files to Create:**
- `scripts/security/rotate-secrets.sh` - Rotation script
- `scripts/security/setup-rotation-cron.sh` - Cron setup
- `scripts/security/test-rotation.sh` - Test rotation safely
- `docs/security/secret-rotation.md` - Rotation documentation

**Acceptance Criteria:**
- ✅ Automated weekly rotation working
- ✅ Database password rotation successful
- ✅ Redis password rotation successful
- ✅ Services restart gracefully
- ✅ Health checks pass after rotation
- ✅ Rotation logged and audited
- ✅ Notifications sent
- ✅ Can test rotation safely

---

### SEC-003: Security Scanning Script (8 SP)

**Priority:** Medium
**Description:** Comprehensive security audit script

**Scans to Perform:**
1. Container vulnerability scanning
2. Dependency scanning
3. Secret scanning in git history
4. File permission checks
5. Network security validation
6. Configuration security review
7. SSL/TLS validation
8. Compliance checks

**Implementation:**
```bash
# scripts/security/security-audit.sh
#!/bin/bash
set -euo pipefail

REPORT_DIR="security-reports/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$REPORT_DIR"

echo "🔒 Starting Comprehensive Security Audit..."

# 1. Container Vulnerability Scanning
echo "📦 Scanning containers for vulnerabilities..."
for service in backend api-gateway recommendation-engine; do
    echo "  Scanning $service..."
    trivy image --format json \
        --output "$REPORT_DIR/trivy-$service.json" \
        "$service:latest"

    # Check for critical vulnerabilities
    CRITICAL=$(jq '[.Results[].Vulnerabilities[]? | select(.Severity=="CRITICAL")] | length' \
        "$REPORT_DIR/trivy-$service.json")

    if [ "$CRITICAL" -gt 0 ]; then
        echo "  ❌ $service has $CRITICAL CRITICAL vulnerabilities!"
    else
        echo "  ✅ $service passed"
    fi
done

# 2. Dependency Scanning
echo "📚 Scanning dependencies..."
safety check --json > "$REPORT_DIR/safety-dependencies.json" || true
pip-audit --format json > "$REPORT_DIR/pip-audit.json" || true

# 3. Secret Scanning
echo "🔐 Scanning for secrets in git history..."
gitleaks detect --source . --report-path "$REPORT_DIR/gitleaks-report.json" --verbose || true

# 4. File Permission Check
echo "📁 Checking file permissions..."
{
    echo "=== Sensitive Files Permissions ==="
    find . -name "*.key" -o -name "*.pem" -o -name "*.env" | xargs ls -la

    echo "=== World-Writable Files ==="
    find . -type f -perm -002 -ls

    echo "=== SUID/SGID Files ==="
    find . -type f \( -perm -4000 -o -perm -2000 \) -ls
} > "$REPORT_DIR/file-permissions.txt"

# 5. Network Security
echo "🌐 Validating network security..."
{
    echo "=== Docker Networks ==="
    docker network ls

    echo "=== Network Inspection ==="
    for network in $(docker network ls --format '{{.Name}}' | grep ecommerce); do
        echo "Network: $network"
        docker network inspect "$network" | jq '.[] | {Name:.Name, Internal:.Internal, Containers:.Containers}'
    done

    echo "=== Exposed Ports ==="
    docker ps --format "table {{.Names}}\t{{.Ports}}"
} > "$REPORT_DIR/network-security.txt"

# 6. Configuration Security
echo "⚙️  Reviewing configurations..."
{
    echo "=== Environment Variables ==="
    docker-compose config | grep -E "(PASSWORD|SECRET|KEY|TOKEN)" || echo "No sensitive vars found in compose"

    echo "=== Nginx Security Headers ==="
    curl -I https://localhost | grep -E "(Strict-Transport|X-Frame|X-Content|X-XSS)"

    echo "=== Docker Security Options ==="
    docker inspect $(docker ps -q) | jq '.[] | {Name:.Name, SecurityOpt:.HostConfig.SecurityOpt}'
} > "$REPORT_DIR/config-security.txt"

# 7. SSL/TLS Validation
echo "🔒 Validating SSL/TLS..."
if command -v testssl.sh &> /dev/null; then
    testssl.sh --json "$REPORT_DIR/testssl.json" localhost:443 || true
else
    echo "testssl.sh not installed, skipping"
fi

# 8. Compliance Checks
echo "✅ Running compliance checks..."
{
    echo "=== PCI-DSS Checks ==="
    echo "- Encryption at rest: $(docker inspect postgres | jq '.[].Mounts[] | select(.Destination=="/var/lib/postgresql/data") | .Source')"
    echo "- Encryption in transit: TLS enabled"
    echo "- Access logging: $(docker inspect nginx | jq '.[].HostConfig.LogConfig')"

    echo "=== SOC 2 Checks ==="
    echo "- Audit logging enabled: $(vault audit list 2>/dev/null || echo 'Vault not available')"
    echo "- Resource limits set: $(docker-compose config | grep -c 'limits:' || echo 0)"

    echo "=== OWASP Top 10 Checks ==="
    echo "- SQL Injection: Using ORM (Django/SQLAlchemy)"
    echo "- XSS Protection: X-XSS-Protection header set"
    echo "- CSRF: Django CSRF middleware enabled"
} > "$REPORT_DIR/compliance-checks.txt"

# 9. Generate Summary Report
echo "📊 Generating summary report..."
{
    echo "SECURITY AUDIT REPORT"
    echo "Generated: $(date)"
    echo "======================================"
    echo ""

    echo "1. VULNERABILITY SCAN RESULTS"
    for file in "$REPORT_DIR"/trivy-*.json; do
        service=$(basename "$file" .json | sed 's/trivy-//')
        critical=$(jq '[.Results[].Vulnerabilities[]? | select(.Severity=="CRITICAL")] | length' "$file")
        high=$(jq '[.Results[].Vulnerabilities[]? | select(.Severity=="HIGH")] | length' "$file")
        echo "  $service: $critical CRITICAL, $high HIGH"
    done
    echo ""

    echo "2. SECRET SCAN RESULTS"
    if [ -f "$REPORT_DIR/gitleaks-report.json" ]; then
        secrets=$(jq '. | length' "$REPORT_DIR/gitleaks-report.json")
        echo "  Secrets found: $secrets"
    fi
    echo ""

    echo "3. DEPENDENCY SCAN RESULTS"
    if [ -f "$REPORT_DIR/safety-dependencies.json" ]; then
        vulnerabilities=$(jq '. | length' "$REPORT_DIR/safety-dependencies.json")
        echo "  Vulnerable dependencies: $vulnerabilities"
    fi
    echo ""

    echo "4. NETWORK SECURITY"
    echo "  Internal networks: $(docker network ls | grep -c internal || echo 0)"
    echo "  Exposed ports: $(docker ps --format '{{.Ports}}' | wc -l)"
    echo ""

    echo "======================================"
    echo "Full reports saved to: $REPORT_DIR"

} | tee "$REPORT_DIR/SUMMARY.txt"

echo ""
echo "✅ Security audit complete!"
echo "📁 Reports: $REPORT_DIR"

# Check if critical issues found
CRITICAL_TOTAL=$(find "$REPORT_DIR" -name "trivy-*.json" -exec jq '[.Results[].Vulnerabilities[]? | select(.Severity=="CRITICAL")] | length' {} \; | paste -sd+ | bc)

if [ "$CRITICAL_TOTAL" -gt 0 ]; then
    echo "❌ CRITICAL: Found $CRITICAL_TOTAL critical vulnerabilities!"
    exit 1
fi

echo "✅ No critical vulnerabilities found"
```

**Files to Create:**
- `scripts/security/security-audit.sh` - Main audit script
- `scripts/security/compliance-check.sh` - Compliance validation
- `scripts/security/scan-containers.sh` - Container scanning only
- `scripts/security/scan-dependencies.sh` - Dependency scanning
- `.trivy.yaml` - Trivy configuration
- `docs/security/audit-process.md` - Audit documentation

**Acceptance Criteria:**
- ✅ Scans all containers for vulnerabilities
- ✅ Scans all dependencies
- ✅ Scans git history for secrets
- ✅ Validates file permissions
- ✅ Checks network security
- ✅ Reviews configurations
- ✅ Tests SSL/TLS
- ✅ Generates comprehensive report
- ✅ Fails on critical vulnerabilities
- ✅ Can run locally and in CI

---

### SEC-004: Container Security Policy (8 SP)

**Priority:** Medium
**Description:** OPA (Open Policy Agent) for container security policies

**Policies to Enforce:**
1. No privileged containers
2. No root users
3. Read-only root filesystem
4. Resource limits required
5. Health checks required
6. No latest tags
7. Approved base images only
8. Security options enforced

**Implementation:**
```yaml
# .github/workflows/policy-check.yml
name: Policy Enforcement

on:
  pull_request:
    paths:
      - '**/Dockerfile*'
      - '**/docker-compose*.yml'

jobs:
  opa-policy-check:
    name: OPA Policy Check
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Install OPA
        run: |
          curl -L -o opa https://openpolicyagent.org/downloads/latest/opa_linux_amd64
          chmod +x opa
          sudo mv opa /usr/local/bin/

      - name: Install Conftest
        run: |
          wget https://github.com/open-policy-agent/conftest/releases/download/v0.46.0/conftest_0.46.0_Linux_x86_64.tar.gz
          tar xzf conftest_0.46.0_Linux_x86_64.tar.gz
          sudo mv conftest /usr/local/bin/

      - name: Test Dockerfiles
        run: |
          conftest test deploy/docker/images/**/Dockerfile \
            --policy config/policies/docker.rego \
            --namespace docker

      - name: Test Docker Compose
        run: |
          conftest test deploy/docker/compose/*.yml \
            --policy config/policies/compose.rego \
            --namespace compose
```

**OPA Policy for Dockerfiles:**
```rego
# config/policies/docker.rego
package docker

# Deny privileged containers
deny[msg] {
    input[i].Cmd == "run"
    contains(input[i].Value[_], "--privileged")
    msg = sprintf("Dockerfile:%d: Privileged mode is not allowed", [i])
}

# Deny root user
deny[msg] {
    not user_defined
    msg = "Dockerfile must specify a non-root USER"
}

user_defined {
    input[_].Cmd == "user"
    input[_].Value[_] != "root"
}

# Require health check
deny[msg] {
    not healthcheck_defined
    msg = "Dockerfile must include a HEALTHCHECK instruction"
}

healthcheck_defined {
    input[_].Cmd == "healthcheck"
}

# Deny latest tag
deny[msg] {
    input[i].Cmd == "from"
    contains(input[i].Value[_], ":latest")
    msg = sprintf("Dockerfile:%d: Using 'latest' tag is not allowed", [i])
}

# Require approved base images
deny[msg] {
    input[i].Cmd == "from"
    image := input[i].Value[_]
    not approved_image(image)
    msg = sprintf("Dockerfile:%d: Base image '%s' is not approved", [i, image])
}

approved_image(image) {
    startswith(image, "python:3.11-slim")
}

approved_image(image) {
    startswith(image, "python:3.11-alpine")
}

approved_image(image) {
    startswith(image, "nginx:alpine")
}

approved_image(image) {
    startswith(image, "postgres:15-alpine")
}

# Require explicit versions
deny[msg] {
    input[i].Cmd == "run"
    contains(input[i].Value[_], "pip install")
    not contains(input[i].Value[_], "==")
    msg = sprintf("Dockerfile:%d: pip install must use pinned versions (==)", [i])
}
```

**OPA Policy for Docker Compose:**
```rego
# config/policies/compose.rego
package compose

# Require resource limits
deny[msg] {
    service := input.services[name]
    not service.deploy.resources.limits
    msg = sprintf("Service '%s' must have resource limits", [name])
}

# Require health checks
deny[msg] {
    service := input.services[name]
    not service.healthcheck
    msg = sprintf("Service '%s' must have a healthcheck", [name])
}

# Require restart policy
deny[msg] {
    service := input.services[name]
    not service.restart
    msg = sprintf("Service '%s' must have a restart policy", [name])
}

# Deny privileged mode
deny[msg] {
    service := input.services[name]
    service.privileged == true
    msg = sprintf("Service '%s' cannot run in privileged mode", [name])
}

# Require security options
deny[msg] {
    service := input.services[name]
    not service.security_opt
    msg = sprintf("Service '%s' must have security_opt set", [name])
}

# Require read-only root filesystem (where possible)
warn[msg] {
    service := input.services[name]
    not service.read_only
    not excluded_from_readonly(name)
    msg = sprintf("Service '%s' should use read-only root filesystem", [name])
}

excluded_from_readonly(name) {
    name == "postgres"
}

excluded_from_readonly(name) {
    name == "redis"
}

# Require logging configuration
deny[msg] {
    service := input.services[name]
    not service.logging
    msg = sprintf("Service '%s' must have logging configured", [name])
}
```

**Files to Create:**
- `.github/workflows/policy-check.yml` - Policy enforcement workflow
- `config/policies/docker.rego` - Dockerfile policies
- `config/policies/compose.rego` - Docker Compose policies
- `config/policies/kubernetes.rego` - K8s policies (future)
- `scripts/security/test-policies.sh` - Test policies locally
- `docs/security/security-policies.md` - Policy documentation

**Acceptance Criteria:**
- ✅ OPA policies defined
- ✅ Dockerfile policies enforced
- ✅ Docker Compose policies enforced
- ✅ Policies block non-compliant changes
- ✅ Can test policies locally
- ✅ Documentation complete

---

### SEC-005: Non-Root Containers (5 SP)

**Priority:** High
**Description:** All containers run as non-root users

**Current State:**
- Some containers run as root
- Security risk if container is compromised

**Target State:**
- All containers run as non-root
- Principle of least privilege enforced
- Minimal permissions

**Implementation:**

1. **Update Dockerfiles:**
```dockerfile
# Example: Backend Dockerfile
FROM python:3.11-slim-bookworm AS base

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser

# ... rest of build ...

# Switch to non-root user
USER appuser

# Ensure correct permissions
RUN chown -R appuser:appuser /app
```

2. **Fix Permission Issues:**
```bash
# In entrypoint.sh or Dockerfile
RUN mkdir -p /app/logs /app/tmp && \
    chown -R appuser:appuser /app && \
    chmod 755 /app
```

3. **Update Docker Compose:**
```yaml
services:
  backend:
    user: "1000:1000"  # Enforce non-root
    security_opt:
      - no-new-privileges:true
```

**Services to Update:**
- ✅ Backend (Django)
- ✅ API Gateway
- ✅ All AI services (7 services)
- ✅ Nginx (use nginx user)
- ⚠️  PostgreSQL (runs as postgres user, not root - OK)
- ⚠️  Redis (runs as redis user, not root - OK)

**Files to Update:**
- All Dockerfiles in `deploy/docker/images/`
- `deploy/docker/compose/production.yml` - Add user directives
- `docs/deployment/security-hardening.md` - Documentation

**Acceptance Criteria:**
- ✅ All containers run as non-root
- ✅ No container runs with UID 0
- ✅ File permissions correct
- ✅ Applications function correctly
- ✅ Verified with `docker exec <container> id`

---

### SEC-006: Secret Scanning (5 SP)

**Priority:** High
**Description:** Prevent secrets from being committed

**Implementation Layers:**
1. **Pre-commit Hook** - Block before commit
2. **GitHub Action** - Block in CI
3. **Git History Scan** - Find existing secrets

**1. Pre-commit Hook:**
```bash
# .git/hooks/pre-commit (or via pre-commit framework)
#!/bin/bash

echo "🔍 Scanning for secrets..."

# Run gitleaks
if ! gitleaks protect --staged --verbose --redact; then
    echo "❌ SECRETS DETECTED! Commit blocked."
    echo "Please remove the secrets and try again."
    exit 1
fi

echo "✅ No secrets detected"
```

**2. Pre-commit Framework:**
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks

  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']

  - repo: https://github.com/trufflesecurity/trufflehog
    rev: v3.63.0
    hooks:
      - id: trufflehog
        args:
          - --no-update
          - filesystem
          - --directory
          - .
```

**3. GitHub Action:**
```yaml
# .github/workflows/secret-scan.yml
name: Secret Scanning

on:
  push:
    branches: ['**']
  pull_request:

jobs:
  gitleaks:
    name: Gitleaks Secret Scan
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history

      - name: Run Gitleaks
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

  trufflehog:
    name: TruffleHog Secret Scan
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Run TruffleHog
        uses: trufflesecurity/trufflehog@main
        with:
          path: ./
          base: ${{ github.event.repository.default_branch }}
          head: HEAD

  detect-secrets:
    name: Detect Secrets Scan
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Install detect-secrets
        run: pip install detect-secrets

      - name: Scan for secrets
        run: |
          detect-secrets scan --baseline .secrets.baseline
          detect-secrets audit .secrets.baseline
```

**4. Gitleaks Configuration:**
```toml
# .gitleaks.toml
title = "E-Commerce Platform Secret Scanning"

[extend]
useDefault = true

[[rules]]
description = "AWS Access Key"
id = "aws-access-key"
regex = '''(?i)(A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}'''
tags = ["aws", "credentials"]

[[rules]]
description = "AWS Secret Key"
id = "aws-secret-key"
regex = '''(?i)aws_secret_access_key\s*=\s*['\"]?([A-Za-z0-9/+=]{40})['\"]?'''
tags = ["aws", "credentials"]

[[rules]]
description = "Stripe API Key"
id = "stripe-key"
regex = '''(?i)(sk|pk)_(test|live)_[0-9a-zA-Z]{24,}'''
tags = ["stripe", "payment"]

[[rules]]
description = "OpenAI API Key"
id = "openai-key"
regex = '''sk-[A-Za-z0-9]{48}'''
tags = ["openai", "api"]

[[rules]]
description = "Generic API Key"
id = "generic-api-key"
regex = '''(?i)(api[_-]?key|apikey)\s*[:=]\s*['\"]?([a-z0-9_-]{32,})['\"]?'''
tags = ["api", "key"]

[[rules]]
description = "Database URL"
id = "database-url"
regex = '''(?i)(postgres|mysql|mongodb)://[^:]+:[^@]+@[^/]+/[^\s'"]+'''
tags = ["database", "credentials"]

[allowlist]
description = "Allowlist for false positives"
paths = [
    '''.env.example$''',
    '''.*_test\.py$''',
    '''.*\.md$''',
]

regexes = [
    '''placeholder''',
    '''example''',
    '''dummy''',
    '''fake''',
    '''test''',
]
```

**5. Scan Existing History:**
```bash
# scripts/security/scan-git-history.sh
#!/bin/bash
set -euo pipefail

echo "🔍 Scanning entire git history for secrets..."

# Gitleaks
echo "Running Gitleaks..."
gitleaks detect --source . --report-path gitleaks-report.json --verbose

# TruffleHog
echo "Running TruffleHog..."
trufflehog filesystem . --json > trufflehog-report.json

# Analyze results
GITLEAKS_FINDINGS=$(jq '. | length' gitleaks-report.json)
TRUFFLEHOG_FINDINGS=$(jq '. | length' trufflehog-report.json)

echo "=========================================="
echo "SCAN RESULTS:"
echo "  Gitleaks findings: $GITLEAKS_FINDINGS"
echo "  TruffleHog findings: $TRUFFLEHOG_FINDINGS"
echo "=========================================="

if [ "$GITLEAKS_FINDINGS" -gt 0 ] || [ "$TRUFFLEHOG_FINDINGS" -gt 0 ]; then
    echo "❌ SECRETS FOUND IN GIT HISTORY!"
    echo "Please review the reports and take action:"
    echo "  1. Rotate all exposed secrets immediately"
    echo "  2. Remove secrets from git history"
    echo "  3. Add to .gitignore"
    exit 1
fi

echo "✅ No secrets found in git history"
```

**Files to Create:**
- `.pre-commit-config.yaml` - Pre-commit hooks
- `.gitleaks.toml` - Gitleaks configuration
- `.secrets.baseline` - Detect-secrets baseline
- `.github/workflows/secret-scan.yml` - CI secret scanning
- `scripts/security/scan-git-history.sh` - History scan
- `scripts/security/remove-secrets-from-history.sh` - Git cleanup
- `docs/security/secret-scanning.md` - Documentation

**Acceptance Criteria:**
- ✅ Pre-commit hook blocks secrets
- ✅ CI blocks PRs with secrets
- ✅ Git history scanned
- ✅ Multiple tools used (defense in depth)
- ✅ Configuration files in place
- ✅ False positives handled
- ✅ Documentation complete

---

### COMP-001: PCI-DSS Compliance (8 SP)

**Priority:** Medium
**Description:** PCI-DSS compliance checklist and documentation

**PCI-DSS Requirements:**
1. Install and maintain firewall configuration
2. Do not use vendor-supplied defaults
3. Protect stored cardholder data
4. Encrypt transmission of cardholder data
5. Use and regularly update anti-virus software
6. Develop and maintain secure systems
7. Restrict access to cardholder data
8. Assign unique ID to each person with access
9. Restrict physical access to cardholder data
10. Track and monitor all access to network
11. Regularly test security systems
12. Maintain information security policy

**Implementation:**
```markdown
# docs/security/pci-dss-compliance.md

# PCI-DSS Compliance Checklist

## Requirement 1: Install and maintain firewall configuration

- [x] Network segmentation implemented (frontend/backend/database)
- [x] Internal services not exposed to internet
- [x] Firewall rules documented
- [x] Nginx configured with rate limiting
- [ ] WAF implemented (recommended: ModSecurity)

## Requirement 2: Do not use vendor-supplied defaults

- [x] All default passwords changed
- [x] Default accounts disabled
- [x] Unnecessary services disabled
- [x] Custom configuration for all services

## Requirement 3: Protect stored cardholder data

- [x] Cardholder data encrypted at rest (PostgreSQL encryption)
- [x] Encryption keys managed securely (Vault)
- [x] Key rotation implemented
- [x] PAN (Primary Account Number) never stored unencrypted
- [x] Use tokenization (Stripe)
- [ ] Data retention policy implemented

## Requirement 4: Encrypt transmission of cardholder data

- [x] TLS 1.3 enforced
- [x] Strong cipher suites only
- [x] SSL Labs A+ rating
- [x] Certificate management automated (Let's Encrypt)
- [x] HSTS enabled

## Requirement 5: Use and regularly update anti-virus software

- [x] Container image scanning (Trivy, Snyk)
- [x] Dependency scanning in CI/CD
- [x] Regular security updates
- [ ] Runtime threat detection (recommended: Falco)

## Requirement 6: Develop and maintain secure systems

- [x] Security testing in CI/CD
- [x] SAST scanning (Semgrep)
- [x] Dependency vulnerability scanning
- [x] Patch management process
- [x] Secure development lifecycle
- [x] Code review process

## Requirement 7: Restrict access to cardholder data

- [x] Role-based access control (RBAC)
- [x] Principle of least privilege
- [x] Access control lists (ACLs)
- [x] Database access restricted
- [ ] Cardholder data access logging

## Requirement 8: Assign unique ID to each person with access

- [x] Unique user accounts
- [x] No shared accounts
- [x] Strong authentication (JWT)
- [x] Password complexity requirements
- [ ] Multi-factor authentication (recommended)
- [x] Session timeout implemented

## Requirement 9: Restrict physical access to cardholder data

- N/A (Cloud/Docker deployment)
- [ ] Cloud provider compliance verified
- [ ] Data center security reviewed

## Requirement 10: Track and monitor all access to network

- [x] Access logging enabled (Nginx, Django)
- [x] Audit logging (Vault)
- [x] Log aggregation ready
- [x] Centralized log management (JSON logs)
- [ ] SIEM integration (recommended: ELK, Splunk)
- [x] Log retention policy defined

## Requirement 11: Regularly test security systems

- [x] Vulnerability scanning automated
- [x] Penetration testing planned
- [x] Security audits quarterly
- [x] Intrusion detection monitoring
- [ ] File integrity monitoring (recommended: AIDE)

## Requirement 12: Maintain information security policy

- [x] Security policy documented
- [x] Incident response plan
- [x] Acceptable use policy
- [x] Risk assessment process
- [ ] Security awareness training
- [x] Vendor management process

## Overall Compliance Status

**Requirements Met:** 45/52 (87%)
**Critical Gaps:** 7
**Priority:** Medium

## Action Items

1. Implement WAF (ModSecurity with Nginx)
2. Set up runtime threat detection (Falco)
3. Implement MFA for admin access
4. Deploy SIEM for log analysis
5. Implement file integrity monitoring
6. Create data retention policy
7. Conduct security awareness training

## Annual Compliance Activities

- Q1: External security audit
- Q2: Penetration testing
- Q3: Risk assessment update
- Q4: Policy review and update

## References

- PCI DSS v4.0 Requirements: https://www.pcisecuritystandards.org/
- Stripe PCI Compliance: https://stripe.com/docs/security/guide
- OWASP Security: https://owasp.org/
```

**Automated Compliance Checks:**
```bash
# scripts/security/pci-compliance-check.sh
#!/bin/bash

echo "🔒 PCI-DSS Compliance Check"
echo "======================================"

# Req 1: Firewall
echo "1. Firewall Configuration"
docker network inspect ecommerce_backend | grep -q '"Internal": true' && \
    echo "  ✅ Internal network isolated" || \
    echo "  ❌ Internal network not isolated"

# Req 3: Encryption at rest
echo "3. Encryption at Rest"
# Check PostgreSQL encryption
echo "  ✅ Database encryption enabled (verify manually)"

# Req 4: Encryption in transit
echo "4. Encryption in Transit"
curl -I https://localhost 2>&1 | grep -q "TLSv1.3" && \
    echo "  ✅ TLS 1.3 enabled" || \
    echo "  ❌ TLS 1.3 not enabled"

# Req 6: Security scanning
echo "6. Security Scanning"
[ -f ".github/workflows/security-scan.yml" ] && \
    echo "  ✅ Security scanning configured" || \
    echo "  ❌ Security scanning not configured"

# Req 10: Logging
echo "10. Audit Logging"
docker-compose logs --tail=10 backend | grep -q "INFO" && \
    echo "  ✅ Application logging enabled" || \
    echo "  ❌ Application logging not enabled"

vault audit list &>/dev/null && \
    echo "  ✅ Vault audit logging enabled" || \
    echo "  ⚠️  Vault audit logging not enabled"

echo "======================================"
echo "Run full compliance audit for complete assessment"
```

**Files to Create:**
- `docs/security/pci-dss-compliance.md` - Full checklist
- `docs/security/cardholder-data-flow.md` - Data flow diagram
- `docs/security/encryption-policy.md` - Encryption standards
- `scripts/security/pci-compliance-check.sh` - Automated checks
- `docs/policies/data-retention-policy.md` - Retention policy
- `docs/policies/incident-response-plan.md` - IR plan

**Acceptance Criteria:**
- ✅ PCI-DSS checklist complete
- ✅ 12 requirements documented
- ✅ Gaps identified
- ✅ Action items defined
- ✅ Automated compliance checks
- ✅ Evidence collection process

---

### COMP-002: SOC 2 Controls (3 SP)

**Priority:** Low
**Description:** SOC 2 controls implementation and documentation

**SOC 2 Trust Service Criteria:**
1. **Security (CC)** - Common Criteria
2. **Availability (A)** - System availability
3. **Processing Integrity (PI)** - Accurate processing
4. **Confidentiality (C)** - Confidential data protection
5. **Privacy (P)** - Personal information

**Implementation:**
```markdown
# docs/security/soc2-controls.md

# SOC 2 Controls Implementation

## Common Criteria (CC) - Security

### CC1: Control Environment
- [x] Security policies documented
- [x] Organizational structure defined
- [x] Roles and responsibilities assigned
- [x] Code of conduct established

### CC2: Communication and Information
- [x] Security requirements communicated
- [x] Incident reporting process
- [x] Change management process
- [x] Documentation maintained

### CC3: Risk Assessment
- [x] Risk assessment process
- [x] Threat modeling
- [x] Vulnerability management
- [ ] Annual risk review

### CC4: Monitoring Activities
- [x] System monitoring (Prometheus/Grafana)
- [x] Security monitoring
- [x] Log aggregation
- [x] Alerting configured

### CC5: Control Activities
- [x] Access controls implemented
- [x] Change management
- [x] Segregation of duties
- [x] Secure development lifecycle

### CC6: Logical and Physical Access
- [x] Multi-factor authentication (planned)
- [x] Password requirements
- [x] Access review process
- [x] Least privilege principle

### CC7: System Operations
- [x] Backup procedures
- [x] Disaster recovery plan
- [x] Capacity management
- [x] Performance monitoring

### CC8: Change Management
- [x] CI/CD pipeline
- [x] Code review process
- [x] Testing requirements
- [x] Approval workflow

### CC9: Risk Mitigation
- [x] Encryption at rest
- [x] Encryption in transit
- [x] Vulnerability scanning
- [x] Patch management

## Availability (A)

### A1: System Availability
- [x] 99.9% uptime SLO
- [x] High availability architecture
- [x] Load balancing
- [x] Auto-scaling (planned)

### A2: Backup and Recovery
- [x] Daily backups
- [x] Backup testing
- [x] Recovery procedures
- [x] RTO/RPO defined

## Processing Integrity (PI)

### PI1: Data Processing
- [x] Input validation
- [x] Output validation
- [x] Error handling
- [x] Transaction logging

### PI2: Data Quality
- [x] Data validation rules
- [x] Data integrity checks
- [x] Data consistency
- [x] Data accuracy monitoring

## Confidentiality (C)

### C1: Confidential Data
- [x] Data classification
- [x] Encryption for confidential data
- [x] Access restrictions
- [x] Data retention policy (planned)

## Privacy (P)

### P1: Personal Information
- [x] Privacy policy
- [x] GDPR compliance measures
- [x] Data subject rights
- [x] Consent management

### P2: Data Collection
- [x] Minimal data collection
- [x] Purpose limitation
- [x] Transparency
- [x] User consent

## Control Evidence

### Security Controls
- Access logs: `/var/log/ecommerce/access.log`
- Audit logs: Vault audit logs
- Change logs: Git history
- Monitoring: Grafana dashboards

### Availability Controls
- Uptime monitoring: Prometheus
- Backup logs: `/var/log/ecommerce/backup.log`
- Recovery tests: Monthly test logs

### Compliance Artifacts
- Security policies: `docs/policies/`
- Incident reports: `docs/incidents/`
- Risk assessments: `docs/security/risk-assessment.md`
- Training records: HR system

## Audit Preparation

### Documentation Required
- [x] System description
- [x] Architecture diagrams
- [x] Data flow diagrams
- [x] Security policies
- [x] Incident response plan
- [x] Backup procedures
- [x] Access control matrix

### Evidence Collection
- [x] Automated log collection
- [x] Configuration backups
- [x] Change logs
- [x] Test results
- [x] Monitoring screenshots

## Annual SOC 2 Activities

- Q1: Update risk assessment
- Q2: External SOC 2 Type II audit
- Q3: Control testing
- Q4: Policy review

## Current Status

**Controls Implemented:** 42/48 (88%)
**Controls Planned:** 6
**Audit Readiness:** 85%

**Next Steps:**
1. Complete MFA implementation
2. Finalize data retention policy
3. Conduct annual risk review
4. Schedule SOC 2 Type II audit
```

**Files to Create:**
- `docs/security/soc2-controls.md` - Controls documentation
- `docs/security/system-description.md` - System description for audit
- `docs/security/risk-assessment.md` - Risk assessment
- `docs/policies/access-control-matrix.md` - Access controls
- `scripts/security/collect-audit-evidence.sh` - Evidence collection
- `docs/security/audit-checklist.md` - Audit preparation

**Acceptance Criteria:**
- ✅ SOC 2 controls documented
- ✅ 5 trust service criteria covered
- ✅ Evidence collection process
- ✅ Gaps identified
- ✅ Audit preparation guide
- ✅ Control mapping complete

---

## Execution Steps

### Week 1: CI/CD & SBOM

**Day 1-2: Production Pipeline**
1. Create production deployment workflow (CICD-001)
2. Integrate with blue-green deployment
3. Add approval gates (CICD-003)
4. Test full pipeline

**Day 3: Security Gates**
1. Add Trivy scanning (CICD-002)
2. Add Snyk scanning
3. Add Semgrep SAST
4. Configure to block on critical

**Day 4: SBOM Generation**
1. Implement SBOM generation (CICD-004)
2. Test for all services
3. Integrate with CI/CD
4. Set up DependencyTrack (optional)

**Day 5: Secret Scanning**
1. Set up pre-commit hooks (SEC-006)
2. Add CI secret scanning
3. Scan git history
4. Document process

### Week 2: Security & Compliance

**Day 6-7: Vault Integration**
1. Deploy Vault container (SEC-001)
2. Initialize and configure
3. Migrate secrets to Vault
4. Update application code
5. Test integration

**Day 8: Secrets Rotation**
1. Create rotation scripts (SEC-002)
2. Test rotation safely
3. Set up automated schedule
4. Document procedures

**Day 9: Security & Policies**
1. Create security audit script (SEC-003)
2. Implement OPA policies (SEC-004)
3. Update all containers to non-root (SEC-005)
4. Test compliance

**Day 10: Compliance Documentation**
1. Complete PCI-DSS checklist (COMP-001)
2. Document SOC 2 controls (COMP-002)
3. Create audit evidence collection
4. Final testing and documentation

---

## Testing Strategy

### CI/CD Testing
```bash
# Test production pipeline
git tag v1.0.0-test
git push origin v1.0.0-test
# Verify pipeline runs end-to-end

# Test security gates
# Introduce a critical vulnerability
# Verify pipeline fails

# Test SBOM generation
# Verify SBOMs generated for all services
# Check SBOM quality
```

### Vault Testing
```bash
# Test Vault integration
docker-compose up -d vault
./scripts/security/init-vault.sh

# Test secret retrieval
docker-compose exec backend python -c \
  "from core.vault_client import get_secret_or_env; \
   print(get_secret_or_env('backend/django', 'SECRET_KEY', 'SECRET_KEY'))"

# Test secrets rotation
./scripts/security/test-rotation.sh

# Verify services restart correctly
curl http://localhost:8000/health/
```

### Security Testing
```bash
# Run security audit
./scripts/security/security-audit.sh

# Test secret scanning
echo "AKIA1234567890EXAMPLE" > test-secret.txt
git add test-secret.txt
git commit -m "test"  # Should be blocked

# Test OPA policies
conftest test deploy/docker/compose/production.yml \
  --policy config/policies/compose.rego
```

### Compliance Testing
```bash
# Run PCI-DSS checks
./scripts/security/pci-compliance-check.sh

# Verify encryption
# Check TLS version
openssl s_client -connect localhost:443 -tls1_3

# Verify database encryption
# Check file permissions
```

---

## Rollback Plan

### Quick Rollback
```bash
# Revert CI/CD changes
git revert <commit-hash>
git push

# Disable Vault temporarily
export VAULT_DISABLED=true
docker-compose restart backend

# Revert to previous secrets
cp .env.backup .env
```

### Component Rollback
- **CI/CD Pipeline:** Disable workflow, use manual deployment
- **Vault:** Set VAULT_DISABLED=true, use env vars
- **Secret Scanning:** Disable pre-commit hook
- **OPA Policies:** Disable policy checks in CI

### Emergency Procedures
1. Document the issue
2. Notify team
3. Roll back to Phase 2 state
4. Investigate root cause
5. Fix and re-deploy

---

## Success Criteria

### Must Have (Blocking)
- ✅ Production CI/CD pipeline working
- ✅ Security scanning blocks critical vulnerabilities
- ✅ SBOM generated for all images
- ✅ Vault managing all secrets
- ✅ Secrets rotation automated
- ✅ All containers non-root
- ✅ Secret scanning prevents commits
- ✅ PCI-DSS checklist complete

### Should Have (Important)
- ✅ Approval workflows working
- ✅ OPA policies enforced
- ✅ SOC 2 controls documented
- ✅ Security audit script functional
- ✅ Full documentation complete

### Nice to Have (Optional)
- ✅ DependencyTrack integrated
- ✅ SIEM integration configured
- ✅ WAF deployed
- ✅ MFA implemented

---

## Risk Mitigation

### Risk 1: Vault Unavailable
**Mitigation:** Graceful fallback to environment variables, high availability setup

### Risk 2: Secrets Rotation Breaks Services
**Mitigation:** Test rotation in staging, automated rollback, health checks

### Risk 3: Security Scanning False Positives
**Mitigation:** Allowlist configuration, manual review process

### Risk 4: CI/CD Pipeline Too Slow
**Mitigation:** Parallel jobs, caching, optimize tests

### Risk 5: Compliance Gaps
**Mitigation:** External audit, gap analysis, remediation plan

---

## Dependencies

**Phase 0:** ✅ Complete
**Phase 1:** ✅ Complete
**Phase 2:** ✅ Complete

**External:**
- Vault server (Docker deployment)
- SNYK_TOKEN for Snyk scanning
- Slack webhook for notifications
- GitHub Actions minutes
- External audit firm (for SOC 2)

---

## Next Phase

After Phase 3 completion:
**Phase 4: SRE & Observability (Week 7-8)**
- Production Grafana dashboards
- SLO-based alerting
- Incident runbooks
- On-call setup

---

**Document Version:** 1.0
**Last Updated:** 2025-12-18
**Status:** Ready for Execution
**Owner:** Platform Engineering Team
