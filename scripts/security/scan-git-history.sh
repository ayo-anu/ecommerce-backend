#!/bin/bash
# ==============================================================================
# Git History Secret Scanning Script
# ==============================================================================
# Scans entire git history for exposed secrets, API keys, and credentials
#
# Usage:
#   ./scripts/security/scan-git-history.sh [options]
#
# Options:
#   --gitleaks         Use Gitleaks scanner (default)
#   --trufflehog       Use TruffleHog scanner
#   --all              Use all scanners
#   --report-dir <dir> Output directory for reports (default: security-reports)
#   --verbose          Show detailed output
#
# Exit Codes:
#   0 - No secrets found
#   1 - Secrets detected
#   2 - Scanner not installed
# ==============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
REPORT_DIR="$PROJECT_ROOT/security-reports/$(date +%Y%m%d_%H%M%S)"

# Options
USE_GITLEAKS=true
USE_TRUFFLEHOG=false
USE_ALL=false
VERBOSE=false

# ==============================================================================
# Functions
# ==============================================================================

print_header() {
    echo -e "${BLUE}=================================================="
    echo -e "$1"
    echo -e "==================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

check_gitleaks() {
    if ! command -v gitleaks &> /dev/null; then
        print_error "Gitleaks is not installed"
        echo ""
        echo "Install with:"
        echo "  # macOS"
        echo "  brew install gitleaks"
        echo ""
        echo "  # Linux"
        echo "  wget https://github.com/gitleaks/gitleaks/releases/download/v8.18.1/gitleaks_8.18.1_linux_x64.tar.gz"
        echo "  tar xzf gitleaks_8.18.1_linux_x64.tar.gz"
        echo "  sudo mv gitleaks /usr/local/bin/"
        return 1
    fi
    return 0
}

check_trufflehog() {
    if ! command -v trufflehog &> /dev/null; then
        print_error "TruffleHog is not installed"
        echo ""
        echo "Install with:"
        echo "  # macOS"
        echo "  brew install trufflehog"
        echo ""
        echo "  # Linux"
        echo "  wget https://github.com/trufflesecurity/trufflehog/releases/download/v3.63.0/trufflehog_3.63.0_linux_amd64.tar.gz"
        echo "  tar xzf trufflehog_3.63.0_linux_amd64.tar.gz"
        echo "  sudo mv trufflehog /usr/local/bin/"
        return 1
    fi
    return 0
}

scan_with_gitleaks() {
    print_header "Scanning with Gitleaks"

    if ! check_gitleaks; then
        return 2
    fi

    local report_file="$REPORT_DIR/gitleaks-report.json"
    mkdir -p "$REPORT_DIR"

    echo ""
    print_info "Scanning entire git history..."
    echo ""

    if [ "$VERBOSE" = true ]; then
        gitleaks detect \
            --source "$PROJECT_ROOT" \
            --report-path "$report_file" \
            --verbose \
            --redact
    else
        gitleaks detect \
            --source "$PROJECT_ROOT" \
            --report-path "$report_file" \
            --redact \
            --no-banner
    fi

    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        print_success "Gitleaks: No secrets found"
        return 0
    else
        print_error "Gitleaks: Secrets detected!"
        echo ""
        print_warning "Report saved to: $report_file"

        # Parse and display findings
        if [ -f "$report_file" ]; then
            local count=$(jq '. | length' "$report_file" 2>/dev/null || echo "unknown")
            print_error "Found $count potential secrets"

            echo ""
            echo "Top findings:"
            jq -r '.[:5] | .[] | "  - \(.RuleID): \(.File):\(.StartLine)"' "$report_file" 2>/dev/null || true
        fi

        return 1
    fi
}

scan_with_trufflehog() {
    print_header "Scanning with TruffleHog"

    if ! check_trufflehog; then
        return 2
    fi

    local report_file="$REPORT_DIR/trufflehog-report.json"
    mkdir -p "$REPORT_DIR"

    echo ""
    print_info "Scanning entire git history..."
    echo ""

    if [ "$VERBOSE" = true ]; then
        trufflehog filesystem "$PROJECT_ROOT" \
            --json \
            --no-update \
            --debug > "$report_file" 2>&1
    else
        trufflehog filesystem "$PROJECT_ROOT" \
            --json \
            --no-update \
            --only-verified > "$report_file" 2>&1
    fi

    local exit_code=$?

    # TruffleHog exits 0 even when finding secrets, check file content
    if [ -f "$report_file" ] && [ -s "$report_file" ]; then
        # File exists and is not empty
        local findings=$(grep -c "\"DetectorName\"" "$report_file" 2>/dev/null || echo "0")

        if [ "$findings" -gt 0 ]; then
            print_error "TruffleHog: $findings secrets detected!"
            echo ""
            print_warning "Report saved to: $report_file"

            echo ""
            echo "Sample findings:"
            jq -r 'select(.DetectorName) | "  - \(.DetectorName): \(.SourceMetadata.Data.Filesystem.file)"' "$report_file" 2>/dev/null | head -5 || true

            return 1
        else
            print_success "TruffleHog: No verified secrets found"
            return 0
        fi
    else
        print_success "TruffleHog: No secrets found"
        return 0
    fi
}

# ==============================================================================
# Main Script
# ==============================================================================

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --gitleaks)
                USE_GITLEAKS=true
                USE_TRUFFLEHOG=false
                USE_ALL=false
                shift
                ;;
            --trufflehog)
                USE_GITLEAKS=false
                USE_TRUFFLEHOG=true
                USE_ALL=false
                shift
                ;;
            --all)
                USE_ALL=true
                USE_GITLEAKS=true
                USE_TRUFFLEHOG=true
                shift
                ;;
            --report-dir)
                REPORT_DIR="$2"
                shift 2
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [options]"
                echo ""
                echo "Options:"
                echo "  --gitleaks         Use Gitleaks scanner (default)"
                echo "  --trufflehog       Use TruffleHog scanner"
                echo "  --all              Use all scanners"
                echo "  --report-dir <dir> Output directory for reports"
                echo "  --verbose          Show detailed output"
                echo "  --help, -h         Show this help message"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done

    cd "$PROJECT_ROOT"

    print_header "Git History Secret Scanning"
    echo ""
    print_info "Project: $PROJECT_ROOT"
    print_info "Report directory: $REPORT_DIR"
    echo ""

    # Track results
    local total_scanners=0
    local passed_scanners=0
    local failed_scanners=0
    local skipped_scanners=0

    # Run Gitleaks
    if [ "$USE_GITLEAKS" = true ]; then
        total_scanners=$((total_scanners + 1))
        echo ""
        if scan_with_gitleaks; then
            passed_scanners=$((passed_scanners + 1))
        else
            exit_code=$?
            if [ $exit_code -eq 2 ]; then
                skipped_scanners=$((skipped_scanners + 1))
            else
                failed_scanners=$((failed_scanners + 1))
            fi
        fi
    fi

    # Run TruffleHog
    if [ "$USE_TRUFFLEHOG" = true ]; then
        total_scanners=$((total_scanners + 1))
        echo ""
        if scan_with_trufflehog; then
            passed_scanners=$((passed_scanners + 1))
        else
            exit_code=$?
            if [ $exit_code -eq 2 ]; then
                skipped_scanners=$((skipped_scanners + 1))
            else
                failed_scanners=$((failed_scanners + 1))
            fi
        fi
    fi

    # Print summary
    echo ""
    print_header "Scan Summary"
    echo ""
    echo "Total scanners:   $total_scanners"
    print_success "Passed:           $passed_scanners"

    if [ $failed_scanners -gt 0 ]; then
        print_error "Failed (secrets):  $failed_scanners"
    else
        echo "Failed (secrets):  $failed_scanners"
    fi

    if [ $skipped_scanners -gt 0 ]; then
        print_warning "Skipped (n/a):    $skipped_scanners"
    fi

    echo ""
    echo "Reports saved to: $REPORT_DIR"
    echo ""

    # Final verdict
    if [ $failed_scanners -eq 0 ]; then
        if [ $skipped_scanners -eq $total_scanners ]; then
            print_error "No scanners were available to run"
            exit 2
        fi

        print_success "No secrets detected in git history! 🎉"
        exit 0
    else
        print_error "SECRETS DETECTED IN GIT HISTORY!"
        echo ""
        print_warning "Action Required:"
        echo "  1. Review the reports in: $REPORT_DIR"
        echo "  2. Rotate ALL compromised credentials immediately"
        echo "  3. Remove secrets from git history (see: scripts/security/remove-secrets-from-history.sh)"
        echo "  4. Update .gitignore to prevent future commits"
        echo "  5. Add to .gitleaks.toml allowlist if false positive"
        echo ""
        exit 1
    fi
}

main "$@"
