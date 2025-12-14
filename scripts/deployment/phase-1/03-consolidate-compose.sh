#!/bin/bash
# ==============================================================================
# Phase 1 - Step 3: Consolidate Docker Compose Files
# ==============================================================================

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[Step 3]${NC} $1"; }
warn() { echo -e "${YELLOW}[Step 3]${NC} $1"; }
info() { echo -e "${BLUE}[Step 3]${NC} $1"; }

log "Consolidating Docker Compose files..."

# Move infrastructure compose files to deploy/docker/compose/
if [ -f "deploy/docker/compose/base.yaml" ]; then
    log "Moving docker-compose.yaml → deploy/docker/compose/base.yml"
    git mv deploy/docker/compose/base.yaml deploy/docker/compose/base.yml
fi

if [ -f "deploy/docker/compose/base.dev.yaml" ]; then
    log "Moving docker-compose.dev.yaml → deploy/docker/compose/development.yml"
    git mv deploy/docker/compose/base.dev.yaml deploy/docker/compose/development.yml
fi

if [ -f "deploy/docker/compose/base.prod.yaml" ]; then
    log "Moving docker-compose.prod.yaml → deploy/docker/compose/production.yml"
    git mv deploy/docker/compose/base.prod.yaml deploy/docker/compose/production.yml
fi

if [ -f "deploy/docker/compose/base.network-policy.yaml" ]; then
    log "Moving docker-compose.network-policy.yaml → deploy/docker/compose/network-policy.yml"
    git mv deploy/docker/compose/base.network-policy.yaml deploy/docker/compose/network-policy.yml
fi

# Move test compose file
if [ -f "tests/integration/docker-compose.test.yml" ]; then
    log "Moving docker-compose.test.yml → deploy/docker/compose/ci.yml"
    git mv tests/integration/docker-compose.test.yml deploy/docker/compose/ci.yml
fi

# Handle base.yaml if it exists and is different
if [ -f "deploy/docker/compose/base.base.yaml" ]; then
    warn "Found docker-compose.base.yaml - checking if it's duplicate..."

    # Check if it's identical to docker-compose.yaml
    if [ -f "deploy/docker/compose/base.yml" ]; then
        if diff -q deploy/docker/compose/base.base.yaml deploy/docker/compose/base.yml > /dev/null 2>&1; then
            log "docker-compose.base.yaml is duplicate, removing..."
            git rm deploy/docker/compose/base.base.yaml
        else
            warn "docker-compose.base.yaml differs from base.yml"
            warn "Manual review required - keeping both for now"
            git mv deploy/docker/compose/base.base.yaml deploy/docker/compose/base-alt.yml
        fi
    else
        git mv deploy/docker/compose/base.base.yaml deploy/docker/compose/base.yml
    fi
fi

# Move resource limits file
if [ -f "infrastructure/docker/resource-limits.yaml" ]; then
    log "Moving resource-limits.yaml to deploy/docker/"
    git mv infrastructure/docker/resource-limits.yaml deploy/docker/resource-limits.yaml
fi

log "✅ Docker Compose files consolidated"

info "New structure:"
info "  deploy/docker/compose/"
info "    ├── base.yml           (core services)"
info "    ├── development.yml    (dev overrides)"
info "    ├── production.yml     (prod config)"
info "    ├── ci.yml             (CI testing)"
info "    └── network-policy.yml (network segmentation)"
