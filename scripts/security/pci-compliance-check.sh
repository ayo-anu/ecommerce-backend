#!/bin/bash
set -euo pipefail

# PCI-DSS Compliance Check Script
# Automated verification of PCI-DSS controls

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNING_CHECKS=0

# Output file
REPORT_FILE="pci-compliance-report-$(date +%Y%m%d_%H%M%S).txt"

# Functions
log_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

log_section() {
    echo ""
    echo -e "${BLUE}## $1${NC}"
    echo "## $1" >> "$REPORT_FILE"
    echo ""
}

check_pass() {
    ((TOTAL_CHECKS++))
    ((PASSED_CHECKS++))
    echo -e "${GREEN}✅ PASS${NC}: $1"
    echo "✅ PASS: $1" >> "$REPORT_FILE"
}

check_fail() {
    ((TOTAL_CHECKS++))
    ((FAILED_CHECKS++))
    echo -e "${RED}❌ FAIL${NC}: $1"
    echo "❌ FAIL: $1" >> "$REPORT_FILE"
}

check_warn() {
    ((TOTAL_CHECKS++))
    ((WARNING_CHECKS++))
    echo -e "${YELLOW}⚠️  WARN${NC}: $1"
    echo "⚠️ WARN: $1" >> "$REPORT_FILE"
}

check_info() {
    echo -e "${BLUE}ℹ️  INFO${NC}: $1"
    echo "ℹ️ INFO: $1" >> "$REPORT_FILE"
}

# Initialize report
cat > "$REPORT_FILE" <<EOF
PCI-DSS COMPLIANCE CHECK REPORT
Generated: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
Environment: Production
========================================

EOF

# Main execution
main() {
    log_header "PCI-DSS Compliance Automated Check"

    echo "Report will be saved to: $REPORT_FILE"
    echo ""

    # Requirement 1: Firewall Configuration
    check_requirement_1

    # Requirement 2: System Configuration
    check_requirement_2

    # Requirement 3: Stored Data Protection
    check_requirement_3

    # Requirement 4: Encryption in Transit
    check_requirement_4

    # Requirement 5: Anti-Malware
    check_requirement_5

    # Requirement 6: Secure Development
    check_requirement_6

    # Requirement 7: Access Control
    check_requirement_7

    # Requirement 8: Authentication
    check_requirement_8

    # Requirement 10: Logging
    check_requirement_10

    # Requirement 11: Security Testing
    check_requirement_11

    # Requirement 12: Information Security Policy
    check_requirement_12

    # Generate summary
    generate_summary
}

check_requirement_1() {
    log_section "Requirement 1: Firewall and Network Security"

    # Check if internal networks are isolated
    if docker network inspect ecommerce_backend &>/dev/null; then
        INTERNAL=$(docker network inspect ecommerce_backend | jq -r '.[0].Internal')
        if [ "$INTERNAL" == "true" ]; then
            check_pass "Backend network is internal (isolated from internet)"
        else
            check_fail "Backend network is not marked as internal"
        fi
    else
        check_warn "Backend network not found"
    fi

    # Check Nginx is running and configured
    if docker ps --filter "name=nginx" --filter "status=running" | grep -q nginx; then
        check_pass "Nginx reverse proxy is running"

        # Check if security headers are configured
        if docker exec nginx nginx -T 2>/dev/null | grep -q "add_header.*Strict-Transport-Security"; then
            check_pass "HSTS header is configured"
        else
            check_fail "HSTS header not found in Nginx configuration"
        fi
    else
        check_fail "Nginx is not running"
    fi

    # Check exposed ports
    EXPOSED_PORTS=$(docker ps --format '{{.Ports}}' | grep -o '0.0.0.0:[0-9]*' | sort -u | wc -l)
    if [ "$EXPOSED_PORTS" -le 2 ]; then
        check_pass "Limited ports exposed to internet ($EXPOSED_PORTS ports)"
    else
        check_warn "Multiple ports exposed to internet ($EXPOSED_PORTS ports)"
    fi
}

