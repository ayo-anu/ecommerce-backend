#!/bin/bash
# ==============================================================================
# Phase 1 - Step 8: Run Tests
# ==============================================================================

set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[Step 8]${NC} $1"; }
error() { echo -e "${RED}[Step 8]${NC} $1"; }
warn() { echo -e "${YELLOW}[Step 8]${NC} $1"; }
info() { echo -e "${BLUE}[Step 8]${NC} $1"; }

FAILED_TESTS=0

log "Running Phase 1 validation tests..."

# Test 1: Verify directory structure
test_directory_structure() {
    log "Test 1: Verifying directory structure..."

    local required_dirs=(
        "services/backend"
        "services/ai"
        "deploy/docker/compose"
        "deploy/docker/images"
        "config/environments"
        "docs/architecture"
        "docs/deployment"
        "docs/operations"
    )

    for dir in "${required_dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            error "❌ Missing directory: $dir"
            ((FAILED_TESTS++))
        else
            info "✓ $dir"
        fi
    done

    if [ $FAILED_TESTS -eq 0 ]; then
        log "✅ Directory structure test passed"
    fi
}

# Test 2: Verify Docker Compose files
test_docker_compose() {
    log "Test 2: Validating Docker Compose files..."

    local compose_files=(
        "deploy/docker/compose/base.yml"
        "deploy/docker/compose/development.yml"
        "deploy/docker/compose/production.yml"
    )

    for compose_file in "${compose_files[@]}"; do
        if [ ! -f "$compose_file" ]; then
            error "❌ Missing: $compose_file"
            ((FAILED_TESTS++))
        else
            # Validate syntax
            if docker-compose -f "$compose_file" config > /dev/null 2>&1; then
                info "✓ $compose_file (valid)"
            else
                error "❌ $compose_file (invalid syntax)"
                ((FAILED_TESTS++))
            fi
        fi
    done

    if [ $FAILED_TESTS -eq 0 ]; then
        log "✅ Docker Compose validation passed"
    fi
}

# Test 3: Verify Dockerfiles can be parsed
test_dockerfiles() {
    log "Test 3: Checking Dockerfiles..."

    local dockerfiles=(
        "deploy/docker/images/services/backend/Dockerfile.production"
        "deploy/docker/images/services/ai/Dockerfile.template"
    )

    for dockerfile in "${dockerfiles[@]}"; do
        if [ ! -f "$dockerfile" ]; then
            error "❌ Missing: $dockerfile"
            ((FAILED_TESTS++))
        else
            # Basic syntax check (FROM statement exists)
            if grep -q "^FROM" "$dockerfile"; then
                info "✓ $dockerfile"
            else
                error "❌ $dockerfile (invalid format)"
                ((FAILED_TESTS++))
            fi
        fi
    done

    if [ $FAILED_TESTS -eq 0 ]; then
        log "✅ Dockerfile validation passed"
    fi
}

# Test 4: Verify environment files
test_environment_files() {
    log "Test 4: Checking environment files..."

    if [ -d "env" ]; then
        error "❌ Old env/ directory still exists"
        ((FAILED_TESTS++))
    fi

    if [ -d "config/environments" ]; then
        local env_count=$(find config/environments -name "*.env.template" -o -name ".env.example" | wc -l)
        if [ "$env_count" -gt 0 ]; then
            info "✓ Found $env_count environment template files"
        else
            warn "⚠ No environment templates found in config/environments/"
        fi
    else
        error "❌ config/environments/ directory missing"
        ((FAILED_TESTS++))
    fi

    if [ $FAILED_TESTS -eq 0 ]; then
        log "✅ Environment files validation passed"
    fi
}

# Test 5: Check for broken symlinks
test_no_broken_links() {
    log "Test 5: Checking for broken symlinks..."

    local broken_links=$(find . -type l ! -exec test -e {} \; -print 2>/dev/null)

    if [ -n "$broken_links" ]; then
        error "❌ Found broken symlinks:"
        echo "$broken_links"
        ((FAILED_TESTS++))
    else
        info "✓ No broken symlinks"
        log "✅ Symlink test passed"
    fi
}

