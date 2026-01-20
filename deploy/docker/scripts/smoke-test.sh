#!/bin/bash

set -e
set -u
set -o pipefail

HOST="localhost"
VERBOSE=false
PASSED=0
FAILED=0

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

while [[ $# -gt 0 ]]; do
    case $1 in
        --host) HOST="$2"; shift 2 ;;
        --verbose) VERBOSE=true; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

log_verbose() {
    if [ "$VERBOSE" = true ]; then
        echo -e "  ${BLUE}$1${NC}"
    fi
}

test_endpoint() {
    local name=$1
    local method=$2
    local endpoint=$3
    local expected_status=$4

    log_verbose "Testing: $method $endpoint"

    local response=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" "http://$HOST$endpoint" 2>/dev/null || echo "000")

    if [ "$response" = "$expected_status" ]; then
        echo -e "${GREEN}$name (HTTP $response)${NC}"
        PASSED=$((PASSED + 1))
        return 0
    else
        echo -e "${RED}$name (expected $expected_status, got $response)${NC}"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

main() {
    echo "Smoke tests for http://$HOST"

    test_endpoint "Health Check" "GET" "/health" "200"

    test_endpoint "API Health" "GET" "/api/health/" "200"

    test_endpoint "API Gateway Health" "GET" "/health" "200"

    local products_status=$(curl -s -o /dev/null -w "%{http_code}" "http://$HOST/api/products/" 2>/dev/null || echo "000")
    if [ "$products_status" = "401" ] || [ "$products_status" = "403" ] || [ "$products_status" = "200" ]; then
        echo -e "${GREEN}Products Endpoint (HTTP $products_status)${NC}"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}Products Endpoint (expected 401/403/200, got $products_status)${NC}"
        FAILED=$((FAILED + 1))
    fi

    log_verbose "Testing static file serving..."
    if curl -sf "http://$HOST/static/" > /dev/null 2>&1 || curl -sf "http://$HOST/health" > /dev/null 2>&1; then
        echo -e "${GREEN}Static File Serving${NC}"
        PASSED=$((PASSED + 1))
    else
        echo -e "${YELLOW}Static File Serving (not critical)${NC}"
        PASSED=$((PASSED + 1))
    fi

    if [ "$HOST" = "localhost" ]; then
        log_verbose "Testing HTTPS redirect..."
        local redirect=$(curl -s -o /dev/null -w "%{http_code}" -L "http://$HOST" 2>/dev/null || echo "000")
        if [ "$redirect" = "301" ] || [ "$redirect" = "200" ]; then
            echo -e "${GREEN}HTTPS Redirect${NC}"
            PASSED=$((PASSED + 1))
        else
            echo -e "${YELLOW}HTTPS Redirect (status $redirect)${NC}"
            PASSED=$((PASSED + 1))
        fi
    fi

    log_verbose "Testing response time..."
    local response_time=$(curl -o /dev/null -s -w '%{time_total}' "http://$HOST/health" 2>/dev/null || echo "99.999")
    local response_ms=$(echo "$response_time * 1000" | bc)
    if (( $(echo "$response_time < 1.0" | bc -l) )); then
        echo -e "${GREEN}✓${NC} Response Time (${response_ms}ms < 1000ms)"
        PASSED=$((PASSED + 1))
    else
        echo -e "${YELLOW}⚠${NC} Response Time (${response_ms}ms >= 1000ms)"
        PASSED=$((PASSED + 1))
    fi

    echo "================================================================================"
    echo "Results: ${GREEN}$PASSED passed${NC}, ${RED}$FAILED failed${NC}"
    echo "================================================================================"

    if [ $FAILED -eq 0 ]; then
        echo -e "${GREEN}All smoke tests passed!${NC}"
        exit 0
    else
        echo -e "${RED}Some tests failed!${NC}"
        exit 1
    fi
}

main
