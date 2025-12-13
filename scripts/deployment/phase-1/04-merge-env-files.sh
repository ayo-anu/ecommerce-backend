#!/bin/bash
# ==============================================================================
# Phase 1 - Step 4: Merge Environment Files
# ==============================================================================

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${GREEN}[Step 4]${NC} $1"; }
warn() { echo -e "${YELLOW}[Step 4]${NC} $1"; }
error() { echo -e "${RED}[Step 4]${NC} $1"; }

# Helper function to move files (handles both tracked and untracked)
safe_move() {
    local src=$1
    local dest=$2

    if [ ! -f "$src" ]; then
        return 0
    fi

    # Check if file is tracked in git
    if git ls-files --error-unmatch "$src" > /dev/null 2>&1; then
        # File is tracked, use git mv
        git mv "$src" "$dest"
    else
        # File is not tracked (gitignored), use regular mv
        warn "File $src not tracked in git (gitignored), using regular mv"
        mv "$src" "$dest"
    fi
}

log "Consolidating environment files..."

# Move root .env.example
if [ -f ".env.example" ]; then
    log "Moving .env.example → config/environments/.env.example"
    safe_move ".env.example" "config/environments/.env.example"
fi

# Move backend env template
if [ -f "services/backend/.env.example" ]; then
    log "Moving backend/.env.example → config/environments/backend.env.template"
    safe_move "services/backend/.env.example" "config/environments/backend.env.template"
fi

# Move AI services env template
if [ -f "services/ai/.env.example" ]; then
    log "Moving ai-services/.env.example → config/environments/ai-services.env.template"
    safe_move "services/ai/.env.example" "config/environments/ai-services.env.template"
fi

# Move infrastructure env templates
if [ -f "infrastructure/env/.env.development" ]; then
    log "Moving infrastructure .env.development → config/environments/development.env.template"
    safe_move "infrastructure/env/.env.development" "config/environments/development.env.template"
fi

if [ -f "infrastructure/env/.env.production" ]; then
    log "Moving infrastructure .env.production → config/environments/production.env.template"
    safe_move "infrastructure/env/.env.production" "config/environments/production.env.template"
fi

if [ -f "infrastructure/env/.env.vault.template" ]; then
    log "Moving vault template"
    safe_move "infrastructure/env/.env.vault.template" "config/environments/vault.env.template"
fi

# Check for committed secrets in env/ directory
if [ -d "env" ]; then
    warn "WARNING: env/ directory exists"

    # Check if it's in git
    if git ls-files env/ | grep -q .; then
        error "⚠️  CRITICAL: env/ directory contains tracked files!"
        error "These files may contain secrets and should NOT be in git"
        error ""
        error "Files found:"
        git ls-files env/
        error ""
        error "Action required:"
        error "1. Review files for secrets"
        error "2. Rotate any exposed credentials"
        error "3. Remove from git: git rm -rf env/"
        error ""
        error "Stopping execution. Please handle secrets manually."
        exit 1
    else
        log "env/ directory not tracked in git (good)"
        log "Removing from filesystem..."
        rm -rf env/
    fi
fi

# Create service-specific env templates if they exist as individual files
if [ -d "infrastructure/env" ] && [ "$(ls -A infrastructure/env 2>/dev/null)" ]; then
    log "Moving remaining infrastructure env files..."
    mkdir -p config/environments/services/

    for env_file in infrastructure/env/*.env; do
        if [ -f "$env_file" ]; then
            filename=$(basename "$env_file")
            log "  Moving $filename to config/environments/services/"
            safe_move "$env_file" "config/environments/services/${filename%.env}.env.template"
        fi
    done

    # Remove empty infrastructure/env directory
    if [ -d "infrastructure/env" ] && [ ! "$(ls -A infrastructure/env)" ]; then
        rmdir infrastructure/env
    fi
fi

log "✅ Environment files consolidated"
log "   All templates now in: config/environments/"
