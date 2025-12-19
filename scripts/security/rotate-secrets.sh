#!/bin/bash
# ==============================================================================
# Automated Secrets Rotation Script
# ==============================================================================
# This script automates the rotation of sensitive credentials stored in Vault
#
# Usage:
#   ./scripts/security/rotate-secrets.sh [service]
#
# Arguments:
#   service: Optional - specific service to rotate (database|redis|jwt|all)
#            If not provided, rotates based on schedule
#
# Schedule:
#   - Weekly (Sunday 2 AM): Database passwords, Redis password
#   - Monthly (1st of month): JWT secrets
#
# Prerequisites:
#   - Vault must be running and unsealed
#   - Services must be running
#   - VAULT_ADDR and VAULT_TOKEN must be set
#
# Exit Codes:
#   0 - Success
#   1 - Rotation failed
#   2 - Health check failed after rotation
# ==============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
VAULT_ADDR="${VAULT_ADDR:-http://localhost:8200}"
LOG_DIR="${LOG_DIR:-/var/log/ecommerce}"
LOG_FILE="${LOG_DIR}/secret-rotation.log"
HEALTH_CHECK_URL="${HEALTH_CHECK_URL:-http://localhost:8000/health/}"
SLACK_WEBHOOK_URL="${SLACK_WEBHOOK_URL:-}"

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Logging function
log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date +'%Y-%m-%d %H:%M:%S')
    echo "[${timestamp}] [${level}] ${message}" | tee -a "$LOG_FILE"
}

log_info() {
    log "INFO" "$@"
}

log_error() {
    log "ERROR" "$@"
}

log_success() {
    log "SUCCESS" "$@"
}

# Send Slack notification
send_notification() {
    local status=$1
    local message=$2

    if [ -z "$SLACK_WEBHOOK_URL" ]; then
        log_info "Slack webhook not configured, skipping notification"
        return 0
    fi

    local emoji
    if [ "$status" = "success" ]; then
        emoji="white_check_mark"
    else
        emoji="x"
    fi

    curl -X POST "$SLACK_WEBHOOK_URL" \
        -H 'Content-Type: application/json' \
        -d "{
            \"text\": \":${emoji}: ${message}\",
            \"username\": \"Secrets Rotation Bot\"
        }" \
        --silent --fail || log_error "Failed to send Slack notification"
}

# Check if Vault is available and unsealed
check_vault() {
    log_info "Checking Vault status..."

    if ! curl -s "${VAULT_ADDR}/v1/sys/health" > /dev/null; then
        log_error "Vault is not accessible at ${VAULT_ADDR}"
        return 1
    fi

    local sealed=$(curl -s "${VAULT_ADDR}/v1/sys/seal-status" | jq -r '.sealed')
    if [ "$sealed" = "true" ]; then
        log_error "Vault is sealed! Run unseal-vault.sh first"
        return 1
    fi

    log_success "Vault is accessible and unsealed"
    return 0
}

