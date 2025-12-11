#!/bin/bash
# ==============================================================================
# Load Testing Script
# ==============================================================================
# This script runs load tests against the e-commerce platform using Locust
#
# Usage:
#   ./scripts/run_load_tests.sh [SCENARIO] [OPTIONS]
#
# Scenarios:
#   smoke       - Quick smoke test (10 users, 2 min)
#   baseline    - Baseline performance (50 users, 10 min)
#   stress      - Stress test (200 users, 15 min)
#   spike       - Traffic spike test (500 users, 5 min)
#   endurance   - Long-running test (100 users, 60 min)
#
# Options:
#   --host URL  - Target host (default: http://localhost:8000)
#   --report    - Generate HTML report
#   --web       - Launch web UI instead of headless mode
#
# Examples:
#   ./scripts/run_load_tests.sh smoke
#   ./scripts/run_load_tests.sh baseline --report
#   ./scripts/run_load_tests.sh stress --host https://api.yourdomain.com --report
# ==============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default configuration
SCENARIO="${1:-baseline}"
shift || true
HOST="http://localhost:8000"
GENERATE_REPORT=false
WEB_MODE=false

# Parse options
while [[ $# -gt 0 ]]; do
    case $1 in
        --host)
            HOST="$2"
            shift 2
            ;;
        --report)
            GENERATE_REPORT=true
            shift
            ;;
        --web)
            WEB_MODE=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Get project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# Banner
echo -e "${BLUE}===================================================================${NC}"
echo -e "${BLUE}Load Testing - E-Commerce Platform${NC}"
echo -e "${BLUE}===================================================================${NC}"
echo ""

# Check if Locust is installed
if ! command -v locust &> /dev/null; then
    echo -e "${YELLOW}Locust not found. Installing...${NC}"
    pip install -r tests/load/requirements.txt
fi

# Scenario configuration
case $SCENARIO in
    smoke)
        USERS=10
        SPAWN_RATE=2
        RUN_TIME="2m"
        DESCRIPTION="Quick smoke test"
        ;;
    baseline)
        USERS=50
        SPAWN_RATE=5
        RUN_TIME="10m"
        DESCRIPTION="Baseline performance test"
        ;;
    stress)
        USERS=200
        SPAWN_RATE=20
        RUN_TIME="15m"
        DESCRIPTION="Stress test"
        ;;
    spike)
        USERS=500
        SPAWN_RATE=100
        RUN_TIME="5m"
        DESCRIPTION="Traffic spike test"
        ;;
    endurance)
        USERS=100
        SPAWN_RATE=10
        RUN_TIME="60m"
        DESCRIPTION="Endurance test"
        ;;
    *)
        echo -e "${RED}Unknown scenario: $SCENARIO${NC}"
        echo "Available scenarios: smoke, baseline, stress, spike, endurance"
        exit 1
        ;;
esac

# Display test configuration
echo -e "Scenario: ${GREEN}$SCENARIO${NC} - $DESCRIPTION"
echo -e "Target: ${GREEN}$HOST${NC}"
echo -e "Users: ${GREEN}$USERS${NC}"
echo -e "Spawn rate: ${GREEN}$SPAWN_RATE users/sec${NC}"
echo -e "Duration: ${GREEN}$RUN_TIME${NC}"
echo ""

# Check if services are running
echo -e "${BLUE}Checking if services are running...${NC}"
if ! curl -sf "$HOST/health" > /dev/null 2>&1; then
    echo -e "${YELLOW}Warning: Cannot reach $HOST/health${NC}"
    echo -e "${YELLOW}Make sure your services are running${NC}"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo -e "${GREEN}✓ Services are reachable${NC}"
fi
echo ""

# Create reports directory
mkdir -p tests/load/reports

# Build Locust command
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="tests/load/reports/${SCENARIO}_${TIMESTAMP}"

LOCUST_CMD="locust -f tests/load/locustfile.py --host=$HOST"

if [ "$WEB_MODE" = true ]; then
    # Web UI mode
    echo -e "${GREEN}Starting Locust in Web UI mode...${NC}"
    echo -e "Access the web interface at: ${BLUE}http://localhost:8089${NC}"
    echo ""
    $LOCUST_CMD --web-host=0.0.0.0
else
    # Headless mode
    echo -e "${GREEN}Starting load test...${NC}"
    echo ""

    LOCUST_CMD="$LOCUST_CMD --users $USERS --spawn-rate $SPAWN_RATE --run-time $RUN_TIME --headless"

    if [ "$GENERATE_REPORT" = true ]; then
        LOCUST_CMD="$LOCUST_CMD --html ${REPORT_FILE}.html --csv ${REPORT_FILE}"
        echo -e "Reports will be saved to:"
        echo -e "  HTML: ${BLUE}${REPORT_FILE}.html${NC}"
        echo -e "  CSV:  ${BLUE}${REPORT_FILE}_*.csv${NC}"
        echo ""
    fi

    # Run Locust
    $LOCUST_CMD

    EXIT_CODE=$?

    echo ""
    echo -e "${BLUE}===================================================================${NC}"

    if [ $EXIT_CODE -eq 0 ]; then
        echo -e "${GREEN}Load test completed successfully!${NC}"
    else
        echo -e "${RED}Load test failed with exit code: $EXIT_CODE${NC}"
    fi

    echo -e "${BLUE}===================================================================${NC}"
    echo ""

    if [ "$GENERATE_REPORT" = true ]; then
        echo -e "View the HTML report:"
        echo -e "  ${BLUE}open ${REPORT_FILE}.html${NC}"
        echo ""
    fi

    # Display quick summary
    if [ -f "${REPORT_FILE}_stats.csv" ]; then
        echo -e "${BLUE}Quick Summary:${NC}"
        echo ""
        head -n 5 "${REPORT_FILE}_stats.csv" | column -t -s ','
        echo ""
    fi
fi
