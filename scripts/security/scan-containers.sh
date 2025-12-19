#!/bin/bash
# ==============================================================================
# Container Vulnerability Scanning Script
# ==============================================================================
# Scans Docker containers for vulnerabilities using Trivy
#
# Usage:
#   ./scripts/security/scan-containers.sh [service-name]
#
# Arguments:
#   service-name: Optional - scan specific service (default: all)
#
# Examples:
#   ./scripts/security/scan-containers.sh              # Scan all
#   ./scripts/security/scan-containers.sh backend      # Scan backend only
# ==============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
REPORT_DIR="container-scan-reports/$(date +%Y%m%d_%H%M%S)"
TARGET_SERVICE="${1:-all}"
SEVERITY_THRESHOLD="${SEVERITY_THRESHOLD:-CRITICAL,HIGH}"

# All services
SERVICES=(
    "backend"
    "api_gateway"
    "recommender"
    "search"
    "pricing"
    "chatbot"
    "fraud"
    "forecasting"
    "vision"
)

# Create report directory
mkdir -p "$REPORT_DIR"

# Counters
TOTAL_CRITICAL=0
TOTAL_HIGH=0
TOTAL_MEDIUM=0
SCANNED=0
FAILED=0

# Check if Trivy is installed
if ! command -v trivy &> /dev/null; then
    echo -e "${RED}Error: Trivy is not installed${NC}"
    echo "Install with: curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin"
    exit 1
fi

# Scan a single service
scan_service() {
    local service=$1

    echo -e "${BLUE}Scanning ${service}...${NC}"

    # Check if image exists
    if ! docker images --format "{{.Repository}}" | grep -q "^${service}$"; then
        echo -e "${YELLOW}  Image ${service} not found, skipping${NC}"
        return 0
    fi

    # Run Trivy scan
    if trivy image \
        --format json \
        --output "${REPORT_DIR}/trivy-${service}.json" \
        --severity "${SEVERITY_THRESHOLD}" \
        "${service}:latest" 2>/dev/null; then

        ((SCANNED++))

        # Parse results
        if [ -f "${REPORT_DIR}/trivy-${service}.json" ]; then
            local critical=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity=="CRITICAL")] | length' \
                "${REPORT_DIR}/trivy-${service}.json" 2>/dev/null || echo 0)
            local high=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity=="HIGH")] | length' \
                "${REPORT_DIR}/trivy-${service}.json" 2>/dev/null || echo 0)
            local medium=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity=="MEDIUM")] | length' \
                "${REPORT_DIR}/trivy-${service}.json" 2>/dev/null || echo 0)

            TOTAL_CRITICAL=$((TOTAL_CRITICAL + critical))
            TOTAL_HIGH=$((TOTAL_HIGH + high))
            TOTAL_MEDIUM=$((TOTAL_MEDIUM + medium))

            # Display results
            if [ "$critical" -gt 0 ]; then
                echo -e "${RED}  ${service}: ${critical} CRITICAL, ${high} HIGH, ${medium} MEDIUM${NC}"
            elif [ "$high" -gt 0 ]; then
                echo -e "${YELLOW}  ${service}: ${high} HIGH, ${medium} MEDIUM${NC}"
            else
                echo -e "${GREEN}  ${service}: No critical/high vulnerabilities${NC}"
            fi

            # Generate human-readable report
            trivy image \
                --format table \
                --output "${REPORT_DIR}/trivy-${service}.txt" \
                --severity "${SEVERITY_THRESHOLD}" \
                "${service}:latest" 2>/dev/null || true
        fi
    else
        echo -e "${RED}  Failed to scan ${service}${NC}"
        ((FAILED++))
    fi
}

# Generate summary
generate_summary() {
    echo ""
    echo "================================================================"
    echo "SCAN SUMMARY"
    echo "================================================================"
    echo ""
    printf "Services scanned:    %d\n" "$SCANNED"
    printf "Scan failures:       %d\n" "$FAILED"
    echo ""
    printf "Total CRITICAL:      %d\n" "$TOTAL_CRITICAL"
    printf "Total HIGH:          %d\n" "$TOTAL_HIGH"
    printf "Total MEDIUM:        %d\n" "$TOTAL_MEDIUM"
    echo ""
    echo "================================================================"
    echo "Reports saved to: ${REPORT_DIR}"
    echo "================================================================"
    echo ""

    # Create summary file
    {
        echo "Container Vulnerability Scan Summary"
        echo "Generated: $(date)"
        echo ""
        echo "Services scanned: ${SCANNED}"
        echo "Scan failures: ${FAILED}"
        echo ""
        echo "Vulnerabilities found:"
        echo "  CRITICAL: ${TOTAL_CRITICAL}"
        echo "  HIGH: ${TOTAL_HIGH}"
        echo "  MEDIUM: ${TOTAL_MEDIUM}"
        echo ""
        echo "Detailed reports:"
        for file in "${REPORT_DIR}"/trivy-*.json; do
            if [ -f "$file" ]; then
                service=$(basename "$file" .json | sed 's/trivy-//')
                critical=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity=="CRITICAL")] | length' "$file")
                high=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity=="HIGH")] | length' "$file")
                medium=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity=="MEDIUM")] | length' "$file")
                printf "  %-20s CRITICAL: %3d  HIGH: %3d  MEDIUM: %3d\n" "$service" "$critical" "$high" "$medium"
            fi
        done
    } > "${REPORT_DIR}/SUMMARY.txt"
}

# Main execution
main() {
    echo "================================================================"
    echo "Container Vulnerability Scanner"
    echo "================================================================"
    echo ""
    echo "Target: ${TARGET_SERVICE}"
    echo "Severity threshold: ${SEVERITY_THRESHOLD}"
    echo ""

    if [ "$TARGET_SERVICE" = "all" ]; then
        for service in "${SERVICES[@]}"; do
            scan_service "$service"
        done
    else
        scan_service "$TARGET_SERVICE"
    fi

    generate_summary

    # Exit based on findings
    if [ $TOTAL_CRITICAL -gt 0 ]; then
        echo -e "${RED}FAILED: Found ${TOTAL_CRITICAL} CRITICAL vulnerabilities!${NC}"
        exit 1
    elif [ $FAILED -gt 0 ]; then
        echo -e "${YELLOW}WARNING: ${FAILED} scan(s) failed${NC}"
        exit 2
    else
        echo -e "${GREEN}PASSED: No critical vulnerabilities found${NC}"
        exit 0
    fi
}

main
