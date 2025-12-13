#!/bin/bash
# ==============================================================================
# Phase 1 - Step 6: Reorganize Documentation
# ==============================================================================

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[Step 6]${NC} $1"; }
warn() { echo -e "${YELLOW}[Step 6]${NC} $1"; }

log "Reorganizing documentation structure..."

# Architecture documentation
if [ -f "docs/architecture.md" ]; then
    log "Moving architecture.md → docs/architecture/system-design.md"
    git mv docs/architecture.md docs/architecture/system-design.md
fi

if [ -f "docs/COMPLETE_ARCHITECTURE.md" ]; then
    log "Moving COMPLETE_ARCHITECTURE.md → docs/architecture/detailed-architecture.md"
    git mv docs/COMPLETE_ARCHITECTURE.md docs/architecture/detailed-architecture.md
fi

if [ -f "docs/ai_services_overview.md" ]; then
    log "Moving AI services overview to architecture/"
    git mv docs/ai_services_overview.md docs/architecture/ai-services.md
fi

# Deployment documentation
if [ -f "docs/deployment_guide.md" ]; then
    log "Moving deployment_guide.md → docs/deployment/docker-deployment.md"
    git mv docs/deployment_guide.md docs/deployment/docker-deployment.md
fi

if [ -f "docs/production_deployment.md" ]; then
    log "Moving production_deployment.md → docs/deployment/production-guide.md"
    git mv docs/production_deployment.md docs/deployment/production-guide.md
fi

if [ -f "docs/BLUE_GREEN_DEPLOYMENT.md" ]; then
    log "Moving blue-green deployment docs"
    git mv docs/BLUE_GREEN_DEPLOYMENT.md docs/deployment/blue-green-deployment.md
fi

if [ -f "docs/DEPLOYMENT_RUNBOOK.md" ]; then
    log "Moving deployment runbook"
    git mv docs/DEPLOYMENT_RUNBOOK.md docs/deployment/runbook.md
fi

# Consolidate Docker documentation
for docker_doc in docs/DOCKER_*.md; do
    if [ -f "$docker_doc" ]; then
        filename=$(basename "$docker_doc")
        log "Moving $filename to docs/deployment/"
        git mv "$docker_doc" "docs/deployment/${filename,,}"
    fi
done

# Operations documentation
if [ -f "docs/DISASTER_RECOVERY.md" ]; then
    log "Moving disaster recovery docs"
    git mv docs/DISASTER_RECOVERY.md docs/operations/disaster-recovery.md
fi

if [ -f ".github/CI_RUNBOOK.md" ]; then
    log "Moving CI runbook to operations/runbooks/"
    git mv .github/CI_RUNBOOK.md docs/operations/runbooks/ci-troubleshooting.md
fi

# Development documentation
if [ -f ".github/INTEGRATION_ENVIRONMENT.md" ]; then
    log "Moving integration environment docs"
    git mv .github/INTEGRATION_ENVIRONMENT.md docs/development/integration-testing.md
fi

# Security documentation
if [ -f "docs/SECURITY_AUDIT_FINDINGS.md" ]; then
    log "Moving security audit findings"
    git mv docs/SECURITY_AUDIT_FINDINGS.md docs/security/audit-findings.md
fi

if [ -f "infrastructure/SECURITY_CHECKLIST.md" ]; then
    log "Moving security checklist from infrastructure/"
    git mv infrastructure/SECURITY_CHECKLIST.md docs/security/security-checklist.md
fi

# Move infrastructure docs
if [ -f "infrastructure/ARCHITECTURE.md" ]; then
    warn "Found duplicate ARCHITECTURE.md in infrastructure/"
    log "Checking if it's different from docs/architecture/"

    # For now, move it as an alternative view
    git mv infrastructure/ARCHITECTURE.md docs/architecture/infrastructure-view.md
fi

if [ -f "infrastructure/DEPLOYMENT.md" ]; then
    warn "Found duplicate DEPLOYMENT.md in infrastructure/"
    git mv infrastructure/DEPLOYMENT.md docs/deployment/infrastructure-deployment.md
fi

if [ -f "infrastructure/DEPLOYMENT_RUNBOOK.md" ]; then
    # Check if docs/deployment/runbook.md already exists
    if [ -f "docs/deployment/runbook.md" ]; then
        warn "Duplicate runbook found, comparing..."
        # If different, keep both; if same, delete
        if ! diff -q infrastructure/DEPLOYMENT_RUNBOOK.md docs/deployment/runbook.md > /dev/null 2>&1; then
            git mv infrastructure/DEPLOYMENT_RUNBOOK.md docs/deployment/runbook-infrastructure.md
        else
            git rm infrastructure/DEPLOYMENT_RUNBOOK.md
        fi
    else
        git mv infrastructure/DEPLOYMENT_RUNBOOK.md docs/deployment/runbook.md
    fi
fi

if [ -f "infrastructure/README.md" ]; then
    log "Moving infrastructure README to deployment/"
    git mv infrastructure/README.md docs/deployment/infrastructure-overview.md
fi

log "✅ Documentation reorganized"
log "   Architecture docs → docs/architecture/"
log "   Deployment docs → docs/deployment/"
log "   Operations docs → docs/operations/"
log "   Security docs → docs/security/"
log "   Development docs → docs/development/"
