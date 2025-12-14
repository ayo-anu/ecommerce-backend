#!/bin/bash

# ==============================================================================
# Run All Tests Script
# ==============================================================================
# Runs all test suites across backend, AI services, frontend, and integration
# ==============================================================================

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Variables
FAILED_TESTS=()
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_COUNT=0

# Functions
print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}→ $1${NC}"
}

# Check if services are running
check_services() {
    print_header "Checking Services"

    if ! docker-compose ps | grep -q "Up"; then
        print_error "Services are not running!"
        print_info "Please start services first with: make dev"
        exit 1
    fi

    print_success "Services are running"
}

# Run backend tests
run_backend_tests() {
    print_header "Running Backend Tests"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    print_info "Running Django tests with coverage..."

    if docker-compose exec -T backend pytest --cov=. --cov-report=term-missing -v; then
        print_success "Backend tests passed"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        print_error "Backend tests failed"
        FAILED_TESTS+=("Backend")
        FAILED_COUNT=$((FAILED_COUNT + 1))
    fi
}

# Run AI services tests
run_ai_tests() {
    print_header "Running AI Services Tests"

    services=("recommender" "search" "pricing" "chatbot" "fraud" "forecasting" "vision")

    for service in "${services[@]}"; do
        TOTAL_TESTS=$((TOTAL_TESTS + 1))
        print_info "Testing $service service..."

        if docker-compose exec -T $service pytest /app/tests -v 2>/dev/null; then
            print_success "$service tests passed"
            PASSED_TESTS=$((PASSED_TESTS + 1))
        else
            print_error "$service tests failed or no tests found"
            FAILED_TESTS+=("AI:$service")
            FAILED_COUNT=$((FAILED_COUNT + 1))
        fi
    done
}

# Run API Gateway tests
run_gateway_tests() {
    print_header "Running API Gateway Tests"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    print_info "Testing API Gateway..."

    if docker-compose exec -T api_gateway pytest /app/tests -v 2>/dev/null; then
        print_success "API Gateway tests passed"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        print_error "API Gateway tests failed or no tests found"
        FAILED_TESTS+=("API Gateway")
        FAILED_COUNT=$((FAILED_COUNT + 1))
    fi
}

# Run frontend tests
run_frontend_tests() {
    print_header "Running Frontend Tests"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    print_info "Running Next.js tests..."

    if docker-compose exec -T frontend npm test -- --watchAll=false 2>/dev/null; then
        print_success "Frontend tests passed"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        print_error "Frontend tests failed or no tests found"
        FAILED_TESTS+=("Frontend")
        FAILED_COUNT=$((FAILED_COUNT + 1))
    fi
}

# Run integration tests
run_integration_tests() {
    print_header "Running Integration Tests"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    print_info "Running cross-service integration tests..."

    # Install test dependencies if needed
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        source venv/bin/activate
        pip install -r tests/integration/requirements.txt
    else
        source venv/bin/activate
    fi

    if pytest tests/integration/ -v; then
        print_success "Integration tests passed"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        print_error "Integration tests failed"
        FAILED_TESTS+=("Integration")
        FAILED_COUNT=$((FAILED_COUNT + 1))
    fi

    deactivate 2>/dev/null || true
}

# Run linting
run_linting() {
    print_header "Running Code Quality Checks"

    print_info "Checking backend code quality..."
    docker-compose exec -T backend bash -c "pip install flake8 black isort && \
        flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics && \
        black --check . && \
        isort --check-only ." || print_error "Backend linting failed"

    print_info "Checking AI services code quality..."
    docker-compose exec -T recommender bash -c "pip install flake8 black isort && \
        flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics" || \
        print_error "AI services linting failed"

    print_info "Checking frontend code quality..."
    docker-compose exec -T frontend npm run lint || print_error "Frontend linting failed"
}

# Generate coverage report
generate_coverage() {
    print_header "Generating Coverage Reports"

    print_info "Backend coverage..."
    docker-compose exec -T backend pytest --cov=. --cov-report=html > /dev/null 2>&1 || true
    print_success "Backend coverage report: services/backend/htmlcov/index.html"

    print_info "Frontend coverage..."
    docker-compose exec -T frontend npm test -- --coverage --watchAll=false > /dev/null 2>&1 || true
    print_success "Frontend coverage report: frontend/coverage/lcov-report/index.html"
}

# Show summary
show_summary() {
    print_header "Test Summary"

    echo ""
    echo -e "${BLUE}Total Test Suites: $TOTAL_TESTS${NC}"
    echo -e "${GREEN}Passed: $PASSED_TESTS${NC}"
    echo -e "${RED}Failed: $FAILED_COUNT${NC}"
    echo ""

    if [ $FAILED_COUNT -eq 0 ]; then
        echo -e "${GREEN}========================================${NC}"
        echo -e "${GREEN}All tests passed! 🎉${NC}"
        echo -e "${GREEN}========================================${NC}"
        exit 0
    else
        echo -e "${RED}========================================${NC}"
        echo -e "${RED}Some tests failed:${NC}"
        for test in "${FAILED_TESTS[@]}"; do
            echo -e "${RED}  ✗ $test${NC}"
        done
        echo -e "${RED}========================================${NC}"
        exit 1
    fi
}

# Main execution
main() {
    print_header "E-Commerce Platform - Test Suite"
    echo -e "${YELLOW}Running all tests...${NC}"

    check_services

    # Parse command line arguments
    if [ "$1" == "--skip-backend" ]; then
        print_info "Skipping backend tests"
    else
        run_backend_tests
    fi

    if [ "$1" == "--skip-ai" ]; then
        print_info "Skipping AI services tests"
    else
        run_ai_tests
        run_gateway_tests
    fi

    if [ "$1" == "--skip-frontend" ]; then
        print_info "Skipping frontend tests"
    else
        run_frontend_tests
    fi

    if [ "$1" == "--skip-integration" ]; then
        print_info "Skipping integration tests"
    else
        run_integration_tests
    fi

    if [ "$1" == "--lint" ] || [ "$2" == "--lint" ]; then
        run_linting
    fi

    if [ "$1" == "--coverage" ] || [ "$2" == "--coverage" ]; then
        generate_coverage
    fi

    show_summary
}

# Help message
if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    echo "Usage: ./scripts/test_all.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --skip-backend      Skip backend tests"
    echo "  --skip-ai           Skip AI services tests"
    echo "  --skip-frontend     Skip frontend tests"
    echo "  --skip-integration  Skip integration tests"
    echo "  --lint              Run code quality checks"
    echo "  --coverage          Generate coverage reports"
    echo "  --help, -h          Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./scripts/test_all.sh                    # Run all tests"
    echo "  ./scripts/test_all.sh --lint --coverage  # Run tests with linting and coverage"
    echo "  ./scripts/test_all.sh --skip-frontend    # Run all except frontend tests"
    exit 0
fi

# Run main function
main "$@"
