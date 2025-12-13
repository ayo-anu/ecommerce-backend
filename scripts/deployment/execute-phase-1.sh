#!/bin/bash
# ==============================================================================
# Phase 1: Architecture Restructuring - Main Execution Script
# ==============================================================================
# This script orchestrates the complete Phase 1 transformation
# Prerequisites: Phase 0 complete, clean git working directory
# ==============================================================================

set -euo pipefail

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Logging functions
log() { echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} $1"; }
error() { echo -e "${RED}[$(date +'%H:%M:%S')] ERROR:${NC} $1" >&2; }
warn() { echo -e "${YELLOW}[$(date +'%H:%M:%S')] WARNING:${NC} $1"; }
info() { echo -e "${BLUE}[$(date +'%H:%M:%S')] INFO:${NC} $1"; }
step() { echo -e "${CYAN}[$(date +'%H:%M:%S')] >>>>${NC} $1"; }

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PHASE1_SCRIPTS="$SCRIPT_DIR/phase-1"

# Configuration
DRY_RUN=${DRY_RUN:-false}
SKIP_TESTS=${SKIP_TESTS:-false}
BACKUP_BRANCH="backup/pre-phase-1"
FEATURE_BRANCH="phase-1/architecture-restructure"

# Banner
print_banner() {
    echo -e "${CYAN}"
    echo "============================================================"
    echo "  PHASE 1: ARCHITECTURE RESTRUCTURING"
    echo "  Enterprise-Grade Repository Transformation"
    echo "============================================================"
    echo -e "${NC}"
    echo "Project Root: $PROJECT_ROOT"
    echo "Dry Run: $DRY_RUN"
    echo "Skip Tests: $SKIP_TESTS"
    echo ""
}

# Pre-flight checks
pre_flight_checks() {
    step "Running pre-flight checks..."

    # Check if in project root
    if [ ! -f "$PROJECT_ROOT/README.md" ]; then
        error "Not in project root directory"
        exit 1
    fi

    # Check git status
    if ! git diff-index --quiet HEAD -- 2>/dev/null; then
        error "Uncommitted changes detected. Please commit or stash."
        git status --short
        exit 1
    fi

    # Check current branch
    local current_branch=$(git branch --show-current)
    if [ "$current_branch" == "$FEATURE_BRANCH" ]; then
        warn "Already on feature branch. Continuing..."
    fi

    # Check if Phase 0 complete
    if ! git log --oneline -1 | grep -q "Phase 0"; then
        warn "Phase 0 may not be complete. Continue anyway? (y/n)"
        read -r response
        if [ "$response" != "y" ]; then
            info "Aborted by user"
            exit 0
        fi
    fi

    # Check Docker is running
    if ! docker info > /dev/null 2>&1; then
        error "Docker is not running"
        exit 1
    fi

    log "✅ Pre-flight checks passed"
}

# Create backup and feature branches
create_branches() {
    step "Creating backup and feature branches..."

    local current_branch=$(git branch --show-current)

    # Create backup branch
    if git show-ref --verify --quiet "refs/heads/$BACKUP_BRANCH"; then
        warn "Backup branch $BACKUP_BRANCH already exists"
        warn "Delete it? (y/n)"
        read -r response
        if [ "$response" == "y" ]; then
            git branch -D "$BACKUP_BRANCH"
            git checkout -b "$BACKUP_BRANCH"
        fi
    else
        git checkout -b "$BACKUP_BRANCH"
    fi

    # Create feature branch
    if git show-ref --verify --quiet "refs/heads/$FEATURE_BRANCH"; then
        warn "Feature branch $FEATURE_BRANCH already exists"
        git checkout "$FEATURE_BRANCH"
    else
        git checkout -b "$FEATURE_BRANCH"
    fi

    log "✅ Branches created: backup=$BACKUP_BRANCH, feature=$FEATURE_BRANCH"
}

# Execute phase steps
execute_step() {
    local step_num=$1
    local step_name=$2
    local script_name=$3

    step "Step $step_num: $step_name"

    if [ "$DRY_RUN" == "true" ]; then
        info "DRY RUN: Would execute $script_name"
        return 0
    fi

    local script_path="$PHASE1_SCRIPTS/$script_name"

    if [ ! -f "$script_path" ]; then
        error "Script not found: $script_path"
        return 1
    fi

    if ! bash "$script_path"; then
        error "Step $step_num failed: $step_name"
        return 1
    fi

    log "✅ Step $step_num complete"
    return 0
}

# Main execution
main() {
    cd "$PROJECT_ROOT"

    print_banner
    pre_flight_checks
    create_branches

    log ""
    log "Starting Phase 1 execution..."
    log ""

    # Step 1: Create directory structure
    execute_step 1 "Create Directory Structure" "01-create-directories.sh" || exit 1

    # Step 2: Move service directories
    execute_step 2 "Move Service Directories" "02-move-services.sh" || exit 1

    # Step 3: Consolidate Docker Compose files
    execute_step 3 "Consolidate Docker Compose" "03-consolidate-compose.sh" || exit 1

    # Step 4: Merge environment files
    execute_step 4 "Merge Environment Files" "04-merge-env-files.sh" || exit 1

    # Step 5: Create multi-stage Dockerfiles
    execute_step 5 "Create Multi-Stage Dockerfiles" "05-create-dockerfiles.sh" || exit 1

    # Step 6: Reorganize documentation
    execute_step 6 "Reorganize Documentation" "06-reorganize-docs.sh" || exit 1

    # Step 7: Update file references
    execute_step 7 "Update File References" "07-update-references.sh" || exit 1

    # Step 8: Run tests
    if [ "$SKIP_TESTS" != "true" ]; then
        execute_step 8 "Run Tests" "08-run-tests.sh" || exit 1
    else
        warn "Skipping tests (SKIP_TESTS=true)"
    fi

    # Summary
    echo ""
    log "=========================================="
    log "✅ PHASE 1 COMPLETE!"
    log "=========================================="
    echo ""

    info "Changes Summary:"
    info "  - Services moved to services/"
    info "  - Docker Compose consolidated to deploy/docker/compose/"
    info "  - Environment files in config/environments/"
    info "  - Documentation reorganized in docs/"
    info "  - Multi-stage Dockerfiles created"
    echo ""

    info "Next Steps:"
    info "  1. Review changes: git diff $BACKUP_BRANCH"
    info "  2. Test manually: docker-compose -f deploy/docker/compose/development.yml up"
    info "  3. Commit changes: git add . && git commit -m 'Phase 1: Architecture Restructuring'"
    info "  4. Create PR: gh pr create --title 'Phase 1: Architecture Restructuring'"
    echo ""

    info "Rollback if needed:"
    info "  git checkout $BACKUP_BRANCH"
    echo ""
}

# Trap errors
trap 'error "Script failed at line $LINENO"' ERR

# Run main
main "$@"
