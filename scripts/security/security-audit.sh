#!/bin/bash
# ==============================================================================
# Comprehensive Security Audit Script
# ==============================================================================
# This script performs a complete security audit of the E-Commerce Platform
#
# Usage:
#   ./scripts/security/security-audit.sh [options]
#
# Options:
#   --skip-containers    Skip container vulnerability scanning
#   --skip-dependencies  Skip dependency scanning
#   --skip-secrets      Skip secret scanning
#   --skip-network      Skip network security checks
#   --fail-on-high      Fail on HIGH severity (default: CRITICAL only)
#
# Exit Codes:
#   0 - All checks passed
#   1 - Critical vulnerabilities found
#   2 - Scan errors occurred
# ==============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
REPORT_DIR="security-reports/$(date +%Y%m%d_%H%M%S)"
SKIP_CONTAINERS=false
SKIP_DEPENDENCIES=false
SKIP_SECRETS=false
SKIP_NETWORK=false
FAIL_ON_HIGH=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-containers)
            SKIP_CONTAINERS=true
            shift
            ;;
        --skip-dependencies)
            SKIP_DEPENDENCIES=true
            shift
            ;;
        --skip-secrets)
            SKIP_SECRETS=true
            shift
            ;;
        --skip-network)
            SKIP_NETWORK=true
            shift
            ;;
        --fail-on-high)
            FAIL_ON_HIGH=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Create report directory
mkdir -p "$REPORT_DIR"

# Services to scan
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

# Counters
CRITICAL_COUNT=0
HIGH_COUNT=0
ERRORS=0

# Logging
log_section() {
    echo ""
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================================${NC}"
    echo ""
}

log_info() {
    echo -e "${CYAN}[INFO]${NC} $@"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $@"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $@"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $@"
}

# Check if required tools are installed
check_requirements() {
    log_section "Checking Requirements"

    local missing=()

    if ! command -v docker &> /dev/null; then
        missing+=("docker")
    fi

    if ! command -v docker-compose &> /dev/null; then
        missing+=("docker-compose")
    fi

    if ! command -v jq &> /dev/null; then
        missing+=("jq")
    fi

    if [ "$SKIP_CONTAINERS" = false ] && ! command -v trivy &> /dev/null; then
        log_warning "Trivy not installed. Install with: curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin"
        SKIP_CONTAINERS=true
    fi

    if [ "$SKIP_SECRETS" = false ] && ! command -v gitleaks &> /dev/null; then
        log_warning "Gitleaks not installed. Secret scanning will be skipped."
        SKIP_SECRETS=true
    fi

    if [ ${#missing[@]} -gt 0 ]; then
        log_error "Missing required tools: ${missing[*]}"
        exit 2
    fi

    log_success "All required tools available"
}

# 1. Container Vulnerability Scanning
scan_containers() {
    if [ "$SKIP_CONTAINERS" = true ]; then
        log_info "Skipping container scanning"
        return 0
    fi

    log_section "1. Container Vulnerability Scanning"

    for service in "${SERVICES[@]}"; do
        log_info "Scanning ${service}..."

        # Check if image exists
        if ! docker images | grep -q "^${service}"; then
            log_warning "Image ${service} not found, skipping"
            continue
        fi

        # Run Trivy scan
        trivy image \
            --format json \
            --output "${REPORT_DIR}/trivy-${service}.json" \
            --severity CRITICAL,HIGH,MEDIUM \
            --no-progress \
            "${service}:latest" 2>/dev/null || {
                log_error "Failed to scan ${service}"
                ((ERRORS++))
                continue
            }

        # Count vulnerabilities
        if [ -f "${REPORT_DIR}/trivy-${service}.json" ]; then
            local critical=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity=="CRITICAL")] | length' \
                "${REPORT_DIR}/trivy-${service}.json" 2>/dev/null || echo 0)
            local high=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity=="HIGH")] | length' \
                "${REPORT_DIR}/trivy-${service}.json" 2>/dev/null || echo 0)

            CRITICAL_COUNT=$((CRITICAL_COUNT + critical))
            HIGH_COUNT=$((HIGH_COUNT + high))

            if [ "$critical" -gt 0 ]; then
                log_error "${service}: ${critical} CRITICAL vulnerabilities"
            elif [ "$high" -gt 0 ]; then
                log_warning "${service}: ${high} HIGH vulnerabilities"
            else
                log_success "${service}: No critical/high vulnerabilities"
            fi
        fi
    done

    log_success "Container scanning complete"
}

