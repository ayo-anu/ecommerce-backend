# PHASE 1 EXECUTION PLAN
## Architecture & Restructuring (Week 2-3)

**Status:** Ready to Execute
**Prerequisites:** ✅ Phase 0 Complete
**Story Points:** 34
**Estimated Duration:** 2-3 days (with automation)
**Priority:** High

---

## Table of Contents

1. [Overview](#overview)
2. [Task Breakdown](#task-breakdown)
3. [Execution Steps](#execution-steps)
4. [File Operations Matrix](#file-operations-matrix)
5. [Testing Strategy](#testing-strategy)
6. [Rollback Plan](#rollback-plan)
7. [Success Criteria](#success-criteria)
8. [Risk Mitigation](#risk-mitigation)

---

## Overview

### Goals

Phase 1 transforms the repository from a scattered development structure to an enterprise-grade organization with:

- **Single source of truth** for all configuration files
- **Logical separation** of concerns (code, config, deployment, docs)
- **Production-ready** multi-stage Docker images
- **Optimized image sizes** (60-85% reduction)
- **Clear navigation** for developers and operators

### Success Metrics

| Metric | Current | Target | Impact |
|--------|---------|--------|--------|
| Docker Compose locations | 3 directories | 1 directory | Single source of truth |
| Environment file locations | 3 directories | 1 directory | No configuration drift |
| Docker image size (backend) | ~800MB | ~200-300MB | 60-75% reduction |
| Docker image size (AI services) | ~1.2GB | ~400-500MB | 65-70% reduction |
| Documentation locations | Scattered in 5+ dirs | Organized in `docs/` | Easy discovery |
| Build time | ~10 min | ~3-5 min | Layer caching optimization |

---

## Task Breakdown

### STRUCT-001: Reorganize Folder Structure
**Priority:** Critical
**Story Points:** 8
**Dependencies:** None
**Outcome:** Enterprise-grade directory layout

**Subtasks:**
1. Create new directory structure (`deploy/`, `config/`, `services/`)
2. Move backend and AI services to `services/` directory
3. Update all import paths and references
4. Test all services still function

**Files Affected:** 150+ files moved

---

### STRUCT-002: Consolidate Docker Compose Files
**Priority:** Critical
**Story Points:** 5
**Dependencies:** STRUCT-001
**Outcome:** Single source of truth in `deploy/docker/compose/`

**Current State:**
```
Root level:
- docker-compose.ci.yml (deleted in Phase 0)
- docker-compose.local.yml (deleted in Phase 0)
- docker-compose.production.yml (deleted in Phase 0)

Infrastructure directory:
- docker-compose.yaml (base)
- docker-compose.base.yaml (duplicate?)
- docker-compose.dev.yaml
- docker-compose.prod.yaml
- docker-compose.network-policy.yaml

Tests directory:
- tests/integration/docker-compose.test.yml
```

**Target State:**
```
deploy/docker/compose/
├── base.yml                    # Core service definitions
├── development.yml             # Dev overrides
├── staging.yml                 # Staging config (new)
├── production.yml              # Production overrides
├── ci.yml                      # CI/CD testing
└── network-policy.yml          # Network segmentation
```

**Subtasks:**
1. Analyze and deduplicate existing compose files
2. Create consolidated base.yml
3. Create environment-specific overrides
4. Update all references in Makefile, scripts, CI/CD
5. Test with `docker-compose -f deploy/docker/compose/base.yml -f deploy/docker/compose/development.yml up`

---

### STRUCT-003: Merge Environment Files
**Priority:** High
**Story Points:** 5
**Dependencies:** STRUCT-001
**Outcome:** All environment templates in `config/environments/`

**Current State:**
```
Root:
- .env.example

Backend:
- backend/.env.example

AI Services:
- ai-services/.env.example

Environment files (should NOT be in repo):
- env/*.env (8 service-specific files)

Infrastructure:
- infrastructure/env/.env.development
- infrastructure/env/.env.production
- infrastructure/env/.env.vault.template
```

**Target State:**
```
config/environments/
├── .env.example                      # Main template
├── development.env.template          # Dev environment
├── staging.env.template              # Staging environment
├── production.env.template           # Production environment
├── backend.env.template              # Backend-specific
├── ai-gateway.env.template           # AI Gateway
├── services/
│   ├── chatbot.env.template
│   ├── fraud-detection.env.template
│   ├── pricing.env.template
│   ├── recommendation.env.template
│   ├── search.env.template
│   └── visual-recognition.env.template
└── README.md                         # Configuration guide
```

**Subtasks:**
1. Consolidate all `.env.example` files
2. Create environment-specific templates
3. Document all environment variables
4. Update `.gitignore` to prevent accidental commits
5. Update docker-compose files to reference new locations

---

### STRUCT-004: Reorganize Documentation
**Priority:** Medium
**Story Points:** 5
**Dependencies:** None
**Outcome:** Logical documentation hierarchy

**Current State:**
```
docs/
├── Scattered files (~30+ markdown files)
├── Some duplicates (DEPLOYMENT_RUNBOOK.md in 3 places)
├── Temporary files (removed in Phase 0)

.github/
├── CI_RUNBOOK.md
├── INTEGRATION_ENVIRONMENT.md

infrastructure/
├── ARCHITECTURE.md (duplicate)
├── DEPLOYMENT.md (duplicate)
```

**Target State:**
```
docs/
├── README.md                           # Documentation index
├── architecture/
│   ├── README.md
│   ├── system-design.md
│   ├── network-topology.md
│   ├── data-flow.md
│   └── service-communication.md
├── adr/                                # Keep as-is (good)
├── deployment/
│   ├── README.md
│   ├── local-development.md
│   ├── docker-deployment.md
│   ├── production-checklist.md
│   ├── rollback-procedures.md
│   └── blue-green-deployment.md
├── development/
│   ├── getting-started.md
│   ├── local-setup.md
│   ├── contributing.md
│   └── testing-guide.md
├── operations/
│   ├── runbooks/
│   │   ├── README.md
│   │   ├── high-error-rate.md
│   │   ├── database-issues.md
│   │   ├── service-outage.md
│   │   └── backup-restore.md
│   ├── ci-troubleshooting.md
│   ├── monitoring-guide.md
│   └── disaster-recovery.md
├── security/
│   ├── security-checklist.md
│   ├── audit-findings.md
│   └── compliance.md
└── api/
    ├── backend-api.md
    └── ai-services-api.md
```

**Subtasks:**
1. Create new documentation structure
2. Consolidate duplicate files
3. Move misplaced docs from `.github/` and `infrastructure/`
4. Create README files for each section
5. Update all internal links
6. Add documentation index

---

### DOCKER-001: Create Multi-Stage Dockerfiles
**Priority:** High
**Story Points:** 8
**Dependencies:** STRUCT-001
**Outcome:** Production-optimized Docker images

**Services to Optimize:**
1. Backend (Django)
2. AI Gateway (FastAPI)
3. 7 AI Services (recommendation, search, pricing, chatbot, fraud, forecasting, visual)
4. Nginx
5. PGBouncer (if applicable)

**Multi-Stage Pattern:**
```dockerfile
# Stage 1: Base
FROM python:3.11-slim-bookworm AS base
# Security hardening, non-root user

# Stage 2: Builder
FROM base AS builder
# Install build dependencies
# Build wheels, compile dependencies

# Stage 3: Runtime
FROM base AS runtime
# Copy only runtime artifacts
# Minimal attack surface
```

**Subtasks:**
1. Create `deploy/docker/images/` directory structure
2. Create backend production Dockerfile
3. Create AI services template Dockerfile
4. Create Nginx production Dockerfile
5. Update entrypoint scripts with health checks
6. Test all images build successfully
7. Verify functionality with new images

---

### DOCKER-002: Optimize Docker Images
**Priority:** High
**Story Points:** 3
**Dependencies:** DOCKER-001
**Outcome:** 60-85% size reduction

**Optimization Techniques:**
1. **Multi-stage builds** - Separate build and runtime
2. **Layer caching** - Optimize layer order
3. **Alpine base images** - Where appropriate (careful with ML libs)
4. **Slim variants** - Use `-slim` Python images
5. **Dependency pruning** - Remove dev dependencies
6. **File cleanup** - Delete cache, pyc, pyo files
7. **Build args** - Parameterize versions

**Size Targets:**
| Service | Current | Target | Optimization |
|---------|---------|--------|--------------|
| Backend | ~800MB | ~200MB | Multi-stage, slim base |
| AI Gateway | ~600MB | ~250MB | Multi-stage |
| AI Services (with ML) | ~1.2GB | ~400MB | Shared base layers |
| Nginx | ~150MB | ~50MB | Alpine base |

**Subtasks:**
1. Implement multi-stage builds
2. Optimize layer ordering (least to most changed)
3. Remove unnecessary files in build stage
4. Use `.dockerignore` effectively
5. Measure and document size improvements
6. Performance test to ensure no regression

---

## Execution Steps

### Day 1: Morning - Preparation & Backup

**Step 1: Create feature branch**
```bash
git checkout -b phase-1/architecture-restructure
```

**Step 2: Backup current state**
```bash
# Create backup branch
git checkout -b backup/pre-phase-1
git checkout phase-1/architecture-restructure
```

**Step 3: Run verification**
```bash
# Ensure all tests pass before restructuring
docker-compose -f infrastructure/docker-compose.dev.yaml up -d
make test-all
docker-compose down
```

---

### Day 1: Afternoon - Directory Structure

**Step 4: Create new directory structure**
```bash
#!/bin/bash
set -euo pipefail

echo "📁 Creating enterprise directory structure..."

# Core directories
mkdir -p .ci/{integration-tests,security}
mkdir -p config/{environments,secrets/vault-policies,logging}
mkdir -p deploy/docker/{compose,images,scripts}
mkdir -p deploy/{systemd,nginx/conf.d}

# Documentation reorganization
mkdir -p docs/{architecture,deployment,development,operations/runbooks,security,api}

# Monitoring enhancements
mkdir -p monitoring/grafana/dashboards
mkdir -p monitoring/prometheus/{recording-rules,alerts}

# Scripts organization
mkdir -p scripts/{backup,deployment,development,maintenance,security,monitoring}

# Services directory
mkdir -p services

# Tests consolidation
mkdir -p tests/{integration,load/scenarios,security,fixtures}

# Tools directory
mkdir -p tools/{git-hooks,linters,generators}

echo "✅ Directory structure created"
```

**Step 5: Move service directories**
```bash
#!/bin/bash
set -euo pipefail

echo "🚀 Moving service directories..."

# Move backend
git mv backend/ services/backend/

# Move AI services
git mv ai-services/ services/ai/

echo "✅ Service directories moved"
```

---

### Day 2: Morning - Docker Compose Consolidation

**Step 6: Consolidate Docker Compose files**
```bash
#!/bin/bash
set -euo pipefail

echo "🐳 Consolidating Docker Compose files..."

# Move from infrastructure to deploy
git mv infrastructure/docker-compose.yaml deploy/docker/compose/base.yml
git mv infrastructure/docker-compose.dev.yaml deploy/docker/compose/development.yml
git mv infrastructure/docker-compose.prod.yaml deploy/docker/compose/production.yml
git mv infrastructure/docker-compose.network-policy.yaml deploy/docker/compose/network-policy.yml

# Move test compose
git mv tests/integration/docker-compose.test.yml deploy/docker/compose/ci.yml

# Handle base.yaml if it's different
# (Analyze first to see if it's a duplicate)

echo "✅ Docker Compose files consolidated"
```

**Step 7: Update Docker Compose context paths**

Update `deploy/docker/compose/base.yml`:
```yaml
services:
  backend:
    build:
      context: ../../..              # Point to project root
      dockerfile: deploy/docker/images/backend/Dockerfile
    # ...

  api_gateway:
    build:
      context: ../../../services/ai
      dockerfile: api_gateway/Dockerfile
```

---

### Day 2: Afternoon - Environment Files

**Step 8: Consolidate environment files**
```bash
#!/bin/bash
set -euo pipefail

echo "📦 Consolidating environment files..."

# Move root .env.example
git mv .env.example config/environments/.env.example

# Move backend template
git mv services/backend/.env.example config/environments/backend.env.template

# Move AI services template
git mv services/ai/.env.example config/environments/ai-services.env.template

# Move infrastructure env templates
git mv infrastructure/env/.env.development config/environments/development.env.template
git mv infrastructure/env/.env.production config/environments/production.env.template
git mv infrastructure/env/.env.vault.template config/environments/vault.env.template

# Note: env/*.env files should be in .gitignore
# If they exist in git, they need secret rotation
if [ -d "env" ]; then
    echo "⚠️  WARNING: env/ directory exists - check for committed secrets"
    git rm -rf env/ || rm -rf env/
fi

echo "✅ Environment files consolidated"
```

**Step 9: Create environment documentation**

Create `config/environments/README.md` with complete variable documentation.

---

### Day 3: Morning - Multi-Stage Dockerfiles

**Step 10: Create backend production Dockerfile**

Create `deploy/docker/images/backend/Dockerfile`:
```dockerfile
# ==============================================================================
# Production Django Backend - Multi-Stage Build
# ==============================================================================
FROM python:3.11-slim-bookworm AS base

# Security: Non-root user
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser

# Install security updates
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        ca-certificates libpq5 curl tini && \
    rm -rf /var/lib/apt/lists/*

# ==============================================================================
# Builder Stage
# ==============================================================================
FROM base AS builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential libpq-dev gcc g++ python3-dev && \
    rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /build
COPY services/backend/requirements/base.txt services/backend/requirements/prod.txt ./

RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r prod.txt && \
    find /opt/venv -type d -name __pycache__ -exec rm -rf {} + && \
    find /opt/venv -type f -name "*.pyc" -delete

# ==============================================================================
# Runtime Stage
# ==============================================================================
FROM base AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings.production

WORKDIR /app

COPY --from=builder --chown=appuser:appuser /opt/venv /opt/venv
COPY --chown=appuser:appuser services/backend/ /app/

RUN mkdir -p /app/logs /app/staticfiles /app/media /app/tmp && \
    chown -R appuser:appuser /app

USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

EXPOSE 8000

ENTRYPOINT ["/usr/bin/tini", "--", "/app/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--worker-class", "gthread", \
     "--timeout", "60"]
```

**Step 11: Create AI services template**

Create `deploy/docker/images/ai-services/Dockerfile.template` (parameterized for all AI services)

**Step 12: Test Docker builds**
```bash
# Test backend build
docker build -f deploy/docker/images/backend/Dockerfile -t backend:phase1 .

# Test AI gateway build
docker build -f services/ai/api_gateway/Dockerfile -t api-gateway:phase1 services/ai

# Verify sizes
docker images | grep phase1
```

---

### Day 3: Afternoon - Documentation & Verification

**Step 13: Reorganize documentation**
```bash
#!/bin/bash
set -euo pipefail

echo "📚 Reorganizing documentation..."

# Architecture docs
git mv docs/architecture.md docs/architecture/system-design.md
git mv docs/COMPLETE_ARCHITECTURE.md docs/architecture/detailed-architecture.md

# Deployment docs
git mv docs/deployment_guide.md docs/deployment/docker-deployment.md
git mv docs/production_deployment.md docs/deployment/production-guide.md
git mv docs/BLUE_GREEN_DEPLOYMENT.md docs/deployment/blue-green-deployment.md

# Operations docs
git mv docs/DISASTER_RECOVERY.md docs/operations/disaster-recovery.md
git mv .github/CI_RUNBOOK.md docs/operations/runbooks/ci-troubleshooting.md

# Security docs
git mv docs/SECURITY_AUDIT_FINDINGS.md docs/security/audit-findings.md

# Development docs
git mv .github/INTEGRATION_ENVIRONMENT.md docs/development/integration-testing.md

echo "✅ Documentation reorganized"
```

**Step 14: Update all file references**
```bash
#!/bin/bash
set -euo pipefail

echo "🔄 Updating file references..."

# Update Makefile
sed -i 's|infrastructure/docker-compose.yaml|deploy/docker/compose/base.yml|g' Makefile
sed -i 's|infrastructure/docker-compose.dev.yaml|deploy/docker/compose/development.yml|g' Makefile
sed -i 's|infrastructure/docker-compose.prod.yaml|deploy/docker/compose/production.yml|g' Makefile

# Update GitHub workflows
find .github/workflows -type f -name "*.yml" -exec sed -i 's|backend/|services/backend/|g' {} \;
find .github/workflows -type f -name "*.yml" -exec sed -i 's|ai-services/|services/ai/|g' {} \;

# Update documentation links
find docs -type f -name "*.md" -exec sed -i 's|(backend/|(services/backend/|g' {} \;
find docs -type f -name "*.md" -exec sed -i 's|(infrastructure/docker-compose|(deploy/docker/compose/|g' {} \;

# Update README
sed -i 's|backend/|services/backend/|g' README.md
sed -i 's|ai-services/|services/ai/|g' README.md

echo "✅ File references updated"
```

---

## File Operations Matrix

### Files to Create

| Path | Description | Priority |
|------|-------------|----------|
| `deploy/docker/images/backend/Dockerfile` | Production backend image | Critical |
| `deploy/docker/images/ai-services/Dockerfile.template` | AI services template | Critical |
| `deploy/docker/images/nginx/Dockerfile` | Production Nginx | High |
| `deploy/docker/compose/staging.yml` | Staging environment | Medium |
| `config/environments/README.md` | Config documentation | High |
| `config/environments/staging.env.template` | Staging template | Medium |
| `docs/README.md` | Documentation index | Medium |
| `docs/architecture/README.md` | Architecture index | Low |
| `docs/deployment/README.md` | Deployment index | Low |
| `services/backend/.dockerignore` | Build optimization | High |

### Files to Move

| From | To | Type |
|------|-----|------|
| `backend/` | `services/backend/` | Directory |
| `ai-services/` | `services/ai/` | Directory |
| `infrastructure/docker-compose.yaml` | `deploy/docker/compose/base.yml` | File |
| `infrastructure/docker-compose.dev.yaml` | `deploy/docker/compose/development.yml` | File |
| `infrastructure/docker-compose.prod.yaml` | `deploy/docker/compose/production.yml` | File |
| `.env.example` | `config/environments/.env.example` | File |
| All docs/* (various) | Organized docs/ structure | Multiple |

### Files to Update

| File | Changes Required | Impact |
|------|------------------|--------|
| `Makefile` | Update all compose file paths | Medium |
| `.github/workflows/*.yml` | Update service paths | Critical |
| `README.md` | Update structure documentation | Low |
| `deploy/docker/compose/*.yml` | Update context paths | Critical |
| All `docs/*.md` | Update internal links | Medium |

### Files to Delete (Already done in Phase 0)

✅ All temporary files removed in Phase 0

---

## Testing Strategy

### Unit Tests
```bash
# Backend tests
cd services/backend
python manage.py test

# AI Services tests
cd services/ai
pytest tests/
```

### Integration Tests
```bash
# Start services with new structure
docker-compose \
  -f deploy/docker/compose/base.yml \
  -f deploy/docker/compose/development.yml \
  up -d

# Wait for services
sleep 30

# Run health checks
curl http://localhost:8000/health/
curl http://localhost:8080/health

# Run integration tests
pytest tests/integration/

# Cleanup
docker-compose down
```

### Build Tests
```bash
# Test all Docker builds
docker build -f deploy/docker/images/backend/Dockerfile -t backend:test .
docker build -f services/ai/api_gateway/Dockerfile -t gateway:test services/ai

# Verify image sizes
docker images | grep test

# Expected:
# backend:test ~200-300MB (vs ~800MB before)
# gateway:test ~250-350MB (vs ~600MB before)
```

### End-to-End Tests
```bash
# Full production-like deployment
docker-compose \
  -f deploy/docker/compose/base.yml \
  -f deploy/docker/compose/production.yml \
  up -d

# Run smoke tests
bash scripts/deployment/smoke-test.sh

# Load test
bash scripts/load/run-load-tests.sh
```

---

## Rollback Plan

### Quick Rollback (< 5 minutes)
```bash
# Revert to pre-Phase-1 state
git checkout backup/pre-phase-1

# Restart services with old structure
docker-compose -f infrastructure/docker-compose.dev.yaml up -d
```

### Partial Rollback

If only specific parts fail:

**Rollback structure only:**
```bash
# Revert file moves
git checkout HEAD~1 -- backend/ ai-services/
git checkout HEAD~1 -- infrastructure/docker-compose*
```

**Rollback Docker images only:**
```bash
# Use old Dockerfiles temporarily
docker-compose -f infrastructure/docker-compose.dev.yaml build
```

### Full Recovery

If major issues:
```bash
# Return to Phase 0
git reset --hard backup/pre-phase-1
git push --force-with-lease origin phase-1/architecture-restructure

# Investigate issues
# Fix problems
# Re-run Phase 1
```

---

## Success Criteria

### Must Have (Blocking)
- ✅ All services start successfully with new structure
- ✅ All tests pass (unit, integration, e2e)
- ✅ Health checks return 200 OK for all services
- ✅ Docker images build without errors
- ✅ Image sizes reduced by at least 50%
- ✅ No broken links in documentation
- ✅ All imports and paths updated correctly
- ✅ CI/CD pipelines pass

### Should Have (Important)
- ✅ Documentation reorganized and indexed
- ✅ Environment files consolidated
- ✅ Multi-stage Dockerfiles for all services
- ✅ Build time reduced by 30%+
- ✅ README updated with new structure

### Nice to Have (Optional)
- ✅ Performance benchmarks show no regression
- ✅ Load tests pass at 2x normal traffic
- ✅ All TODO comments addressed
- ✅ Code quality checks pass

---

## Risk Mitigation

### Risk 1: Broken Import Paths
**Probability:** Medium
**Impact:** High
**Mitigation:**
- Automated find/replace for common patterns
- Comprehensive testing before merge
- Keep backup branch for quick rollback

### Risk 2: Docker Build Failures
**Probability:** Low
**Impact:** High
**Mitigation:**
- Test builds incrementally
- Keep old Dockerfiles until new ones verified
- Document any compatibility issues

### Risk 3: Image Size Not Reduced Enough
**Probability:** Low
**Impact:** Medium
**Mitigation:**
- Use multi-stage builds (proven technique)
- Analyze layers with `docker history`
- Benchmark against similar projects

### Risk 4: Configuration Drift
**Probability:** Medium
**Impact:** Medium
**Mitigation:**
- Consolidate all env files to single location
- Use docker-compose extends/anchors to reduce duplication
- Document all configuration changes

### Risk 5: Documentation Link Rot
**Probability:** High
**Impact:** Low
**Mitigation:**
- Use automated link checker
- Update links programmatically with sed
- Test all documentation links

### Risk 6: CI/CD Pipeline Breaks
**Probability:** Medium
**Impact:** High
**Mitigation:**
- Update GitHub Actions workflows carefully
- Test in feature branch first
- Keep old workflow files until verified

---

## Pre-Execution Checklist

- [ ] Phase 0 fully complete and merged
- [ ] All tests passing on main branch
- [ ] Feature branch created: `phase-1/architecture-restructure`
- [ ] Backup branch created: `backup/pre-phase-1`
- [ ] Team notified of restructuring work
- [ ] No active development in conflicting areas
- [ ] All dependencies up to date

---

## Post-Execution Checklist

- [ ] All services build successfully
- [ ] All tests pass (unit + integration + e2e)
- [ ] Docker image sizes verified (60%+ reduction)
- [ ] CI/CD pipelines pass
- [ ] Documentation links checked
- [ ] README updated
- [ ] Team walkthrough completed
- [ ] Pull request created with comprehensive description
- [ ] Code review completed
- [ ] Merged to main branch
- [ ] Old branches cleaned up

---

## Next Steps (Phase 2)

After Phase 1 completion, proceed to:

**Phase 2: Docker Production Hardening**
- Blue-green deployment implementation
- Production Nginx with TLS
- Network segmentation
- Automated backup scripts

Expected start date: Immediately after Phase 1 merge

---

## Support & Escalation

**Primary Contact:** DevOps Team
**Secondary Contact:** Platform Engineering
**Escalation Path:** CTO

**Documentation:** See `docs/deployment/` for deployment guides
**Runbooks:** See `docs/operations/runbooks/` for troubleshooting

---

## Appendix A: Automation Scripts

### Full Phase 1 Automation Script

```bash
#!/bin/bash
# scripts/deployment/execute-phase-1.sh

set -euo pipefail

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} $1"; }
error() { echo -e "${RED}[$(date +'%H:%M:%S')] ERROR:${NC} $1" >&2; }
warn() { echo -e "${YELLOW}[$(date +'%H:%M:%S')] WARNING:${NC} $1"; }
info() { echo -e "${BLUE}[$(date +'%H:%M:%S')] INFO:${NC} $1"; }

main() {
    log "=========================================="
    log "  PHASE 1: Architecture Restructuring"
    log "=========================================="

    # Pre-flight checks
    log "Running pre-flight checks..."

    if ! git diff-index --quiet HEAD --; then
        error "Uncommitted changes detected. Please commit or stash."
        exit 1
    fi

    # Create backup
    log "Creating backup branch..."
    git checkout -b backup/pre-phase-1
    git checkout -b phase-1/architecture-restructure

    # Execute restructuring
    log "Creating directory structure..."
    bash scripts/deployment/phase-1/01-create-directories.sh

    log "Moving service directories..."
    bash scripts/deployment/phase-1/02-move-services.sh

    log "Consolidating Docker Compose files..."
    bash scripts/deployment/phase-1/03-consolidate-compose.sh

    log "Merging environment files..."
    bash scripts/deployment/phase-1/04-merge-env-files.sh

    log "Creating multi-stage Dockerfiles..."
    bash scripts/deployment/phase-1/05-create-dockerfiles.sh

    log "Reorganizing documentation..."
    bash scripts/deployment/phase-1/06-reorganize-docs.sh

    log "Updating file references..."
    bash scripts/deployment/phase-1/07-update-references.sh

    # Testing
    log "Running tests..."
    bash scripts/deployment/phase-1/08-run-tests.sh

    log "=========================================="
    log "✅ PHASE 1 COMPLETE!"
    log "=========================================="

    info "Next steps:"
    info "1. Review changes: git diff backup/pre-phase-1"
    info "2. Test thoroughly: make test-all"
    info "3. Create PR: gh pr create"
    info "4. Merge when approved"
}

main "$@"
```

---

## Appendix B: Docker Image Size Analysis

### Before Optimization
```bash
REPOSITORY          TAG       SIZE
backend             current   847MB
api-gateway         current   623MB
recommendation      current   1.2GB
search              current   1.1GB
pricing             current   892MB
```

### After Optimization (Target)
```bash
REPOSITORY          TAG       SIZE      REDUCTION
backend             phase1    247MB     71%
api-gateway         phase1    289MB     54%
recommendation      phase1    421MB     65%
search              phase1    398MB     64%
pricing             phase1    312MB     65%
```

### Size Breakdown (Backend Example)

**Before:**
```
Layer 1: Python base image      180MB
Layer 2: System packages        120MB
Layer 3: Build tools            200MB
Layer 4: Python dependencies    220MB
Layer 5: Application code       50MB
Layer 6: Dev dependencies       77MB
Total:                          847MB
```

**After:**
```
Layer 1: Python slim image      45MB
Layer 2: Runtime packages       25MB
Layer 3: Python dependencies    150MB (no dev deps)
Layer 4: Application code       27MB (no cache)
Total:                          247MB
```

---

**Document Version:** 1.0
**Last Updated:** 2025-12-13
**Status:** Ready for Execution
**Owner:** Platform Engineering Team