# Rotate database password
rotate_database_password() {
    log_info "Starting database password rotation..."

    # Generate new strong password
    local new_password=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)

    # Get current password from Vault for rollback
    local current_password=$(curl -s \
        -H "X-Vault-Token: ${VAULT_TOKEN}" \
        "${VAULT_ADDR}/v1/ecommerce/data/backend/database" \
        | jq -r '.data.data.DB_PASSWORD')

    if [ -z "$current_password" ] || [ "$current_password" = "null" ]; then
        log_error "Could not retrieve current database password from Vault"
        return 1
    fi

    log_info "Updating database password in Vault..."
    curl -s \
        -H "X-Vault-Token: ${VAULT_TOKEN}" \
        --request POST \
        --data "{
            \"data\": {
                \"DB_PASSWORD\": \"${new_password}\",
                \"POSTGRES_PASSWORD\": \"${new_password}\",
                \"rotated_at\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
                \"rotated_by\": \"automation\"
            }
        }" \
        "${VAULT_ADDR}/v1/ecommerce/data/backend/database" > /dev/null

    if [ $? -ne 0 ]; then
        log_error "Failed to update password in Vault"
        return 1
    fi

    log_info "Updating database password in PostgreSQL..."
    if ! docker-compose exec -T postgres psql -U postgres -c \
        "ALTER USER ecommerce_user WITH PASSWORD '${new_password}';" > /dev/null 2>&1; then
        log_error "Failed to update password in PostgreSQL, rolling back Vault..."
        # Rollback Vault
        curl -s \
            -H "X-Vault-Token: ${VAULT_TOKEN}" \
            --request POST \
            --data "{\"data\": {\"DB_PASSWORD\": \"${current_password}\", \"POSTGRES_PASSWORD\": \"${current_password}\"}}" \
            "${VAULT_ADDR}/v1/ecommerce/data/backend/database" > /dev/null
        return 1
    fi

    log_info "Restarting backend services..."
    docker-compose restart backend celery_worker > /dev/null 2>&1

    # Wait for services to start
    log_info "Waiting for services to stabilize..."
    sleep 15

    # Health check
    log_info "Running health check..."
    if ! curl -f -s "${HEALTH_CHECK_URL}" > /dev/null; then
        log_error "Health check failed after database password rotation!"
        log_error "Manual intervention required. Previous password: ${current_password}"
        return 2
    fi

    log_success "Database password rotated successfully"
    return 0
}

# Rotate Redis password
rotate_redis_password() {
    log_info "Starting Redis password rotation..."

    # Generate new strong password
    local new_password=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)

    # Get current password from Vault for rollback
    local current_password=$(curl -s \
        -H "X-Vault-Token: ${VAULT_TOKEN}" \
        "${VAULT_ADDR}/v1/ecommerce/data/backend/redis" \
        | jq -r '.data.data.REDIS_PASSWORD')

    if [ -z "$current_password" ] || [ "$current_password" = "null" ]; then
        log_error "Could not retrieve current Redis password from Vault"
        return 1
    fi

    log_info "Updating Redis password in Vault..."
    curl -s \
        -H "X-Vault-Token: ${VAULT_TOKEN}" \
        --request POST \
        --data "{
            \"data\": {
                \"REDIS_PASSWORD\": \"${new_password}\",
                \"REDIS_URL\": \"redis://:${new_password}@redis:6379/0\",
                \"rotated_at\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
                \"rotated_by\": \"automation\"
            }
        }" \
        "${VAULT_ADDR}/v1/ecommerce/data/backend/redis" > /dev/null

    if [ $? -ne 0 ]; then
        log_error "Failed to update password in Vault"
        return 1
    fi

    log_info "Updating Redis password in Redis server..."
    if ! docker-compose exec -T redis redis-cli -a "${current_password}" \
        CONFIG SET requirepass "${new_password}" > /dev/null 2>&1; then
        log_error "Failed to update password in Redis, rolling back Vault..."
        # Rollback Vault
        curl -s \
            -H "X-Vault-Token: ${VAULT_TOKEN}" \
            --request POST \
            --data "{\"data\": {\"REDIS_PASSWORD\": \"${current_password}\"}}" \
            "${VAULT_ADDR}/v1/ecommerce/data/backend/redis" > /dev/null
        return 1
    fi

    log_info "Restarting services that use Redis..."
    docker-compose restart backend api_gateway celery_worker > /dev/null 2>&1

    # Wait for services to start
    log_info "Waiting for services to stabilize..."
    sleep 15

    # Health check
    log_info "Running health check..."
    if ! curl -f -s "${HEALTH_CHECK_URL}" > /dev/null; then
        log_error "Health check failed after Redis password rotation!"
        log_error "Manual intervention required. Previous password: ${current_password}"
        return 2
    fi

    log_success "Redis password rotated successfully"
    return 0
}

