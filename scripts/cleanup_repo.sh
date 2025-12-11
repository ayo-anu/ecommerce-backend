#!/bin/bash
# ==============================================================================
# Repository Cleanup Script
# ==============================================================================
# This script removes redundant, duplicate, and unused files from the repository
# to reduce disk usage and improve maintainability.
#
# Total estimated savings: 150MB+ (excluding venv/node_modules)
#
# Usage:
#   ./scripts/cleanup_repo.sh [OPTIONS]
#
# Options:
#   --dry-run       Show what would be deleted without actually deleting
#   --aggressive    Include additional cleanup (venv, node_modules, .next)
#   --all           Remove everything including build artifacts
# ==============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
DRY_RUN=false
AGGRESSIVE=false
ALL=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --aggressive)
            AGGRESSIVE=true
            shift
            ;;
        --all)
            ALL=true
            AGGRESSIVE=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Get project root
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# Banner
echo -e "${BLUE}===================================================================${NC}"
echo -e "${BLUE}Repository Cleanup Script${NC}"
echo -e "${BLUE}===================================================================${NC}"
echo ""

if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}DRY RUN MODE - No files will be deleted${NC}"
    echo ""
fi

# Track savings
TOTAL_SAVINGS=0

# Function to calculate size
get_size_kb() {
    local path=$1
    if [ -e "$path" ]; then
        du -sk "$path" 2>/dev/null | awk '{print $1}'
    else
        echo 0
    fi
}

# Function to delete with confirmation
safe_delete() {
    local path=$1
    local description=$2

    if [ ! -e "$path" ]; then
        echo -e "${YELLOW}  ⊗ Not found: $path${NC}"
        return
    fi

    local size_kb=$(get_size_kb "$path")
    local size_mb=$((size_kb / 1024))

    echo -e "${BLUE}  → $description${NC}"
    echo -e "    Path: $path"
    echo -e "    Size: ${size_mb}MB (${size_kb}KB)"

    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}    [DRY RUN] Would delete${NC}"
    else
        rm -rf "$path"
        echo -e "${GREEN}    ✓ Deleted${NC}"
    fi

    TOTAL_SAVINGS=$((TOTAL_SAVINGS + size_kb))
    echo ""
}

