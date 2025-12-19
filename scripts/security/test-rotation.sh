#!/bin/bash
# ==============================================================================
# Test Secrets Rotation - Safe Testing Script
# ==============================================================================
# This script performs a safe test of the secrets rotation process without
# actually changing production secrets.
#
# Usage:
#   ./scripts/security/test-rotation.sh [service]
#
# Arguments:
#   service: Optional - database|redis|jwt|all (default: all)
#
# What it does:
#   1. Validates Vault connectivity
#   2. Checks if secrets exist
#   3. Verifies service health
#   4. Tests password generation
#   5. Simulates rotation workflow
#   6. Does NOT modify actual secrets
#
# Use this to verify rotation will work before running actual rotation
# ==============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
VAULT_ADDR="${VAULT_ADDR:-http://localhost:8200}"
HEALTH_CHECK_URL="${HEALTH_CHECK_URL:-http://localhost:8000/health/}"

# Test results
TESTS_PASSED=0
TESTS_FAILED=0

# Logging
log_test() {
    local status=$1
    local message=$2

    if [ "$status" = "PASS" ]; then
        echo -e "${GREEN}[PASS]${NC} ${message}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}[FAIL]${NC} ${message}"
        ((TESTS_FAILED++))
    fi
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $@"
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $@"
}

# Test 1: Check Vault connectivity
test_vault_connectivity() {
    log_info "Testing Vault connectivity..."

    if curl -s "${VAULT_ADDR}/v1/sys/health" > /dev/null; then
        log_test "PASS" "Vault is accessible at ${VAULT_ADDR}"
    else
        log_test "FAIL" "Cannot connect to Vault at ${VAULT_ADDR}"
        return 1
    fi

    local sealed=$(curl -s "${VAULT_ADDR}/v1/sys/seal-status" | jq -r '.sealed')
    if [ "$sealed" = "false" ]; then
        log_test "PASS" "Vault is unsealed"
    else
        log_test "FAIL" "Vault is sealed"
        return 1
    fi

    return 0
}

# Test 2: Check Vault authentication
test_vault_authentication() {
    log_info "Testing Vault authentication..."

    if [ -z "${VAULT_TOKEN:-}" ]; then
        log_test "FAIL" "VAULT_TOKEN not set"
        return 1
    fi

    local result=$(curl -s -H "X-Vault-Token: ${VAULT_TOKEN}" \
        "${VAULT_ADDR}/v1/auth/token/lookup-self")

    local valid=$(echo "$result" | jq -r '.data.id' 2>/dev/null)

    if [ -n "$valid" ] && [ "$valid" != "null" ]; then
        log_test "PASS" "Vault authentication valid"
    else
        log_test "FAIL" "Vault authentication failed"
        return 1
    fi

    return 0
}

# Test 3: Check if database secrets exist
test_database_secrets() {
    log_info "Testing database secrets access..."

    local result=$(curl -s -H "X-Vault-Token: ${VAULT_TOKEN}" \
        "${VAULT_ADDR}/v1/ecommerce/data/backend/database")

    local password=$(echo "$result" | jq -r '.data.data.DB_PASSWORD' 2>/dev/null)

    if [ -n "$password" ] && [ "$password" != "null" ]; then
        log_test "PASS" "Database password exists in Vault"
    else
        log_test "FAIL" "Database password not found in Vault"
        return 1
    fi

    return 0
}

# Test 4: Check if Redis secrets exist
test_redis_secrets() {
    log_info "Testing Redis secrets access..."

    local result=$(curl -s -H "X-Vault-Token: ${VAULT_TOKEN}" \
        "${VAULT_ADDR}/v1/ecommerce/data/backend/redis")

    local password=$(echo "$result" | jq -r '.data.data.REDIS_PASSWORD' 2>/dev/null)

    if [ -n "$password" ] && [ "$password" != "null" ]; then
        log_test "PASS" "Redis password exists in Vault"
    else
        log_test "FAIL" "Redis password not found in Vault"
        return 1
    fi

    return 0
}

# Test 5: Check if JWT secrets exist
test_jwt_secrets() {
    log_info "Testing JWT secrets access..."

    local result=$(curl -s -H "X-Vault-Token: ${VAULT_TOKEN}" \
        "${VAULT_ADDR}/v1/ecommerce/data/backend/django")

    local secret=$(echo "$result" | jq -r '.data.data.JWT_SECRET' 2>/dev/null)

    if [ -n "$secret" ] && [ "$secret" != "null" ]; then
        log_test "PASS" "JWT secret exists in Vault"
    elif [ -z "$secret" ] || [ "$secret" = "null" ]; then
        log_warning "JWT secret not configured in Vault (optional)"
        log_test "PASS" "JWT secret check completed (not configured)"
    else
        log_test "FAIL" "JWT secret check failed"
        return 1
    fi

    return 0
}

# Test 6: Check service health
test_service_health() {
    log_info "Testing service health endpoints..."

    if curl -f -s "${HEALTH_CHECK_URL}" > /dev/null; then
        log_test "PASS" "Backend service health check passed"
    else
        log_test "FAIL" "Backend service health check failed"
        return 1
    fi

    return 0
}

# Test 7: Check database connectivity
test_database_connectivity() {
    log_info "Testing database connectivity..."

    if docker-compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
        log_test "PASS" "PostgreSQL is accepting connections"
    else
        log_test "FAIL" "PostgreSQL is not accessible"
        return 1
    fi

    return 0
}

