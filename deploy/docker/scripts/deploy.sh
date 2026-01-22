#!/bin/bash
set -euo pipefail

# ==============================================================================
# Unified Deployment Script
# Supports: development, staging, production
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} $1"; }
warn() { echo -e "${YELLOW}[$(date +'%H:%M:%S')] WARNING:${NC} $1"; }
error() { echo -e "${RED}[$(date +'%H:%M:%S')] ERROR:${NC} $1" >&2; }
info() { echo -e "${BLUE}[$(date +'%H:%M:%S')] INFO:${NC} $1"; }

# ==============================================================================
# Configuration
# ==============================================================================

ENVIRONMENT="${1:-development}"
VERSION="${2:-latest}"
DRY_RUN="${DRY_RUN:-false}"

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(development|staging|production)$ ]]; then
    error "Invalid environment: $ENVIRONMENT"
    error "Usage: $0 <development|staging|production> [version]"
    exit 1
fi

# Set compose file based on environment
COMPOSE_FILE="$PROJECT_ROOT/deploy/docker/compose/${ENVIRONMENT}.yml"
BASE_COMPOSE_FILE="$PROJECT_ROOT/deploy/docker/compose/base.yml"

if [ ! -f "$COMPOSE_FILE" ]; then
    error "Compose file not found: $COMPOSE_FILE"
    exit 1
fi

# ==============================================================================
# Pre-deployment Checks
# ==============================================================================

pre_deployment_checks() {
    log "🔍 Running pre-deployment checks..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed"
        exit 1
    fi

    # Check docker-compose
    if ! command -v docker-compose &> /dev/null; then
        error "docker-compose is not installed"
        exit 1
    fi

    # Check environment file
    ENV_FILE="$PROJECT_ROOT/config/environments/${ENVIRONMENT}.env"
    if [ ! -f "$ENV_FILE" ]; then
        warn "Environment file not found: $ENV_FILE"
    fi

    # Check disk space
    AVAILABLE_SPACE=$(df -h "$PROJECT_ROOT" | awk 'NR==2 {print $4}')
    info "Available disk space: $AVAILABLE_SPACE"

    # Check if services are running
    if docker-compose -f "$BASE_COMPOSE_FILE" -f "$COMPOSE_FILE" ps | grep -q "Up"; then
        info "Some services are already running"
    fi

    log "✅ Pre-deployment checks passed"
}

# ==============================================================================
# Pull Images
# ==============================================================================

pull_images() {
    log "📦 Pulling Docker images..."

    if [ "$DRY_RUN" = "true" ]; then
        info "DRY RUN: Would pull images"
        return 0
    fi

    export VERSION
    docker-compose -f "$BASE_COMPOSE_FILE" -f "$COMPOSE_FILE" pull || {
        error "Failed to pull images"
        exit 1
    }

    log "✅ Images pulled successfully"
}

# ==============================================================================
# Database Migrations
# ==============================================================================

run_migrations() {
    log "🔄 Running database migrations..."

    if [ "$DRY_RUN" = "true" ]; then
        info "DRY RUN: Would run migrations"
        return 0
    fi

    # Check if backend service exists in compose file
    if docker-compose -f "$BASE_COMPOSE_FILE" -f "$COMPOSE_FILE" config --services | grep -q "backend"; then
        docker-compose -f "$BASE_COMPOSE_FILE" -f "$COMPOSE_FILE" run --rm backend \
            python manage.py migrate --noinput || {
            error "Database migration failed"
            return 1
        }
        log "✅ Migrations completed"
    else
        warn "Backend service not found, skipping migrations"
    fi
}

# ==============================================================================
# Collect Static Files
# ==============================================================================

collect_static() {
    if [ "$ENVIRONMENT" != "production" ]; then
        info "Skipping static file collection for $ENVIRONMENT"
        return 0
    fi

    log "📦 Collecting static files..."

    if [ "$DRY_RUN" = "true" ]; then
        info "DRY RUN: Would collect static files"
        return 0
    fi

    docker-compose -f "$BASE_COMPOSE_FILE" -f "$COMPOSE_FILE" run --rm backend \
        python manage.py collectstatic --noinput --clear || {
        warn "Static file collection failed (non-fatal)"
    }

    log "✅ Static files collected"
}

# ==============================================================================
# Deploy Services
# ==============================================================================

deploy_services() {
    log "🚀 Deploying services..."

    if [ "$DRY_RUN" = "true" ]; then
        info "DRY RUN: Would deploy services"
        return 0
    fi

    # For production, use blue-green deployment
    if [ "$ENVIRONMENT" = "production" ]; then
        if [ -f "$PROJECT_ROOT/deploy/docker/scripts/blue-green-deploy.sh" ]; then
            log "Using blue-green deployment for production..."
            bash "$PROJECT_ROOT/deploy/docker/scripts/blue-green-deploy.sh"
            return $?
        else
            warn "Blue-green deployment script not found, using standard deployment"
        fi
    fi

    # Standard deployment
    export VERSION
    docker-compose -f "$BASE_COMPOSE_FILE" -f "$COMPOSE_FILE" up -d --remove-orphans || {
        error "Service deployment failed"
        exit 1
    }

    log "✅ Services deployed"
}

