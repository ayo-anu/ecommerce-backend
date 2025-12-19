#!/bin/bash
set -euo pipefail

# SBOM Generation Script
# Generates Software Bill of Materials for all container images locally

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
OUTPUT_DIR="${SBOM_OUTPUT_DIR:-./sbom-reports}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_DIR="$OUTPUT_DIR/$TIMESTAMP"

# Service list
SERVICES=(
    "backend"
    "api-gateway"
    "recommendation-engine"
    "search-engine"
    "pricing-engine"
    "chatbot-rag"
    "fraud-detection"
    "demand-forecasting"
    "visual-recognition"
)

# Functions
log() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} $1"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

check_dependencies() {
    log "Checking dependencies..."

    local missing_deps=()

    if ! command -v docker &> /dev/null; then
        missing_deps+=("docker")
    fi

    if ! command -v syft &> /dev/null; then
        warn "syft not found. Install from: https://github.com/anchore/syft"
        missing_deps+=("syft")
    fi

    if ! command -v grype &> /dev/null; then
        warn "grype not found. Install from: https://github.com/anchore/grype"
        missing_deps+=("grype")
    fi

    if ! command -v trivy &> /dev/null; then
        warn "trivy not found. Install from: https://github.com/aquasecurity/trivy"
        missing_deps+=("trivy")
    fi

    if [ ${#missing_deps[@]} -gt 0 ]; then
        error "Missing required dependencies: ${missing_deps[*]}"
        echo ""
        echo "Installation instructions:"
        echo "  Syft:  curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin"
        echo "  Grype: curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh -s -- -b /usr/local/bin"
        echo "  Trivy: https://aquasecurity.github.io/trivy/latest/getting-started/installation/"
        exit 1
    fi

    log "All dependencies satisfied"
}

get_service_dockerfile() {
    local service=$1

    if [ "$service" == "backend" ]; then
        echo "services/backend/Dockerfile"
    elif [ "$service" == "api-gateway" ]; then
        echo "services/ai/api_gateway/Dockerfile"
    else
        echo "services/ai/$service/Dockerfile"
    fi
}

get_service_context() {
    local service=$1

    if [ "$service" == "backend" ]; then
        echo "services/backend"
    elif [ "$service" == "api-gateway" ]; then
        echo "services/ai/api_gateway"
    else
        echo "services/ai/$service"
    fi
}

build_image() {
    local service=$1
    local dockerfile=$(get_service_dockerfile "$service")
    local context=$(get_service_context "$service")

    if [ ! -f "$dockerfile" ]; then
        warn "Dockerfile not found for $service at $dockerfile"
        return 1
    fi

    log "Building Docker image for $service..."
    docker build -t "$service:sbom-scan" -f "$dockerfile" "$context" >/dev/null 2>&1 || {
        error "Failed to build image for $service"
        return 1
    }

    log "Image built: $service:sbom-scan"
}

generate_sbom_syft() {
    local service=$1
    local service_dir="$REPORT_DIR/$service"

    info "Generating SBOM with Syft..."

    # CycloneDX JSON
    syft "$service:sbom-scan" \
        -o cyclonedx-json \
        --file "$service_dir/sbom-$service-cyclonedx.json" 2>/dev/null

    # SPDX JSON
    syft "$service:sbom-scan" \
        -o spdx-json \
        --file "$service_dir/sbom-$service-spdx.json" 2>/dev/null

    # Human-readable table
    syft "$service:sbom-scan" \
        -o table \
        --file "$service_dir/sbom-$service-table.txt" 2>/dev/null

    log "Syft SBOM generated"
}

generate_sbom_trivy() {
    local service=$1
    local service_dir="$REPORT_DIR/$service"

    info "Generating SBOM with Trivy..."

    trivy image \
        --format cyclonedx \
        --output "$service_dir/sbom-$service-trivy.json" \
        "$service:sbom-scan" 2>/dev/null

    log "Trivy SBOM generated"
}

scan_vulnerabilities() {
    local service=$1
    local service_dir="$REPORT_DIR/$service"

    info "Scanning for vulnerabilities with Grype..."

    grype "sbom:$service_dir/sbom-$service-cyclonedx.json" \
        -o json \
        --file "$service_dir/grype-results.json" 2>/dev/null || true

    grype "sbom:$service_dir/sbom-$service-cyclonedx.json" \
        -o table \
        --file "$service_dir/grype-results.txt" 2>/dev/null || true

    log "Vulnerability scan complete"
}

scan_trivy() {
    local service=$1
    local service_dir="$REPORT_DIR/$service"

    info "Scanning with Trivy..."

    trivy image \
        --format json \
        --output "$service_dir/trivy-scan.json" \
        "$service:sbom-scan" 2>/dev/null || true

    trivy image \
        --format table \
        --output "$service_dir/trivy-scan.txt" \
        "$service:sbom-scan" 2>/dev/null || true

    log "Trivy scan complete"
}

generate_summary() {
    local service=$1
    local service_dir="$REPORT_DIR/$service"

    info "Generating summary report..."

    # Extract vulnerability counts
    local critical=0
    local high=0
    local medium=0
    local low=0

    if [ -f "$service_dir/grype-results.json" ]; then
        critical=$(jq '[.matches[] | select(.vulnerability.severity=="Critical")] | length' "$service_dir/grype-results.json" 2>/dev/null || echo 0)
        high=$(jq '[.matches[] | select(.vulnerability.severity=="High")] | length' "$service_dir/grype-results.json" 2>/dev/null || echo 0)
        medium=$(jq '[.matches[] | select(.vulnerability.severity=="Medium")] | length' "$service_dir/grype-results.json" 2>/dev/null || echo 0)
        low=$(jq '[.matches[] | select(.vulnerability.severity=="Low")] | length' "$service_dir/grype-results.json" 2>/dev/null || echo 0)
    fi

    cat > "$service_dir/SUMMARY.md" <<EOF
# SBOM Summary - $service

**Generated**: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
**Image**: $service:sbom-scan

---

## Vulnerability Summary

| Severity | Count |
|----------|-------|
| Critical | $critical |
| High     | $high |
| Medium   | $medium |
| Low      | $low |

---

## SBOM Formats Generated

- **CycloneDX JSON** (Syft): \`sbom-$service-cyclonedx.json\`
- **SPDX JSON** (Syft): \`sbom-$service-spdx.json\`
- **CycloneDX JSON** (Trivy): \`sbom-$service-trivy.json\`
- **Table format** (Syft): \`sbom-$service-table.txt\`

---

## Vulnerability Scan Results

- **Grype JSON**: \`grype-results.json\`
- **Grype Table**: \`grype-results.txt\`
- **Trivy JSON**: \`trivy-scan.json\`
- **Trivy Table**: \`trivy-scan.txt\`

---

## Package Overview

\`\`\`
$(head -30 "$service_dir/sbom-$service-table.txt" 2>/dev/null || echo "N/A")
\`\`\`

---

## Critical & High Vulnerabilities

\`\`\`
$(grep -E "Critical|High" "$service_dir/grype-results.txt" 2>/dev/null | head -20 || echo "No critical or high vulnerabilities found")
\`\`\`

---

## Action Items

EOF

    if [ "$critical" -gt 0 ]; then
        echo "- ⚠️ **URGENT**: Fix $critical CRITICAL vulnerabilities" >> "$service_dir/SUMMARY.md"
    fi

    if [ "$high" -gt 0 ]; then
        echo "- ⚠️ Fix $high HIGH vulnerabilities" >> "$service_dir/SUMMARY.md"
    fi

    if [ "$medium" -gt 0 ]; then
        echo "- Review $medium MEDIUM vulnerabilities" >> "$service_dir/SUMMARY.md"
    fi

    if [ "$critical" -eq 0 ] && [ "$high" -eq 0 ]; then
        echo "- ✅ No critical or high vulnerabilities found" >> "$service_dir/SUMMARY.md"
    fi

    log "Summary report generated"
}

process_service() {
    local service=$1
    local service_dir="$REPORT_DIR/$service"

    echo ""
    log "=========================================="
    log "Processing: $service"
    log "=========================================="

    mkdir -p "$service_dir"

    # Build image
    if ! build_image "$service"; then
        error "Skipping $service due to build failure"
        return 1
    fi

    # Generate SBOMs
    generate_sbom_syft "$service"
    generate_sbom_trivy "$service"

    # Scan for vulnerabilities
    scan_vulnerabilities "$service"
    scan_trivy "$service"

    # Generate summary
    generate_summary "$service"

    log "✅ $service complete"
}

generate_consolidated_report() {
    log "Generating consolidated report..."

    cat > "$REPORT_DIR/CONSOLIDATED_REPORT.md" <<EOF
# Consolidated SBOM Report

**Generated**: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
**Report Directory**: $REPORT_DIR

---

## Services Scanned

EOF

    for service in "${SERVICES[@]}"; do
        if [ -f "$REPORT_DIR/$service/SUMMARY.md" ]; then
            local critical=$(jq '[.matches[] | select(.vulnerability.severity=="Critical")] | length' "$REPORT_DIR/$service/grype-results.json" 2>/dev/null || echo 0)
            local high=$(jq '[.matches[] | select(.vulnerability.severity=="High")] | length' "$REPORT_DIR/$service/grype-results.json" 2>/dev/null || echo 0)
            local medium=$(jq '[.matches[] | select(.vulnerability.severity=="Medium")] | length' "$REPORT_DIR/$service/grype-results.json" 2>/dev/null || echo 0)

            local status="✅"
            if [ "$critical" -gt 0 ]; then
                status="🔴"
            elif [ "$high" -gt 0 ]; then
                status="🟡"
            fi

            cat >> "$REPORT_DIR/CONSOLIDATED_REPORT.md" <<EOF
### $status $service

- **Critical**: $critical
- **High**: $high
- **Medium**: $medium
- [View detailed report](./$service/SUMMARY.md)

EOF
        fi
    done

    cat >> "$REPORT_DIR/CONSOLIDATED_REPORT.md" <<EOF

---

## Overall Statistics

\`\`\`
$(find "$REPORT_DIR" -name "SUMMARY.md" -exec grep -h "| Critical" {} \; | awk -F'|' '{sum+=$3} END {print "Total Critical: " sum}')
$(find "$REPORT_DIR" -name "SUMMARY.md" -exec grep -h "| High" {} \; | awk -F'|' '{sum+=$3} END {print "Total High: " sum}')
$(find "$REPORT_DIR" -name "SUMMARY.md" -exec grep -h "| Medium" {} \; | awk -F'|' '{sum+=$3} END {print "Total Medium: " sum}')
\`\`\`

---

## Files Generated

All SBOMs and vulnerability reports are stored in:
\`$REPORT_DIR\`

## Next Steps

1. Review services with CRITICAL vulnerabilities (🔴)
2. Update vulnerable dependencies
3. Rebuild affected images
4. Re-run SBOM generation to verify fixes
5. Archive SBOMs for compliance

EOF

    log "Consolidated report generated"
}

# Main execution
main() {
    echo ""
    log "=========================================="
    log "  SBOM Generation Script"
    log "=========================================="
    echo ""

    # Check dependencies
    check_dependencies

    # Create output directory
    mkdir -p "$REPORT_DIR"
    log "Output directory: $REPORT_DIR"
    echo ""

    # Process services
    local services_to_process=("${SERVICES[@]}")

    # Allow single service via command line
    if [ $# -gt 0 ]; then
        services_to_process=("$@")
    fi

    local success=0
    local failed=0

    for service in "${services_to_process[@]}"; do
        if process_service "$service"; then
            ((success++))
        else
            ((failed++))
        fi
    done

    echo ""

    # Generate consolidated report
    generate_consolidated_report

    # Summary
    echo ""
    log "=========================================="
    log "  SBOM Generation Complete"
    log "=========================================="
    log "Successful: $success"
    log "Failed: $failed"
    log "Output directory: $REPORT_DIR"
    log "Consolidated report: $REPORT_DIR/CONSOLIDATED_REPORT.md"
    echo ""

    # Open report
    if command -v xdg-open &> /dev/null; then
        info "Opening consolidated report..."
        xdg-open "$REPORT_DIR/CONSOLIDATED_REPORT.md" 2>/dev/null &
    fi
}

# Run main function
main "$@"