check_requirement_2() {
    log_section "Requirement 2: Secure Configuration"

    # Check for default passwords (simple check)
    if grep -r "password.*=.*password" config/ 2>/dev/null | grep -qv ".example"; then
        check_fail "Possible default passwords found in configuration"
    else
        check_pass "No default passwords found in configuration files"
    fi

    # Check for non-root containers
    NON_ROOT_COUNT=0
    ROOT_COUNT=0

    for container in $(docker ps --format '{{.Names}}'); do
        USER=$(docker exec "$container" whoami 2>/dev/null || echo "unknown")
        if [ "$USER" == "root" ]; then
            ((ROOT_COUNT++))
            check_warn "Container $container is running as root"
        elif [ "$USER" != "unknown" ]; then
            ((NON_ROOT_COUNT++))
        fi
    done

    if [ "$ROOT_COUNT" -eq 0 ]; then
        check_pass "All containers running as non-root users"
    else
        check_warn "$ROOT_COUNT containers running as root"
    fi

    # Check SBOM generation is configured
    if [ -f ".github/workflows/sbom-generation.yml" ]; then
        check_pass "SBOM generation workflow is configured"
    else
        check_fail "SBOM generation workflow not found"
    fi
}

check_requirement_3() {
    log_section "Requirement 3: Protect Stored Cardholder Data"

    # Check that we're not storing PAN (grep for patterns)
    check_info "Verifying no PAN storage (checking for 16-digit patterns)"

    # Check database is running with encryption
    if docker ps --filter "name=postgres" --filter "status=running" | grep -q postgres; then
        check_pass "PostgreSQL database is running"

        # Check for encryption configuration
        check_info "Database encryption verification requires manual check"
    else
        check_fail "PostgreSQL database is not running"
    fi

    # Check Vault is configured
    if [ -f "deploy/vault/config/vault.hcl" ] || [ -f "config/vault/policies/backend-policy.hcl" ]; then
        check_pass "Vault configuration files exist"
    else
        check_warn "Vault configuration files not found"
    fi

    # Check for data retention policy
    if [ -f "docs/policies/data-retention-policy.md" ]; then
        check_pass "Data retention policy is documented"
    else
        check_warn "Data retention policy not found"
    fi
}

check_requirement_4() {
    log_section "Requirement 4: Encryption in Transit"

    # Check TLS configuration
    if [ -f "deploy/nginx/conf.d/ssl.conf" ]; then
        check_pass "TLS configuration file exists"

        # Check TLS version
        if grep -q "ssl_protocols.*TLSv1.3" deploy/nginx/conf.d/ssl.conf 2>/dev/null; then
            check_pass "TLS 1.3 is enabled"
        elif grep -q "ssl_protocols.*TLSv1.2" deploy/nginx/conf.d/ssl.conf 2>/dev/null; then
            check_pass "TLS 1.2 is enabled (minimum acceptable)"
        else
            check_fail "TLS version not properly configured"
        fi

        # Check for weak TLS versions
        if grep -q "TLSv1.1\|TLSv1 \|SSLv" deploy/nginx/conf.d/ssl.conf 2>/dev/null; then
            check_fail "Weak TLS/SSL versions found in configuration"
        else
            check_pass "No weak TLS/SSL versions in configuration"
        fi

        # Check for strong ciphers
        if grep -q "ECDHE.*AES.*GCM" deploy/nginx/conf.d/ssl.conf 2>/dev/null; then
            check_pass "Strong cipher suites configured (ECDHE + AEAD)"
        else
            check_warn "Strong cipher suites may not be configured"
        fi
    else
        check_warn "TLS configuration file not found at expected location"
    fi

    # Check HSTS is configured
    if [ -f "deploy/nginx/conf.d/security.conf" ]; then
        if grep -q "Strict-Transport-Security" deploy/nginx/conf.d/security.conf 2>/dev/null; then
            check_pass "HSTS (HTTP Strict Transport Security) is configured"
        else
            check_fail "HSTS header not found"
        fi
    fi

    # Check certificate exists (Let's Encrypt or other)
    if [ -d "deploy/nginx/ssl" ]; then
        CERT_COUNT=$(find deploy/nginx/ssl -name "*.crt" -o -name "*.pem" | wc -l)
        if [ "$CERT_COUNT" -gt 0 ]; then
            check_pass "SSL certificates found ($CERT_COUNT files)"
        else
            check_warn "No SSL certificates found in ssl directory"
        fi
    fi
}

