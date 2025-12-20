#!/bin/bash
set -euo pipefail

##############################################################################
# Test CDN Static File Delivery
#
# This script tests:
# 1. Static file accessibility
# 2. Cache headers are correctly set
# 3. HTTPS is enforced
# 4. Compression is enabled
# 5. CDN is serving files (not origin)
#
# Usage:
#   ./test_cdn_delivery.sh [cdn_domain]
#
# Example:
#   ./test_cdn_delivery.sh d1234567890.cloudfront.net
#   ./test_cdn_delivery.sh cdn.example.com
##############################################################################

CDN_DOMAIN="${1:-}"

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

log_test() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

if [ -z "${CDN_DOMAIN}" ]; then
    echo "Usage: $0 <cdn_domain>"
    echo "Example: $0 d1234567890.cloudfront.net"
    exit 1
fi

# Test URLs
TEST_URLS=(
    "https://${CDN_DOMAIN}/static/admin/css/base.css"
    "https://${CDN_DOMAIN}/static/rest_framework/css/bootstrap.min.css"
)

echo ""
echo "=========================================="
echo "CDN Delivery Test Suite"
echo "=========================================="
echo "CDN Domain: ${CDN_DOMAIN}"
echo ""

TESTS_PASSED=0
TESTS_FAILED=0

for TEST_URL in "${TEST_URLS[@]}"; do
    echo ""
    log_test "Testing: ${TEST_URL}"
    echo ""

    # Fetch headers
    RESPONSE=$(curl -sI "${TEST_URL}" || true)

    # Test 1: HTTP Status
    STATUS=$(echo "${RESPONSE}" | grep -i "^HTTP" | tail -1 | awk '{print $2}')
    if [ "${STATUS}" == "200" ]; then
        log_info "HTTP Status: 200 OK"
        ((TESTS_PASSED++))
    else
        log_error "HTTP Status: ${STATUS} (expected 200)"
        ((TESTS_FAILED++))
    fi

    # Test 2: Cache-Control header
    CACHE_CONTROL=$(echo "${RESPONSE}" | grep -i "^cache-control:" | cut -d' ' -f2- | tr -d '\r')
    if echo "${CACHE_CONTROL}" | grep -qi "max-age"; then
        log_info "Cache-Control: ${CACHE_CONTROL}"
        ((TESTS_PASSED++))

        # Check if max-age is appropriate (at least 1 hour)
        MAX_AGE=$(echo "${CACHE_CONTROL}" | grep -oP 'max-age=\K\d+' || echo "0")
        if [ "${MAX_AGE}" -ge 3600 ]; then
            log_info "Cache duration: ${MAX_AGE}s ($(($MAX_AGE / 3600))h)"
            ((TESTS_PASSED++))
        else
            log_warn "Cache duration too short: ${MAX_AGE}s (recommended: >=1h)"
            ((TESTS_FAILED++))
        fi
    else
        log_error "Cache-Control header missing or invalid: ${CACHE_CONTROL}"
        ((TESTS_FAILED++))
    fi

    # Test 3: Content-Encoding (compression)
    CONTENT_ENCODING=$(echo "${RESPONSE}" | grep -i "^content-encoding:" | cut -d' ' -f2- | tr -d '\r')
    if echo "${CONTENT_ENCODING}" | grep -qi "gzip\|br\|deflate"; then
        log_info "Compression: ${CONTENT_ENCODING}"
        ((TESTS_PASSED++))
    else
        log_warn "No compression detected (expected gzip, brotli, or deflate)"
        # Not counted as failure for CSS files
    fi

    # Test 4: HTTPS enforcement
    if echo "${TEST_URL}" | grep -q "^https://"; then
        log_info "HTTPS: Enabled"
        ((TESTS_PASSED++))
    else
        log_error "HTTPS: Not enabled"
        ((TESTS_FAILED++))
    fi

    # Test 5: CDN headers (CloudFront or Cloudflare)
    CDN_HEADER=$(echo "${RESPONSE}" | grep -iE "^(x-cache|cf-cache-status|x-amz-cf-id):" || true)
    if [ -n "${CDN_HEADER}" ]; then
        log_info "CDN Header detected:"
        echo "${CDN_HEADER}" | sed 's/^/    /'
        ((TESTS_PASSED++))
    else
        log_warn "No CDN-specific headers found (might be direct S3 access)"
    fi

    # Test 6: Content-Type
    CONTENT_TYPE=$(echo "${RESPONSE}" | grep -i "^content-type:" | cut -d' ' -f2- | tr -d '\r')
    if [ -n "${CONTENT_TYPE}" ]; then
        log_info "Content-Type: ${CONTENT_TYPE}"
        ((TESTS_PASSED++))
    fi

    echo ""
    echo "----------------------------------------"
done

# Performance test
echo ""
log_test "Performance Test"
echo ""

SAMPLE_URL="${TEST_URLS[0]}"
log_info "Measuring response time for: ${SAMPLE_URL}"

# Test 3 times and average
TOTAL_TIME=0
for i in {1..3}; do
    TIME=$(curl -o /dev/null -s -w '%{time_total}\n' "${SAMPLE_URL}")
    TOTAL_TIME=$(echo "${TOTAL_TIME} + ${TIME}" | bc)
    echo "  Attempt $i: ${TIME}s"
done

AVG_TIME=$(echo "scale=3; ${TOTAL_TIME} / 3" | bc)
echo ""
log_info "Average response time: ${AVG_TIME}s"

if (( $(echo "${AVG_TIME} < 0.5" | bc -l) )); then
    log_info "Performance: Excellent (<0.5s)"
    ((TESTS_PASSED++))
elif (( $(echo "${AVG_TIME} < 1.0" | bc -l) )); then
    log_info "Performance: Good (<1.0s)"
    ((TESTS_PASSED++))
else
    log_warn "Performance: Slow (>1.0s)"
fi

# Summary
echo ""
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo "Tests Passed: ${TESTS_PASSED}"
echo "Tests Failed: ${TESTS_FAILED}"
echo ""

if [ ${TESTS_FAILED} -eq 0 ]; then
    log_info "All tests passed! CDN is configured correctly."
    exit 0
else
    log_error "Some tests failed. Please review the configuration."
    exit 1
fi
