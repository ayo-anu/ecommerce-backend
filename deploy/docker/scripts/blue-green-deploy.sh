#!/bin/bash

set -e
set -u
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/deploy/docker/compose/production.yml"
UPSTREAM_CONF="$PROJECT_ROOT/deploy/nginx/conf.d/upstream.conf"

VERSION=""
SERVICE="all"
SKIP_TESTS=false
FORCE=false
DRY_RUN=false
TIMEOUT=300
HEALTH_CHECK_INTERVAL=5

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Zero-downtime deployment using blue-green strategy.

Options:
    --version VERSION    Docker image version to deploy (required)
    --service SERVICE    Service to deploy (default: all)
    --skip-tests         Skip smoke tests after deployment
    --force              Force deployment even if health checks fail
    --dry-run            Show what would be done without executing
    -h, --help           Show this help message

Examples:
    $0 --version v1.2.3

    $0 --version v1.2.3 --service backend

    $0 --version v1.2.3 --dry-run
EOF
    exit 1
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --version)
            VERSION="$2"
            shift 2
            ;;
        --service)
            SERVICE="$2"
            shift 2
            ;;
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            ;;
    esac
done

if [ -z "$VERSION" ]; then
    log_error "Version is required. Use --version to specify."
    usage
fi


preflight_checks() {
    log_info "Running pre-flight checks..."

    if ! docker info > /dev/null 2>&1; then
        log_error "Docker is not running"
        exit 1
    fi

    if [ ! -f "$COMPOSE_FILE" ]; then
        log_error "Compose file not found: $COMPOSE_FILE"
        exit 1
    fi

    if [ ! -f "$UPSTREAM_CONF" ]; then
        log_error "Upstream config not found: $UPSTREAM_CONF"
        exit 1
    fi

    if ! docker ps | grep -q ecommerce_nginx; then
        log_error "Nginx container is not running"
        exit 1
    fi

    log_success "Pre-flight checks passed"
}


detect_active_environment() {
    log_info "Detecting active environment..."

    if grep -q "server api_gateway:8080.*# ACTIVE: blue" "$UPSTREAM_CONF"; then
        CURRENT_ENV="blue"
        TARGET_ENV="green"
    elif grep -q "server api_gateway_green:8080.*# ACTIVE: green" "$UPSTREAM_CONF"; then
        CURRENT_ENV="green"
        TARGET_ENV="blue"
    else
        CURRENT_ENV="blue"
        TARGET_ENV="green"
    fi

    log_info "Current active environment: ${GREEN}$CURRENT_ENV${NC}"
    log_info "Target deployment environment: ${BLUE}$TARGET_ENV${NC}"
}


deploy_to_target() {
    log_info "Deploying version $VERSION to $TARGET_ENV environment..."

    if [ "$DRY_RUN" = true ]; then
        log_warning "[DRY RUN] Would deploy the following:"
        log_info "  Service: $SERVICE"
        log_info "  Version: $VERSION"
        log_info "  Environment: $TARGET_ENV"
        return 0
    fi

    export VERSION="$VERSION"

    if [ "$SERVICE" = "all" ]; then
        log_info "Deploying all services..."
        docker-compose -f "$COMPOSE_FILE" up -d --no-deps \
            api_gateway backend
    else
        log_info "Deploying service: $SERVICE"
        docker-compose -f "$COMPOSE_FILE" up -d --no-deps "$SERVICE"
    fi

    log_success "Deployment to $TARGET_ENV completed"
}


wait_for_healthy() {
    local service=$1
    local endpoint=${2:-/health}
    local max_attempts=$((TIMEOUT / HEALTH_CHECK_INTERVAL))
    local attempt=0

    log_info "Waiting for $service to be healthy..."

    while [ $attempt -lt $max_attempts ]; do
        if docker exec ecommerce_nginx curl -sf "http://$service:8080$endpoint" > /dev/null 2>&1; then
            log_success "$service is healthy"
            return 0
        fi

        attempt=$((attempt + 1))
        log_info "  Attempt $attempt/$max_attempts - waiting ${HEALTH_CHECK_INTERVAL}s..."
        sleep $HEALTH_CHECK_INTERVAL
    done

    log_error "$service failed health check after $TIMEOUT seconds"
    return 1
}

validate_health() {
    log_info "Validating health of deployed services..."

    if [ "$DRY_RUN" = true ]; then
        log_warning "[DRY RUN] Would validate health checks"
        return 0
    fi

    local failed=false

    if ! wait_for_healthy "api_gateway" "/health"; then
        failed=true
    fi

    if ! wait_for_healthy "backend" "/api/health/"; then
        failed=true
    fi

    if [ "$failed" = true ]; then
        if [ "$FORCE" = true ]; then
            log_warning "Health checks failed but --force specified, continuing..."
            return 0
        else
            log_error "Health checks failed. Use --force to override."
            return 1
        fi
    fi

    log_success "All health checks passed"
}