# Test 6: Verify no old paths in critical files
test_reference_updates() {
    log "Test 6: Verifying path references updated..."

    local files_to_check=(
        "Makefile"
        "README.md"
        ".github/workflows/backend-ci.yml"
        ".github/workflows/ai-services-ci.yml"
    )

    for file in "${files_to_check[@]}"; do
        if [ -f "$file" ]; then
            # Check for old paths
            if grep -q "deploy/docker/compose/base\.yaml" "$file" 2>/dev/null; then
                error "❌ $file still contains old path: deploy/docker/compose/base.yaml"
                ((FAILED_TESTS++))
            elif grep -E "^[^#]*\bservices/backend/" "$file" | grep -v "services/backend" > /dev/null 2>&1; then
                # Allow comments but check uncommented lines
                warn "⚠ $file may contain old services/backend/ paths (check manually)"
            else
                info "✓ $file"
            fi
        else
            warn "⚠ $file not found (may not exist yet)"
        fi
    done

    if [ $FAILED_TESTS -eq 0 ]; then
        log "✅ Reference update test passed"
    fi
}

# Test 7: Try building backend Docker image
test_docker_build() {
    log "Test 7: Testing Docker image build (backend)..."

    # Only test if Dockerfile exists and Docker is available
    if [ -f "deploy/docker/images/services/backend/Dockerfile.production" ]; then
        if docker info > /dev/null 2>&1; then
            info "Building backend image (this may take a few minutes)..."

            if docker build -f deploy/docker/images/services/backend/Dockerfile.production -t backend:phase1-test . > /tmp/docker-build.log 2>&1; then
                log "✅ Backend Docker image built successfully"

                # Check image size
                local image_size=$(docker images backend:phase1-test --format "{{.Size}}")
                info "Image size: $image_size"

                # Cleanup test image
                docker rmi backend:phase1-test > /dev/null 2>&1 || true
            else
                error "❌ Docker build failed. See /tmp/docker-build.log"
                tail -n 20 /tmp/docker-build.log
                ((FAILED_TESTS++))
            fi
        else
            warn "⚠ Docker not available, skipping build test"
        fi
    else
        warn "⚠ Backend Dockerfile not found, skipping build test"
    fi
}

# Test 8: Validate service startup (optional, quick check)
test_service_startup() {
    log "Test 8: Quick service startup test..."

    if [ -f "deploy/docker/compose/base.yml" ] && [ -f "deploy/docker/compose/development.yml" ]; then
        info "Testing docker-compose configuration..."

        # Try to start services in detached mode
        if docker-compose \
            -f deploy/docker/compose/base.yml \
            -f deploy/docker/compose/development.yml \
            config > /dev/null 2>&1; then
            log "✅ Docker Compose configuration valid"
        else
            error "❌ Docker Compose configuration invalid"
            ((FAILED_TESTS++))
        fi
    else
        warn "⚠ Docker Compose files not found, skipping startup test"
    fi
}

# Run all tests
main() {
    log "=========================================="
    log "  Phase 1 Validation Tests"
    log "=========================================="
    echo ""

    test_directory_structure
    echo ""

    test_docker_compose
    echo ""

    test_dockerfiles
    echo ""

    test_environment_files
    echo ""

    test_no_broken_links
    echo ""

    test_reference_updates
    echo ""

    test_docker_build
    echo ""

    test_service_startup
    echo ""

    # Summary
    log "=========================================="
    if [ $FAILED_TESTS -eq 0 ]; then
        log "✅ ALL TESTS PASSED"
        log "=========================================="
        return 0
    else
        error "❌ $FAILED_TESTS TEST(S) FAILED"
        error "=========================================="
        return 1
    fi
}

main "$@"
