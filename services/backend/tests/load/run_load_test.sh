#!/bin/bash
set -euo pipefail

##############################################################################
# Run Load Tests with Locust
#
# This script runs comprehensive load tests against the application and
# generates detailed reports.
#
# Usage:
#   ./run_load_test.sh [test_profile] [host]
#
# Test Profiles:
#   smoke    - Quick smoke test (10 users, 1 min)
#   baseline - Establish performance baseline (100 users, 10 min)
#   load     - Standard load test (500 users, 10 min)
#   stress   - Stress test (1000 users, 15 min)
#   spike    - Spike test (rapid ramp-up to 2000 users)
#   soak     - Endurance test (200 users, 60 min)
#
# Examples:
#   ./run_load_test.sh smoke http://localhost:8000
#   ./run_load_test.sh load https://api.production.com
##############################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPORTS_DIR="${SCRIPT_DIR}/reports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Parse arguments
PROFILE="${1:-load}"
HOST="${2:-http://localhost:8000}"

# Ensure reports directory exists
mkdir -p "${REPORTS_DIR}"

log_info "Load Test Configuration"
log_info "======================="
log_info "Profile: ${PROFILE}"
log_info "Target Host: ${HOST}"
log_info "Report Directory: ${REPORTS_DIR}"
log_info "Timestamp: ${TIMESTAMP}"
echo ""

# Configure test parameters based on profile
case "${PROFILE}" in
    smoke)
        USERS=10
        SPAWN_RATE=5
        RUN_TIME="1m"
        log_info "Running SMOKE test (quick validation)"
        ;;
    baseline)
        USERS=100
        SPAWN_RATE=10
        RUN_TIME="10m"
        log_info "Running BASELINE test (establish performance metrics)"
        ;;
    load)
        USERS=500
        SPAWN_RATE=50
        RUN_TIME="10m"
        log_info "Running LOAD test (standard load)"
        ;;
    stress)
        USERS=1000
        SPAWN_RATE=100
        RUN_TIME="15m"
        log_info "Running STRESS test (high load)"
        ;;
    spike)
        USERS=2000
        SPAWN_RATE=500
        RUN_TIME="5m"
        log_info "Running SPIKE test (rapid scaling)"
        ;;
    soak)
        USERS=200
        SPAWN_RATE=20
        RUN_TIME="60m"
        log_info "Running SOAK test (endurance)"
        ;;
    *)
        log_error "Unknown profile: ${PROFILE}"
        log_info "Available profiles: smoke, baseline, load, stress, spike, soak"
        exit 1
        ;;
esac

# Report files
HTML_REPORT="${REPORTS_DIR}/load_test_${PROFILE}_${TIMESTAMP}.html"
CSV_STATS="${REPORTS_DIR}/load_test_${PROFILE}_${TIMESTAMP}_stats.csv"
CSV_HISTORY="${REPORTS_DIR}/load_test_${PROFILE}_${TIMESTAMP}_history.csv"
CSV_FAILURES="${REPORTS_DIR}/load_test_${PROFILE}_${TIMESTAMP}_failures.csv"
JSON_REPORT="${REPORTS_DIR}/load_test_${PROFILE}_${TIMESTAMP}.json"

log_step "Starting load test..."
log_info "Users: ${USERS}"
log_info "Spawn Rate: ${SPAWN_RATE} users/sec"
log_info "Duration: ${RUN_TIME}"
echo ""

# Run Locust
locust -f "${SCRIPT_DIR}/locustfile.py" \
    --host="${HOST}" \
    --users="${USERS}" \
    --spawn-rate="${SPAWN_RATE}" \
    --run-time="${RUN_TIME}" \
    --headless \
    --html="${HTML_REPORT}" \
    --csv="${REPORTS_DIR}/load_test_${PROFILE}_${TIMESTAMP}" \
    --logfile="${REPORTS_DIR}/load_test_${PROFILE}_${TIMESTAMP}.log" \
    --loglevel INFO

EXIT_CODE=$?

echo ""
if [ ${EXIT_CODE} -eq 0 ]; then
    log_info "Load test completed successfully!"
else
    log_error "Load test failed with exit code ${EXIT_CODE}"
fi

# Generate summary
log_step "Generating test summary..."

if [ -f "${CSV_STATS}" ]; then
    log_info "Performance Summary:"
    echo ""
    echo "Top 5 Slowest Endpoints (by P99):"
    # Skip header, sort by P99 (column 9), show top 5
    tail -n +2 "${CSV_STATS}" | sort -t',' -k9 -nr | head -5 | \
        awk -F',' '{printf "  %-40s P99: %6s ms\n", $1, $9}'

    echo ""
    echo "Endpoints with Failures:"
    # Show endpoints with failures (column 5 > 0)
    tail -n +2 "${CSV_STATS}" | awk -F',' '$5 > 0 {printf "  %-40s Failures: %s\n", $1, $5}'
fi

echo ""
log_info "Test Reports:"
log_info "  HTML Report: ${HTML_REPORT}"
log_info "  Stats CSV: ${CSV_STATS}"
log_info "  History CSV: ${CSV_HISTORY}"
log_info "  Log File: ${REPORTS_DIR}/load_test_${PROFILE}_${TIMESTAMP}.log"

echo ""
log_step "Next Steps:"
echo "  1. Open HTML report: ${HTML_REPORT}"
echo "  2. Review performance metrics against baselines"
echo "  3. Run regression analysis: ./analyze_results.py ${CSV_STATS}"
echo "  4. Archive report if this is a baseline run"

exit ${EXIT_CODE}
