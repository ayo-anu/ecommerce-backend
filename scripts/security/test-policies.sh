#!/bin/bash
# ==============================================================================
# OPA Policy Testing Script
# ==============================================================================
# Tests OPA security policies against Dockerfiles and Docker Compose files
#
# Usage:
#   ./scripts/security/test-policies.sh [options]
#
# Options:
#   --dockerfile <path>    Test specific Dockerfile
#   --compose <path>       Test specific compose file
#   --all                  Test all files (default)
#   --fix                  Show suggestions for fixing violations
#   --verbose              Show detailed output
#
# Requirements:
#   - conftest (https://www.conftest.dev/)
#
# Installation:
#   wget https://github.com/open-policy-agent/conftest/releases/download/v0.49.1/conftest_0.49.1_Linux_x86_64.tar.gz
#   tar xzf conftest_0.49.1_Linux_x86_64.tar.gz
#   sudo mv conftest /usr/local/bin/
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
POLICY_DIR="$PROJECT_ROOT/config/policies"
DOCKERFILE_POLICY="$POLICY_DIR/docker.rego"
COMPOSE_POLICY="$POLICY_DIR/compose.rego"

# Options
TEST_ALL=true
VERBOSE=false
SHOW_FIX=false
SPECIFIC_DOCKERFILE=""
SPECIFIC_COMPOSE=""

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

check_conftest() {
    if ! command -v conftest &> /dev/null; then
        print_error "conftest is not installed"
        echo ""
        echo "Install with:"
        echo "  wget https://github.com/open-policy-agent/conftest/releases/download/v0.49.1/conftest_0.49.1_Linux_x86_64.tar.gz"
        echo "  tar xzf conftest_0.49.1_Linux_x86_64.tar.gz"
        echo "  sudo mv conftest /usr/local/bin/"
        exit 1
    fi
}

test_dockerfile() {
    local dockerfile="$1"
    local passed=true

    echo ""
    print_header "Testing: $dockerfile"

    if [ "$VERBOSE" = true ]; then
        conftest test "$dockerfile" \
            --policy "$DOCKERFILE_POLICY" \
            --namespace docker \
            --no-color || passed=false
    else
        conftest test "$dockerfile" \
            --policy "$DOCKERFILE_POLICY" \
            --namespace docker \
            --no-color \
            --output stdout || passed=false
    fi

    if [ "$passed" = true ]; then
        print_success "Dockerfile passed all policy checks"
    else
        print_error "Dockerfile failed policy checks"

        if [ "$SHOW_FIX" = true ]; then
            echo ""
            print_info "Common fixes:"
            echo "  - Add USER directive: USER appuser"
            echo "  - Add HEALTHCHECK: HEALTHCHECK CMD curl -f http://localhost:8000/health/ || exit 1"
            echo "  - Use specific tags: python:3.11-slim-bookworm (not :latest)"
            echo "  - Pin pip versions: pip install package==1.2.3"
        fi
    fi

    return $([ "$passed" = true ] && echo 0 || echo 1)
}

test_compose_file() {
    local composefile="$1"
    local passed=true

    # Skip base files
    if [[ "$composefile" == *"base.yml"* ]] || [[ "$composefile" == *"base-alt.yml"* ]]; then
        print_info "Skipping base file: $composefile (extended by production)"
        return 0
    fi

    echo ""
    print_header "Testing: $composefile"

    if [ "$VERBOSE" = true ]; then
        conftest test "$composefile" \
            --policy "$COMPOSE_POLICY" \
            --namespace compose \
            --no-color || passed=false
    else
        conftest test "$composefile" \
            --policy "$COMPOSE_POLICY" \
            --namespace compose \
            --no-color \
            --output stdout || passed=false
    fi

    if [ "$passed" = true ]; then
        print_success "Compose file passed all policy checks"
    else
        print_error "Compose file failed policy checks"

        if [ "$SHOW_FIX" = true ]; then
            echo ""
            print_info "Common fixes:"
            echo "  - Add resource limits: deploy.resources.limits.memory and .cpus"
            echo "  - Add healthcheck: healthcheck: test: [\"CMD\", \"curl\", ...]"
            echo "  - Add restart policy: restart: always"
            echo "  - Add security options: security_opt: [\"no-new-privileges:true\"]"
            echo "  - Add logging: logging: driver: json-file"
            echo "  - Avoid privileged mode: Remove privileged: true"
        fi
    fi

    return $([ "$passed" = true ] && echo 0 || echo 1)
}

