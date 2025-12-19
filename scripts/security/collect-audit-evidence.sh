#!/bin/bash

###############################################################################
# SOC 2 Audit Evidence Collection Script
#
# Purpose: Automate collection of evidence for SOC 2 Type II audit
# Usage: ./collect-audit-evidence.sh [--period YYYY-MM] [--output-dir PATH]
# Schedule: Run weekly to maintain continuous evidence collection
#
# Evidence Collected:
# - Access logs
# - Audit logs (Vault, application)
# - Security scan results
# - Backup verification
# - Configuration snapshots
# - Change logs (Git)
# - Monitoring screenshots
# - Incident reports
# - System inventory
#
###############################################################################

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DEFAULT_OUTPUT_DIR="$PROJECT_ROOT/compliance/evidence"
CURRENT_MONTH=$(date +%Y-%m)

# Parse arguments
OUTPUT_DIR="${DEFAULT_OUTPUT_DIR}"
PERIOD="${CURRENT_MONTH}"

while [[ $# -gt 0 ]]; do
    case $1 in
        --period)
            PERIOD="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [--period YYYY-MM] [--output-dir PATH]"
            echo ""
            echo "Options:"
            echo "  --period YYYY-MM        Evidence collection period (default: current month)"
            echo "  --output-dir PATH       Output directory (default: compliance/evidence)"
            echo "  --help                  Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Create output directory structure
EVIDENCE_DIR="$OUTPUT_DIR/$PERIOD"
mkdir -p "$EVIDENCE_DIR"/{access-logs,audit-logs,security-scans,backups,configs,changes,monitoring,incidents,inventory}

# Logging
LOG_FILE="$EVIDENCE_DIR/collection.log"
exec 1> >(tee -a "$LOG_FILE")
exec 2>&1

###############################################################################
# Helper Functions
###############################################################################

log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_warning "$1 is not installed, skipping related evidence collection"
        return 1
    fi
    return 0
}

###############################################################################
# Evidence Collection Functions
###############################################################################

collect_access_logs() {
    log_info "Collecting access logs..."

    local output="$EVIDENCE_DIR/access-logs"

    # Nginx access logs
    if [ -f "/var/log/nginx/access.log" ]; then
        cp /var/log/nginx/access.log "$output/nginx-access-$(date +%Y%m%d).log" 2>/dev/null || \
            log_warning "Could not access nginx logs"
    fi

    # Django access logs (if available)
    if [ -d "/var/log/ecommerce" ]; then
        cp /var/log/ecommerce/access.log "$output/django-access-$(date +%Y%m%d).log" 2>/dev/null || true
    fi

    # Docker logs for backend service
    if check_command docker; then
        docker logs backend --since "${PERIOD}-01" --until "$(date +%Y-%m-%d)" \
            > "$output/backend-logs-$PERIOD.log" 2>&1 || log_warning "Could not collect backend logs"
    fi

    log_success "Access logs collected"
}

collect_audit_logs() {
    log_info "Collecting audit logs..."

    local output="$EVIDENCE_DIR/audit-logs"

    # Vault audit logs
    if [ -f "/vault/logs/audit.log" ]; then
        cp /vault/logs/audit.log "$output/vault-audit-$(date +%Y%m%d).log" 2>/dev/null || \
            log_warning "Could not access Vault audit logs"
    fi

    # Django audit logs (user actions, login attempts)
    if [ -d "/var/log/ecommerce" ]; then
        cp /var/log/ecommerce/audit.log "$output/django-audit-$(date +%Y%m%d).log" 2>/dev/null || true
    fi

    # Database audit logs (if enabled)
    if check_command docker; then
        docker exec postgres psql -U postgres -c "SELECT * FROM audit_log WHERE created_at >= '${PERIOD}-01'" \
            > "$output/database-audit-$PERIOD.log" 2>&1 || log_warning "Database audit log not available"
    fi

    # Authentication logs
    grep "authentication" /var/log/ecommerce/access.log > "$output/authentication-$PERIOD.log" 2>/dev/null || true

    log_success "Audit logs collected"
}