# ==============================================================================
# Health Checks
# ==============================================================================

wait_for_healthy() {
    log "🏥 Waiting for services to be healthy..."

    local MAX_WAIT=120
    local ELAPSED=0
    local INTERVAL=5

    if [ "$DRY_RUN" = "true" ]; then
        info "DRY RUN: Would wait for health checks"
        return 0
    fi

    while [ $ELAPSED -lt $MAX_WAIT ]; do
        # Check if all services are healthy
        UNHEALTHY=$(docker-compose -f "$BASE_COMPOSE_FILE" -f "$COMPOSE_FILE" ps | grep -c "unhealthy" || true)

        if [ "$UNHEALTHY" -eq 0 ]; then
            log "✅ All services are healthy"
            return 0
        fi

        info "Waiting for services to be healthy... ($ELAPSED/$MAX_WAIT seconds)"
        sleep $INTERVAL
        ELAPSED=$((ELAPSED + INTERVAL))
    done

    error "Services did not become healthy within $MAX_WAIT seconds"
    docker-compose -f "$BASE_COMPOSE_FILE" -f "$COMPOSE_FILE" ps
    return 1
}

# ==============================================================================
# Post-deployment Tests
# ==============================================================================

run_smoke_tests() {
    log "🧪 Running smoke tests..."

    if [ "$DRY_RUN" = "true" ]; then
        info "DRY RUN: Would run smoke tests"
        return 0
    fi

    SMOKE_TEST_SCRIPT="$PROJECT_ROOT/deploy/docker/scripts/smoke-test.sh"

    if [ -f "$SMOKE_TEST_SCRIPT" ]; then
        bash "$SMOKE_TEST_SCRIPT" "$ENVIRONMENT" || {
            error "Smoke tests failed"
            return 1
        }
    else
        warn "Smoke test script not found: $SMOKE_TEST_SCRIPT"

        # Basic health check
        local BACKEND_URL="http://localhost:8000"
        if [ "$ENVIRONMENT" = "production" ]; then
            BACKEND_URL="${PRODUCTION_URL:-https://api.example.com}"
        elif [ "$ENVIRONMENT" = "staging" ]; then
            BACKEND_URL="${STAGING_URL:-https://staging-api.example.com}"
        fi

        if curl -sf "$BACKEND_URL/health/" > /dev/null; then
            log "✅ Basic health check passed"
        else
            error "Basic health check failed"
            return 1
        fi
    fi

    log "✅ Smoke tests passed"
}

# ==============================================================================
# Cleanup
# ==============================================================================

cleanup_old_images() {
    log "🧹 Cleaning up old Docker images..."

    if [ "$DRY_RUN" = "true" ]; then
        info "DRY RUN: Would cleanup old images"
        return 0
    fi

    # Remove dangling images
    docker image prune -f || true

    # Remove images older than 7 days (except latest)
    docker images --format "{{.Repository}}:{{.Tag}} {{.CreatedAt}}" | \
        grep -v "latest" | \
        awk '$2 < "'$(date -d '7 days ago' +%Y-%m-%d)'" {print $1}' | \
        xargs -r docker rmi || true

    log "✅ Cleanup complete"
}

# ==============================================================================
# Rollback on Failure
# ==============================================================================

rollback_on_failure() {
    error "Deployment failed! Initiating rollback..."

    ROLLBACK_SCRIPT="$PROJECT_ROOT/deploy/docker/scripts/rollback.sh"

    if [ -f "$ROLLBACK_SCRIPT" ]; then
        bash "$ROLLBACK_SCRIPT"
    else
        error "Rollback script not found!"
        error "Manual intervention required"
    fi
}

# ==============================================================================
# Main Deployment Flow
# ==============================================================================

main() {
    log "=========================================="
    log "  E-Commerce Platform Deployment"
    log "=========================================="
    log "Environment: $ENVIRONMENT"
    log "Version: $VERSION"
    log "Dry Run: $DRY_RUN"
    log "=========================================="

    # Change to project root
    cd "$PROJECT_ROOT"

    # Execute deployment steps
    pre_deployment_checks || exit 1
    pull_images || exit 1
    run_migrations || { rollback_on_failure; exit 1; }
    collect_static || { rollback_on_failure; exit 1; }
    deploy_services || { rollback_on_failure; exit 1; }
    wait_for_healthy || { rollback_on_failure; exit 1; }
    run_smoke_tests || { rollback_on_failure; exit 1; }
    cleanup_old_images || true  # Non-fatal

    log "=========================================="
    log "✅ Deployment Complete!"
    log "=========================================="
    log "Environment: $ENVIRONMENT"
    log "Version: $VERSION"
    log "Time: $(date)"
    log "=========================================="

    # Show running services
    info "Running services:"
    docker-compose -f "$BASE_COMPOSE_FILE" -f "$COMPOSE_FILE" ps
}

# ==============================================================================
# Script Entry Point
# ==============================================================================

# Trap errors and rollback
trap 'error "Deployment failed at line $LINENO"' ERR

# Run main function
main "$@"
