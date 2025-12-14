#!/bin/bash
# ==============================================================================
# Phase 1 - Step 7: Update File References
# ==============================================================================

set -euo pipefail

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[Step 7]${NC} $1"; }
info() { echo -e "${BLUE}[Step 7]${NC} $1"; }

log "Updating file references across the repository..."

# Update Makefile
if [ -f "Makefile" ]; then
    log "Updating Makefile..."

    # Docker compose paths
    sed -i 's|deploy/docker/compose/base\.yaml|deploy/docker/compose/base.yml|g' Makefile
    sed -i 's|deploy/docker/compose/base\.dev\.yaml|deploy/docker/compose/development.yml|g' Makefile
    sed -i 's|deploy/docker/compose/base\.prod\.yaml|deploy/docker/compose/production.yml|g' Makefile
    sed -i 's|docker-compose\.ci\.yml|deploy/docker/compose/ci.yml|g' Makefile

    # Service paths
    sed -i 's|services/backend/|services/services/backend/|g' Makefile
    sed -i 's|services/ai/|services/ai/|g' Makefile
fi

# Update GitHub workflows
log "Updating GitHub Actions workflows..."
if [ -d ".github/workflows" ]; then
    find .github/workflows -type f -name "*.yml" -o -name "*.yaml" | while read -r workflow; do
        # Service paths
        sed -i 's|services/backend/|services/services/backend/|g' "$workflow"
        sed -i 's|services/ai/|services/ai/|g' "$workflow"

        # Docker compose paths
        sed -i 's|deploy/docker/compose/base|deploy/docker/compose/base|g' "$workflow"
        sed -i 's|docker-compose\.ci\.yml|deploy/docker/compose/ci.yml|g' "$workflow"

        # Context paths for Docker builds
        sed -i 's|context: \./backend|context: ./services/backend|g' "$workflow"
        sed -i 's|context: \./ai-services|context: ./services/ai|g' "$workflow"
    done
fi

# Update Docker Compose files
log "Updating Docker Compose context paths..."
if [ -d "deploy/docker/compose" ]; then
    find deploy/docker/compose -type f \( -name "*.yml" -o -name "*.yaml" \) | while read -r compose_file; do
        # Update build contexts
        sed -i 's|context: \./backend|context: ../../services/backend|g' "$compose_file"
        sed -i 's|context: backend|context: ../../services/backend|g' "$compose_file"
        sed -i 's|context: \./ai-services|context: ../../services/ai|g' "$compose_file"
        sed -i 's|context: ai-services|context: ../../services/ai|g' "$compose_file"

        # Update dockerfile paths
        sed -i 's|dockerfile: services/backend/Dockerfile|dockerfile: services/services/backend/Dockerfile|g' "$compose_file"
        sed -i 's|dockerfile: services/ai/|dockerfile: services/ai/|g' "$compose_file"

        # Update volume paths
        sed -i 's|\.\/backend:|./services/backend:|g' "$compose_file"
        sed -i 's|\.\/ai-services:|./services/ai:|g' "$compose_file"

        # Update monitoring and infrastructure paths
        sed -i 's|\./monitoring:|../../monitoring:|g' "$compose_file" || true
        sed -i 's|\./infrastructure:|../../infrastructure:|g' "$compose_file" || true
    done
fi

# Update documentation links
log "Updating documentation internal links..."
if [ -d "docs" ]; then
    find docs -type f -name "*.md" | while read -r doc_file; do
        # Service path references
        sed -i 's|(services/backend/|(services/services/backend/|g' "$doc_file"
        sed -i 's|(services/ai/|(services/ai/|g' "$doc_file"
        sed -i 's|`services/backend/|`services/services/backend/|g' "$doc_file"
        sed -i 's|`services/ai/|`services/ai/|g' "$doc_file"

        # Docker compose references
        sed -i 's|(deploy/docker/compose/base|(deploy/docker/compose/|g' "$doc_file"
        sed -i 's|`deploy/docker/compose/base|`deploy/docker/compose/|g' "$doc_file"

        # Documentation path references
        sed -i 's|(docs/DEPLOYMENT_RUNBOOK\.md)|(docs/deployment/runbook.md)|g' "$doc_file"
        sed -i 's|(docs/DISASTER_RECOVERY\.md)|(docs/operations/disaster-recovery.md)|g' "$doc_file"
        sed -i 's|(docs/architecture\.md)|(docs/architecture/system-design.md)|g' "$doc_file"
    done
fi

# Update README.md
if [ -f "README.md" ]; then
    log "Updating README.md..."

    # Service paths
    sed -i 's|services/backend/|services/services/backend/|g' README.md
    sed -i 's|services/ai/|services/ai/|g' README.md

    # Docker compose commands
    sed -i 's|deploy/docker/compose/base\.yaml|deploy/docker/compose/base.yml|g' README.md
    sed -i 's|deploy/docker/compose/base\.dev\.yaml|deploy/docker/compose/development.yml|g' README.md
    sed -i 's|docker-compose\.local\.yml|deploy/docker/compose/development.yml|g' README.md

    # Documentation references
    sed -i 's|docs/deployment_guide\.md|docs/deployment/docker-deployment.md|g' README.md
    sed -i 's|docs/architecture\.md|docs/architecture/system-design.md|g' README.md
fi

# Update environment file references in docker-compose
log "Updating environment file references..."
if [ -d "deploy/docker/compose" ]; then
    find deploy/docker/compose -type f \( -name "*.yml" -o -name "*.yaml" \) | while read -r compose_file; do
        # Update env_file paths
        sed -i 's|env_file: \.env|env_file: ../../../config/environments/.env|g' "$compose_file"
        sed -i 's|env_file: services/backend/\.env|env_file: ../../../config/environments/backend.env|g' "$compose_file"
        sed -i 's|env_file: infrastructure/env/|env_file: ../../../config/environments/|g' "$compose_file"
    done
fi

# Update Python import paths in backend
log "Updating Python import paths (if needed)..."
# Note: Django apps should still work as they use relative imports from the project root

# Update scripts that reference old paths
if [ -d "scripts" ]; then
    log "Updating script references..."
    find scripts -type f -name "*.sh" | while read -r script_file; do
        sed -i 's|services/backend/|services/services/backend/|g' "$script_file"
        sed -i 's|services/ai/|services/ai/|g' "$script_file"
        sed -i 's|deploy/docker/compose/base|deploy/docker/compose/base|g' "$script_file"
    done
fi

log "✅ File references updated"

info "Updated references in:"
info "  - Makefile"
info "  - GitHub Actions workflows"
info "  - Docker Compose files"
info "  - Documentation (*.md)"
info "  - README.md"
info "  - Scripts (*.sh)"
