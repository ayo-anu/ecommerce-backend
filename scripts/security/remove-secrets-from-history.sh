#!/bin/bash
# ==============================================================================
# Remove Secrets from Git History
# ==============================================================================
# Helps remove sensitive data from git history using BFG Repo-Cleaner
#
# WARNING: This script rewrites git history. Use with caution!
# Always create a backup before running.
#
# Usage:
#   ./scripts/security/remove-secrets-from-history.sh [options]
#
# Options:
#   --pattern <regex>    Regex pattern to replace (e.g., "sk_live_[a-zA-Z0-9]+")
#   --file <path>        Remove specific file from history
#   --passwords <file>   File containing passwords to remove
#   --backup             Create backup before cleaning (default: yes)
#   --no-backup          Skip backup creation
#   --dry-run            Show what would be done without making changes
#
# Prerequisites:
#   - BFG Repo-Cleaner (faster alternative to git-filter-branch)
#   - Clean working directory (commit or stash changes)
#
# Installation:
#   brew install bfg  # macOS
#   # or download from: https://rtyley.github.io/bfg-repo-cleaner/
# ==============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKUP_DIR="$PROJECT_ROOT/../ecommerce-project-backup-$(date +%Y%m%d_%H%M%S)"

# Options
PATTERN=""
FILE_TO_REMOVE=""
PASSWORDS_FILE=""
CREATE_BACKUP=true
DRY_RUN=false

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

check_prerequisites() {
    print_info "Checking prerequisites..."

    # Check if BFG is installed
    if ! command -v bfg &> /dev/null; then
        print_error "BFG Repo-Cleaner is not installed"
        echo ""
        echo "Install with:"
        echo "  # macOS"
        echo "  brew install bfg"
        echo ""
        echo "  # Manual installation"
        echo "  1. Download from: https://rtyley.github.io/bfg-repo-cleaner/"
        echo "  2. Save as 'bfg.jar'"
        echo "  3. Run with: java -jar bfg.jar"
        return 1
    fi

    # Check for clean working directory
    if [ -n "$(git status --porcelain)" ]; then
        print_error "Working directory is not clean"
        echo ""
        echo "Please commit or stash your changes first:"
        echo "  git stash"
        echo "  # or"
        echo "  git add . && git commit -m 'WIP: before secret removal'"
        return 1
    fi

    print_success "Prerequisites check passed"
    return 0
}

create_backup() {
    if [ "$CREATE_BACKUP" = false ]; then
        print_warning "Skipping backup as requested"
        return 0
    fi

    print_info "Creating backup..."

    # Create backup directory
    mkdir -p "$BACKUP_DIR"

    # Clone repository for backup
    git clone "$PROJECT_ROOT" "$BACKUP_DIR"

    print_success "Backup created at: $BACKUP_DIR"
    echo ""
    print_warning "Keep this backup until you verify the cleanup worked correctly"
}

remove_by_pattern() {
    local pattern="$1"

    print_header "Removing Pattern from History"
    echo ""
    print_info "Pattern: $pattern"
    echo ""

    if [ "$DRY_RUN" = true ]; then
        print_warning "DRY RUN - No changes will be made"
        echo ""
        echo "Command that would run:"
        echo "  bfg --replace-text <(echo '$pattern===>***REMOVED***') ."
        return 0
    fi

    print_warning "This will rewrite git history!"
    echo ""
    read -p "Are you sure you want to continue? (yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        print_info "Operation cancelled"
        exit 0
    fi

    # Use BFG to replace pattern
    echo "$pattern===>***REMOVED***" | bfg --replace-text /dev/stdin .

    print_success "Pattern removed from history"
}

remove_file() {
    local file="$1"

    print_header "Removing File from History"
    echo ""
    print_info "File: $file"
    echo ""

    if [ "$DRY_RUN" = true ]; then
        print_warning "DRY RUN - No changes will be made"
        echo ""
        echo "Command that would run:"
        echo "  bfg --delete-files '$file' ."
        return 0
    fi

    print_warning "This will remove the file from ALL commits!"
    echo ""
    read -p "Are you sure you want to continue? (yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        print_info "Operation cancelled"
        exit 0
    fi

    # Use BFG to delete file
    bfg --delete-files "$file" .

    print_success "File removed from history"
}

