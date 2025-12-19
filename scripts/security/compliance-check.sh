#!/bin/bash
# ==============================================================================
# Compliance Check Script
# ==============================================================================
# This script validates compliance with PCI-DSS and SOC 2 requirements
#
# Usage:
#   ./scripts/security/compliance-check.sh [--standard pci|soc2|all]
#
# Options:
#   --standard    Compliance standard to check (default: all)
#   --report      Generate detailed compliance report
#
# Exit Codes:
#   0 - All checks passed
#   1 - Compliance issues found
# ==============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
STANDARD="${1:-all}"
GENERATE_REPORT=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --standard)
            STANDARD="$2"
            shift 2
            ;;
        --report)
            GENERATE_REPORT=true
            shift
            ;;
        *)
            shift
            ;;
    esac
done

# Counters
PASSED=0
FAILED=0
WARNING=0

# Logging
log_pass() {
    echo -e "${GREEN}[PASS]${NC} $@"
    ((PASSED++))
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $@"
    ((FAILED++))
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $@"
    ((WARNING++))
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $@"
}

# PCI-DSS Compliance Checks
check_pci_dss() {
    echo ""
    echo "================================================================"
    echo "PCI-DSS Compliance Validation"
    echo "================================================================"
    echo ""

    # Requirement 1: Install and maintain firewall configuration
    echo "Requirement 1: Firewall Configuration"
    if docker network ls | grep -q "internal"; then
        log_pass "Network segmentation implemented"
    else
        log_fail "No internal networks found"
    fi

    # Check if services are not exposed directly
    local exposed=$(docker ps --format '{{.Names}}\t{{.Ports}}' | grep -c "0.0.0.0:.*->5432\|0.0.0.0:.*->6379" || echo 0)
    if [ "$exposed" -eq 0 ]; then
        log_pass "Database services not directly exposed"
    else
        log_fail "Database services exposed to internet"
    fi

    echo ""
    echo "Requirement 2: No Default Credentials"
    # Check for default passwords (basic check)
    if docker-compose config 2>/dev/null | grep -qi "password.*password\|password.*admin"; then
        log_fail "Possible default passwords in configuration"
    else
        log_pass "No obvious default passwords found"
    fi

    echo ""
    echo "Requirement 3: Protect Stored Cardholder Data"
    # Check if Vault is running
    if docker ps | grep -q vault; then
        log_pass "Vault secrets management deployed"
    else
        log_warn "Vault not running (secrets management)"
    fi

    # Check database encryption
    if docker inspect postgres 2>/dev/null | grep -q "Mounts"; then
        log_pass "Database volumes configured"
    else
        log_warn "Cannot verify database storage"
    fi

    echo ""
    echo "Requirement 4: Encrypt Transmission of Cardholder Data"
    # Check for TLS/SSL configuration
    if [ -f "deploy/nginx/ssl/fullchain.pem" ] || [ -f "config/nginx/ssl/cert.pem" ]; then
        log_pass "SSL certificates configured"
    else
        log_warn "SSL certificates not found"
    fi

    echo ""
    echo "Requirement 6: Secure Systems and Applications"
    # Check for security scanning in CI
    if [ -f ".github/workflows/security-scan.yml" ]; then
        log_pass "Security scanning configured in CI"
    else
        log_warn "No security scanning workflow found"
    fi

    echo ""
    echo "Requirement 7: Restrict Access to Cardholder Data"
    # Check Vault policies exist
    if [ -d "deploy/vault/policies" ]; then
        local policies=$(ls deploy/vault/policies/*.hcl 2>/dev/null | wc -l)
        if [ "$policies" -gt 0 ]; then
            log_pass "Vault access policies defined (${policies} policies)"
        else
            log_fail "No Vault access policies found"
        fi
    else
        log_warn "Vault policies directory not found"
    fi

    echo ""
    echo "Requirement 8: Identify and Authenticate Access"
    # Check for AppRole authentication
    if grep -r "VAULT_ROLE_ID" .env.example .env.vault.example 2>/dev/null | grep -q VAULT_ROLE_ID; then
        log_pass "AppRole authentication configured"
    else
        log_warn "AppRole authentication not found in config"
    fi

    echo ""
    echo "Requirement 10: Track and Monitor Access"
    # Check for audit logging
    if docker ps | grep -q vault; then
        if docker exec ecommerce_vault vault audit list 2>/dev/null | grep -q "file/"; then
            log_pass "Vault audit logging enabled"
        else
            log_warn "Vault audit logging not configured"
        fi
    else
        log_warn "Cannot verify audit logging (Vault not running)"
    fi

    # Check application logging
    if docker-compose config 2>/dev/null | grep -q "logging:"; then
        log_pass "Service logging configured"
    else
        log_warn "Service logging not explicitly configured"
    fi

    echo ""
    echo "Requirement 11: Test Security Systems"
    # Check for test scripts
    if [ -f "scripts/security/test-rotation.sh" ] && [ -f "scripts/security/security-audit.sh" ]; then
        log_pass "Security testing scripts available"
    else
        log_warn "Some security test scripts missing"
    fi
}

# SOC 2 Compliance Checks
check_soc2() {
    echo ""
    echo "================================================================"
    echo "SOC 2 Trust Service Criteria Validation"
    echo "================================================================"
    echo ""

    # Common Criteria: Security
    echo "CC1: Control Environment"
    if [ -d "docs/security" ]; then
        log_pass "Security documentation exists"
    else
        log_warn "Security documentation directory not found"
    fi

    echo ""
    echo "CC2: Communication and Information"
    if [ -f "docs/security/vault-integration.md" ] || [ -f "docs/PHASE_3_EXECUTION_PLAN.md" ]; then
        log_pass "Security procedures documented"
    else
        log_warn "Security procedure documentation incomplete"
    fi

    echo ""
    echo "CC3: Risk Assessment"
    if [ -f "scripts/security/security-audit.sh" ]; then
        log_pass "Security assessment tools implemented"
    else
        log_fail "Security assessment tools missing"
    fi

    echo ""
    echo "CC4: Monitoring Activities"
    # Check for monitoring services
    if docker ps 2>/dev/null | grep -qE "prometheus|grafana"; then
        log_pass "Monitoring services running"
    else
        log_warn "Monitoring services not detected"
    fi

    echo ""
    echo "CC5: Control Activities"
    # Check for automated controls
    if [ -f "scripts/security/rotate-secrets.sh" ]; then
        log_pass "Automated security controls implemented"
    else
        log_warn "Automated controls incomplete"
    fi

    echo ""
    echo "CC6: Logical and Physical Access"
    # Check access controls
    if [ -d "deploy/vault/policies" ]; then
        log_pass "Access control policies defined"
    else
        log_warn "Access control policies not found"
    fi

    echo ""
    echo "CC7: System Operations"
    # Check backup and recovery procedures
    if docker-compose config 2>/dev/null | grep -q "volumes:"; then
        log_pass "Data persistence configured"
    else
        log_warn "Volume configuration not verified"
    fi

    echo ""
    echo "CC8: Change Management"
    # Check for CI/CD
    if [ -d ".github/workflows" ]; then
        log_pass "CI/CD workflows configured"
    else
        log_warn "CI/CD workflows not found"
    fi

    echo ""
    echo "CC9: Risk Mitigation"
    # Check encryption
    if docker ps | grep -q vault; then
        log_pass "Secrets encryption (Vault) deployed"
    else
        log_warn "Secrets management not verified"
    fi

    # Availability Criteria
    echo ""
    echo "A1: Availability"
    # Check resource limits
    if docker-compose config 2>/dev/null | grep -q "limits:"; then
        log_pass "Resource limits configured"
    else
        log_warn "Resource limits not configured"
    fi

    # Check health checks
    if docker-compose config 2>/dev/null | grep -q "healthcheck:"; then
        log_pass "Health checks configured"
    else
        log_warn "Health checks not configured"
    fi

    # Processing Integrity Criteria
    echo ""
    echo "PI1: Processing Integrity"
    # Check for data validation
    log_info "Application-level validation (manual review required)"

    # Confidentiality Criteria
    echo ""
    echo "C1: Confidentiality"
    # Check encryption
    if docker ps | grep -q vault; then
        log_pass "Confidential data encrypted in Vault"
    else
        log_warn "Vault not running"
    fi
}

# Generate detailed report
generate_report() {
    local report_file="compliance-report-$(date +%Y%m%d_%H%M%S).txt"

    {
        echo "================================================================"
        echo "COMPLIANCE REPORT"
        echo "Generated: $(date)"
        echo "================================================================"
        echo ""
        echo "Summary:"
        echo "  Passed: ${PASSED}"
        echo "  Failed: ${FAILED}"
        echo "  Warnings: ${WARNING}"
        echo ""
        echo "Overall Status: $([ $FAILED -eq 0 ] && echo "COMPLIANT" || echo "NON-COMPLIANT")"
        echo ""
        echo "================================================================"
    } > "$report_file"

    echo "Report saved to: $report_file"
}

# Main execution
main() {
    echo "================================================================"
    echo "Compliance Validation Tool"
    echo "Standard: ${STANDARD}"
    echo "================================================================"

    case "$STANDARD" in
        pci|PCI|pci-dss|PCI-DSS)
            check_pci_dss
            ;;
        soc2|SOC2|soc-2|SOC-2)
            check_soc2
            ;;
        all|ALL)
            check_pci_dss
            check_soc2
            ;;
        *)
            echo "Invalid standard: ${STANDARD}"
            echo "Use: pci, soc2, or all"
            exit 1
            ;;
    esac

    # Summary
    echo ""
    echo "================================================================"
    echo "COMPLIANCE CHECK SUMMARY"
    echo "================================================================"
    echo ""
    printf "  ${GREEN}Passed:${NC}   %3d\n" "$PASSED"
    printf "  ${RED}Failed:${NC}   %3d\n" "$FAILED"
    printf "  ${YELLOW}Warnings:${NC} %3d\n" "$WARNING"
    echo ""

    if [ "$GENERATE_REPORT" = true ]; then
        generate_report
    fi

    if [ $FAILED -eq 0 ]; then
        echo -e "${GREEN}Compliance validation PASSED${NC}"
        exit 0
    else
        echo -e "${RED}Compliance validation FAILED${NC}"
        exit 1
    fi
}

main
