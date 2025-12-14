#!/bin/bash

# ==============================================================================
# Blue/Green Deployment Script
# ==============================================================================
# Zero-downtime deployment using blue/green strategy with Docker Compose.
#
# Blue/Green Deployment:
#   - Two identical production environments (blue and green)
#   - One serves production traffic (active)
#   - One is idle or receiving new deployment (standby)
#   - Traffic switched atomically after validation
#   - Instant rollback by switching back
#
# Usage:
#   ./scripts/blue_green_deploy.sh [deploy|rollback|status]
#
# Examples:
#   ./scripts/blue_green_deploy.sh deploy     # Deploy to standby, switch traffic
#   ./scripts/blue_green_deploy.sh rollback   # Roll back to previous version
#   ./scripts/blue_green_deploy.sh status     # Show current active environment
#
# Requirements:
#   - Docker and Docker Compose
#   - nginx configured for upstream switching
#   - Sufficient resources for two full stacks
# ==============================================================================

set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
ACTIVE_ENV_FILE="/var/run/active_environment"
BLUE_COMPOSE="deploy/docker/compose/base.yaml"
GREEN_COMPOSE="deploy/docker/compose/base.yaml"
BLUE_PROJECT="ecommerce-blue"
GREEN_PROJECT="ecommerce-green"
NGINX_CONTAINER="ecommerce_nginx"
HEALTH_CHECK_TIMEOUT=60
HEALTH_CHECK_INTERVAL=5

# ==============================================================================
# Helper Functions
# ==============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

get_active_environment() {
    if [ -f "$ACTIVE_ENV_FILE" ]; then
        cat "$ACTIVE_ENV_FILE"
    else
        echo "blue"  # Default to blue
    fi
}

set_active_environment() {
    local env=$1
    echo "$env" > "$ACTIVE_ENV_FILE"
    log_success "Active environment set to: $env"
}

get_standby_environment() {
    local active=$(get_active_environment)
    if [ "$active" == "blue" ]; then
        echo "green"
    else
        echo "blue"
    fi
}

get_project_name() {
    local env=$1
    if [ "$env" == "blue" ]; then
        echo "$BLUE_PROJECT"
    else
        echo "$GREEN_PROJECT"
    fi
}

# ==============================================================================
# Health Check Functions
# ==============================================================================

wait_for_health() {
    local env=$1
    local project=$(get_project_name "$env")
    local elapsed=0

    log_info "Waiting for $env environment to be healthy..."

    while [ $elapsed -lt $HEALTH_CHECK_TIMEOUT ]; do
        # Check backend health
        if docker-compose -p "$project" exec -T backend wget -q -O- http://localhost:8000/health/ 2>/dev/null | grep -q "healthy"; then
            # Check API gateway health
            if docker-compose -p "$project" exec -T api_gateway wget -q -O- http://localhost:8080/health 2>/dev/null | grep -q "healthy"; then
                log_success "$env environment is healthy!"
                return 0
            fi
        fi

        sleep $HEALTH_CHECK_INTERVAL
        elapsed=$((elapsed + HEALTH_CHECK_INTERVAL))
        echo -n "."
    done

    echo ""
    log_error "$env environment failed health check after ${HEALTH_CHECK_TIMEOUT}s"
    return 1
}

run_smoke_tests() {
    local env=$1
    local project=$(get_project_name "$env")

    log_info "Running smoke tests on $env environment..."

    # Test 1: Backend API responds
    if ! docker-compose -p "$project" exec -T backend wget -q -O- http://localhost:8000/api/ 2>/dev/null; then
        log_error "Backend API not responding"
        return 1
    fi

    # Test 2: Database connection
    if ! docker-compose -p "$project" exec -T backend python manage.py check --database default 2>/dev/null; then
        log_error "Database connection failed"
        return 1
    fi

    # Test 3: Redis connection
    if ! docker-compose -p "$project" exec -T redis redis-cli ping 2>/dev/null | grep -q "PONG"; then
        log_error "Redis connection failed"
        return 1
    fi

    # Test 4: API Gateway routing
    if ! docker-compose -p "$project" exec -T api_gateway wget -q -O- http://localhost:8080/routes 2>/dev/null; then
        log_error "API Gateway routing check failed"
        return 1
    fi

    log_success "All smoke tests passed!"
    return 0
}

# ==============================================================================
# Deployment Functions
# ==============================================================================

deploy_to_standby() {
    local standby=$(get_standby_environment)
    local project=$(get_project_name "$standby")

    log_info "Deploying to $standby environment (project: $project)..."

    # Pull latest images
    log_info "Pulling latest images..."
    docker-compose -f "$BLUE_COMPOSE" -p "$project" pull

    # Build any local images
    log_info "Building images..."
    docker-compose -f "$BLUE_COMPOSE" -p "$project" build

    # Start services
    log_info "Starting services..."
    docker-compose -f "$BLUE_COMPOSE" -p "$project" up -d

    # Wait for health
    if ! wait_for_health "$standby"; then
        log_error "Deployment failed - $standby environment unhealthy"
        return 1
    fi

    # Run smoke tests
    if ! run_smoke_tests "$standby"; then
        log_error "Deployment failed - smoke tests failed"
        return 1
    fi

    # Run database migrations (if any)
    log_info "Running database migrations..."
    docker-compose -p "$project" exec -T backend python manage.py migrate --noinput

    log_success "Deployment to $standby completed successfully!"
    return 0
}

