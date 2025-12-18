#!/bin/bash
# ==============================================================================
# Database Restore Script
# ==============================================================================
# Restores PostgreSQL databases from backup
#
# Usage:
#   ./restore-database.sh --file BACKUP_FILE [OPTIONS]
#
# Options:
#   --file FILE          Backup file to restore (required)
#   --database TYPE      Database type: main, ai, redis (default: main)
#   --decrypt            Decrypt backup with GPG
#   --confirm            Skip confirmation prompt
#
# WARNING: This will replace all data in the target database!
# ==============================================================================

set -e
set -u
set -o pipefail

# Configuration
BACKUP_FILE=""
DATABASE_TYPE="main"
DECRYPT=false
CONFIRM=false

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --file) BACKUP_FILE="$2"; shift 2 ;;
        --database) DATABASE_TYPE="$2"; shift 2 ;;
        --decrypt) DECRYPT=true; shift ;;
        --confirm) CONFIRM=true; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

if [ -z "$BACKUP_FILE" ]; then
    log_error "Backup file is required. Use --file to specify."
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    log_error "Backup file not found: $BACKUP_FILE"
    exit 1
fi

confirm_restore() {
    if [ "$CONFIRM" = false ]; then
        echo "================================================================================"
        log_warning "DATABASE RESTORE CONFIRMATION"
        echo "This will REPLACE ALL DATA in the $DATABASE_TYPE database!"
        echo "Backup file: $BACKUP_FILE"
        echo "================================================================================"
        read -p "Are you sure you want to proceed? (yes/no): " -r
        echo

        if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
            log_info "Restore cancelled"
            exit 0
        fi
    fi
}

decrypt_if_needed() {
    if [ "$DECRYPT" = true ]; then
        log_info "Decrypting backup..."
        local decrypted="${BACKUP_FILE%.gpg}"
        gpg --decrypt "$BACKUP_FILE" > "$decrypted"
        BACKUP_FILE="$decrypted"
    fi
}

restore_main_database() {
    log_info "Restoring main PostgreSQL database..."

    # Decompress and restore
    gunzip -c "$BACKUP_FILE" | docker exec -i ecommerce_postgres psql -U postgres

    if [ $? -eq 0 ]; then
        log_info "Main database restored successfully"
    else
        log_error "Failed to restore main database"
        exit 1
    fi
}

restore_ai_database() {
    log_info "Restoring AI PostgreSQL database..."

    gunzip -c "$BACKUP_FILE" | docker exec -i ecommerce_postgres_ai psql -U postgres

    if [ $? -eq 0 ]; then
        log_info "AI database restored successfully"
    else
        log_error "Failed to restore AI database"
        exit 1
    fi
}

restore_redis() {
    log_info "Restoring Redis..."

    # Stop Redis
    docker exec ecommerce_redis redis-cli SHUTDOWN NOSAVE || true
    sleep 2

    # Decompress and copy RDB file
    gunzip -c "$BACKUP_FILE" > /tmp/dump.rdb
    docker cp /tmp/dump.rdb ecommerce_redis:/data/dump.rdb
    rm /tmp/dump.rdb

    # Start Redis
    docker start ecommerce_redis

    log_info "Redis restored successfully"
}

main() {
    echo "================================================================================"
    echo "Database Restore"
    echo "File: $BACKUP_FILE"
    echo "Database: $DATABASE_TYPE"
    echo "================================================================================"

    confirm_restore
    decrypt_if_needed

    case $DATABASE_TYPE in
        main)
            restore_main_database
            ;;
        ai)
            restore_ai_database
            ;;
        redis)
            restore_redis
            ;;
        *)
            log_error "Invalid database type: $DATABASE_TYPE"
            exit 1
            ;;
    esac

    log_info "Restore complete!"
}

main