# Rotate JWT secret
rotate_jwt_secret() {
    log_info "Starting JWT secret rotation..."
    log_info "WARNING: This will invalidate all existing JWT tokens"

    # Generate new JWT secret
    local new_secret=$(openssl rand -base64 64 | tr -d '\n')

    # Get current secret from Vault for rollback
    local current_secret=$(curl -s \
        -H "X-Vault-Token: ${VAULT_TOKEN}" \
        "${VAULT_ADDR}/v1/ecommerce/data/backend/django" \
        | jq -r '.data.data.JWT_SECRET')

    log_info "Updating JWT secret in Vault..."
    curl -s \
        -H "X-Vault-Token: ${VAULT_TOKEN}" \
        --request POST \
        --data "{
            \"data\": {
                \"JWT_SECRET\": \"${new_secret}\",
                \"rotated_at\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
                \"rotated_by\": \"automation\"
            }
        }" \
        "${VAULT_ADDR}/v1/ecommerce/data/backend/django" > /dev/null

    if [ $? -ne 0 ]; then
        log_error "Failed to update JWT secret in Vault"
        return 1
    fi

    log_info "Restarting backend services..."
    docker-compose restart backend api_gateway > /dev/null 2>&1

    # Wait for services to start
    log_info "Waiting for services to stabilize..."
    sleep 15

    # Health check
    log_info "Running health check..."
    if ! curl -f -s "${HEALTH_CHECK_URL}" > /dev/null; then
        log_error "Health check failed after JWT secret rotation!"
        log_error "Manual intervention required"
        return 2
    fi

    log_success "JWT secret rotated successfully (all tokens invalidated)"
    return 0
}

# Main rotation logic
main() {
    local service="${1:-auto}"
    local exit_code=0

    echo "============================================================"
    echo "  E-Commerce Platform - Secrets Rotation"
    echo "  Started: $(date)"
    echo "============================================================"
    echo ""

    log_info "Secrets rotation started (mode: ${service})"

    # Check Vault availability
    if ! check_vault; then
        log_error "Vault check failed, aborting rotation"
        send_notification "failure" "Secrets rotation failed: Vault unavailable"
        exit 1
    fi

    # Determine what to rotate
    case "$service" in
        database)
            rotate_database_password || exit_code=$?
            ;;
        redis)
            rotate_redis_password || exit_code=$?
            ;;
        jwt)
            rotate_jwt_secret || exit_code=$?
            ;;
        all)
            rotate_database_password || exit_code=$?
            rotate_redis_password || exit_code=$?
            rotate_jwt_secret || exit_code=$?
            ;;
        auto)
            # Schedule-based rotation
            local day_of_week=$(date +%u)  # 1-7 (Monday-Sunday)
            local day_of_month=$(date +%d)

            log_info "Running scheduled rotation (Day of week: ${day_of_week}, Day of month: ${day_of_month})"

            # Weekly: Database and Redis (Sunday)
            if [ "$day_of_week" -eq 7 ]; then
                log_info "Running weekly rotation (Database + Redis)"
                rotate_database_password || exit_code=$?
                rotate_redis_password || exit_code=$?
            fi

            # Monthly: JWT secrets (1st of month)
            if [ "$day_of_month" = "01" ]; then
                log_info "Running monthly rotation (JWT secrets)"
                rotate_jwt_secret || exit_code=$?
            fi

            # If neither condition met
            if [ "$day_of_week" -ne 7 ] && [ "$day_of_month" != "01" ]; then
                log_info "No rotation scheduled for today"
            fi
            ;;
        *)
            log_error "Invalid service: ${service}"
            echo "Usage: $0 [database|redis|jwt|all|auto]"
            exit 1
            ;;
    esac

    # Summary
    echo ""
    echo "============================================================"
    if [ $exit_code -eq 0 ]; then
        log_success "Secrets rotation completed successfully"
        send_notification "success" "Secrets rotation completed successfully"
    else
        log_error "Secrets rotation completed with errors (exit code: ${exit_code})"
        send_notification "failure" "Secrets rotation failed with exit code ${exit_code}"
    fi
    echo "  Finished: $(date)"
    echo "============================================================"

    exit $exit_code
}

# Run main function
main "$@"