switch_traffic() {
    local old_active=$(get_active_environment)
    local new_active=$(get_standby_environment)

    log_info "Switching traffic from $old_active to $new_active..."

    # Update nginx upstream configuration
    log_info "Updating nginx configuration..."

    if [ "$new_active" == "blue" ]; then
        docker exec "$NGINX_CONTAINER" sed -i 's/server green-backend:8000/server blue-backend:8000/g' /etc/nginx/conf.d/default.conf
        docker exec "$NGINX_CONTAINER" sed -i 's/server green-api-gateway:8080/server blue-api-gateway:8080/g' /etc/nginx/conf.d/default.conf
    else
        docker exec "$NGINX_CONTAINER" sed -i 's/server blue-backend:8000/server green-backend:8000/g' /etc/nginx/conf.d/default.conf
        docker exec "$NGINX_CONTAINER" sed -i 's/server blue-api-gateway:8080/server green-api-gateway:8080/g' /etc/nginx/conf.d/default.conf
    fi

    # Reload nginx gracefully
    log_info "Reloading nginx..."
    docker exec "$NGINX_CONTAINER" nginx -s reload

    # Update active environment
    set_active_environment "$new_active"

    log_success "Traffic switched to $new_active!"

    # Keep old environment running for quick rollback
    log_warning "Old $old_active environment is still running for rollback capability"
    log_info "Stop it manually when confirmed stable: docker-compose -p ecommerce-$old_active down"
}

# ==============================================================================
# Rollback Functions
# ==============================================================================

rollback() {
    local current_active=$(get_active_environment)
    local rollback_to=$(get_standby_environment)

    log_warning "Rolling back from $current_active to $rollback_to..."

    # Check if rollback target is running
    local project=$(get_project_name "$rollback_to")
    if ! docker-compose -p "$project" ps | grep -q "Up"; then
        log_error "Cannot rollback - $rollback_to environment is not running"
        return 1
    fi

    # Check health of rollback target
    if ! wait_for_health "$rollback_to"; then
        log_error "Cannot rollback - $rollback_to environment is unhealthy"
        return 1
    fi

    # Switch traffic back
    switch_traffic

    log_success "Rollback completed! Now running $rollback_to environment"
}

# ==============================================================================
# Status Functions
# ==============================================================================

show_status() {
    local active=$(get_active_environment)
    local standby=$(get_standby_environment)

    echo ""
    echo "======================================================================"
    echo "  Blue/Green Deployment Status"
    echo "======================================================================"
    echo ""
    echo "Active Environment:  $active (serving production traffic)"
    echo "Standby Environment: $standby"
    echo ""

    # Check blue status
    log_info "Blue environment status:"
    docker-compose -p "$BLUE_PROJECT" ps || echo "  Not running"

    echo ""

    # Check green status
    log_info "Green environment status:"
    docker-compose -p "$GREEN_PROJECT" ps || echo "  Not running"

    echo ""
    echo "======================================================================"
}

# ==============================================================================
# Main Commands
# ==============================================================================

cmd_deploy() {
    log_info "Starting blue/green deployment..."

    # Deploy to standby environment
    if ! deploy_to_standby; then
        log_error "Deployment failed"
        return 1
    fi

    # Confirm before switching traffic
    local standby=$(get_standby_environment)
    read -p "Deploy to $standby successful. Switch traffic? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        switch_traffic
        log_success "Deployment completed successfully!"
    else
        log_warning "Traffic not switched. Run 'switch-traffic' command when ready."
    fi
}

cmd_rollback() {
    read -p "Are you sure you want to rollback? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rollback
    else
        log_info "Rollback cancelled"
    fi
}

cmd_status() {
    show_status
}

cmd_switch_traffic() {
    switch_traffic
}

# ==============================================================================
# Main
# ==============================================================================

main() {
    local command=${1:-}

    case "$command" in
        deploy)
            cmd_deploy
            ;;
        rollback)
            cmd_rollback
            ;;
        status)
            cmd_status
            ;;
        switch-traffic)
            cmd_switch_traffic
            ;;
        *)
            echo "Usage: $0 {deploy|rollback|status|switch-traffic}"
            echo ""
            echo "Commands:"
            echo "  deploy          - Deploy new version to standby environment and switch traffic"
            echo "  rollback        - Rollback to previous environment"
            echo "  status          - Show current deployment status"
            echo "  switch-traffic  - Manually switch traffic between environments"
            exit 1
            ;;
    esac
}

main "$@"