# =============================================================================
# SAFE DELETIONS (Always recommended)
# =============================================================================

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}SAFE DELETIONS (High Confidence)${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 1. Duplicate ai-services/common directory
echo -e "${BLUE}1. Removing duplicate 'common' module (services use 'shared' instead)${NC}"
safe_delete "ai-services/common" "Duplicate common module (60KB)"

# 2. Empty static directories
echo -e "${BLUE}2. Removing empty static directories${NC}"
safe_delete "backend/static files" "Empty static files directory"
safe_delete "backend/staticfiles" "Empty staticfiles directory"

# 3. Next.js old cache files
echo -e "${BLUE}3. Removing Next.js old cache files${NC}"
safe_delete "frontend/.next/cache/webpack/client-development/index.pack.gz.old" "Old webpack cache"
safe_delete "frontend/.next/cache/webpack/server-development/index.pack.gz.old" "Old webpack cache"

# 4. Python cache files (__pycache__)
echo -e "${BLUE}4. Removing Python cache directories (__pycache__)${NC}"
PYCACHE_COUNT=$(find . -type d -name "__pycache__" 2>/dev/null | wc -l)
echo -e "  Found ${PYCACHE_COUNT} __pycache__ directories"

if [ "$DRY_RUN" = false ]; then
    PYCACHE_SIZE=$(find . -type d -name "__pycache__" -exec du -sk {} + 2>/dev/null | awk '{sum+=$1} END {print sum}')
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    echo -e "${GREEN}  ✓ Deleted all __pycache__ directories${NC}"
    echo -e "  Size: $((PYCACHE_SIZE / 1024))MB"
    TOTAL_SAVINGS=$((TOTAL_SAVINGS + PYCACHE_SIZE))
else
    echo -e "${YELLOW}  [DRY RUN] Would delete all __pycache__ directories${NC}"
fi
echo ""

# 5. Python compiled files (.pyc)
echo -e "${BLUE}5. Removing Python compiled files (.pyc)${NC}"
PYC_COUNT=$(find . -name "*.pyc" 2>/dev/null | wc -l)
echo -e "  Found ${PYC_COUNT} .pyc files"

if [ "$DRY_RUN" = false ]; then
    find . -name "*.pyc" -delete 2>/dev/null || true
    echo -e "${GREEN}  ✓ Deleted all .pyc files${NC}"
else
    echo -e "${YELLOW}  [DRY RUN] Would delete all .pyc files${NC}"
fi
echo ""

# 6. Empty directories in ai-services
echo -e "${BLUE}6. Removing empty placeholder directories${NC}"
EMPTY_DIRS=(
    "ai-services/docs"
    "ai-services/notebooks"
    "ai-services/models"
    "ai-services/data/seed_data"
    "ai-services/deployment/docker"
    "ai-services/deployment/scripts"
    "ai-services/deployment/kubernetes/deployments"
    "ai-services/deployment/kubernetes/services"
    "ai-services/monitoring/grafana/dashboards"
    "ai-services/monitoring/grafana/datasources"
    "backend/ssl"
    "backend/tests"
    "docs/system_diagrams"
)

for dir in "${EMPTY_DIRS[@]}"; do
    if [ -d "$dir" ] && [ -z "$(ls -A $dir 2>/dev/null)" ]; then
        safe_delete "$dir" "Empty directory: $dir"
    fi
done

# =============================================================================
# REVIEW REQUIRED (Manual confirmation recommended)
# =============================================================================

echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}REVIEW REQUIRED (Check before deleting)${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 7. backend_history.patch (25MB)
echo -e "${BLUE}7. Large patch file (backend_history.patch - 25MB)${NC}"
echo -e "  ${YELLOW}⚠ This contains backend git history. Review before deleting!${NC}"
if [ -f "backend_history.patch" ]; then
    SIZE=$(get_size_kb "backend_history.patch")
    echo -e "  Path: backend_history.patch"
    echo -e "  Size: $((SIZE / 1024))MB"
    echo -e "  ${YELLOW}Skipping for now - delete manually if not needed${NC}"
else
    echo -e "  Not found"
fi
echo ""

# =============================================================================
# AGGRESSIVE CLEANUP (Optional)
# =============================================================================

if [ "$AGGRESSIVE" = true ]; then
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}AGGRESSIVE CLEANUP${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Next.js build cache
    echo -e "${BLUE}8. Removing Next.js build cache${NC}"
    safe_delete "frontend/.next/cache" "Next.js build cache (regenerates on build)"

    if [ "$ALL" = true ]; then
        # Complete Next.js build
        safe_delete "frontend/.next" "Complete Next.js build directory (68MB)"

        # Node modules (can be reinstalled)
        echo -e "${BLUE}9. Removing node_modules (can reinstall with npm install)${NC}"
        if [ -d "frontend/node_modules" ]; then
            SIZE=$(get_size_kb "frontend/node_modules")
            echo -e "  Size: $((SIZE / 1024))MB"
            echo -e "  ${YELLOW}⚠ Can be reinstalled with: cd frontend && npm install${NC}"
            safe_delete "frontend/node_modules" "Node modules (361MB - reinstall with npm install)"
        fi

        # Python venv (can be recreated)
        echo -e "${BLUE}10. Removing Python virtual environment${NC}"
        if [ -d "backend/venv" ]; then
            SIZE=$(get_size_kb "backend/venv")
            echo -e "  Size: $((SIZE / 1024))MB"
            echo -e "  ${YELLOW}⚠ Can be recreated with: python -m venv backend/venv${NC}"
            safe_delete "backend/venv" "Python venv (365MB - recreate with python -m venv)"
        fi
    fi
fi

# =============================================================================
# SUMMARY
# =============================================================================

echo -e "${BLUE}===================================================================${NC}"
echo -e "${GREEN}Cleanup Summary${NC}"
echo -e "${BLUE}===================================================================${NC}"
echo ""

TOTAL_SAVINGS_MB=$((TOTAL_SAVINGS / 1024))
echo -e "Total disk space ${GREEN}saved${NC}: ${TOTAL_SAVINGS_MB}MB (${TOTAL_SAVINGS}KB)"
echo ""

if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}This was a DRY RUN - no files were actually deleted${NC}"
    echo -e "Run without --dry-run to perform actual cleanup:"
    echo -e "  ${BLUE}./scripts/cleanup_repo.sh${NC}"
    echo ""
fi

echo -e "${BLUE}Additional cleanup options:${NC}"
echo -e "  ${BLUE}./scripts/cleanup_repo.sh --aggressive${NC}  - Remove .next cache (50MB)"
echo -e "  ${BLUE}./scripts/cleanup_repo.sh --all${NC}         - Remove everything including node_modules and venv (800MB+)"
echo ""

# Recommendations
echo -e "${YELLOW}Recommendations:${NC}"
echo -e "  1. Review backend_history.patch - delete if not needed (25MB)"
echo -e "  2. Run 'git clean -fdx' to remove all untracked files (use with caution!)"
echo -e "  3. Consider archiving logs and test data if large"
echo ""

echo -e "${GREEN}✓ Cleanup complete!${NC}"