# ==============================================================================
# Main Script
# ==============================================================================

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dockerfile)
                SPECIFIC_DOCKERFILE="$2"
                TEST_ALL=false
                shift 2
                ;;
            --compose)
                SPECIFIC_COMPOSE="$2"
                TEST_ALL=false
                shift 2
                ;;
            --all)
                TEST_ALL=true
                shift
                ;;
            --fix)
                SHOW_FIX=true
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [options]"
                echo ""
                echo "Options:"
                echo "  --dockerfile <path>    Test specific Dockerfile"
                echo "  --compose <path>       Test specific compose file"
                echo "  --all                  Test all files (default)"
                echo "  --fix                  Show suggestions for fixing violations"
                echo "  --verbose              Show detailed output"
                echo "  --help, -h             Show this help message"
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

    print_header "OPA Security Policy Testing"
    echo ""
    print_info "Policy directory: $POLICY_DIR"
    print_info "Project root: $PROJECT_ROOT"
    echo ""

    # Check dependencies
    check_conftest
    print_success "conftest is installed: $(conftest --version)"
    echo ""

    # Test results
    TOTAL_TESTS=0
    PASSED_TESTS=0
    FAILED_TESTS=0

    # Test specific Dockerfile
    if [ -n "$SPECIFIC_DOCKERFILE" ]; then
        if [ ! -f "$SPECIFIC_DOCKERFILE" ]; then
            print_error "Dockerfile not found: $SPECIFIC_DOCKERFILE"
            exit 1
        fi
        TOTAL_TESTS=$((TOTAL_TESTS + 1))
        if test_dockerfile "$SPECIFIC_DOCKERFILE"; then
            PASSED_TESTS=$((PASSED_TESTS + 1))
        else
            FAILED_TESTS=$((FAILED_TESTS + 1))
        fi
    fi

    # Test specific compose file
    if [ -n "$SPECIFIC_COMPOSE" ]; then
        if [ ! -f "$SPECIFIC_COMPOSE" ]; then
            print_error "Compose file not found: $SPECIFIC_COMPOSE"
            exit 1
        fi
        TOTAL_TESTS=$((TOTAL_TESTS + 1))
        if test_compose_file "$SPECIFIC_COMPOSE"; then
            PASSED_TESTS=$((PASSED_TESTS + 1))
        else
            FAILED_TESTS=$((FAILED_TESTS + 1))
        fi
    fi

    # Test all files
    if [ "$TEST_ALL" = true ]; then
        print_info "Testing all Dockerfiles..."

        # Find all Dockerfiles
        while IFS= read -r dockerfile; do
            TOTAL_TESTS=$((TOTAL_TESTS + 1))
            if test_dockerfile "$dockerfile"; then
                PASSED_TESTS=$((PASSED_TESTS + 1))
            else
                FAILED_TESTS=$((FAILED_TESTS + 1))
            fi
        done < <(find deploy/docker/images -name "Dockerfile*" -type f 2>/dev/null || true)

        print_info "Testing all Docker Compose files..."

        # Find all compose files
        while IFS= read -r composefile; do
            TOTAL_TESTS=$((TOTAL_TESTS + 1))
            if test_compose_file "$composefile"; then
                PASSED_TESTS=$((PASSED_TESTS + 1))
            else
                FAILED_TESTS=$((FAILED_TESTS + 1))
            fi
        done < <(find deploy/docker/compose -name "*.yml" -type f 2>/dev/null || true)
    fi

    # Print summary
    echo ""
    print_header "Test Summary"
    echo ""
    echo "Total tests:  $TOTAL_TESTS"
    print_success "Passed:       $PASSED_TESTS"
    if [ $FAILED_TESTS -gt 0 ]; then
        print_error "Failed:       $FAILED_TESTS"
    else
        echo "Failed:       $FAILED_TESTS"
    fi
    echo ""

    if [ $FAILED_TESTS -eq 0 ]; then
        print_success "All policy checks passed! 🎉"
        exit 0
    else
        print_error "Some policy checks failed"
        if [ "$SHOW_FIX" = false ]; then
            print_info "Run with --fix to see suggestions for fixing violations"
        fi
        exit 1
    fi
}

main "$@"