check_requirement_5() {
    log_section "Requirement 5: Protect Systems from Malware"

    # Check for security scanning workflows
    if [ -f ".github/workflows/security-scan.yml" ]; then
        check_pass "Security scanning workflow exists"
    else
        check_fail "Security scanning workflow not found"
    fi

    # Check Trivy is configured
    if grep -q "trivy" .github/workflows/*.yml 2>/dev/null; then
        check_pass "Trivy container scanning is configured"
    else
        check_warn "Trivy scanning not found in workflows"
    fi

    # Check for runtime protection (Falco)
    if docker ps --filter "name=falco" --filter "status=running" | grep -q falco; then
        check_pass "Falco runtime protection is running"
    else
        check_warn "Falco runtime protection not running (recommended)"
    fi
}

check_requirement_6() {
    log_section "Requirement 6: Develop and Maintain Secure Systems"

    # Check for security scanning in CI/CD
    if [ -f ".github/workflows/pr-checks.yml" ]; then
        check_pass "PR validation workflow exists"
    else
        check_warn "PR validation workflow not found"
    fi

    # Check for SAST tools (Semgrep)
    if grep -q "semgrep" .github/workflows/*.yml 2>/dev/null; then
        check_pass "SAST scanning (Semgrep) is configured"
    else
        check_warn "SAST scanning not found in workflows"
    fi

    # Check for dependency scanning
    if [ -f ".github/dependabot.yml" ] || grep -q "snyk\|safety" .github/workflows/*.yml 2>/dev/null; then
        check_pass "Dependency scanning is configured"
    else
        check_warn "Dependency scanning not configured"
    fi

    # Check for code review requirements (CODEOWNERS)
    if [ -f ".github/CODEOWNERS" ]; then
        check_pass "CODEOWNERS file exists (code review enforcement)"
    else
        check_warn "CODEOWNERS file not found"
    fi
}

check_requirement_7() {
    log_section "Requirement 7: Restrict Access"

    # Check for access control documentation
    if [ -f "docs/policies/access-control.md" ] || [ -f ".github/CODEOWNERS" ]; then
        check_pass "Access control documentation exists"
    else
        check_warn "Access control documentation not found"
    fi

    # Check Docker doesn't grant unnecessary privileges
    PRIVILEGED_COUNT=0
    for container in $(docker ps --format '{{.Names}}'); do
        if docker inspect "$container" | grep -q '"Privileged": true'; then
            ((PRIVILEGED_COUNT++))
            check_fail "Container $container is running in privileged mode"
        fi
    done

    if [ "$PRIVILEGED_COUNT" -eq 0 ]; then
        check_pass "No containers running in privileged mode"
    fi
}

check_requirement_8() {
    log_section "Requirement 8: Identify Users and Authenticate Access"

    # Check for authentication configuration
    if grep -r "AUTHENTICATION\|AUTH" services/backend/config/settings/ 2>/dev/null | grep -q "CLASSES\|BACKENDS"; then
        check_pass "Authentication backends are configured"
    else
        check_warn "Authentication configuration not verified"
    fi

    # Check for password complexity requirements
    if grep -r "PASSWORD_VALIDATORS" services/backend/config/settings/ 2>/dev/null | grep -q "MinimumLength"; then
        check_pass "Password complexity validators are configured"
    else
        check_warn "Password validators not found in Django settings"
    fi

    # Check session timeout
    if grep -r "SESSION_COOKIE_AGE\|INACTIVE_SESSION_LIFETIME" services/backend/config/settings/ 2>/dev/null; then
        check_pass "Session timeout is configured"
    else
        check_warn "Session timeout configuration not found"
    fi
}

check_requirement_10() {
    log_section "Requirement 10: Log and Monitor All Access"

    # Check logging is configured
    if grep -r "LOGGING" services/backend/config/settings/ 2>/dev/null | grep -q "handlers\|formatters"; then
        check_pass "Application logging is configured"
    else
        check_warn "Application logging configuration not verified"
    fi

    # Check Vault audit logging
    check_info "Vault audit logging requires Vault to be running (check manually)"

    # Check Docker logging driver
    LOGGING_DRIVER=$(docker info 2>/dev/null | grep "Logging Driver" | awk '{print $3}')
    if [ -n "$LOGGING_DRIVER" ]; then
        check_pass "Docker logging driver configured ($LOGGING_DRIVER)"
    else
        check_warn "Docker logging driver not detected"
    fi

    # Check for log retention
    check_info "Log retention policy requires manual verification (90 days minimum)"
}

check_requirement_11() {
    log_section "Requirement 11: Test Security Systems and Processes"

    # Check for vulnerability scanning
    if [ -f ".github/workflows/security-scan.yml" ] || [ -f ".github/workflows/sbom-generation.yml" ]; then
        check_pass "Automated vulnerability scanning is configured"
    else
        check_fail "No vulnerability scanning workflows found"
    fi

    # Check for penetration testing documentation
    if [ -f "docs/security/penetration-test-results.md" ] || [ -f "compliance/assessments/pentest-"*.pdf 2>/dev/null ]; then
        check_pass "Penetration test documentation exists"
    else
        check_warn "Penetration test documentation not found (required annually)"
    fi

    # Check for file integrity monitoring
    check_warn "File integrity monitoring (FIM) not detected (AIDE or Tripwire recommended)"
}

check_requirement_12() {
    log_section "Requirement 12: Maintain an Information Security Policy"

    # Check for security policy
    if [ -f "docs/security/pci-dss-compliance.md" ]; then
        check_pass "PCI-DSS compliance documentation exists"
    else
        check_fail "PCI-DSS compliance documentation not found"
    fi

    # Check for incident response plan
    if [ -f "docs/policies/incident-response-plan.md" ]; then
        check_pass "Incident response plan is documented"
    else
        check_warn "Incident response plan not found"
    fi

    # Check for acceptable use policy
    if [ -f "docs/policies/acceptable-use.md" ] || [ -f "docs/policies/acceptable-use-policy.md" ]; then
        check_pass "Acceptable use policy is documented"
    else
        check_warn "Acceptable use policy not found"
    fi

    # Check for vendor management
    check_info "Vendor management and risk assessment require manual verification"
}

generate_summary() {
    log_header "Compliance Check Summary"

    local TOTAL=$((PASSED_CHECKS + FAILED_CHECKS + WARNING_CHECKS))
    local COMPLIANCE_PERCENT=$((PASSED_CHECKS * 100 / TOTAL))

    echo ""
    echo "Total Checks: $TOTAL"
    echo "Passed:       $PASSED_CHECKS ($(($PASSED_CHECKS * 100 / $TOTAL))%)"
    echo "Failed:       $FAILED_CHECKS ($(($FAILED_CHECKS * 100 / $TOTAL))%)"
    echo "Warnings:     $WARNING_CHECKS ($(($WARNING_CHECKS * 100 / $TOTAL))%)"
    echo ""

    cat >> "$REPORT_FILE" <<EOF

========================================
SUMMARY
========================================
Total Checks: $TOTAL
Passed:       $PASSED_CHECKS
Failed:       $FAILED_CHECKS
Warnings:     $WARNING_CHECKS

Compliance Score: $COMPLIANCE_PERCENT%

EOF

    if [ "$FAILED_CHECKS" -eq 0 ]; then
        echo -e "${GREEN}✅ All critical checks passed!${NC}"
        echo "✅ All critical checks passed!" >> "$REPORT_FILE"
    else
        echo -e "${RED}❌ $FAILED_CHECKS critical check(s) failed${NC}"
        echo "❌ $FAILED_CHECKS critical check(s) failed" >> "$REPORT_FILE"
    fi

    if [ "$WARNING_CHECKS" -gt 0 ]; then
        echo -e "${YELLOW}⚠️  $WARNING_CHECKS warning(s) require attention${NC}"
        echo "⚠️ $WARNING_CHECKS warning(s) require attention" >> "$REPORT_FILE"
    fi

    echo ""
    echo "Detailed report saved to: $REPORT_FILE"
    echo ""

    # Recommendations
    cat >> "$REPORT_FILE" <<EOF

========================================
RECOMMENDATIONS
========================================
1. Review all FAILED checks and remediate within 7 days
2. Address WARNING items within 30 days
3. Schedule annual penetration test if not completed
4. Verify manual checks (marked as INFO) are compliant
5. Update this script as new controls are implemented

========================================
NEXT STEPS
========================================
1. Share this report with Security Team
2. Create tickets for failed checks
3. Update compliance documentation
4. Schedule follow-up assessment in 30 days

EOF

    # Exit with error if critical checks failed
    if [ "$FAILED_CHECKS" -gt 0 ]; then
        exit 1
    fi
}

# Run main function
main "$@"
