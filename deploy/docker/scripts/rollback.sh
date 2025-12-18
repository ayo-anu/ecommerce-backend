#!/bin/bash
# ==============================================================================
# Rollback Script
# ==============================================================================
# Quickly switches traffic back to the previous environment
#
# Usage:
#   ./rollback.sh [OPTIONS]
#
# Options:
#   --confirm            Skip confirmation prompt
#   --dry-run            Show what would be done
#
# This script provides emergency rollback capability by switching nginx
# upstream back to the previous environment.
# ==============================================================================

set -e
set -u
set -o pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
UPSTREAM_CONF="$PROJECT_ROOT/deploy/nginx/conf.d/upstream.conf"
BACKUP_CONF="$UPSTREAM_CONF.backup"

CONFIRM=false
DRY_RUN=false

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --confirm) CONFIRM=true; shift ;;
        --dry-run) DRY_RUN=true; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

detect_current_environment() {
    if grep -q "server api_gateway:8080.*# ACTIVE: blue" "$UPSTREAM_CONF"; then
        CURRENT="blue"
        PREVIOUS="green"
    elif grep -q "server api_gateway_green:8080.*# ACTIVE: green" "$UPSTREAM_CONF"; then
        CURRENT="green"
        PREVIOUS="blue"
    else
        log_error "Cannot determine current environment from upstream config"
        exit 1
    fi
}

confirm_rollback() {
    if [ "$CONFIRM" = false ]; then
        echo "================================================================================"
        log_warning "ROLLBACK CONFIRMATION"
        echo "Current environment: $CURRENT"
        echo "Will rollback to: $PREVIOUS"
        echo "================================================================================"
        read -p "Are you sure you want to rollback? (yes/no): " -r
        echo

        if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
            log_info "Rollback cancelled"
            exit 0
        fi
    fi
}

perform_rollback() {
    log_info "Rolling back from $CURRENT to $PREVIOUS..."

    if [ "$DRY_RUN" = true ]; then
        log_warning "[DRY RUN] Would switch traffic from $CURRENT to $PREVIOUS"
        return 0
    fi

    # Create backup
    cp "$UPSTREAM_CONF" "${UPSTREAM_CONF}.pre-rollback"

    # Switch based on previous environment
    if [ "$PREVIOUS" = "blue" ]; then
        # Switch back to blue
        sed -i.tmp \
            -e 's/# server api_gateway:8080.*# INACTIVE: blue/server api_gateway:8080 max_fails=3 fail_timeout=30s;  # ACTIVE: blue/' \
            -e 's/server api_gateway_green:8080.*# ACTIVE: green/# server api_gateway_green:8080  # INACTIVE: green/' \
            "$UPSTREAM_CONF"
    else
        # Switch back to green
        sed -i.tmp \
            -e 's/server api_gateway:8080.*# ACTIVE: blue/# server api_gateway:8080  # INACTIVE: blue/' \
            -e 's/# server api_gateway_green:8080.*# INACTIVE: green/server api_gateway_green:8080 max_fails=3 fail_timeout=30s;  # ACTIVE: green/' \
            "$UPSTREAM_CONF"
    fi

    rm -f "$UPSTREAM_CONF.tmp"

    # Test and reload nginx
    log_info "Testing nginx configuration..."
    if docker exec ecommerce_nginx nginx -t > /dev/null 2>&1; then
        log_info "Reloading nginx..."
        docker exec ecommerce_nginx nginx -s reload

        if [ $? -eq 0 ]; then
            log_success "Rollback completed successfully!"
            log_info "Traffic is now routed to: $PREVIOUS"
            return 0
        else
            log_error "Failed to reload nginx"
            return 1
        fi
    else
        log_error "Nginx configuration test failed, restoring original config"
        mv "${UPSTREAM_CONF}.pre-rollback" "$UPSTREAM_CONF"
        return 1
    fi
}

verify_rollback() {
    log_info "Verifying rollback..."

    if [ "$DRY_RUN" = true ]; then
        log_warning "[DRY RUN] Would verify rollback"
        return 0
    fi

    sleep 2

    # Quick health check
    if docker exec ecommerce_nginx curl -sf http://localhost/health > /dev/null 2>&1; then
        log_success "Service is responding after rollback"
    else
        log_warning "Service health check failed, but rollback completed"
    fi
}

main() {
    echo "================================================================================"
    echo "Emergency Rollback"
    echo "================================================================================"

    # Check if nginx is running
    if ! docker ps | grep -q ecommerce_nginx; then
        log_error "Nginx container is not running"
        exit 1
    fi

    # Check if config file exists
    if [ ! -f "$UPSTREAM_CONF" ]; then
        log_error "Upstream config not found: $UPSTREAM_CONF"
        exit 1
    fi

    # Detect environments
    detect_current_environment

    # Confirm rollback
    confirm_rollback

    # Perform rollback
    if ! perform_rollback; then
        log_error "Rollback failed"
        exit 1
    fi

    # Verify rollback
    verify_rollback

    echo "================================================================================"
    log_success "Rollback complete!"
    log_info "Monitor the application to ensure stability"
    echo "================================================================================"
}

main