remove_passwords() {
    local passwords_file="$1"

    print_header "Removing Passwords from History"
    echo ""
    print_info "Passwords file: $passwords_file"
    echo ""

    if [ ! -f "$passwords_file" ]; then
        print_error "Passwords file not found: $passwords_file"
        return 1
    fi

    if [ "$DRY_RUN" = true ]; then
        print_warning "DRY RUN - No changes will be made"
        echo ""
        echo "Command that would run:"
        echo "  bfg --replace-text '$passwords_file' ."
        return 0
    fi

    print_warning "This will replace all passwords with ***REMOVED***"
    echo ""
    read -p "Are you sure you want to continue? (yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        print_info "Operation cancelled"
        exit 0
    fi

    # Use BFG to replace passwords
    bfg --replace-text "$passwords_file" .

    print_success "Passwords removed from history"
}

cleanup_repo() {
    print_header "Cleaning Up Repository"
    echo ""

    if [ "$DRY_RUN" = true ]; then
        print_warning "DRY RUN - Skipping cleanup"
        return 0
    fi

    # Expire reflog
    print_info "Expiring reflog..."
    git reflog expire --expire=now --all

    # Garbage collect
    print_info "Running garbage collection..."
    git gc --prune=now --aggressive

    print_success "Repository cleanup complete"
}

push_changes() {
    echo ""
    print_warning "IMPORTANT: You need to force push to update remote repository"
    echo ""
    echo "Review the changes first:"
    echo "  git log --oneline -10"
    echo ""
    echo "Then force push (WARNING: affects all collaborators):"
    echo "  git push origin --force --all"
    echo "  git push origin --force --tags"
    echo ""
    print_error "ALL COLLABORATORS must re-clone the repository after force push!"
}

# ==============================================================================
# Main Script
# ==============================================================================

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --pattern)
                PATTERN="$2"
                shift 2
                ;;
            --file)
                FILE_TO_REMOVE="$2"
                shift 2
                ;;
            --passwords)
                PASSWORDS_FILE="$2"
                shift 2
                ;;
            --backup)
                CREATE_BACKUP=true
                shift
                ;;
            --no-backup)
                CREATE_BACKUP=false
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [options]"
                echo ""
                echo "Options:"
                echo "  --pattern <regex>    Regex pattern to replace"
                echo "  --file <path>        Remove specific file from history"
                echo "  --passwords <file>   File containing passwords to remove"
                echo "  --backup             Create backup before cleaning (default)"
                echo "  --no-backup          Skip backup creation"
                echo "  --dry-run            Show what would be done"
                echo "  --help, -h           Show this help message"
                echo ""
                echo "Examples:"
                echo "  # Remove API key pattern"
                echo "  $0 --pattern 'sk_live_[a-zA-Z0-9]+'"
                echo ""
                echo "  # Remove file"
                echo "  $0 --file '.env'"
                echo ""
                echo "  # Remove passwords from file"
                echo "  $0 --passwords passwords.txt"
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

    print_header "Remove Secrets from Git History"
    echo ""

    # Validate options
    if [ -z "$PATTERN" ] && [ -z "$FILE_TO_REMOVE" ] && [ -z "$PASSWORDS_FILE" ]; then
        print_error "No operation specified"
        echo ""
        echo "Use one of:"
        echo "  --pattern <regex>"
        echo "  --file <path>"
        echo "  --passwords <file>"
        echo ""
        echo "Use --help for more information"
        exit 1
    fi

    # Check prerequisites
    if ! check_prerequisites; then
        exit 2
    fi

    echo ""

    # Create backup
    if [ "$DRY_RUN" = false ]; then
        create_backup
        echo ""
    fi

    # Perform operations
    if [ -n "$PATTERN" ]; then
        remove_by_pattern "$PATTERN"
        echo ""
    fi

    if [ -n "$FILE_TO_REMOVE" ]; then
        remove_file "$FILE_TO_REMOVE"
        echo ""
    fi

    if [ -n "$PASSWORDS_FILE" ]; then
        remove_passwords "$PASSWORDS_FILE"
        echo ""
    fi

    # Cleanup
    cleanup_repo
    echo ""

    # Instructions for pushing
    if [ "$DRY_RUN" = false ]; then
        push_changes
    fi

    echo ""
    print_success "Secret removal process complete!"

    if [ "$DRY_RUN" = false ]; then
        echo ""
        print_warning "Next steps:"
        echo "  1. Verify changes: git log --all --oneline -20"
        echo "  2. Test the application"
        echo "  3. Rotate compromised credentials"
        echo "  4. Force push to remote (see above)"
        echo "  5. Notify all collaborators to re-clone"
    fi
}

main "$@"
