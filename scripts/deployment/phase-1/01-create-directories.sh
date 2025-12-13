#!/bin/bash
# ==============================================================================
# Phase 1 - Step 1: Create Enterprise Directory Structure
# ==============================================================================

set -euo pipefail

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[Step 1]${NC} $1"; }
info() { echo -e "${BLUE}[Step 1]${NC} $1"; }

log "Creating enterprise directory structure..."

# Core infrastructure directories
mkdir -p .ci/{integration-tests,security}
mkdir -p config/{environments,secrets/vault-policies,logging}
mkdir -p deploy/docker/{compose,images,scripts}
mkdir -p deploy/{systemd,nginx/conf.d,nginx/ssl}

# Image directories for each service
mkdir -p deploy/docker/images/{backend,ai-services,nginx,postgres,redis,vault,pgbouncer}

# Documentation structure
mkdir -p docs/{architecture,deployment,development,operations/runbooks,security,api}

# Enhanced monitoring
mkdir -p monitoring/grafana/dashboards
mkdir -p monitoring/prometheus/{recording-rules,alerts}

# Organized scripts
mkdir -p scripts/{backup,deployment,development,maintenance,security,monitoring}

# Services directory (will move existing services here)
mkdir -p services

# Consolidated tests
mkdir -p tests/{integration,load/scenarios,security,fixtures}

# Development tools
mkdir -p tools/{git-hooks,linters,generators}

log "✅ Directory structure created successfully"

info "Created directories:"
info "  - .ci/ (CI/CD test configurations)"
info "  - config/ (centralized configuration)"
info "  - deploy/ (deployment artifacts)"
info "  - docs/ (organized documentation)"
info "  - monitoring/ (enhanced observability)"
info "  - scripts/ (organized by function)"
info "  - services/ (application code)"
info "  - tests/ (all test types)"
info "  - tools/ (development utilities)"