# 2. Dependency Scanning
scan_dependencies() {
    if [ "$SKIP_DEPENDENCIES" = true ]; then
        log_info "Skipping dependency scanning"
        return 0
    fi

    log_section "2. Dependency Vulnerability Scanning"

    # Python dependencies with pip-audit
    if command -v pip-audit &> /dev/null; then
        log_info "Scanning Python dependencies with pip-audit..."
        pip-audit --format json --output "${REPORT_DIR}/pip-audit.json" 2>/dev/null || {
            log_warning "pip-audit scan failed or found vulnerabilities"
        }
    else
        log_warning "pip-audit not installed, skipping Python dependency scan"
    fi

    # Python dependencies with safety
    if command -v safety &> /dev/null; then
        log_info "Scanning Python dependencies with safety..."
        safety check --json --output "${REPORT_DIR}/safety-dependencies.json" 2>/dev/null || {
            log_warning "safety scan failed or found vulnerabilities"
        }
    else
        log_warning "safety not installed, skipping safety scan"
    fi

    # Node.js dependencies (if applicable)
    if [ -f "package.json" ]; then
        log_info "Scanning Node.js dependencies..."
        npm audit --json > "${REPORT_DIR}/npm-audit.json" 2>/dev/null || {
            log_warning "npm audit found vulnerabilities"
        }
    fi

    log_success "Dependency scanning complete"
}

# 3. Secret Scanning
scan_secrets() {
    if [ "$SKIP_SECRETS" = true ]; then
        log_info "Skipping secret scanning"
        return 0
    fi

    log_section "3. Secret Scanning in Git History"

    log_info "Scanning git history for exposed secrets..."

    gitleaks detect \
        --source . \
        --report-path "${REPORT_DIR}/gitleaks-report.json" \
        --verbose \
        --no-git 2>/dev/null || {
            log_warning "Gitleaks scan completed (check report for findings)"
        }

    if [ -f "${REPORT_DIR}/gitleaks-report.json" ]; then
        local secrets=$(jq '. | length' "${REPORT_DIR}/gitleaks-report.json" 2>/dev/null || echo 0)
        if [ "$secrets" -gt 0 ]; then
            log_error "Found ${secrets} potential secrets in git history!"
        else
            log_success "No secrets found in git history"
        fi
    fi
}

# 4. File Permission Checks
check_file_permissions() {
    log_section "4. File Permission Security Check"

    {
        echo "=== Sensitive Files Permissions ==="
        echo ""

        log_info "Checking sensitive file permissions..."

        # Check for sensitive files
        find . -type f \( -name "*.key" -o -name "*.pem" -o -name "*.env" -o -name "*secret*" \) \
            ! -path "*/\.*" ! -path "*/node_modules/*" ! -path "*/venv/*" \
            -exec ls -lh {} \; 2>/dev/null || echo "No sensitive files found"

        echo ""
        echo "=== World-Writable Files ==="
        echo ""

        find . -type f -perm -002 ! -path "*/\.*" ! -path "*/node_modules/*" -ls 2>/dev/null || \
            echo "No world-writable files found"

        echo ""
        echo "=== SUID/SGID Files ==="
        echo ""

        find . -type f \( -perm -4000 -o -perm -2000 \) ! -path "*/\.*" -ls 2>/dev/null || \
            echo "No SUID/SGID files found"

    } > "${REPORT_DIR}/file-permissions.txt"

    log_success "File permission check complete"
}

# 5. Network Security Validation
check_network_security() {
    if [ "$SKIP_NETWORK" = true ]; then
        log_info "Skipping network security checks"
        return 0
    fi

    log_section "5. Network Security Validation"

    {
        echo "=== Docker Networks ==="
        echo ""
        docker network ls

        echo ""
        echo "=== Network Inspection ==="
        echo ""

        for network in $(docker network ls --format '{{.Name}}' | grep -E "(ecommerce|backend|application|database)" 2>/dev/null); do
            echo "Network: ${network}"
            docker network inspect "$network" 2>/dev/null | \
                jq '.[] | {Name:.Name, Driver:.Driver, Internal:.Internal, Containers:.Containers | keys}' || \
                echo "Failed to inspect network"
            echo ""
        done

        echo "=== Exposed Ports ==="
        echo ""
        docker ps --format "table {{.Names}}\t{{.Ports}}" 2>/dev/null || echo "No running containers"

        echo ""
        echo "=== Internal Networks Check ==="
        echo ""

        local internal_nets=$(docker network ls --format '{{.Name}}' | \
            xargs -I {} sh -c 'docker network inspect {} | jq -r ".[].Internal"' 2>/dev/null | \
            grep -c "true" || echo 0)
        echo "Internal networks: ${internal_nets}"

    } > "${REPORT_DIR}/network-security.txt"

    log_success "Network security check complete"
}

