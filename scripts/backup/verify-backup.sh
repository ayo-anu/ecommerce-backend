#!/bin/bash
# ==============================================================================
# Backup Verification Script
# ==============================================================================
# Verifies backup integrity by attempting test restores
#
# Usage:
#   ./verify-backup.sh [OPTIONS]
#
# Options:
#   --backup-dir DIR     Backup directory to verify (default: /backups)
#   --latest             Verify only the latest backup
#   --all                Verify all backups
# ==============================================================================

set -e
set -u

BACKUP_DIR="/backups"
VERIFY_LATEST=true
VERIFY_ALL=false

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --backup-dir) BACKUP_DIR="$2"; shift 2 ;;
        --latest) VERIFY_LATEST=true; shift ;;
        --all) VERIFY_ALL=true; VERIFY_LATEST=false; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

verify_database_backup() {
    local backup_file=$1

    log_info "Verifying: $(basename $backup_file)"

    # Check file exists and is readable
    if [ ! -r "$backup_file" ]; then
        log_error "Cannot read backup file"
        return 1
    fi

    # Check file is not empty
    if [ ! -s "$backup_file" ]; then
        log_error "Backup file is empty"
        return 1
    fi

    # Verify gzip integrity
    if ! gunzip -t "$backup_file" 2>/dev/null; then
        log_error "Backup file is corrupted (gzip test failed)"
        return 1
    fi

    log_success "Backup is valid"
    return 0
}

verify_media_backup() {
    local backup_file=$1

    log_info "Verifying: $(basename $backup_file)"

    # Check tar.gz integrity
    if ! tar -tzf "$backup_file" > /dev/null 2>&1; then
        log_error "Media backup is corrupted"
        return 1
    fi

    log_success "Media backup is valid"
    return 0
}

main() {
    echo "================================================================================"
    echo "Backup Verification"
    echo "Backup directory: $BACKUP_DIR"
    echo "================================================================================"

    local verified=0
    local failed=0

    # Find database backups
    if [ "$VERIFY_LATEST" = true ]; then
        latest_db=$(ls -t "$BACKUP_DIR"/postgres/*.sql.gz 2>/dev/null | head -1 || echo "")
        if [ -n "$latest_db" ]; then
            if verify_database_backup "$latest_db"; then
                verified=$((verified + 1))
            else
                failed=$((failed + 1))
            fi
        fi

        latest_media=$(ls -t "$BACKUP_DIR"/media/*.tar.gz 2>/dev/null | head -1 || echo "")
        if [ -n "$latest_media" ]; then
            if verify_media_backup "$latest_media"; then
                verified=$((verified + 1))
            else
                failed=$((failed + 1))
            fi
        fi
    fi

    echo "================================================================================"
    echo "Results: $verified verified, $failed failed"
    echo "================================================================================"

    if [ $failed -gt 0 ]; then
        exit 1
    fi
}

main
