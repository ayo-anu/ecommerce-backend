# ENTERPRISE-GRADE PRODUCTION MODERNIZATION PLAN
**E-Commerce Platform - Complete DevOps Transformation**

**Date:** 2025-12-12
**Scope:** Docker-Only Production (No Kubernetes)
**Current State:** Development-Ready Monorepo
**Target State:** True Enterprise Production Grade
**Auditor:** Principal DevOps Engineer, SRE, Senior Software Architect

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [File Tree Analysis](#file-tree-analysis)
3. [Findings](#findings)
4. [Issues Catalog](#issues-catalog)
5. [Restructure Plan](#restructure-plan)
6. [Docker Productionization](#docker-productionization)
7. [CI/CD Pipeline](#cicd-pipeline)
8. [Security & Compliance](#security--compliance)
9. [SRE & Observability](#sre--observability)
10. [Automated Patches](#automated-patches)
11. [Multi-Phase Roadmap](#multi-phase-roadmap)
12. [Deliverables Summary](#deliverables-summary)

---

## Executive Summary

### Current State Assessment

The e-commerce platform repository shows **good architectural foundations** with:
- ✅ Modern tech stack (Django 5.1, FastAPI, Next.js 14)
- ✅ Microservices separation (backend + 7 AI services)
- ✅ Docker containerization
- ✅ CI/CD workflows in place
- ✅ Monitoring infrastructure (Prometheus, Grafana, Jaeger)
- ✅ Comprehensive documentation

However, **critical gaps prevent production deployment**:
- ❌ Multiple docker-compose files scattered across repository
- ❌ Environment files in 3 different locations
- ❌ 25MB temporary files in git history
- ❌ Secrets management incomplete (Vault disabled)
- ❌ No container image scanning in CI/CD
- ❌ Missing resource limits on most services
- ❌ No production Nginx hardening
- ❌ No automated backup/restore
- ❌ No disaster recovery procedures
- ❌ Missing SRE runbooks and dashboards

### Modernization Goals

1. **Zero-downtime deployments** with blue-green strategy
2. **Enterprise security** with Vault, secrets rotation, image scanning
3. **Production observability** with real Grafana dashboards and SLO monitoring
4. **Automated operations** with backup/restore, health checks, rollback
5. **Compliance-ready** for PCI-DSS, SOC 2, GDPR
6. **Cost optimization** with multi-stage Docker builds (60-85% size reduction)
7. **Clear structure** with enterprise-grade folder organization

### Success Metrics

| Metric | Current | Target | Impact |
|--------|---------|--------|--------|
| Docker image size | 3-4 GB | 600 MB - 1.5 GB | 60-75% reduction |
| Deployment time | Manual, 30+ min | Automated, <5 min | 83% faster |
| Security vulnerabilities | Unknown | 0 Critical/High | Compliance |
| MTTR (Mean Time To Recovery) | Unknown | <15 min | 4x SLA |
| Uptime SLO | N/A | 99.9% | Production-ready |
| Secret rotation | Never | Weekly | Security compliance |

---

## File Tree Analysis

### Current Repository Structure

```
ecommerce-project/
├── .archived/                              # ❌ REMOVE - Dead code, not in active use
├── .claude/                                # ⚠️  Tool-specific, should be .gitignored
│   └── settings.local.json
├── .github/
│   ├── workflows/
│   │   ├── ai-services-ci.yml              # ✅ Good
│   │   ├── backend-ci.yml                  # ✅ Good
│   │   ├── docker-release.yml              # ✅ Good
│   │   └── dependabot-auto-merge.yml.disabled  # ⚠️  Should enable or remove
│   ├── dependabot.yml                      # ✅ Good
│   ├── CI_RUNBOOK.md                       # ⚠️  Move to docs/runbooks/
│   ├── INTEGRATION_ENVIRONMENT.md          # ⚠️  Move to docs/
│   └── WORKFLOWS_CLEANUP_NOTES.md          # ❌ REMOVE - Temporary notes
├── ai-services/                            # ✅ Core service directory
│   ├── api_gateway/                        # ✅ Good structure
│   ├── services/
│   │   ├── chatbot_rag/
│   │   ├── demand_forecasting/
│   │   ├── fraud_detection/
│   │   ├── pricing_engine/
│   │   ├── recommendation_engine/
│   │   ├── search_engine/
│   │   ├── visual_recognition/
│   │   ├── EXAMPLE_refactored_service.py   # ❌ REMOVE - Example/template file
│   │   └── SERVICE_TEMPLATE_main.py        # ⚠️  Move to docs/templates/
│   ├── shared/                             # ✅ Good
│   ├── test_data/                          # ⚠️  Should be in tests/fixtures/
│   ├── tests/                              # ✅ Good
│   ├── logs/app.log                        # ❌ REMOVE - Should not be in repo
│   ├── .dockerignore                       # ✅ Good
│   ├── .env.example                        # ⚠️  Consolidate with root
│   └── Dockerfile.template                 # ✅ Good
├── backend/                                # ✅ Core service directory
│   ├── apps/
│   │   ├── accounts/
│   │   ├── analytics/
│   │   ├── health/
│   │   ├── notifications/
│   │   ├── orders/
│   │   ├── payments/
│   │   └── products/
│   ├── config/                             # ✅ Django settings
│   │   └── settings/
│   │       ├── base.py
│   │       ├── development.py
│   │       ├── production.py
│   │       ├── production_test.py          # ❌ REMOVE or clarify purpose
│   │       ├── staging.py
│   │       └── tests.py
│   ├── core/                               # ✅ Good
│   ├── requirements/                       # ✅ Good structure
│   │   ├── base.txt
│   │   ├── dev.txt
│   │   ├── prod.txt
│   │   └── tests.txt
│   ├── logs/django.log                     # ❌ REMOVE - Should not be in repo
│   ├── media/*.prof                        # ❌ REMOVE - Profiling artifacts
│   ├── docker/docker                       # ❌ REMOVE - Looks like misplaced file
│   ├── .env.example                        # ⚠️  Consolidate with root
│   ├── .github/workflows/ci-cd.yml         # ❌ MOVE to root .github/
│   ├── Dockerfile                          # ✅ Good
│   ├── Dockerfile.optimized                # ⚠️  Should replace main or remove
│   ├── .dockerignore                       # ✅ Good
│   └── entrypoint.sh                       # ✅ Good
├── docs/                                   # ⚠️  Good but needs organization
│   ├── adr/                                # ✅ Excellent - Architecture Decision Records
│   ├── architecture.md                     # ✅ Good
│   ├── ai_services_overview.md             # ✅ Good
│   ├── deployment_guide.md                 # ✅ Good
│   ├── production_deployment.md            # ⚠️  CONSOLIDATE with deployment_guide
│   ├── COMPLETE_ARCHITECTURE.md            # ⚠️  CONSOLIDATE with architecture.md
│   ├── DEPLOYMENT_RUNBOOK.md               # ⚠️  Duplicate - see infrastructure/
│   ├── IMPLEMENTATION_SUMMARY.md           # ❌ REMOVE - Temporary artifact
│   ├── SECURITY_AUDIT_FINDINGS.md          # ⚠️  Move to docs/security/
│   ├── SECURITY_REMEDIATION_COMPLETE.md    # ❌ REMOVE - Temporary artifact
│   ├── BLUE_GREEN_DEPLOYMENT.md            # ⚠️  Move to docs/deployment/
│   ├── DISASTER_RECOVERY.md                # ⚠️  Move to docs/sre/
│   ├── DOCKER_*.md (multiple)              # ⚠️  Move to docs/docker/
│   └── [many other docs]                   # ⚠️  Needs reorganization
├── env/                                    # ❌ WRONG LOCATION - Should be in config/
│   ├── chatbot.env
│   ├── forecasting.env
│   ├── fraud.env
│   ├── gateway.env
│   ├── pricing.env
│   ├── recommender.env
│   ├── search.env
│   └── vision.env
├── infrastructure/                         # ✅ Good concept but needs cleanup
│   ├── docker/
│   │   ├── nginx/
│   │   ├── pgbouncer/
│   │   └── postgres/
│   ├── env/
│   │   ├── .env.development
│   │   ├── .env.example.example            # ❌ DOUBLE .example - naming error
│   │   ├── .env.production
│   │   └── .env.vault.template
│   ├── nginx/                              # ⚠️  Duplicate with docker/nginx
│   ├── docker-compose.yaml                 # ✅ Good
│   ├── docker-compose.base.yaml            # ⚠️  Should be .base.yml
│   ├── docker-compose.dev.yaml             # ✅ Good
│   ├── docker-compose.prod.yaml            # ✅ Good
│   ├── docker-compose.network-policy.yaml  # ✅ Good
│   ├── ARCHITECTURE.md                     # ⚠️  Duplicate with docs/architecture.md
│   ├── DEPLOYMENT.md                       # ⚠️  Duplicate
│   ├── DEPLOYMENT_RUNBOOK.md               # ⚠️  Duplicate
│   ├── README.md                           # ⚠️  Needs content review
│   └── SECURITY_CHECKLIST.md               # ✅ Good
├── integration_tests/                      # ⚠️  Should be tests/integration/
│   ├── test_health_endpoints.sh
│   └── test_service_connectivity.sh
├── monitoring/                             # ✅ Good structure
│   ├── alertmanager/
│   ├── grafana/
│   │   └── provisioning/
│   └── prometheus/
│       └── alerts/
├── scripts/                                # ✅ Good but needs organization
│   ├── backup_databases.sh
│   ├── blue_green_deploy.sh
│   ├── cleanup_repo.sh
│   ├── generate_service_keys.py
│   ├── health_check.py
│   ├── local_dev.sh
│   ├── restore_database.sh
│   ├── run_load_tests.sh
│   ├── setup_backup_cron.sh
│   ├── setup_ssl.sh
│   ├── setup_zero_trust.sh
│   ├── test_all.sh
│   ├── update_dockerfiles_multistage.sh
│   ├── verify_network_security.py
│   ├── verify_security.sh
│   └── verify_structure.py
├── terraform/                              # ⚠️  FUTURE USE - Document or remove
├── tests/                                  # ⚠️  Merge with integration_tests/
│   └── integration/
│       ├── docker-compose.test.yml
│       └── Dockerfile.test
├── backend_history.patch                   # ❌ REMOVE - 25MB artifact
├── docker-compose.ci.yml                   # ⚠️  MOVE to infrastructure/
├── docker-compose.local.yml                # ⚠️  MOVE to infrastructure/
├── docker-compose.production.yml           # ⚠️  CONSOLIDATE with infrastructure/
├── git-filter-repo                         # ❌ REMOVE - Git tool
├── pyproject.toml                          # ⚠️  Root config - verify usage
├── .dockerignore                           # ✅ Good
├── .env.example                            # ✅ Good but consolidate
├── .gitignore                              # ✅ Good
├── .markdown-link-check.json               # ✅ Good
├── .markdownlint.json                      # ✅ Good
├── .pre-commit-config.yaml                 # ✅ Good
├── Makefile                                # ✅ Excellent
├── OPTIMIZATION_SUMMARY.md                 # ❌ REMOVE - Temporary
├── QUICK_START_SECURE.md                   # ⚠️  Consolidate with README
├── README.md                               # ✅ Good
└── SECURITY_FIXES_SUMMARY.md               # ❌ REMOVE - Temporary
```

**Summary Statistics:**
- **Total Files:** ~350+
- **Total Dockerfiles:** 14
- **Total YAML Configs:** 26
- **Duplicate Docs:** ~8-10
- **Dead/Temporary Files:** ~15
- **Misplaced Files:** ~20

---

## Findings

### Critical Structural Issues

1. **Multiple Docker Compose Files Scattered Across Repository**
   - Root level: `docker-compose.{local,production,ci}.yml`
   - Infrastructure dir: `docker-compose.{yaml,base.yaml,dev.yaml,prod.yaml,network-policy.yaml}`
   - **Impact:** Confusion about which file to use, inconsistent configurations
   - **Fix:** Consolidate all into `deploy/docker/compose/` with clear naming

2. **Environment Files in Three Different Locations**
   - `/env/` folder at root with service-specific `.env` files
   - `/infrastructure/env/` with environment templates
   - Service-level `.env.example` in `backend/` and `ai-services/`
   - **Impact:** Secret sprawl, configuration drift, security risk
   - **Fix:** Single source of truth in `config/environments/`

3. **Large Temporary Files in Repository**
   - `backend_history.patch` (25MB) - Git patch file
   - `git-filter-repo` - Git maintenance tool
   - Log files in `backend/logs/`, `ai-services/logs/`
   - Profiling artifacts in `backend/media/*.prof`
   - **Impact:** Bloated repository, slow clones, contains sensitive data
   - **Fix:** Remove immediately, add to `.gitignore`

4. **Documentation Proliferation and Duplication**
   - Multiple `DEPLOYMENT_RUNBOOK.md` (in `docs/`, `infrastructure/`, `.github/`)
   - Multiple architecture docs (`architecture.md`, `COMPLETE_ARCHITECTURE.md`)
   - Temporary artifacts (`OPTIMIZATION_SUMMARY.md`, `SECURITY_FIXES_SUMMARY.md`)
   - **Impact:** Documentation debt, outdated/conflicting information
   - **Fix:** Consolidate into organized `docs/` structure

5. **Missing Production-Grade Files**
   - No `systemd` service units for production deployment
   - No proper secrets management implementation (Vault configured but not integrated)
   - No backup/restore automation (scripts exist but no cron jobs)
   - No production `nginx.conf` with hardening
   - No rate limiting configurations
   - No WAF (Web Application Firewall) setup
   - **Impact:** Cannot deploy to production safely
   - **Fix:** Create production deployment artifacts

6. **Insufficient CI/CD Security Gates**
   - No container image scanning (Trivy, Anchore, Snyk)
   - No dependency vulnerability scanning in CI
   - No SAST (Static Application Security Testing)
   - No compliance checks (CIS benchmarks)
   - No deployment approval workflows
   - **Impact:** Vulnerable code reaches production
   - **Fix:** Add comprehensive security pipeline stages

7. **Missing SRE Tooling**
   - No actual Grafana dashboards (only provisioning configs)
   - No Prometheus recording rules
   - No runbooks for common incidents
   - No SLO/SLI definitions
   - No error budget tracking
   - No oncall rotation setup
   - **Impact:** Cannot operate production system reliably
   - **Fix:** Create full SRE toolkit

8. **Docker Images Not Production-Hardened**
   - Some Dockerfiles missing multi-stage builds
   - No resource limits in many services
   - No security scanning in build process
   - No image signing/verification
   - Inconsistent base images
   - **Impact:** Large images, potential security vulnerabilities
   - **Fix:** Standardize and harden all Dockerfiles

9. **Secrets Management Not Implemented**
   - Vault client code exists but not activated
   - Secrets in environment variables (not rotated)
   - No secrets rotation strategy
   - No audit trail for secret access
   - **Impact:** Security vulnerability, compliance failure
   - **Fix:** Fully implement HashiCorp Vault integration

10. **No Disaster Recovery Implementation**
    - Backup scripts exist but not automated
    - No backup verification/testing
    - No restore procedures documented
    - No RTO/RPO defined
    - No offsite backup strategy
    - **Impact:** Data loss risk in disaster scenarios
    - **Fix:** Implement automated backup/restore with testing

---

## Issues Catalog

### Critical Severity Issues

#### **CRIT-001: Secrets Exposure Risk**

**Severity:** Critical
**Files Affected:**
- `/env/*.env` (8 files with service-specific configs)
- `/.env` (if exists - gitignored but pattern dangerous)
- `infrastructure/env/.env.production`

**Problem:**
- Environment files with actual secrets may have been committed historically
- Multiple `.env` locations increase risk of accidental commit
- No secrets scanning in CI/CD
- Vault integration incomplete (disabled via `VAULT_DISABLED=true`)

**Business Impact:**
- Data breach if secrets leak
- Compliance violations (PCI-DSS, SOC 2)
- Potential AWS/Stripe credential exposure
- Customer data at risk

**Technical Impact:**
- API keys, database passwords, JWT secrets could be exposed
- Attackers could gain full system access
- Historical git commits may contain secrets

**Fix:**

```bash
# 1. Scan git history for secrets
git log --all --full-history -- "*.env" "**/*.env"
pip install git-secrets truffleHog gitleaks
gitleaks detect --source . --verbose

# 2. If secrets found, rotate ALL credentials immediately
# 3. Remove from history
git filter-repo --path .env --invert-paths
git filter-repo --path 'env/' --invert-paths

# 4. Consolidate environment files
mkdir -p config/environments
git mv env/* config/environments/
git rm infrastructure/env/.env.production  # Not in repo!

# 5. Add pre-commit hook
cat >> .git/hooks/pre-commit << 'EOF'
#!/bin/bash
if git diff --cached --name-only | grep -E '\.env$|\.env\.'; then
    echo "ERROR: Attempted to commit .env file!"
    exit 1
fi
EOF
chmod +x .git/hooks/pre-commit
```

**Git Patch:**
```diff
--- a/.gitignore
+++ b/.gitignore
@@ -34,9 +34,15 @@

 # Environment variables
 .env
-*.env
+*.env*
+!.env.example
+!.env.*.template
+config/environments/*.env
+config/environments/.env.*
 .env.*
-!.env.example
+infrastructure/env/.env.production
+infrastructure/env/.env.staging
+infrastructure/env/.env.development
```

---

#### **CRIT-002: Missing Resource Limits in Production**

**Severity:** Critical
**Files Affected:**
- `docker-compose.production.yml`
- `infrastructure/docker-compose.prod.yaml`

**Problem:**
- Most services missing CPU/memory limits
- No disk I/O limits
- Can cause cascading failures and resource exhaustion
- OOM killer can terminate critical services randomly

**Business Impact:**
- Service outages during load spikes
- One rogue container can take down entire system
- Unpredictable costs in cloud environments

**Technical Impact:**
- Memory leaks crash entire host
- No predictable capacity planning
- Cannot calculate infrastructure costs

**Fix:**

Create `infrastructure/docker/resource-limits.yaml`:
```yaml
# Resource limits for all services
x-resource-limits-small: &resource-limits-small
  deploy:
    resources:
      limits:
        cpus: '0.5'
        memory: 512M
        pids: 100
      reservations:
        cpus: '0.25'
        memory: 256M

x-resource-limits-medium: &resource-limits-medium
  deploy:
    resources:
      limits:
        cpus: '1.0'
        memory: 1G
        pids: 200
      reservations:
        cpus: '0.5'
        memory: 512M

x-resource-limits-large: &resource-limits-large
  deploy:
    resources:
      limits:
        cpus: '2.0'
        memory: 2G
        pids: 500
      reservations:
        cpus: '1.0'
        memory: 1G
```

**Updated docker-compose.prod.yaml:**
```diff
--- a/docker-compose.production.yml
+++ b/docker-compose.production.yml
@@ -1,5 +1,7 @@
 version: '3.8'

+include:
+  - infrastructure/docker/resource-limits.yaml
+
 services:
   postgres:
     image: postgres:15-alpine
@@ -14,6 +16,13 @@ services:
       retries: 5
       start_period: 10s
+    <<: *resource-limits-medium
+    ulimits:
+      nofile:
+        soft: 65536
+        hard: 65536
+    security_opt:
+      - no-new-privileges:true
+    read_only: false  # Postgres needs write access
```

---

#### **CRIT-003: No Container Image Scanning**

**Severity:** Critical
**Files Affected:**
- `.github/workflows/backend-ci.yml`
- `.github/workflows/ai-services-ci.yml`
- `.github/workflows/docker-release.yml`

**Problem:**
- Docker images built and pushed without security scanning
- No vulnerability detection
- No compliance checks
- No SBOM (Software Bill of Materials) generation

**Business Impact:**
- Deploying vulnerable containers to production
- Compliance failures (SOC 2, ISO 27001)
- Potential data breaches from known CVEs

**Technical Impact:**
- Critical/High vulnerabilities in base images
- Outdated dependencies with known exploits
- No audit trail of what's deployed

**Fix:**

Create `.github/workflows/security-scan.yml`:
```yaml
name: Container Security Scan

on:
  pull_request:
    paths:
      - '**/Dockerfile*'
      - '.github/workflows/security-scan.yml'
  push:
    branches: [main]

jobs:
  trivy-scan:
    name: Trivy Vulnerability Scanner
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build backend image
        run: docker build -t backend:${{ github.sha }} ./backend

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'backend:${{ github.sha }}'
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'
          exit-code: '1'  # Fail on critical/high

      - name: Upload Trivy results to GitHub Security
        uses: github/codeql-action/upload-sarif@v2
        if: always()
        with:
          sarif_file: 'trivy-results.sarif'

  snyk-scan:
    name: Snyk Container Scan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run Snyk to check Docker image for vulnerabilities
        uses: snyk/actions/docker@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          image: backend:latest
          args: --severity-threshold=high --fail-on=all

  grype-scan:
    name: Anchore Grype SBOM
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build image
        run: docker build -t backend:scan ./backend

      - name: Scan image with Grype
        uses: anchore/scan-action@v3
        with:
          image: "backend:scan"
          fail-build: true
          severity-cutoff: high

      - name: Generate SBOM
        uses: anchore/sbom-action@v0
        with:
          image: "backend:scan"
          format: cyclonedx-json
          output-file: "backend-sbom.json"

      - name: Upload SBOM artifact
        uses: actions/upload-artifact@v3
        with:
          name: sbom
          path: backend-sbom.json
```

---

### High Severity Issues

#### **HIGH-001: Missing Production Nginx Configuration**

**Severity:** High
**Files Affected:**
- `infrastructure/nginx/nginx.conf`
- `infrastructure/docker/nginx/nginx.conf`
- `infrastructure/nginx/conf.d/api.conf`

**Problem:**
- Nginx config exists but lacks production hardening
- No rate limiting
- No request size limits
- No security headers
- No DDoS protection
- No TLS hardening
- No access logging to structured format

**Business Impact:**
- Vulnerable to DDoS attacks
- Poor SEO due to missing security headers
- Cannot meet compliance requirements
- Potential data exfiltration via oversized requests

**Technical Impact:**
- No protection against brute force
- XSS/Clickjacking vulnerabilities
- Weak TLS configuration
- Cannot diagnose production issues

**Fix:** See Docker Productionization section for complete production-grade Nginx configuration.

---

#### **HIGH-002: No Secrets Management Implementation**

**Severity:** High
**Files Affected:**
- `backend/core/vault_client.py`
- All docker-compose files
- `.env` files

**Problem:**
- HashiCorp Vault client exists but disabled (`VAULT_DISABLED=true`)
- Secrets stored in environment variables
- No secrets rotation
- No audit trail
- No encryption at rest for secrets

**Business Impact:**
- Compliance violations (PCI-DSS requires secrets rotation)
- Cannot audit who accessed secrets when
- Secrets never expire
- One compromised secret = full breach

**Technical Impact:**
- Secrets in plaintext in environment
- No centralized secrets management
- Manual rotation required
- Cannot revoke access quickly

**Fix:** See Security & Compliance section for complete Vault implementation.

---

## Restructure Plan

### Proposed Enterprise Folder Structure

```
ecommerce-platform/
├── .ci/                                    # CI/CD configurations
│   ├── docker-compose.test.yml
│   ├── security-scan.yml
│   └── integration-tests/
├── .github/
│   └── workflows/                          # Keep as-is, well organized
├── config/                                 # ⭐ NEW - Centralized configuration
│   ├── environments/                       # All environment files
│   │   ├── .env.example
│   │   ├── development.env.template
│   │   ├── staging.env.template
│   │   └── production.env.template
│   ├── secrets/                            # Vault/secrets configs
│   │   └── vault-policies/
│   └── logging/                            # Logging configurations
│       ├── fluent-bit.conf
│       └── logrotate.conf
├── deploy/                                 # ⭐ NEW - Deployment artifacts
│   ├── docker/                             # Docker-specific deployment
│   │   ├── compose/
│   │   │   ├── base.yml
│   │   │   ├── development.yml
│   │   │   ├── staging.yml
│   │   │   ├── production.yml
│   │   │   └── ci.yml
│   │   ├── images/                         # Dockerfile storage
│   │   │   ├── backend/
│   │   │   ├── ai-services/
│   │   │   ├── nginx/
│   │   │   ├── vault/
│   │   │   └── pgbouncer/
│   │   └── scripts/
│   │       ├── deploy.sh
│   │       ├── rollback.sh
│   │       └── blue-green-deploy.sh
│   ├── systemd/                            # Systemd unit files
│   │   ├── ecommerce-backend.service
│   │   ├── ecommerce-ai-gateway.service
│   │   └── ecommerce-docker-compose@.service
│   └── nginx/                              # Nginx configs
│       ├── nginx.conf
│       ├── conf.d/
│       └── ssl/
├── docs/                                   # Reorganized documentation
│   ├── architecture/
│   │   ├── README.md
│   │   ├── system-design.md
│   │   ├── network-topology.md
│   │   └── data-flow.md
│   ├── adr/                                # Architecture Decision Records
│   ├── deployment/
│   │   ├── docker-deployment.md
│   │   ├── production-checklist.md
│   │   └── rollback-procedures.md
│   ├── development/
│   │   ├── getting-started.md
│   │   ├── local-setup.md
│   │   └── contributing.md
│   ├── operations/                         # ⭐ NEW - SRE documentation
│   │   ├── runbooks/
│   │   │   ├── database-failover.md
│   │   │   ├── service-outage.md
│   │   │   ├── high-cpu-debug.md
│   │   │   └── backup-restore.md
│   │   ├── oncall-guide.md
│   │   ├── incident-response.md
│   │   └── disaster-recovery.md
│   ├── security/
│   │   ├── security-checklist.md
│   │   ├── audit-findings.md
│   │   └── compliance.md
│   └── api/                                # API documentation
│       ├── backend-api.md
│       └── ai-services-api.md
├── monitoring/                             # Keep, enhance
│   ├── prometheus/
│   │   ├── prometheus.yml
│   │   ├── alerts/
│   │   └── recording-rules/
│   ├── grafana/
│   │   ├── dashboards/                     # ⭐ ADD actual dashboard JSONs
│   │   │   ├── system-overview.json
│   │   │   ├── database-metrics.json
│   │   │   ├── api-performance.json
│   │   │   └── business-kpis.json
│   │   └── provisioning/
│   ├── alertmanager/
│   │   └── alertmanager.yml
│   └── jaeger/
│       └── config.yml
├── scripts/                                # Reorganized scripts
│   ├── backup/
│   │   ├── backup-databases.sh
│   │   ├── backup-to-s3.sh
│   │   ├── restore-database.sh
│   │   ├── verify-backup.sh
│   │   └── setup-cron.sh
│   ├── deployment/
│   │   ├── deploy.sh
│   │   ├── health-check.sh
│   │   └── smoke-test.sh
│   ├── development/
│   │   ├── local-dev.sh
│   │   ├── generate-test-data.sh
│   │   └── reset-local-db.sh
│   ├── maintenance/
│   │   ├── rotate-logs.sh
│   │   ├── cleanup-docker.sh
│   │   └── vacuum-database.sh
│   ├── security/
│   │   ├── rotate-secrets.sh
│   │   ├── init-vault.sh
│   │   ├── scan-secrets.sh
│   │   └── audit-permissions.sh
│   └── monitoring/
│       ├── setup-alerts.sh
│       └── test-alerting.sh
├── services/                               # ⭐ RENAMED from backend/ and ai-services/
│   ├── backend/                            # Django backend
│   │   ├── apps/
│   │   ├── config/
│   │   ├── core/
│   │   ├── requirements/
│   │   ├── Dockerfile
│   │   └── entrypoint.sh
│   └── ai/                                 # ⭐ RENAMED from ai-services/
│       ├── gateway/
│       ├── services/
│       │   ├── recommendation/
│       │   ├── search/
│       │   ├── pricing/
│       │   ├── chatbot/
│       │   ├── fraud-detection/
│       │   ├── demand-forecasting/
│       │   └── visual-recognition/
│       ├── shared/
│       └── tests/
├── tests/                                  # Consolidated testing
│   ├── integration/
│   │   ├── test_api_gateway.py
│   │   ├── test_backend_integration.py
│   │   └── docker-compose.test.yml
│   ├── load/
│   │   ├── locustfile.py
│   │   └── scenarios/
│   ├── security/
│   │   ├── test_auth.py
│   │   └── test_vulnerabilities.py
│   └── fixtures/
├── tools/                                  # ⭐ NEW - Development tools
│   ├── git-hooks/
│   │   ├── pre-commit
│   │   └── pre-push
│   ├── linters/
│   │   ├── .flake8
│   │   ├── .pylintrc
│   │   └── .markdownlint.json
│   └── generators/
│       ├── generate-service-keys.py
│       └── create-migration.sh
├── .dockerignore
├── .gitignore
├── .pre-commit-config.yaml
├── Makefile                                # Keep, excellent
├── pyproject.toml
└── README.md
```

### File Move Commands

```bash
#!/bin/bash
set -euo pipefail

echo "🔄 Restructuring repository to enterprise-grade layout..."

# Create new directory structure
mkdir -p .ci/{integration-tests,security}
mkdir -p config/{environments,secrets/vault-policies,logging}
mkdir -p deploy/docker/{compose,images,scripts}
mkdir -p deploy/{systemd,nginx/conf.d}
mkdir -p docs/{architecture,deployment,development,operations/runbooks,security,api}
mkdir -p monitoring/grafana/dashboards
mkdir -p scripts/{backup,deployment,development,maintenance,security,monitoring}
mkdir -p services/{backend,ai}
mkdir -p tests/{integration,load/scenarios,security,fixtures}
mkdir -p tools/{git-hooks,linters,generators}

# ===================================================
# DELETIONS - Remove dead/temporary files
# ===================================================
echo "🗑️  Removing dead files..."
git rm -f backend_history.patch
git rm -f git-filter-repo
git rm -f OPTIMIZATION_SUMMARY.md
git rm -f SECURITY_FIXES_SUMMARY.md
git rm -rf .archived/
git rm -f .github/WORKFLOWS_CLEANUP_NOTES.md
git rm -f docs/IMPLEMENTATION_SUMMARY.md
git rm -f docs/SECURITY_REMEDIATION_COMPLETE.md
git rm -f backend/logs/django.log
git rm -f ai-services/logs/app.log
git rm -f backend/media/*.prof
git rm -f backend/docker/docker
git rm -f infrastructure/env/.env.example.example
git rm -f ai-services/services/EXAMPLE_refactored_service.py

# ===================================================
# MOVES - Reorganize files
# ===================================================

## Environment files
echo "📦 Moving environment files..."
git mv env/*.env config/environments/ 2>/dev/null || true
git mv .env.example config/environments/
git mv backend/.env.example config/environments/backend.env.template
git mv ai-services/.env.example config/environments/ai-services.env.template

## Docker Compose files
echo "🐳 Consolidating Docker Compose files..."
git mv infrastructure/docker-compose.yaml deploy/docker/compose/base.yml
git mv infrastructure/docker-compose.dev.yaml deploy/docker/compose/development.yml
git mv infrastructure/docker-compose.prod.yaml deploy/docker/compose/production.yml
git mv docker-compose.ci.yml deploy/docker/compose/ci.yml
git rm docker-compose.local.yml docker-compose.production.yml  # Duplicates

## Dockerfiles
echo "🏗️  Organizing Dockerfiles..."
mv backend/Dockerfile deploy/docker/images/backend/
mv backend/Dockerfile.optimized deploy/docker/images/backend/Dockerfile.optimized
mv ai-services/api_gateway/Dockerfile deploy/docker/images/ai-services/gateway.Dockerfile
mv infrastructure/docker/nginx/Dockerfile deploy/docker/images/nginx/
mv infrastructure/docker/pgbouncer/Dockerfile deploy/docker/images/pgbouncer/

## Services
echo "🚀 Reorganizing services..."
git mv backend/ services/
git mv ai-services/ services/ai/

## Scripts
echo "📜 Organizing scripts..."
git mv scripts/backup_databases.sh scripts/backup/
git mv scripts/restore_database.sh scripts/backup/
git mv scripts/setup_backup_cron.sh scripts/backup/setup-cron.sh
git mv scripts/blue_green_deploy.sh deploy/docker/scripts/
git mv scripts/health_check.py scripts/deployment/
git mv scripts/local_dev.sh scripts/development/
git mv scripts/init_vault.sh scripts/security/
git mv scripts/verify_security.sh scripts/security/
git mv scripts/run_load_tests.sh tests/load/

## Documentation
echo "📚 Reorganizing documentation..."
git mv docs/architecture.md docs/architecture/system-design.md
git mv docs/COMPLETE_ARCHITECTURE.md docs/architecture/detailed-architecture.md
git mv docs/deployment_guide.md docs/deployment/docker-deployment.md
git mv docs/production_deployment.md docs/deployment/production-guide.md
git mv docs/DEPLOYMENT_RUNBOOK.md docs/deployment/runbook.md
git mv docs/DISASTER_RECOVERY.md docs/operations/disaster-recovery.md
git mv docs/SECURITY_AUDIT_FINDINGS.md docs/security/audit-findings.md
git mv docs/DOCKER_*.md docs/deployment/
git mv .github/CI_RUNBOOK.md docs/operations/runbooks/ci-troubleshooting.md
git mv .github/INTEGRATION_ENVIRONMENT.md docs/development/integration-testing.md

## CI/CD
echo "🔧 Organizing CI/CD..."
git mv integration_tests/ .ci/integration-tests/
git mv tests/integration/docker-compose.test.yml .ci/

## Nginx
echo "🌐 Moving Nginx configs..."
git mv infrastructure/nginx/* deploy/nginx/

# ===================================================
# UPDATE REFERENCES
# ===================================================

echo "📝 Updating file references..."

# Update Makefile
sed -i 's|infrastructure/docker-compose.yaml|deploy/docker/compose/base.yml|g' Makefile
sed -i 's|infrastructure/docker-compose.dev.yaml|deploy/docker/compose/development.yml|g' Makefile
sed -i 's|infrastructure/docker-compose.prod.yaml|deploy/docker/compose/production.yml|g' Makefile

# Update GitHub workflows
find .github/workflows -type f -name "*.yml" -exec sed -i 's|backend/|services/backend/|g' {} \;
find .github/workflows -type f -name "*.yml" -exec sed -i 's|ai-services/|services/ai/|g' {} \;
find .github/workflows -type f -name "*.yml" -exec sed -i 's|docker-compose.ci.yml|deploy/docker/compose/ci.yml|g' {} \;

# Update documentation links
find docs -type f -name "*.md" -exec sed -i 's|(backend/|(services/backend/|g' {} \;
find docs -type f -name "*.md" -exec sed -i 's|(infrastructure/|(deploy/|g' {} \;

# Update Docker Compose files
find deploy/docker/compose -type f -name "*.yml" -exec sed -i 's|context: ../backend|context: ../../services/backend|g' {} \;
find deploy/docker/compose -type f -name "*.yml" -exec sed -i 's|context: ../ai-services|context: ../../services/ai|g' {} \;
find deploy/docker/compose -type f -name "*.yml" -exec sed -i 's|../monitoring|../../monitoring|g' {} \;

echo "✅ Restructuring complete!"
```

---

## Docker Productionization

### Production-Grade Multi-Stage Dockerfiles

#### Backend Production Dockerfile

Create `deploy/docker/images/backend/Dockerfile.production`:

```dockerfile
# ==============================================================================
# Production Django Backend - Multi-Stage Build
# Size: ~200MB (vs 800MB+ with dev dependencies)
# ==============================================================================

# ==============================================================================
# Stage 1: Base Python with Security Hardening
# ==============================================================================
FROM python:3.11-slim-bookworm AS base

# Security: Run as non-root user
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser

# Install security updates
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        libpq5 \
        curl \
        tini && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# ==============================================================================
# Stage 2: Builder - Install Dependencies
# ==============================================================================
FROM base AS builder

# Build arguments
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0

# Labels for metadata
LABEL org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.authors="devops@ecommerce.com" \
      org.opencontainers.image.url="https://github.com/your-org/ecommerce" \
      org.opencontainers.image.source="https://github.com/your-org/ecommerce" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.vendor="E-Commerce Platform" \
      org.opencontainers.image.title="Backend API" \
      org.opencontainers.image.description="Django REST Framework backend"

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        gcc \
        g++ \
        python3-dev && \
    rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install requirements
WORKDIR /build
COPY requirements/base.txt requirements/prod.txt ./
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r prod.txt && \
    find /opt/venv -type d -name __pycache__ -exec rm -rf {} + && \
    find /opt/venv -type f -name "*.pyc" -delete && \
    find /opt/venv -type f -name "*.pyo" -delete

# ==============================================================================
# Stage 3: Runtime - Minimal Production Image
# ==============================================================================
FROM base AS runtime

# Build arguments
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    WORKERS=4 \
    THREADS=2 \
    TIMEOUT=60 \
    MAX_REQUESTS=1000

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder --chown=appuser:appuser /opt/venv /opt/venv

# Copy application code
COPY --chown=appuser:appuser . /app/

# Create necessary directories with correct permissions
RUN mkdir -p /app/logs /app/staticfiles /app/media /app/tmp && \
    chown -R appuser:appuser /app && \
    chmod 750 /app

# Security: Remove unnecessary packages and files
RUN apt-get purge -y --auto-remove && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* && \
    rm -rf /root/.cache

# Security: Make filesystem read-only where possible
RUN chmod 444 /app/manage.py && \
    find /app/config -type f -exec chmod 444 {} \; && \
    find /app/apps -type f -name "*.py" -exec chmod 444 {} \;

# Copy entrypoint
COPY --chmod=755 entrypoint.sh /entrypoint.sh

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Expose port
EXPOSE 8000

# Use tini as init system (proper signal handling)
ENTRYPOINT ["/usr/bin/tini", "--", "/entrypoint.sh"]

# Default command
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "${WORKERS}", \
     "--threads", "${THREADS}", \
     "--worker-class", "gthread", \
     "--worker-tmp-dir", "/dev/shm", \
     "--max-requests", "${MAX_REQUESTS}", \
     "--max-requests-jitter", "50", \
     "--timeout", "${TIMEOUT}", \
     "--graceful-timeout", "30", \
     "--keep-alive", "5", \
     "--preload", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info"]
```

#### Enhanced Entrypoint Script

Update `services/backend/entrypoint.sh`:

```bash
#!/bin/bash
set -e

# ==============================================================================
# Production Entrypoint with Health Checks and Graceful Shutdown
# ==============================================================================

echo "🚀 Starting E-Commerce Backend..."

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" >&2
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

# Pre-flight checks
log "Running pre-flight checks..."

required_vars=("DATABASE_URL" "SECRET_KEY" "ALLOWED_HOSTS")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        error "Required environment variable $var is not set"
        exit 1
    fi
done

# Wait for database
log "Waiting for database..."
timeout=60
counter=0
while ! pg_isready -d "$DATABASE_URL" > /dev/null 2>&1; do
    counter=$((counter + 1))
    if [ $counter -gt $timeout ]; then
        error "Database did not become ready in time"
        exit 1
    fi
    sleep 1
done
log "✅ Database is ready"

# Run migrations
if [ "$RUN_MIGRATIONS" = "true" ]; then
    log "Running database migrations..."
    python manage.py migrate --noinput
    log "✅ Migrations complete"
fi

# Collect static files
if [ "$DJANGO_SETTINGS_MODULE" = "config.settings.production" ] && [ "$COLLECT_STATIC" = "true" ]; then
    log "Collecting static files..."
    python manage.py collectstatic --noinput --clear
    log "✅ Static files collected"
fi

# Health check
log "Performing application health check..."
python manage.py check --deploy
log "✅ All pre-flight checks passed"

# Graceful shutdown handler
graceful_shutdown() {
    log "Received shutdown signal, gracefully stopping..."
    if [ -n "$GUNICORN_PID" ]; then
        kill -TERM "$GUNICORN_PID"
        wait "$GUNICORN_PID"
    fi
    log "✅ Shutdown complete"
    exit 0
}

trap graceful_shutdown SIGTERM SIGINT SIGQUIT

log "🎯 Starting application..."
exec "$@" &
GUNICORN_PID=$!
wait $GUNICORN_PID
```

#### AI Services Production Dockerfile Template

Create `deploy/docker/images/ai-services/Dockerfile.template`:

```dockerfile
# ==============================================================================
# AI Services - Production Multi-Stage Dockerfile
# ARG SERVICE_NAME must be passed during build
# ==============================================================================

ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim-bookworm AS base

ARG SERVICE_NAME
ENV SERVICE_NAME=${SERVICE_NAME}

RUN groupadd -r aiuser && useradd -r -g aiuser -u 1001 aiuser

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        libgomp1 \
        libglib2.0-0 \
        curl \
        tini && \
    rm -rf /var/lib/apt/lists/*

# ==============================================================================
# Stage 2: Builder
# ==============================================================================
FROM base AS builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        g++ \
        git && \
    rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /build
COPY services/${SERVICE_NAME}/requirements.txt .
COPY shared/requirements.txt shared_requirements.txt

RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r shared_requirements.txt && \
    find /opt/venv -type d -name __pycache__ -exec rm -rf {} + && \
    find /opt/venv -type f -name "*.pyc" -delete

# ==============================================================================
# Stage 3: Runtime
# ==============================================================================
FROM base AS runtime

ARG SERVICE_NAME
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    SERVICE_NAME=${SERVICE_NAME} \
    WORKERS=2 \
    PORT=8000

WORKDIR /app

COPY --from=builder --chown=aiuser:aiuser /opt/venv /opt/venv
COPY --chown=aiuser:aiuser services/${SERVICE_NAME}/ /app/
COPY --chown=aiuser:aiuser shared/ /app/shared/

RUN mkdir -p /app/logs /app/models /app/tmp && \
    chown -R aiuser:aiuser /app && \
    chmod 750 /app

USER aiuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

EXPOSE ${PORT}

ENTRYPOINT ["/usr/bin/tini", "--"]

CMD ["uvicorn", "main:app", \
     "--host", "0.0.0.0", \
     "--port", "${PORT}", \
     "--workers", "${WORKERS}", \
     "--loop", "uvloop", \
     "--http", "httptools"]
```

### Production Nginx Configuration

Create `deploy/nginx/nginx.conf`:

```nginx
user nginx;
worker_processes auto;
worker_rlimit_nofile 65535;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 4096;
    use epoll;
    multi_accept on;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Structured JSON logging
    log_format json_combined escape=json
    '{'
        '"time_local":"$time_local",'
        '"remote_addr":"$remote_addr",'
        '"request":"$request",'
        '"status":"$status",'
        '"body_bytes_sent":"$body_bytes_sent",'
        '"request_time":"$request_time",'
        '"http_referrer":"$http_referer",'
        '"http_user_agent":"$http_user_agent",'
        '"upstream_response_time":"$upstream_response_time"'
    '}';

    access_log /var/log/nginx/access.log json_combined;

    # Performance
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    server_tokens off;

    # Buffer sizes
    client_body_buffer_size 10K;
    client_header_buffer_size 1k;
    client_max_body_size 20m;
    large_client_header_buffers 2 1k;

    # Gzip
    gzip on;
    gzip_vary on;
    gzip_comp_level 6;
    gzip_types text/plain text/css application/json application/javascript;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=general:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=auth:10m rate=5r/m;
    limit_req_zone $binary_remote_addr zone=api:10m rate=100r/s;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    include /etc/nginx/conf.d/*.conf;
}
```

Create `deploy/nginx/conf.d/api.conf`:

```nginx
upstream api_gateway {
    least_conn;
    server api_gateway:8080 max_fails=3 fail_timeout=30s;
    keepalive 32;
}

upstream backend {
    least_conn;
    server backend:8000 max_fails=3 fail_timeout=30s;
    keepalive 32;
}

# HTTP -> HTTPS redirect
server {
    listen 80;
    server_name _;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # TLS configuration
    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256';
    ssl_prefer_server_ciphers off;

    # Security headers
    add_header Strict-Transport-Security "max-age=63072000" always;
    add_header Content-Security-Policy "default-src 'self'" always;

    # Rate limiting
    limit_req zone=general burst=20 nodelay;

    location /api/ {
        limit_req zone=api burst=100 nodelay;
        proxy_pass http://api_gateway/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /admin/ {
        limit_req zone=auth burst=5 nodelay;
        proxy_pass http://backend/admin/;
    }

    location /static/ {
        alias /var/www/static/;
        expires 1y;
    }
}
```

### Blue-Green Deployment Script

Create `deploy/docker/scripts/blue-green-deploy.sh`:

```bash
#!/bin/bash
set -euo pipefail

# ==============================================================================
# Blue-Green Deployment Script
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} $1"; }
error() { echo -e "${RED}[$(date +'%H:%M:%S')] ERROR:${NC} $1" >&2; }

ACTIVE_COLOR=""
SERVICE_NAME="${SERVICE_NAME:-backend}"

get_active_color() {
    if docker ps --filter "name=${SERVICE_NAME}_blue" | grep -q "${SERVICE_NAME}_blue"; then
        echo "blue"
    elif docker ps --filter "name=${SERVICE_NAME}_green" | grep -q "${SERVICE_NAME}_green"; then
        echo "green"
    else
        echo "none"
    fi
}

health_check() {
    local color=$1
    local url=$2

    for i in {1..30}; do
        if curl -sf "$url" > /dev/null; then
            log "✅ Health check passed"
            return 0
        fi
        sleep 2
    done

    error "❌ Health check failed"
    return 1
}

deploy_environment() {
    local color=$1

    log "🚀 Deploying $color environment..."

    docker-compose -p "ecommerce-$color" build "$SERVICE_NAME"
    docker-compose -p "ecommerce-$color" up -d "$SERVICE_NAME"

    local port=$([[ "$color" == "blue" ]] && echo "8001" || echo "8002")

    if ! health_check "$color" "http://localhost:$port/health/"; then
        error "Deployment failed"
        return 1
    fi

    log "✅ $color environment deployed"
    return 0
}

switch_traffic() {
    local new_color=$1
    log "🔄 Switching traffic to $new_color..."

    # Update nginx
    docker exec ecommerce_nginx_prod nginx -s reload
    log "✅ Traffic switched"
}

main() {
    log "=========================================="
    log "  Blue-Green Deployment"
    log "=========================================="

    ACTIVE_COLOR=$(get_active_color)
    INACTIVE_COLOR=$([[ "$ACTIVE_COLOR" == "blue" ]] && echo "green" || echo "blue")

    log "Active: $ACTIVE_COLOR, Deploying: $INACTIVE_COLOR"

    if ! deploy_environment "$INACTIVE_COLOR"; then
        error "Deployment failed"
        exit 1
    fi

    switch_traffic "$INACTIVE_COLOR"

    log "=========================================="
    log "✅ Deployment complete!"
    log "=========================================="
}

main "$@"
```

---

## CI/CD Pipeline

### Complete Production Deployment Pipeline

Create `.github/workflows/production-deploy.yml`:

```yaml
name: Production Deployment Pipeline

on:
  push:
    tags:
      - 'v*.*.*'
  workflow_dispatch:

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  security-scan:
    name: Security Scanning
    runs-on: ubuntu-latest
    permissions:
      contents: read
      security-events: write

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Run Trivy
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'

      - name: Upload Trivy results
        uses: github/codeql-action/upload-sarif@v2
        if: always()
        with:
          sarif_file: 'trivy-results.sarif'

  build-and-test:
    name: Build & Test
    runs-on: ubuntu-latest
    needs: [security-scan]

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build backend
        uses: docker/build-push-action@v5
        with:
          context: ./services/backend
          file: ./deploy/docker/images/backend/Dockerfile.production
          push: false
          tags: backend:test
          cache-from: type=gha
          cache-to: type=gha,mode=max

  integration-tests:
    name: Integration Tests
    runs-on: ubuntu-latest
    needs: [build-and-test]

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Start test environment
        run: |
          docker-compose -f deploy/docker/compose/ci.yml up -d
          sleep 30

      - name: Run tests
        run: |
          docker-compose -f deploy/docker/compose/ci.yml exec -T backend \
            pytest tests/integration/ -v

  build-push:
    name: Build & Push Images
    runs-on: ubuntu-latest
    needs: [integration-tests]

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Log in to registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: ./services/backend
          push: true
          tags: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}/backend:${{ github.ref_name }}

  deploy-production:
    name: Deploy to Production
    runs-on: ubuntu-latest
    needs: [build-push]
    environment:
      name: production
      url: https://api.example.com

    steps:
      - name: Deploy
        run: |
          ssh ${{ secrets.PROD_USER }}@${{ secrets.PROD_HOST }} << 'EOF'
            cd /opt/ecommerce
            git checkout ${{ github.ref_name }}
            ./deploy/docker/scripts/blue-green-deploy.sh
          EOF
```

---

## Security & Compliance

### Automated Secrets Rotation

Create `scripts/security/rotate-secrets.sh`:

```bash
#!/bin/bash
set -euo pipefail

# ==============================================================================
# Automated Secrets Rotation Script
# ==============================================================================

VAULT_ADDR="${VAULT_ADDR:-http://localhost:8200}"
LOG_FILE="/var/log/ecommerce/secret-rotation.log"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

generate_secret() {
    openssl rand -base64 32
}

rotate_db_password() {
    local db_name=$1
    log "Rotating password for database: $db_name"

    local new_password=$(generate_secret)

    vault kv put "ecommerce/database/$db_name" \
        password="$new_password" \
        rotated_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

    docker exec ecommerce_postgres_prod psql -U postgres -c \
        "ALTER USER ecommerce_${db_name}_user WITH PASSWORD '$new_password';"

    docker-compose restart backend
    log "✅ Database password rotated"
}

rotate_redis_password() {
    log "Rotating Redis password..."

    local new_password=$(generate_secret)
    vault kv put ecommerce/redis/main password="$new_password"

    docker exec ecommerce_redis_prod redis-cli CONFIG SET requirepass "$new_password"
    docker-compose restart backend api_gateway

    log "✅ Redis password rotated"
}

main() {
    log "=========================================="
    log "  Starting Secret Rotation"
    log "=========================================="

    vault login -method=userpass username="${VAULT_USERNAME}"

    rotate_db_password "main"
    rotate_redis_password

    log "✅ Secret Rotation Complete"
}

main "$@"
```

### Vault Integration

Create `scripts/security/init-vault.sh`:

```bash
#!/bin/bash
set -euo pipefail

# ==============================================================================
# Vault Initialization Script
# ==============================================================================

VAULT_ADDR="${VAULT_ADDR:-http://vault:8200}"
export VAULT_ADDR

echo "🔐 Initializing Vault..."

# Initialize
vault operator init -key-shares=5 -key-threshold=3 > /tmp/vault_keys.txt

# Unseal
UNSEAL_KEY_1=$(grep 'Unseal Key 1:' /tmp/vault_keys.txt | awk '{print $4}')
UNSEAL_KEY_2=$(grep 'Unseal Key 2:' /tmp/vault_keys.txt | awk '{print $4}')
UNSEAL_KEY_3=$(grep 'Unseal Key 3:' /tmp/vault_keys.txt | awk '{print $4}')

vault operator unseal "$UNSEAL_KEY_1"
vault operator unseal "$UNSEAL_KEY_2"
vault operator unseal "$UNSEAL_KEY_3"

# Enable secrets engine
vault secrets enable -path=ecommerce -version=2 kv

# Create policies
vault policy write backend - << EOF
path "ecommerce/data/backend/*" {
  capabilities = ["read", "list"]
}
EOF

# Enable AppRole
vault auth enable approle
vault write auth/approle/role/backend token_policies="backend"

echo "✅ Vault initialized!"
```

---

## SRE & Observability

### Grafana System Dashboard

Create `monitoring/grafana/dashboards/system-overview.json`:

```json
{
  "dashboard": {
    "title": "E-Commerce Platform - System Overview",
    "refresh": "30s",
    "panels": [
      {
        "id": 1,
        "title": "Service Health",
        "type": "stat",
        "targets": [{
          "expr": "up{job=~\"backend|api-gateway\"}"
        }]
      },
      {
        "id": 2,
        "title": "Request Rate",
        "type": "graph",
        "targets": [{
          "expr": "rate(http_requests_total[5m])"
        }]
      },
      {
        "id": 3,
        "title": "Error Rate",
        "type": "graph",
        "targets": [{
          "expr": "rate(http_requests_total{status=~\"5..\"}[5m])"
        }]
      }
    ]
  }
}
```

### Prometheus Recording Rules

Create `monitoring/prometheus/recording-rules/slo-rules.yml`:

```yaml
groups:
  - name: slo_recording_rules
    interval: 30s
    rules:
      - record: slo:availability:ratio_rate5m
        expr: |
          sum(rate(http_requests_total{status!~"5.."}[5m]))
          /
          sum(rate(http_requests_total[5m]))

      - record: slo:latency:p95_5m
        expr: |
          histogram_quantile(0.95,
            rate(http_request_duration_seconds_bucket[5m])
          )
```

### SLO Alerts

Create `monitoring/prometheus/alerts/slo-alerts.yml`:

```yaml
groups:
  - name: slo_alerts
    rules:
      - alert: ErrorBudgetBurnRateCritical
        expr: slo:availability:ratio_rate5m < 0.999
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Critical error budget burn rate"

      - alert: LatencySLOViolation
        expr: slo:latency:p95_5m > 0.2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "P95 latency exceeds 200ms SLO"

      - alert: ServiceDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Service {{ $labels.job }} is down"
```

### Incident Response Runbook

Create `docs/operations/runbooks/high-error-rate.md`:

```markdown
# Runbook: High Error Rate (5xx Errors)

**Alert:** `HighErrorRate`
**Severity:** Critical
**MTTR Target:** 15 minutes

## 🚨 Immediate Actions (First 5 minutes)

### 1. Check Current Status
```bash
make health
docker-compose logs --tail=100 backend | grep ERROR
```

### 2. Identify Affected Services
```bash
docker ps --filter "health=unhealthy"
docker stats --no-stream
```

## 🔍 Diagnosis (Minutes 5-10)

### Check Database
```bash
docker exec ecommerce_backend_prod python manage.py check --database default
```

### Check Redis
```bash
docker exec ecommerce_redis_prod redis-cli ping
```

### Check Logs
```bash
docker-compose logs backend | grep -E "ERROR|Exception"
```

## ⚡ Resolution Strategies

### Scenario A: Database Connection Pool Exhausted
```bash
# Kill idle connections
docker exec ecommerce_postgres_prod psql -U postgres -c "
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle';
"

# Restart backend
docker-compose restart backend
```

### Scenario B: Deployment Issue
```bash
# Rollback
git checkout <previous-version>
docker-compose up -d --build
```

## 📊 Verification

```bash
# Check error rate
watch -n 5 'curl -s http://prometheus:9090/api/v1/query?query=rate(http_requests_total{status=~\"5..\"}[1m])'

# Run smoke tests
./scripts/deployment/smoke-test.sh
```

## 📝 Post-Incident

- Schedule post-mortem within 48 hours
- Update runbook with learnings
- Create action items
```

---

## Automated Patches

### PATCH-001: Add Resource Limits to All Services

**File:** `deploy/docker/compose/production.yml`

```diff
--- a/deploy/docker/compose/production.yml
+++ b/deploy/docker/compose/production.yml
@@ -50,6 +50,15 @@ services:
     networks:
       - backend_network
+    deploy:
+      resources:
+        limits:
+          cpus: '1.0'
+          memory: 1G
+        reservations:
+          cpus: '0.5'
+          memory: 512M
+    security_opt:
+      - no-new-privileges:true
```

### PATCH-002: Enable Vault in Production

**File:** `services/backend/config/settings/production.py`

```diff
--- a/services/backend/config/settings/production.py
+++ b/services/backend/config/settings/production.py
@@ -10,7 +10,7 @@ DEBUG = False
 ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')

 # Vault integration
-USE_VAULT = env.bool('USE_VAULT', default=False)
+USE_VAULT = env.bool('USE_VAULT', default=True)

 if USE_VAULT:
     from core.vault_client import get_secret_or_env
```

### PATCH-003: Add Container Scanning to CI

**File:** `.github/workflows/backend-ci.yml`

```diff
--- a/.github/workflows/backend-ci.yml
+++ b/.github/workflows/backend-ci.yml
@@ -95,3 +95,18 @@ jobs:
           tags: backend-ci:latest
           cache-from: type=gha
           cache-to: type=gha,mode=max
+
+  security-scan:
+    name: Security Scan
+    runs-on: ubuntu-latest
+    needs: [build-sanity]
+    steps:
+      - uses: actions/checkout@v4
+
+      - name: Run Trivy
+        uses: aquasecurity/trivy-action@master
+        with:
+          image-ref: 'backend-ci:latest'
+          severity: 'CRITICAL,HIGH'
+          exit-code: '1'
```

---

## Multi-Phase Roadmap

### Phase 0: Critical Fixes (Week 1)
**Priority:** Immediate
**Story Points:** 21

| Task | Description | Acceptance Criteria | SP |
|------|-------------|---------------------|-----|
| CRIT-001 | Scan and remove secrets from git history | No secrets in git log | 5 |
| CRIT-002 | Add resource limits to all services | All services have CPU/memory limits | 3 |
| CRIT-003 | Add container image scanning to CI | Trivy/Snyk scans pass | 5 |
| HIGH-001 | Implement production Nginx config | Rate limiting, TLS 1.3, security headers | 5 |
| DOC-001 | Remove temporary artifacts | No SUMMARY.md files in repo | 3 |

**Dependencies:** None
**Deliverables:**
- Git history cleaned
- Resource limits in docker-compose
- Security scanning workflow
- Production nginx.conf

---

### Phase 1: Architecture & Restructuring (Week 2-3)
**Priority:** High
**Story Points:** 34

| Task | Description | Acceptance Criteria | SP |
|------|-------------|---------------------|-----|
| STRUCT-001 | Reorganize folder structure | New deploy/, config/, services/ structure | 8 |
| STRUCT-002 | Consolidate docker-compose files | Single source in deploy/docker/compose/ | 5 |
| STRUCT-003 | Merge environment files | All in config/environments/ | 5 |
| STRUCT-004 | Reorganize documentation | New docs structure with operations/ | 5 |
| DOCKER-001 | Create multi-stage Dockerfiles | All services use production Dockerfiles | 8 |
| DOCKER-002 | Optimize Docker images | 60%+ size reduction | 3 |

**Dependencies:** Phase 0 complete
**Deliverables:**
- Enterprise folder structure
- Optimized Docker images
- Consolidated configuration

---

### Phase 2: Docker Production Hardening (Week 3-4)
**Priority:** High
**Story Points:** 55

| Task | Description | Acceptance Criteria | SP |
|------|-------------|---------------------|-----|
| DOCKER-003 | Implement blue-green deployment | Zero-downtime deployments working | 13 |
| DOCKER-004 | Add health checks to all services | All containers have healthchecks | 5 |
| DOCKER-005 | Configure production logging | Structured JSON logs to file/stdout | 5 |
| NGINX-001 | Production Nginx with TLS | SSL A+ rating on SSL Labs | 8 |
| NGINX-002 | Implement rate limiting | Rate limits on all endpoints | 5 |
| NET-001 | Network segmentation | Backend network is internal-only | 8 |
| COMPOSE-001 | Production docker-compose.yml | All best practices implemented | 8 |
| BACKUP-001 | Automated backup scripts | Daily backups to S3 | 3 |

**Dependencies:** Phase 1 complete
**Deliverables:**
- Blue-green deployment working
- Production-grade Nginx
- Network isolation
- Automated backups

---

### Phase 3: CI/CD & Security (Week 5-6)
**Priority:** Critical
**Story Points:** 89

| Task | Description | Acceptance Criteria | SP |
|------|-------------|---------------------|-----|
| CICD-001 | Complete production pipeline | Full pipeline from PR to prod | 13 |
| CICD-002 | Add security gates | Trivy, Snyk, SAST in pipeline | 8 |
| CICD-003 | Implement approval workflows | Manual approval for prod | 5 |
| CICD-004 | Add SBOM generation | SBOM for all images | 5 |
| SEC-001 | Implement Vault integration | Vault managing all secrets | 13 |
| SEC-002 | Secrets rotation automation | Weekly automated rotation | 8 |
| SEC-003 | Security scanning script | Comprehensive audit script | 8 |
| SEC-004 | Container security policy | OPA policies enforced | 8 |
| SEC-005 | Enable non-root containers | All containers run as non-root | 5 |
| SEC-006 | Implement secret scanning | Pre-commit and CI secret scanning | 5 |
| COMP-001 | PCI-DSS compliance checklist | All requirements documented | 8 |
| COMP-002 | SOC 2 controls implementation | Controls mapped and implemented | 3 |

**Dependencies:** Phase 2 complete
**Deliverables:**
- Production CI/CD pipeline
- Vault secrets management
- Security automation
- Compliance documentation

---

### Phase 4: SRE & Observability (Week 7-8)
**Priority:** High
**Story Points:** 55

| Task | Description | Acceptance Criteria | SP |
|------|-------------|---------------------|-----|
| SRE-001 | Create Grafana dashboards | 5+ production dashboards | 13 |
| SRE-002 | Define SLOs/SLIs | Availability, latency, error budget | 8 |
| SRE-003 | Implement SLO alerting | Alerts based on error budget | 8 |
| SRE-004 | Write incident runbooks | 10+ runbooks for common incidents | 13 |
| SRE-005 | Setup on-call rotation | PagerDuty/Opsgenie configured | 5 |
| PROM-001 | Recording rules | Pre-compute SLO metrics | 5 |
| PROM-002 | Alert rules | Comprehensive alerting | 3 |

**Dependencies:** Phase 3 complete
**Deliverables:**
- Production Grafana dashboards
- SLO monitoring
- Incident runbooks
- On-call setup

---

### Phase 5: Performance & Scaling (Week 9-10)
**Priority:** Medium
**Story Points:** 34

| Task | Description | Acceptance Criteria | SP |
|------|-------------|---------------------|-----|
| PERF-001 | Database query optimization | N+1 queries eliminated | 8 |
| PERF-002 | Redis caching strategy | Cache hit rate >90% | 5 |
| PERF-003 | CDN for static assets | Static files served from CDN | 5 |
| PERF-004 | Connection pooling tuning | Optimal pool sizes configured | 3 |
| SCALE-001 | Horizontal scaling tests | Can scale to 10 backend instances | 8 |
| SCALE-002 | Load testing suite | Locust tests for all endpoints | 5 |

**Dependencies:** Phase 4 complete
**Deliverables:**
- Optimized database queries
- Caching implementation
- Load testing results
- Scaling documentation

---

### Phase 6: Compliance & Long-term Maintainability (Week 11-12)
**Priority:** Medium
**Story Points:** 34

| Task | Description | Acceptance Criteria | SP |
|------|-------------|---------------------|-----|
| DR-001 | Disaster recovery procedures | Documented RTO/RPO | 8 |
| DR-002 | Backup verification automation | Weekly restore tests | 5 |
| DR-003 | Multi-region failover plan | Failover procedures documented | 8 |
| MAINT-001 | Automated dependency updates | Dependabot configured | 3 |
| MAINT-002 | Quarterly security reviews | Process documented | 3 |
| MAINT-003 | Infrastructure as Code audit | All infra in version control | 5 |
| DOC-001 | Complete operations manual | Comprehensive ops documentation | 2 |

**Dependencies:** Phase 5 complete
**Deliverables:**
- Disaster recovery plan
- Backup automation
- Maintenance procedures
- Complete documentation

---

### Summary Timeline

| Phase | Duration | Total Story Points | Priority |
|-------|----------|-------------------|----------|
| Phase 0: Critical Fixes | Week 1 | 21 | Immediate |
| Phase 1: Architecture | Week 2-3 | 34 | High |
| Phase 2: Docker Production | Week 3-4 | 55 | High |
| Phase 3: CI/CD & Security | Week 5-6 | 89 | Critical |
| Phase 4: SRE & Observability | Week 7-8 | 55 | High |
| Phase 5: Performance | Week 9-10 | 34 | Medium |
| Phase 6: Compliance | Week 11-12 | 34 | Medium |
| **Total** | **12 weeks** | **322 SP** | |

**Recommended Team Size:** 3-4 engineers
**Velocity Assumption:** ~25 SP per week per team
**Buffer:** 20% for unknowns and tech debt

---

## Deliverables Summary

### Files to Create

#### Configuration Files
- [ ] `config/environments/.env.example` - Consolidated environment template
- [ ] `config/environments/production.env.template` - Production config template
- [ ] `config/secrets/vault-policies/backend-policy.hcl` - Vault policy
- [ ] `config/logging/fluent-bit.conf` - Centralized logging config

#### Docker Files
- [ ] `deploy/docker/compose/base.yml` - Base compose configuration
- [ ] `deploy/docker/compose/production.yml` - Production overrides
- [ ] `deploy/docker/compose/ci.yml` - CI/CD compose file
- [ ] `deploy/docker/images/backend/Dockerfile.production` - Production backend image
- [ ] `deploy/docker/images/ai-services/Dockerfile.template` - AI services template
- [ ] `deploy/docker/images/nginx/Dockerfile` - Production Nginx image
- [ ] `deploy/docker/images/vault/Dockerfile` - Vault container

#### Deployment Scripts
- [ ] `deploy/docker/scripts/blue-green-deploy.sh` - Zero-downtime deployment
- [ ] `deploy/docker/scripts/rollback.sh` - Emergency rollback
- [ ] `deploy/docker/scripts/health-check.sh` - Health verification
- [ ] `deploy/systemd/ecommerce-backend.service` - Systemd unit file

#### Nginx Configuration
- [ ] `deploy/nginx/nginx.conf` - Main nginx config
- [ ] `deploy/nginx/conf.d/api.conf` - API routing config
- [ ] `deploy/nginx/conf.d/security.conf` - Security headers

#### CI/CD Workflows
- [ ] `.github/workflows/production-deploy.yml` - Production pipeline
- [ ] `.github/workflows/security-scan.yml` - Security scanning
- [ ] `.github/workflows/dependency-update.yml` - Automated updates

#### Security Scripts
- [ ] `scripts/security/rotate-secrets.sh` - Secrets rotation
- [ ] `scripts/security/init-vault.sh` - Vault initialization
- [ ] `scripts/security/security-audit.sh` - Comprehensive audit
- [ ] `scripts/security/scan-secrets.sh` - Secret scanning

#### Backup Scripts
- [ ] `scripts/backup/backup-databases.sh` - Database backup
- [ ] `scripts/backup/backup-to-s3.sh` - S3 backup upload
- [ ] `scripts/backup/restore-database.sh` - Database restore
- [ ] `scripts/backup/verify-backup.sh` - Backup verification
- [ ] `scripts/backup/setup-cron.sh` - Automated backup setup

#### Monitoring & SRE
- [ ] `monitoring/grafana/dashboards/system-overview.json` - System dashboard
- [ ] `monitoring/grafana/dashboards/database-metrics.json` - DB dashboard
- [ ] `monitoring/grafana/dashboards/api-performance.json` - API dashboard
- [ ] `monitoring/grafana/dashboards/business-kpis.json` - Business metrics
- [ ] `monitoring/prometheus/recording-rules/slo-rules.yml` - SLO rules
- [ ] `monitoring/prometheus/alerts/slo-alerts.yml` - SLO alerts
- [ ] `monitoring/prometheus/alerts/resource-alerts.yml` - Resource alerts

#### Runbooks
- [ ] `docs/operations/runbooks/high-error-rate.md` - 5xx errors runbook
- [ ] `docs/operations/runbooks/database-failover.md` - DB failover
- [ ] `docs/operations/runbooks/service-outage.md` - Service down
- [ ] `docs/operations/runbooks/high-cpu.md` - CPU spike debugging
- [ ] `docs/operations/runbooks/memory-leak.md` - Memory investigation
- [ ] `docs/operations/runbooks/backup-restore.md` - Backup procedures
- [ ] `docs/operations/incident-response.md` - Incident response plan
- [ ] `docs/operations/disaster-recovery.md` - DR procedures

#### Documentation
- [ ] `docs/deployment/production-checklist.md` - Pre-deployment checklist
- [ ] `docs/deployment/rollback-procedures.md` - Rollback guide
- [ ] `docs/security/security-checklist.md` - Security requirements
- [ ] `docs/security/compliance.md` - Compliance documentation
- [ ] `docs/architecture/network-topology.md` - Network design
- [ ] `docs/development/local-setup.md` - Developer onboarding

### Files to Update

#### Existing Files Requiring Patches
- [ ] `.gitignore` - Add comprehensive ignore patterns
- [ ] `Makefile` - Update compose file paths
- [ ] `README.md` - Update with new structure
- [ ] `docker-compose.production.yml` - Add resource limits
- [ ] `services/backend/config/settings/production.py` - Enable Vault
- [ ] `services/backend/core/vault_client.py` - Complete implementation
- [ ] `.github/workflows/backend-ci.yml` - Add security scanning
- [ ] `.github/workflows/ai-services-ci.yml` - Add security scanning

### Files to Move

#### Repository Restructuring
- [ ] Move `backend/` → `services/backend/`
- [ ] Move `ai-services/` → `services/ai/`
- [ ] Move `env/` → `config/environments/`
- [ ] Move `infrastructure/docker-compose.*.yaml` → `deploy/docker/compose/`
- [ ] Move `infrastructure/nginx/` → `deploy/nginx/`
- [ ] Move `integration_tests/` → `.ci/integration-tests/`
- [ ] Move `scripts/backup_*.sh` → `scripts/backup/`
- [ ] Move `scripts/security_*.sh` → `scripts/security/`

### Files to Delete

#### Temporary/Dead Files
- [ ] `backend_history.patch` (25MB)
- [ ] `git-filter-repo`
- [ ] `OPTIMIZATION_SUMMARY.md`
- [ ] `SECURITY_FIXES_SUMMARY.md`
- [ ] `QUICK_START_SECURE.md` (merge into README)
- [ ] `.archived/` directory
- [ ] `.github/WORKFLOWS_CLEANUP_NOTES.md`
- [ ] `docs/IMPLEMENTATION_SUMMARY.md`
- [ ] `docs/SECURITY_REMEDIATION_COMPLETE.md`
- [ ] `backend/logs/django.log`
- [ ] `ai-services/logs/app.log`
- [ ] `backend/media/*.prof`
- [ ] `infrastructure/env/.env.example.example`

---

## Expected Pull Request Description

```markdown
# Enterprise-Grade Production Modernization

## Summary
Complete transformation of the e-commerce platform from development-ready to true enterprise production grade using Docker-only deployment (no Kubernetes).

## Changes Overview

### 🏗️ Architecture & Structure
- Reorganized repository into enterprise-grade folder structure
- Consolidated Docker Compose files into `deploy/docker/compose/`
- Centralized environment configuration in `config/environments/`
- Separated deployment artifacts into `deploy/` directory

### 🐳 Docker Productionization
- Implemented multi-stage Dockerfiles (60-85% size reduction)
- Added resource limits to all services
- Configured production-grade Nginx with TLS 1.3, rate limiting, security headers
- Implemented blue-green deployment for zero-downtime releases
- Added health checks to all containers
- Network segmentation with internal-only backend network

### 🔐 Security & Compliance
- Full HashiCorp Vault integration for secrets management
- Automated secrets rotation (weekly)
- Container image scanning (Trivy, Snyk, Grype) in CI/CD
- SBOM generation for all images
- Secret scanning in git history and pre-commit hooks
- Non-root containers with read-only filesystems
- Security policies and compliance checklists (PCI-DSS, SOC 2)

### 🚀 CI/CD Pipeline
- Complete production deployment pipeline
- Security gates (SAST, dependency scanning, image scanning)
- Integration tests with isolated test environment
- Automated SBOM generation
- Manual approval workflow for production
- Image signing with cosign

### 📊 SRE & Observability
- Production Grafana dashboards (system, database, API, business KPIs)
- SLO-based alerting (availability, latency, error budget)
- Prometheus recording rules for pre-computed metrics
- Comprehensive incident runbooks (10+ scenarios)
- On-call setup documentation
- Error budget tracking

### 🔄 Operational Excellence
- Automated database backups (daily to S3)
- Backup verification and restore procedures
- Disaster recovery documentation (RTO/RPO defined)
- Blue-green deployment with automatic rollback
- Health check automation
- Load testing suite

## Testing Performed

- ✅ All services build successfully with new Dockerfiles
- ✅ Blue-green deployment tested in staging
- ✅ Security scans pass (0 Critical/High vulnerabilities)
- ✅ Integration tests pass in CI environment
- ✅ Backup/restore procedures verified
- ✅ Load tests show <200ms P95 latency
- ✅ Vault secrets rotation tested
- ✅ Rollback procedure verified

## Migration Guide

See [docs/deployment/migration-guide.md](docs/deployment/migration-guide.md) for step-by-step migration instructions.

### Key Steps:
1. Run secret scanning: `scripts/security/scan-secrets.sh`
2. Initialize Vault: `scripts/security/init-vault.sh`
3. Migrate secrets to Vault
4. Update environment files
5. Deploy with blue-green: `deploy/docker/scripts/blue-green-deploy.sh`

## Breaking Changes

- ⚠️ Environment files moved to `config/environments/`
- ⚠️ Docker Compose files now in `deploy/docker/compose/`
- ⚠️ Vault required for production (secrets no longer in .env)
- ⚠️ Backend/AI services moved to `services/` directory

## Rollback Plan

If issues arise:
```bash
git checkout <previous-version>
docker-compose -f deploy/docker/compose/production.yml up -d
```

## Monitoring

- Grafana: http://grafana.example.com
- Prometheus: http://prometheus.example.com
- Alerts: #ops-alerts Slack channel

## Documentation

- [Architecture](docs/architecture/system-design.md)
- [Deployment Guide](docs/deployment/production-guide.md)
- [Security Checklist](docs/security/security-checklist.md)
- [Incident Runbooks](docs/operations/runbooks/)
- [Disaster Recovery](docs/operations/disaster-recovery.md)

## Metrics

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Docker image size | 3-4 GB | 600 MB - 1.5 GB | 60-75% reduction |
| Deployment time | 30+ min (manual) | <5 min (automated) | 83% faster |
| Security vulnerabilities | Unknown | 0 Critical/High | Production-ready |
| MTTR | Unknown | <15 min (SLO) | Measurable |
| Uptime SLO | N/A | 99.9% | Defined |

## Checklist

- [x] All tests passing
- [x] Documentation updated
- [x] Security scans passing
- [x] Runbooks created
- [x] Migration guide written
- [x] Rollback tested
- [x] Monitoring configured
- [x] Secrets rotated
- [x] Compliance checklist completed

## Reviewers

@senior-devops @security-team @platform-team

---

**This is a major architectural change. Please review thoroughly.**
```

---

## Conclusion

This enterprise-grade modernization plan transforms the e-commerce platform from a development-ready monorepo into a true production-grade system with:

1. **Zero-downtime deployments** via blue-green strategy
2. **Enterprise security** with Vault, secrets rotation, and comprehensive scanning
3. **Production observability** with real dashboards, SLO monitoring, and runbooks
4. **Automated operations** with CI/CD pipelines, backup/restore, and health checks
5. **Compliance-ready** architecture for PCI-DSS, SOC 2, and GDPR
6. **Optimized infrastructure** with 60-85% smaller Docker images
7. **Clear operational procedures** with incident runbooks and disaster recovery

**Total Effort:** 12 weeks, 322 story points
**Team Size:** 3-4 engineers
**Investment:** ~$150K-200K (engineering time)
**ROI:** Production-ready platform, reduced downtime, security compliance, operational excellence

This plan provides a complete blueprint for taking the platform to enterprise production quality using Docker-only deployment, without Kubernetes complexity.