collect_security_scans() {
    log_info "Collecting security scan results..."

    local output="$EVIDENCE_DIR/security-scans"

    # GitHub Actions artifacts (security scans)
    if [ -d ".github/workflows" ]; then
        log_info "Security scans from CI/CD artifacts should be downloaded from GitHub Actions"
        echo "Download security scan artifacts from GitHub Actions:" > "$output/scan-sources.txt"
        echo "- Trivy container scans" >> "$output/scan-sources.txt"
        echo "- Snyk dependency scans" >> "$output/scan-sources.txt"
        echo "- Semgrep SAST scans" >> "$output/scan-sources.txt"
        echo "- Gitleaks secret scans" >> "$output/scan-sources.txt"
    fi

    # SBOM files
    if [ -d "sbom" ]; then
        cp -r sbom/* "$output/" 2>/dev/null || log_warning "No SBOM files found"
    fi

    # Run local security audit
    if [ -f "$SCRIPT_DIR/security-audit.sh" ]; then
        log_info "Running local security audit..."
        bash "$SCRIPT_DIR/security-audit.sh" 2>&1 | tee "$output/security-audit-$(date +%Y%m%d).log" || true
    fi

    log_success "Security scan results collected"
}

collect_backup_evidence() {
    log_info "Collecting backup evidence..."

    local output="$EVIDENCE_DIR/backups"

    # Backup logs
    if [ -f "/var/log/ecommerce/backup.log" ]; then
        cp /var/log/ecommerce/backup.log "$output/backup-log-$(date +%Y%m%d).log" 2>/dev/null || \
            log_warning "Backup logs not found"
    fi

    # List recent backups
    if [ -d "/backup" ]; then
        ls -lah /backup > "$output/backup-inventory-$(date +%Y%m%d).txt"
    fi

    # Backup verification test results
    if [ -f "/var/log/ecommerce/backup-test.log" ]; then
        cp /var/log/ecommerce/backup-test.log "$output/backup-test-$(date +%Y%m%d).log" 2>/dev/null || true
    fi

    # PostgreSQL backup verification
    if check_command docker; then
        docker exec postgres pg_dump --version > "$output/pg-backup-version.txt" 2>&1 || true
    fi

    log_success "Backup evidence collected"
}

collect_configuration_snapshots() {
    log_info "Collecting configuration snapshots..."

    local output="$EVIDENCE_DIR/configs"

    # Docker Compose configurations
    if [ -f "deploy/docker/compose/production.yml" ]; then
        cp deploy/docker/compose/production.yml "$output/docker-compose-$(date +%Y%m%d).yml"
    fi

    # Nginx configurations
    if [ -d "deploy/nginx" ]; then
        cp -r deploy/nginx "$output/nginx-config-$(date +%Y%m%d)/" 2>/dev/null || true
    fi

    # Prometheus configurations
    if [ -d "deploy/prometheus" ]; then
        cp -r deploy/prometheus "$output/prometheus-config-$(date +%Y%m%d)/" 2>/dev/null || true
    fi

    # Security policies (OPA)
    if [ -d "config/policies" ]; then
        cp -r config/policies "$output/opa-policies-$(date +%Y%m%d)/" 2>/dev/null || true
    fi

    # Environment template (sanitized, no secrets)
    if [ -f ".env.example" ]; then
        cp .env.example "$output/env-template-$(date +%Y%m%d).txt"
    fi

    log_success "Configuration snapshots collected"
}

collect_change_logs() {
    log_info "Collecting change logs..."

    local output="$EVIDENCE_DIR/changes"

    # Git commit history for the period
    if [ -d ".git" ]; then
        git log --since="${PERIOD}-01" --until="$(date +%Y-%m-%d)" \
            --pretty=format:"%h - %an, %ar : %s" \
            > "$output/git-commits-$PERIOD.log" 2>&1 || log_warning "Could not collect git logs"

        # Detailed git log with diffs
        git log --since="${PERIOD}-01" --until="$(date +%Y-%m-%d)" \
            --pretty=fuller --stat \
            > "$output/git-detailed-$PERIOD.log" 2>&1 || true

        # PR merge history (if using GitHub)
        git log --since="${PERIOD}-01" --until="$(date +%Y-%m-%d)" \
            --grep="Merge pull request" --oneline \
            > "$output/pr-merges-$PERIOD.log" 2>&1 || true
    fi

    # Deployment history from CI/CD
    log_info "Note: Deployment history should be exported from GitHub Actions"
    echo "Export deployment history from GitHub Actions for period: $PERIOD" > "$output/deployment-history.txt"

    log_success "Change logs collected"
}

collect_monitoring_data() {
    log_info "Collecting monitoring data and screenshots..."

    local output="$EVIDENCE_DIR/monitoring"

    # Prometheus metrics snapshot
    if check_command curl; then
        # Uptime metrics
        curl -s "http://localhost:9090/api/v1/query?query=up" \
            > "$output/uptime-metrics-$(date +%Y%m%d).json" 2>&1 || log_warning "Prometheus not accessible"

        # Error rate metrics
        curl -s "http://localhost:9090/api/v1/query?query=rate(http_requests_total{status=~\"5..\"}[1h])" \
            > "$output/error-rate-$(date +%Y%m%d).json" 2>&1 || true
    fi

    # Grafana dashboard export
    log_info "Note: Export Grafana dashboards manually"
    echo "Manually export the following Grafana dashboards as screenshots:" > "$output/grafana-export-instructions.txt"
    echo "1. System Overview Dashboard" >> "$output/grafana-export-instructions.txt"
    echo "2. Application Performance Dashboard" >> "$output/grafana-export-instructions.txt"
    echo "3. Security Monitoring Dashboard" >> "$output/grafana-export-instructions.txt"
    echo "4. Database Performance Dashboard" >> "$output/grafana-export-instructions.txt"

    # Alert history
    if [ -d "/var/log/ecommerce/alerts" ]; then
        cp -r /var/log/ecommerce/alerts/* "$output/" 2>/dev/null || true
    fi

    log_success "Monitoring data collected"
}

collect_incident_reports() {
    log_info "Collecting incident reports..."

    local output="$EVIDENCE_DIR/incidents"

    # Incident reports from docs
    if [ -d "docs/incidents" ]; then
        # Copy incident reports from the period
        find docs/incidents -name "*$PERIOD*.md" -exec cp {} "$output/" \; 2>/dev/null || true

        # List all incidents
        ls -lah docs/incidents > "$output/incident-inventory.txt" 2>/dev/null || true
    else
        log_warning "No incidents directory found"
        echo "No incidents reported for $PERIOD" > "$output/no-incidents.txt"
    fi

    # PagerDuty/on-call incident exports (if integrated)
    log_info "Note: Export PagerDuty incidents if applicable"

    log_success "Incident reports collected"
}

collect_system_inventory() {
    log_info "Collecting system inventory..."

    local output="$EVIDENCE_DIR/inventory"

    # Docker containers
    if check_command docker; then
        docker ps -a --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}" \
            > "$output/docker-containers-$(date +%Y%m%d).txt"

        # Docker images with tags
        docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}" \
            > "$output/docker-images-$(date +%Y%m%d).txt"

        # Docker networks
        docker network ls > "$output/docker-networks-$(date +%Y%m%d).txt"
    fi

    # SBOM (Software Bill of Materials)
    log_info "Generate SBOM for current deployed images"
    echo "SBOM should be generated during CI/CD and stored in artifacts" > "$output/sbom-instructions.txt"

    # System resource usage
    if check_command df; then
        df -h > "$output/disk-usage-$(date +%Y%m%d).txt"
    fi

    if check_command free; then
        free -h > "$output/memory-usage-$(date +%Y%m%d).txt"
    fi

    # Package versions
    echo "Python: $(python3 --version 2>&1)" > "$output/software-versions.txt"
    echo "Docker: $(docker --version 2>&1)" >> "$output/software-versions.txt"
    echo "Docker Compose: $(docker-compose --version 2>&1)" >> "$output/software-versions.txt"

    log_success "System inventory collected"
}

collect_compliance_documentation() {
    log_info "Collecting compliance documentation..."

    local output="$EVIDENCE_DIR/documentation"
    mkdir -p "$output"

    # Copy compliance documentation
    if [ -d "docs/security" ]; then
        cp -r docs/security "$output/security-docs-$(date +%Y%m%d)/"
    fi

    if [ -d "docs/policies" ]; then
        cp -r docs/policies "$output/policies-$(date +%Y%m%d)/"
    fi

    # Architecture diagrams
    if [ -d "docs/architecture" ]; then
        cp -r docs/architecture "$output/architecture-$(date +%Y%m%d)/"
    fi

    log_success "Compliance documentation collected"
}

generate_evidence_summary() {
    log_info "Generating evidence summary..."

    local summary_file="$EVIDENCE_DIR/EVIDENCE_SUMMARY.md"

    cat > "$summary_file" <<EOF
# SOC 2 Audit Evidence Summary

**Collection Date:** $(date '+%Y-%m-%d %H:%M:%S')
**Collection Period:** $PERIOD
**Evidence Location:** $EVIDENCE_DIR

---

## Evidence Categories

### 1. Access Logs
Location: \`access-logs/\`

Files collected:
$(ls -1 "$EVIDENCE_DIR/access-logs" 2>/dev/null | sed 's/^/- /' || echo "- No files")

### 2. Audit Logs
Location: \`audit-logs/\`

Files collected:
$(ls -1 "$EVIDENCE_DIR/audit-logs" 2>/dev/null | sed 's/^/- /' || echo "- No files")

### 3. Security Scans
Location: \`security-scans/\`

Files collected:
$(ls -1 "$EVIDENCE_DIR/security-scans" 2>/dev/null | sed 's/^/- /' || echo "- No files")

### 4. Backup Evidence
Location: \`backups/\`

Files collected:
$(ls -1 "$EVIDENCE_DIR/backups" 2>/dev/null | sed 's/^/- /' || echo "- No files")

### 5. Configuration Snapshots
Location: \`configs/\`

Files collected:
$(ls -1 "$EVIDENCE_DIR/configs" 2>/dev/null | sed 's/^/- /' || echo "- No files")

### 6. Change Logs
Location: \`changes/\`

Files collected:
$(ls -1 "$EVIDENCE_DIR/changes" 2>/dev/null | sed 's/^/- /' || echo "- No files")

### 7. Monitoring Data
Location: \`monitoring/\`

Files collected:
$(ls -1 "$EVIDENCE_DIR/monitoring" 2>/dev/null | sed 's/^/- /' || echo "- No files")

### 8. Incident Reports
Location: \`incidents/\`

Files collected:
$(ls -1 "$EVIDENCE_DIR/incidents" 2>/dev/null | sed 's/^/- /' || echo "- No files")

### 9. System Inventory
Location: \`inventory/\`

Files collected:
$(ls -1 "$EVIDENCE_DIR/inventory" 2>/dev/null | sed 's/^/- /' || echo "- No files")

### 10. Compliance Documentation
Location: \`documentation/\`

Files collected:
$(ls -1 "$EVIDENCE_DIR/documentation" 2>/dev/null | sed 's/^/- /' || echo "- No files")

---

## Manual Collection Required

The following evidence requires manual collection:

1. **GitHub Actions Artifacts**
   - Security scan results (Trivy, Snyk, Semgrep)
   - SBOM generation results
   - CI/CD pipeline logs

2. **Grafana Dashboards**
   - Export dashboard screenshots for the period
   - System Overview, Performance, Security dashboards

3. **PagerDuty/Incident Management**
   - Export incident history (if using PagerDuty)

4. **Vendor Compliance Certificates**
   - Stripe SOC 2 report
   - Cloud provider compliance certificates
   - Third-party security attestations

5. **Training Records**
   - Security awareness training completion
   - Employee security briefing records

---

## Evidence Archive

To create a compressed archive for audit submission:

\`\`\`bash
cd $OUTPUT_DIR
tar -czf soc2-evidence-$PERIOD.tar.gz $PERIOD/
\`\`\`

Archive can then be securely transferred to auditors.

---

## Next Steps

1. Review collected evidence for completeness
2. Collect manual evidence items listed above
3. Verify file integrity (checksums)
4. Encrypt archive before transfer
5. Submit to SOC 2 auditor

---

**Evidence Collection Complete**
EOF

    log_success "Evidence summary generated: $summary_file"
}

create_evidence_archive() {
    log_info "Creating evidence archive..."

    local archive_name="soc2-evidence-$PERIOD.tar.gz"
    local archive_path="$OUTPUT_DIR/$archive_name"

    cd "$OUTPUT_DIR"
    tar -czf "$archive_name" "$PERIOD/" 2>&1 || log_error "Failed to create archive"

    # Generate checksum
    if check_command sha256sum; then
        sha256sum "$archive_name" > "$archive_name.sha256"
        log_success "Archive created: $archive_path"
        log_info "SHA256: $(cat "$archive_name.sha256")"
    fi
}

###############################################################################
# Main Execution
###############################################################################

main() {
    log_info "=========================================="
    log_info "SOC 2 Audit Evidence Collection"
    log_info "=========================================="
    log_info "Period: $PERIOD"
    log_info "Output Directory: $EVIDENCE_DIR"
    log_info "=========================================="

    # Collect all evidence
    collect_access_logs
    collect_audit_logs
    collect_security_scans
    collect_backup_evidence
    collect_configuration_snapshots
    collect_change_logs
    collect_monitoring_data
    collect_incident_reports
    collect_system_inventory
    collect_compliance_documentation

    # Generate summary
    generate_evidence_summary

    # Create archive
    create_evidence_archive

    log_info "=========================================="
    log_success "Evidence collection complete!"
    log_info "Evidence location: $EVIDENCE_DIR"
    log_info "Summary: $EVIDENCE_DIR/EVIDENCE_SUMMARY.md"
    log_info "Log file: $LOG_FILE"
    log_info "=========================================="

    # Display summary
    cat "$EVIDENCE_DIR/EVIDENCE_SUMMARY.md"
}

# Run main function
main "$@"