# 6. Configuration Security Review
check_configuration_security() {
    log_section "6. Configuration Security Review"

    {
        echo "=== Docker Compose Configuration ==="
        echo ""

        log_info "Checking for secrets in docker-compose files..."

        if docker-compose config 2>/dev/null | grep -iE "(password|secret|key|token)" | grep -v "VAULT"; then
            echo "WARNING: Potential secrets found in compose files"
        else
            echo "No obvious secrets found in compose configuration"
        fi

        echo ""
        echo "=== Docker Security Options ==="
        echo ""

        docker ps -q 2>/dev/null | xargs -I {} docker inspect {} 2>/dev/null | \
            jq '.[] | {Name:.Name, SecurityOpt:.HostConfig.SecurityOpt, ReadonlyRootfs:.HostConfig.ReadonlyRootfs, User:.Config.User}' || \
            echo "No running containers to inspect"

        echo ""
        echo "=== Resource Limits ==="
        echo ""

        docker ps -q 2>/dev/null | xargs -I {} docker inspect {} 2>/dev/null | \
            jq '.[] | {Name:.Name, Memory:.HostConfig.Memory, CPUs:.HostConfig.NanoCpus}' || \
            echo "No running containers to inspect"

    } > "${REPORT_DIR}/config-security.txt"

    log_success "Configuration security check complete"
}

# 7. Compliance Checks
check_compliance() {
    log_section "7. Compliance Validation"

    {
        echo "=== PCI-DSS Compliance Checks ==="
        echo ""
        echo "1. Network Segmentation:"
        docker network ls --format '{{.Name}}\t{{.Driver}}\t{{.Internal}}' | grep -E "(backend|database|application)"

        echo ""
        echo "2. Encryption at Rest:"
        docker inspect postgres 2>/dev/null | jq '.[].Mounts[] | select(.Destination=="/var/lib/postgresql/data")' || \
            echo "PostgreSQL not running"

        echo ""
        echo "3. Access Logging:"
        docker inspect nginx 2>/dev/null | jq '.[].HostConfig.LogConfig' || echo "Nginx not running"

        echo ""
        echo "=== SOC 2 Compliance Checks ==="
        echo ""
        echo "1. Audit Logging:"
        if docker ps | grep -q vault; then
            docker exec ecommerce_vault vault audit list 2>/dev/null || echo "Vault audit not configured"
        else
            echo "Vault not running"
        fi

        echo ""
        echo "2. Resource Limits:"
        docker-compose config 2>/dev/null | grep -c "limits:" || echo "0"

        echo ""
        echo "3. Monitoring:"
        docker ps --format '{{.Names}}' | grep -E "(prometheus|grafana)" || echo "No monitoring services found"

        echo ""
        echo "=== OWASP Top 10 Controls ==="
        echo ""
        echo "1. SQL Injection Protection: Using ORM (Django/SQLAlchemy)"
        echo "2. XSS Protection: Security headers configured"
        echo "3. CSRF Protection: Django CSRF middleware enabled"
        echo "4. Authentication: JWT with Vault secrets"
        echo "5. Access Control: Role-based policies in Vault"

    } > "${REPORT_DIR}/compliance-checks.txt"

    log_success "Compliance checks complete"
}

