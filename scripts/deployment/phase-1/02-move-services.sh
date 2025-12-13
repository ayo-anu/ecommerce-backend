#!/bin/bash
# ==============================================================================
# Phase 1 - Step 2: Move Service Directories
# ==============================================================================

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[Step 2]${NC} $1"; }
warn() { echo -e "${YELLOW}[Step 2]${NC} $1"; }

log "Moving service directories to services/..."

# Check if directories exist before moving
if [ -d "backend" ]; then
    log "Moving backend/ to services/backend/"
    git mv backend/ services/backend/
else
    warn "backend/ directory not found, may have been moved already"
fi

if [ -d "ai-services" ]; then
    log "Moving ai-services/ to services/ai/"
    git mv ai-services/ services/ai/
else
    warn "ai-services/ directory not found, may have been moved already"
fi

log "✅ Service directories moved successfully"
log "   backend/ → services/backend/"
log "   ai-services/ → services/ai/"