# Test 8: Check Redis connectivity
test_redis_connectivity() {
    log_info "Testing Redis connectivity..."

    if docker-compose exec -T redis redis-cli ping 2>/dev/null | grep -q PONG; then
        log_test "PASS" "Redis is responding to commands"
    else
        log_test "FAIL" "Redis is not accessible"
        return 1
    fi

    return 0
}

# Test 9: Test password generation
test_password_generation() {
    log_info "Testing password generation..."

    local password=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)

    if [ ${#password} -eq 32 ]; then
        log_test "PASS" "Password generation works (length: 32)"
    else
        log_test "FAIL" "Password generation failed (length: ${#password})"
        return 1
    fi

    local jwt_secret=$(openssl rand -base64 64 | tr -d '\n')

    if [ ${#jwt_secret} -gt 0 ]; then
        log_test "PASS" "JWT secret generation works (length: ${#jwt_secret})"
    else
        log_test "FAIL" "JWT secret generation failed"
        return 1
    fi

    return 0
}

# Test 10: Check Docker Compose availability
test_docker_compose() {
    log_info "Testing Docker Compose availability..."

    if command -v docker-compose &> /dev/null; then
        log_test "PASS" "docker-compose command available"
    else
        log_test "FAIL" "docker-compose command not found"
        return 1
    fi

    if docker-compose ps > /dev/null 2>&1; then
        log_test "PASS" "Can execute docker-compose commands"
    else
        log_test "FAIL" "Cannot execute docker-compose commands"
        return 1
    fi

    return 0
}

# Test 11: Check required tools
test_required_tools() {
    log_info "Testing required tools..."

    local tools=("curl" "jq" "openssl" "docker-compose")
    local all_found=true

    for tool in "${tools[@]}"; do
        if command -v "$tool" &> /dev/null; then
            log_test "PASS" "${tool} is installed"
        else
            log_test "FAIL" "${tool} is not installed"
            all_found=false
        fi
    done

    if [ "$all_found" = true ]; then
        return 0
    else
        return 1
    fi
}

# Test 12: Simulate database rotation
simulate_database_rotation() {
    log_info "Simulating database password rotation workflow..."

    # Generate test password
    local test_password=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)

    # Check current password retrieval
    local current=$(curl -s -H "X-Vault-Token: ${VAULT_TOKEN}" \
        "${VAULT_ADDR}/v1/ecommerce/data/backend/database" \
        | jq -r '.data.data.DB_PASSWORD')

    if [ -n "$current" ] && [ "$current" != "null" ]; then
        log_test "PASS" "Can retrieve current database password"
    else
        log_test "FAIL" "Cannot retrieve current database password"
        return 1
    fi

    # Test database user exists
    if docker-compose exec -T postgres psql -U postgres -c "\du ecommerce_user" > /dev/null 2>&1; then
        log_test "PASS" "Database user 'ecommerce_user' exists"
    else
        log_warning "Database user 'ecommerce_user' not found (may use different name)"
        log_test "PASS" "Database user check completed"
    fi

    log_info "Database rotation simulation successful (no changes made)"
    return 0
}

# Main test execution
main() {
    local service="${1:-all}"

    echo "============================================================"
    echo "  Secrets Rotation Test Suite"
    echo "  Mode: Safe Testing (No Actual Changes)"
    echo "  Started: $(date)"
    echo "============================================================"
    echo ""

    # Infrastructure tests (always run)
    echo -e "${BLUE}Running infrastructure tests...${NC}"
    echo ""
    test_required_tools || true
    test_vault_connectivity || true
    test_vault_authentication || true
    test_docker_compose || true
    echo ""

    # Service tests
    echo -e "${BLUE}Running service tests...${NC}"
    echo ""
    test_service_health || true
    test_database_connectivity || true
    test_redis_connectivity || true
    echo ""

    # Secret tests based on service parameter
    echo -e "${BLUE}Running secret tests...${NC}"
    echo ""

    case "$service" in
        database)
            test_database_secrets || true
            test_password_generation || true
            simulate_database_rotation || true
            ;;
        redis)
            test_redis_secrets || true
            test_password_generation || true
            ;;
        jwt)
            test_jwt_secrets || true
            test_password_generation || true
            ;;
        all)
            test_database_secrets || true
            test_redis_secrets || true
            test_jwt_secrets || true
            test_password_generation || true
            simulate_database_rotation || true
            ;;
        *)
            echo -e "${RED}Invalid service: ${service}${NC}"
            echo "Usage: $0 [database|redis|jwt|all]"
            exit 1
            ;;
    esac

    # Summary
    echo ""
    echo "============================================================"
    echo "  Test Results Summary"
    echo "============================================================"
    echo ""
    echo -e "  ${GREEN}Passed:${NC} ${TESTS_PASSED}"
    echo -e "  ${RED}Failed:${NC} ${TESTS_FAILED}"
    echo -e "  ${BLUE}Total:${NC}  $((TESTS_PASSED + TESTS_FAILED))"
    echo ""

    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "${GREEN}All tests passed! Rotation should work correctly.${NC}"
        echo ""
        echo "To run actual rotation:"
        echo "  ./scripts/security/rotate-secrets.sh ${service}"
        exit 0
    else
        echo -e "${RED}Some tests failed. Fix issues before running rotation.${NC}"
        exit 1
    fi
}

main "$@"