run_smoke_tests() {
    log_info "Running smoke tests..."

    if [ "$SKIP_TESTS" = true ]; then
        log_warning "Skipping smoke tests (--skip-tests specified)"
        return 0
    fi

    if [ "$DRY_RUN" = true ]; then
        log_warning "[DRY RUN] Would run smoke tests"
        return 0
    fi

    local smoke_test_script="$SCRIPT_DIR/smoke-test.sh"

    if [ -f "$smoke_test_script" ]; then
        if bash "$smoke_test_script"; then
            log_success "Smoke tests passed"
            return 0
        else
            log_error "Smoke tests failed"
            return 1
        fi
    else
        log_warning "Smoke test script not found, skipping: $smoke_test_script"
        return 0
    fi
}


switch_traffic() {
    log_info "Switching traffic from $CURRENT_ENV to $TARGET_ENV..."

    if [ "$DRY_RUN" = true ]; then
        log_warning "[DRY RUN] Would switch traffic to $TARGET_ENV"
        return 0
    fi

    cp "$UPSTREAM_CONF" "$UPSTREAM_CONF.backup"

    if [ "$TARGET_ENV" = "green" ]; then
        sed -i.tmp \
            -e 's/server api_gateway:8080.*# ACTIVE: blue/# server api_gateway:8080  # INACTIVE: blue/' \
            -e 's/# server api_gateway_green:8080.*# ACTIVE: green/server api_gateway_green:8080 max_fails=3 fail_timeout=30s;  # ACTIVE: green/' \
            "$UPSTREAM_CONF"
    else
        sed -i.tmp \
            -e 's/# server api_gateway:8080.*# INACTIVE: blue/server api_gateway:8080 max_fails=3 fail_timeout=30s;  # ACTIVE: blue/' \
            -e 's/server api_gateway_green:8080.*# ACTIVE: green/# server api_gateway_green:8080  # INACTIVE: green/' \
            "$UPSTREAM_CONF"
    fi

    rm -f "$UPSTREAM_CONF.tmp"

    log_info "Reloading nginx configuration..."
    docker exec ecommerce_nginx nginx -t && docker exec ecommerce_nginx nginx -s reload

    if [ $? -eq 0 ]; then
        log_success "Traffic switched to $TARGET_ENV environment"
        rm -f "$UPSTREAM_CONF.backup"
    else
        log_error "Failed to reload nginx, restoring backup..."
        mv "$UPSTREAM_CONF.backup" "$UPSTREAM_CONF"
        docker exec ecommerce_nginx nginx -s reload
        return 1
    fi
}


verify_deployment() {
    log_info "Verifying deployment..."

    if [ "$DRY_RUN" = true ]; then
        log_warning "[DRY RUN] Would verify deployment"
        return 0
    fi

    sleep 5

    if docker exec ecommerce_nginx curl -sf http://localhost/health > /dev/null; then
        log_success "Nginx is responding correctly"
    else
        log_error "Nginx health check failed"
        return 1
    fi

    if docker exec ecommerce_nginx curl -sf http://localhost/api/health/ > /dev/null; then
        log_success "API is responding correctly through nginx"
    else
        log_error "API health check failed through nginx"
        return 1
    fi

    log_success "Deployment verified successfully"
}


cleanup_old_environment() {
    log_info "Old $CURRENT_ENV environment is still running for rollback if needed"
    log_info "To cleanup manually, run: docker-compose -f $COMPOSE_FILE down $CURRENT_ENV"
    log_info ""
    log_info "Monitor the deployment for issues. If stable, cleanup after 30 minutes."
}


main() {
    log_info "Starting Blue-Green Deployment"
    log_info "Version: $VERSION"
    log_info "Service: $SERVICE"

    preflight_checks

    detect_active_environment

    deploy_to_target

    if ! validate_health; then
        log_error "Deployment failed at health check stage"
        exit 1
    fi

    if ! run_smoke_tests; then
        log_error "Deployment failed at smoke test stage"
        log_warning "Target environment is running but traffic not switched"
        log_info "You can manually switch traffic or rollback"
        exit 1
    fi

    if ! switch_traffic; then
        log_error "Failed to switch traffic"
        exit 1
    fi

    if ! verify_deployment; then
        log_error "Deployment verification failed"
        log_warning "Consider rolling back: ./rollback.sh"
        exit 1
    fi

    cleanup_old_environment

    log_success "🎉 DEPLOYMENT SUCCESSFUL!"
    log_info "Active environment: $TARGET_ENV"
    log_info "Version: $VERSION"
    log_info "Monitor logs: docker-compose -f $COMPOSE_FILE logs -f"
}


main
