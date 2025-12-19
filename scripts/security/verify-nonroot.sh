#!/bin/bash
# ==============================================================================
# Non-Root Container Verification Script
# ==============================================================================
# Verifies that all running containers execute as non-root users
#
# Usage:
#   ./scripts/security/verify-nonroot.sh [options]
#
# Options:
#   --all              Check all running containers (default)
#   --service <name>   Check specific service
#   --fix              Show how to fix root containers
#   --strict           Exit with error if any root containers found
#
# Exit Codes:
#   0 - All containers non-root
#   1 - Some containers running as root
#   2 - No containers running
# ==============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Options
CHECK_ALL=true
SPECIFIC_SERVICE=""
SHOW_FIX=false
STRICT_MODE=false

# ==============================================================================
# Functions
# ==============================================================================

print_header() {
    echo -e "${BLUE}=================================================="
    echo -e "$1"
    echo -e "==================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

check_container_user() {
    local container_name="$1"
    local container_id

    # Get container ID
    container_id=$(docker ps --filter "name=${container_name}" --format "{{.ID}}" | head -1)

    if [ -z "$container_id" ]; then
        print_warning "Container '$container_name' is not running"
        return 2
    fi

    # Get the user running the main process
    local user_info
    user_info=$(docker exec "$container_id" id 2>/dev/null || echo "error")

    if [ "$user_info" = "error" ]; then
        print_error "Failed to check user for container: $container_name"
        return 1
    fi

    # Extract UID
    local uid
    uid=$(echo "$user_info" | grep -oP 'uid=\K\d+' || echo "unknown")

    # Extract username
    local username
    username=$(echo "$user_info" | grep -oP 'uid=\d+\(\K[^)]+' || echo "unknown")

    # Check if running as root (UID 0)
    if [ "$uid" = "0" ]; then
        print_error "Container '$container_name' is running as root (UID: 0)"
        echo "         User info: $user_info"

        if [ "$SHOW_FIX" = true ]; then
            echo ""
            print_info "To fix this container:"
            echo "  1. Update Dockerfile to create and use non-root user:"
            echo "     RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser"
            echo "     USER appuser"
            echo ""
            echo "  2. Update docker-compose.yml:"
            echo "     services:"
            echo "       $container_name:"
            echo "         user: \"1000:1000\""
            echo ""
        fi

        return 1
    else
        print_success "Container '$container_name' runs as non-root"
        echo "         User: $username (UID: $uid)"
        return 0
    fi
}

# ==============================================================================
# Main Script
# ==============================================================================

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --all)
                CHECK_ALL=true
                shift
                ;;
            --service)
                SPECIFIC_SERVICE="$2"
                CHECK_ALL=false
                shift 2
                ;;
            --fix)
                SHOW_FIX=true
                shift
                ;;
            --strict)
                STRICT_MODE=true
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [options]"
                echo ""
                echo "Options:"
                echo "  --all              Check all running containers (default)"
                echo "  --service <name>   Check specific service"
                echo "  --fix              Show how to fix root containers"
                echo "  --strict           Exit with error if any root containers found"
                echo "  --help, -h         Show this help message"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done

    cd "$PROJECT_ROOT"

    print_header "Non-Root Container Verification"
    echo ""
    print_info "Checking containers for non-root execution..."
    echo ""

    # Get running containers
    local running_containers
    if [ "$CHECK_ALL" = true ]; then
        running_containers=$(docker ps --format "{{.Names}}" | grep "^ecommerce_" || true)
    else
        running_containers="ecommerce_${SPECIFIC_SERVICE}"
    fi

    if [ -z "$running_containers" ]; then
        print_warning "No ecommerce containers are running"
        echo ""
        print_info "Start containers with: docker-compose up -d"
        exit 2
    fi

    # Check each container
    local total_containers=0
    local nonroot_containers=0
    local root_containers=0
    local error_containers=0

    while IFS= read -r container_name; do
        if [ -z "$container_name" ]; then
            continue
        fi

        total_containers=$((total_containers + 1))
        echo ""

        if check_container_user "$container_name"; then
            nonroot_containers=$((nonroot_containers + 1))
        else
            exit_code=$?
            if [ $exit_code -eq 1 ]; then
                root_containers=$((root_containers + 1))
            elif [ $exit_code -eq 2 ]; then
                error_containers=$((error_containers + 1))
            fi
        fi
    done <<< "$running_containers"

    # Print summary
    echo ""
    print_header "Verification Summary"
    echo ""
    echo "Total containers checked: $total_containers"
    print_success "Non-root containers:      $nonroot_containers"

    if [ $root_containers -gt 0 ]; then
        print_error "Root containers:          $root_containers"
    else
        echo "Root containers:          $root_containers"
    fi

    if [ $error_containers -gt 0 ]; then
        print_warning "Errors/Not running:       $error_containers"
    fi

    echo ""

    # Final verdict
    if [ $root_containers -eq 0 ] && [ $error_containers -eq 0 ]; then
        print_success "All containers are running as non-root users! 🎉"
        exit 0
    elif [ $root_containers -gt 0 ]; then
        print_error "Security Issue: $root_containers container(s) running as root"

        if [ "$SHOW_FIX" = false ]; then
            print_info "Run with --fix to see remediation steps"
        fi

        if [ "$STRICT_MODE" = true ]; then
            exit 1
        else
            print_warning "Not in strict mode - exiting with success"
            exit 0
        fi
    else
        print_warning "Some containers not running or errors occurred"
        exit 2
    fi
}

main "$@"
