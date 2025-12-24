#!/bin/bash
# ==============================================================================
# Dependency Audit Script
# ==============================================================================
# Checks all Python dependencies for outdated packages and security vulnerabilities
#
# Usage:
#   ./audit-dependencies.sh [OPTIONS]
#
# Options:
#   --outdated-only      Only check for outdated packages
#   --security-only      Only run security checks
#   --json               Output in JSON format
#   --report-dir DIR     Directory for reports (default: /tmp/dependency-audit)
#
# Requirements:
#   - pip-audit (install: pip install pip-audit)
#   - jq (for JSON processing)
# ==============================================================================

set -e
set -u
set -o pipefail

# Configuration
OUTDATED_ONLY=false
SECURITY_ONLY=false
JSON_OUTPUT=false
REPORT_DIR="/tmp/dependency-audit"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --outdated-only) OUTDATED_ONLY=true; shift ;;
        --security-only) SECURITY_ONLY=true; shift ;;
        --json) JSON_OUTPUT=true; shift ;;
        --report-dir) REPORT_DIR="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# Create report directory
mkdir -p "$REPORT_DIR"

# Check for required tools
check_requirements() {
    if ! command -v pip-audit &> /dev/null; then
        log_error "pip-audit is not installed"
        log_info "Install with: pip install pip-audit"
        exit 1
    fi
}

# Audit specific service
audit_service() {
    local service_name=$1
    local service_path=$2

    log_header "Auditing: $service_name"

    if [ ! -f "$service_path/requirements.txt" ]; then
        log_warn "No requirements.txt found at $service_path"
        return 0
    fi

    # Change to service directory
    cd "$service_path"

    # Check for outdated packages
    if [ "$SECURITY_ONLY" != "true" ]; then
        log_info "Checking for outdated packages..."

        local outdated_file="$REPORT_DIR/${service_name}-outdated-${TIMESTAMP}.txt"

        if pip list --outdated --format=columns > "$outdated_file" 2>&1; then
            local count=$(tail -n +3 "$outdated_file" | wc -l)
            if [ "$count" -gt 0 ]; then
                log_warn "Found $count outdated packages in $service_name"
                cat "$outdated_file"
            else
                log_info "All packages up to date"
            fi
        else
            log_error "Failed to check outdated packages"
        fi
    fi

    # Security audit
    if [ "$OUTDATED_ONLY" != "true" ]; then
        log_info "Running security audit..."

        local audit_file="$REPORT_DIR/${service_name}-security-${TIMESTAMP}.json"

        if pip-audit --format json --output "$audit_file" 2>&1; then
            log_info "✅ No security vulnerabilities found"
        else
            local vuln_count=$(jq '.dependencies | length' "$audit_file" 2>/dev/null || echo "unknown")
            log_error "❌ Found $vuln_count vulnerable packages in $service_name"

            # Display vulnerabilities
            if [ "$JSON_OUTPUT" != "true" ]; then
                pip-audit --desc on
            fi
        fi
    fi

    cd - > /dev/null
}

# Generate summary report
generate_summary() {
    log_header "Audit Summary"

    local total_outdated=0
    local total_vulnerable=0

    # Count outdated packages
    for file in "$REPORT_DIR"/*-outdated-*.txt; do
        if [ -f "$file" ]; then
            local count=$(tail -n +3 "$file" | wc -l)
            total_outdated=$((total_outdated + count))
        fi
    done

    # Count vulnerable packages
    for file in "$REPORT_DIR"/*-security-*.json; do
        if [ -f "$file" ]; then
            local count=$(jq '.dependencies | length' "$file" 2>/dev/null || echo "0")
            total_vulnerable=$((total_vulnerable + count))
        fi
    done

    echo ""
    echo "📊 Audit Results:"
    echo "   Outdated Packages: $total_outdated"
    echo "   Vulnerable Packages: $total_vulnerable"
    echo ""
    echo "📁 Reports saved to: $REPORT_DIR"
    echo ""

    # Create summary file
    cat > "$REPORT_DIR/summary-${TIMESTAMP}.txt" <<EOF
Dependency Audit Summary
========================
Date: $(date)
Timestamp: $TIMESTAMP

Results:
  Total Outdated Packages: $total_outdated
  Total Vulnerable Packages: $total_vulnerable

Status: $( [ $total_vulnerable -eq 0 ] && echo "✅ PASSED" || echo "❌ FAILED - Security vulnerabilities found" )

Reports:
$(ls -1 "$REPORT_DIR"/*-${TIMESTAMP}.* 2>/dev/null || echo "  No reports generated")

Recommendations:
$( [ $total_vulnerable -gt 0 ] && echo "  ⚠️  URGENT: Review and fix security vulnerabilities immediately" )
$( [ $total_outdated -gt 5 ] && echo "  - Consider updating outdated packages in next sprint" )
$( [ $total_outdated -eq 0 ] && [ $total_vulnerable -eq 0 ] && echo "  ✅ All dependencies are up to date and secure" )

Next Audit: $(date -d "+1 month" +%Y-%m-%d)
EOF

    cat "$REPORT_DIR/summary-${TIMESTAMP}.txt"
}

main() {
    echo "================================================================================"
    echo "  Dependency Audit"
    echo "================================================================================"
    echo "  Timestamp: $(date)"
    echo "  Report Directory: $REPORT_DIR"
    echo "================================================================================"

    check_requirements

    # Get project root
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

    cd "$PROJECT_ROOT"

    # Audit all services
    audit_service "backend" "services/backend"
    audit_service "ai-api-gateway" "services/ai/api_gateway"
    audit_service "recommendation-engine" "services/ai/services/recommendation_engine"
    audit_service "fraud-detection" "services/ai/services/fraud_detection"
    audit_service "search-engine" "services/ai/services/search_engine"
    audit_service "chatbot-rag" "services/ai/services/chatbot_rag"
    audit_service "pricing-engine" "services/ai/services/pricing_engine"
    audit_service "demand-forecasting" "services/ai/services/demand_forecasting"
    audit_service "visual-recognition" "services/ai/services/visual_recognition"

    # Generate summary
    generate_summary

    # Exit with error if vulnerabilities found
    local vuln_count=$(find "$REPORT_DIR" -name "*-security-${TIMESTAMP}.json" -exec jq -s 'map(.dependencies | length) | add' {} \; 2>/dev/null || echo "0")

    if [ "$vuln_count" -gt 0 ]; then
        log_error "Security vulnerabilities found! Please review and fix."
        exit 1
    fi

    log_info "Audit complete - no security issues found"
    exit 0
}

main