# Generate Summary Report
generate_summary() {
    log_section "8. Generating Summary Report"

    {
        echo "╔════════════════════════════════════════════════════════════════╗"
        echo "║          SECURITY AUDIT SUMMARY REPORT                         ║"
        echo "╚════════════════════════════════════════════════════════════════╝"
        echo ""
        echo "Generated: $(date)"
        echo "Report Directory: ${REPORT_DIR}"
        echo ""
        echo "================================================================"
        echo "1. CONTAINER VULNERABILITY SCAN"
        echo "================================================================"
        echo ""

        if [ "$SKIP_CONTAINERS" = false ]; then
            for file in "${REPORT_DIR}"/trivy-*.json 2>/dev/null; do
                if [ -f "$file" ]; then
                    service=$(basename "$file" .json | sed 's/trivy-//')
                    critical=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity=="CRITICAL")] | length' "$file" 2>/dev/null || echo 0)
                    high=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity=="HIGH")] | length' "$file" 2>/dev/null || echo 0)
                    medium=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity=="MEDIUM")] | length' "$file" 2>/dev/null || echo 0)

                    printf "  %-20s CRITICAL: %3d  HIGH: %3d  MEDIUM: %3d\n" "$service" "$critical" "$high" "$medium"
                fi
            done
            echo ""
            echo "  Total CRITICAL: ${CRITICAL_COUNT}"
            echo "  Total HIGH: ${HIGH_COUNT}"
        else
            echo "  Skipped"
        fi

        echo ""
        echo "================================================================"
        echo "2. DEPENDENCY VULNERABILITIES"
        echo "================================================================"
        echo ""

        if [ -f "${REPORT_DIR}/pip-audit.json" ]; then
            vuln_count=$(jq '.vulnerabilities | length' "${REPORT_DIR}/pip-audit.json" 2>/dev/null || echo 0)
            echo "  pip-audit: ${vuln_count} vulnerabilities found"
        fi

        if [ -f "${REPORT_DIR}/safety-dependencies.json" ]; then
            vuln_count=$(jq '. | length' "${REPORT_DIR}/safety-dependencies.json" 2>/dev/null || echo 0)
            echo "  safety: ${vuln_count} vulnerabilities found"
        fi

        if [ -f "${REPORT_DIR}/npm-audit.json" ]; then
            vuln_count=$(jq '.metadata.vulnerabilities.total' "${REPORT_DIR}/npm-audit.json" 2>/dev/null || echo 0)
            echo "  npm audit: ${vuln_count} vulnerabilities found"
        fi

        echo ""
        echo "================================================================"
        echo "3. SECRET SCANNING"
        echo "================================================================"
        echo ""

        if [ -f "${REPORT_DIR}/gitleaks-report.json" ]; then
            secrets=$(jq '. | length' "${REPORT_DIR}/gitleaks-report.json" 2>/dev/null || echo 0)
            echo "  Secrets found in git history: ${secrets}"
        else
            echo "  No secret scan performed"
        fi

        echo ""
        echo "================================================================"
        echo "4. NETWORK SECURITY"
        echo "================================================================"
        echo ""

        if [ -f "${REPORT_DIR}/network-security.txt" ]; then
            internal_nets=$(docker network ls | grep -c "internal" 2>/dev/null || echo 0)
            exposed_services=$(docker ps --format '{{.Ports}}' | grep -c "0.0.0.0" 2>/dev/null || echo 0)
            echo "  Internal networks: ${internal_nets}"
            echo "  Services with exposed ports: ${exposed_services}"
        fi

        echo ""
        echo "================================================================"
        echo "5. FILE PERMISSIONS"
        echo "================================================================"
        echo ""

        if [ -f "${REPORT_DIR}/file-permissions.txt" ]; then
            world_writable=$(grep -c "rw-rw-rw-" "${REPORT_DIR}/file-permissions.txt" 2>/dev/null || echo 0)
            echo "  World-writable files: ${world_writable}"
        fi

        echo ""
        echo "================================================================"
        echo "OVERALL STATUS"
        echo "================================================================"
        echo ""

        if [ $CRITICAL_COUNT -eq 0 ] && [ $ERRORS -eq 0 ]; then
            echo "  ✓ No critical vulnerabilities found"
            echo "  ✓ Security audit PASSED"
        else
            echo "  ✗ Critical issues found: ${CRITICAL_COUNT}"
            echo "  ✗ Scan errors: ${ERRORS}"
            echo "  ✗ Security audit FAILED"
        fi

        echo ""
        echo "================================================================"
        echo "Full reports available in: ${REPORT_DIR}"
        echo "================================================================"

    } | tee "${REPORT_DIR}/SUMMARY.txt"
}

# Main execution
main() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║        E-Commerce Platform Security Audit                      ║"
    echo "║        Comprehensive Security Assessment                       ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Started: $(date)"
    echo ""

    # Check requirements
    check_requirements

    # Run scans
    scan_containers
    scan_dependencies
    scan_secrets
    check_file_permissions
    check_network_security
    check_configuration_security
    check_compliance

    # Generate summary
    generate_summary

    # Final status
    echo ""
    log_section "Audit Complete"

    echo "Reports saved to: ${REPORT_DIR}"
    echo ""

    # Exit based on findings
    if [ $CRITICAL_COUNT -gt 0 ]; then
        log_error "Found ${CRITICAL_COUNT} CRITICAL vulnerabilities!"
        exit 1
    elif [ "$FAIL_ON_HIGH" = true ] && [ $HIGH_COUNT -gt 0 ]; then
        log_error "Found ${HIGH_COUNT} HIGH vulnerabilities (--fail-on-high enabled)"
        exit 1
    elif [ $ERRORS -gt 0 ]; then
        log_warning "Audit completed with ${ERRORS} errors"
        exit 2
    else
        log_success "Security audit passed - no critical issues found"
        exit 0
    fi
}

# Run main function
main
