#!/bin/bash
# ==============================================================================
# Database Backup Script
# ==============================================================================
# Creates encrypted backups of all PostgreSQL databases
#
# Usage:
#   ./backup-databases.sh [OPTIONS]
#
# Options:
#   --output-dir DIR     Backup output directory (default: /backups/postgres)
#   --retention-days N   Number of days to keep backups (default: 7)
#   --encrypt            Encrypt backup with GPG (requires GPG_RECIPIENT env var)
#   --s3-upload          Upload to S3 (requires AWS credentials)
#   --s3-bucket BUCKET   S3 bucket name
#
# Environment Variables:
#   POSTGRES_PASSWORD    PostgreSQL password
#   GPG_RECIPIENT        GPG key for encryption
#   AWS_ACCESS_KEY_ID    AWS access key
#   AWS_SECRET_ACCESS_KEY AWS secret key
# ==============================================================================

set -e
set -u
set -o pipefail

# Configuration
BACKUP_DIR="${BACKUP_OUTPUT_DIR:-/backups/postgres}"
RETENTION_DAYS=7
ENCRYPT=false
S3_UPLOAD=false
S3_BUCKET=""
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DATE_ONLY=$(date +%Y%m%d)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --output-dir) BACKUP_DIR="$2"; shift 2 ;;
        --retention-days) RETENTION_DAYS="$2"; shift 2 ;;
        --encrypt) ENCRYPT=true; shift ;;
        --s3-upload) S3_UPLOAD=true; shift ;;
        --s3-bucket) S3_BUCKET="$2"; shift 2 ;;
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

preflight_checks() {
    log_info "Running preflight checks..."

    # Check if docker is running
    if ! docker ps > /dev/null 2>&1; then
        log_error "Docker is not running"
        exit 1
    fi

    # Check if postgres containers are running
    if ! docker ps | grep -q ecommerce_postgres; then
        log_error "PostgreSQL container is not running"
        exit 1
    fi

    # Create backup directory
    mkdir -p "$BACKUP_DIR"

    # Check if encryption is requested but no GPG recipient
    if [ "$ENCRYPT" = true ] && [ -z "${GPG_RECIPIENT:-}" ]; then
        log_error "Encryption requested but GPG_RECIPIENT not set"
        exit 1
    fi

    # Check S3 upload requirements
    if [ "$S3_UPLOAD" = true ]; then
        if [ -z "$S3_BUCKET" ]; then
            log_error "S3 upload requested but --s3-bucket not specified"
            exit 1
        fi
        if [ -z "${AWS_ACCESS_KEY_ID:-}" ] || [ -z "${AWS_SECRET_ACCESS_KEY:-}" ]; then
            log_error "S3 upload requested but AWS credentials not set"
            exit 1
        fi
    fi

    log_success "Preflight checks passed"
}

backup_main_database() {
    local backup_file="$BACKUP_DIR/main_db_${TIMESTAMP}.sql.gz"

    log_info "Backing up main PostgreSQL database..."

    # Perform backup using pg_dumpall
    docker exec -t ecommerce_postgres pg_dumpall -U postgres | gzip > "$backup_file"

    if [ $? -eq 0 ]; then
        local size=$(du -h "$backup_file" | cut -f1)
        log_success "Main database backup complete: $backup_file ($size)"
        echo "$backup_file"
    else
        log_error "Failed to backup main database"
        exit 1
    fi
}

backup_ai_database() {
    local backup_file="$BACKUP_DIR/ai_db_${TIMESTAMP}.sql.gz"

    log_info "Backing up AI PostgreSQL database..."

    # Perform backup using pg_dumpall
    docker exec -t ecommerce_postgres_ai pg_dumpall -U postgres | gzip > "$backup_file"

    if [ $? -eq 0 ]; then
        local size=$(du -h "$backup_file" | cut -f1)
        log_success "AI database backup complete: $backup_file ($size)"
        echo "$backup_file"
    else
        log_error "Failed to backup AI database"
        exit 1
    fi
}

backup_redis() {
    local backup_file="$BACKUP_DIR/redis_${TIMESTAMP}.rdb"

    log_info "Backing up Redis..."

    # Trigger Redis save
    docker exec ecommerce_redis redis-cli SAVE

    # Copy RDB file
    docker cp ecommerce_redis:/data/dump.rdb "$backup_file"

    if [ $? -eq 0 ]; then
        # Compress
        gzip "$backup_file"
        local size=$(du -h "${backup_file}.gz" | cut -f1)
        log_success "Redis backup complete: ${backup_file}.gz ($size)"
        echo "${backup_file}.gz"
    else
        log_error "Failed to backup Redis"
        exit 1
    fi
}

encrypt_backup() {
    local file=$1

    if [ "$ENCRYPT" = false ]; then
        return 0
    fi

    log_info "Encrypting backup: $(basename $file)"

    gpg --encrypt --recipient "$GPG_RECIPIENT" --trust-model always "$file"

    if [ $? -eq 0 ]; then
        # Remove unencrypted file
        rm "$file"
        log_success "Backup encrypted: ${file}.gpg"
        echo "${file}.gpg"
    else
        log_error "Failed to encrypt backup"
        return 1
    fi
}

upload_to_s3() {
    local file=$1

    if [ "$S3_UPLOAD" = false ]; then
        return 0
    fi

    log_info "Uploading to S3: s3://$S3_BUCKET/postgres/$DATE_ONLY/$(basename $file)"

    # Use AWS CLI or docker container with AWS CLI
    if command -v aws &> /dev/null; then
        aws s3 cp "$file" "s3://$S3_BUCKET/postgres/$DATE_ONLY/" --storage-class STANDARD_IA
    else
        # Use AWS CLI via Docker
        docker run --rm \
            -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" \
            -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" \
            -v "$BACKUP_DIR:/backups" \
            amazon/aws-cli \
            s3 cp "/backups/$(basename $file)" "s3://$S3_BUCKET/postgres/$DATE_ONLY/" \
            --storage-class STANDARD_IA
    fi

    if [ $? -eq 0 ]; then
        log_success "Uploaded to S3"
    else
        log_error "Failed to upload to S3"
        return 1
    fi
}

cleanup_old_backups() {
    log_info "Cleaning up backups older than $RETENTION_DAYS days..."

    # Find and delete old backups
    find "$BACKUP_DIR" -name "*.sql.gz*" -type f -mtime +$RETENTION_DAYS -delete
    find "$BACKUP_DIR" -name "*.rdb.gz*" -type f -mtime +$RETENTION_DAYS -delete

    log_success "Old backups cleaned up"
}

create_backup_manifest() {
    local manifest_file="$BACKUP_DIR/manifest_${TIMESTAMP}.txt"

    log_info "Creating backup manifest..."

    cat > "$manifest_file" << EOF
Backup Manifest
===============
Date: $(date)
Timestamp: $TIMESTAMP

Files:
EOF

    for file in "$BACKUP_DIR"/*_${TIMESTAMP}.*; do
        if [ -f "$file" ]; then
            echo "  - $(basename $file) ($(du -h $file | cut -f1))" >> "$manifest_file"
        fi
    done

    log_success "Manifest created: $manifest_file"
}

main() {
    echo "================================================================================"
    echo "Database Backup"
    echo "Target: $BACKUP_DIR"
    echo "Retention: $RETENTION_DAYS days"
    echo "Encrypt: $ENCRYPT"
    echo "S3 Upload: $S3_UPLOAD"
    echo "================================================================================"

    # Preflight checks
    preflight_checks

    # Backup main database
    main_db_backup=$(backup_main_database)
    [ "$ENCRYPT" = true ] && main_db_backup=$(encrypt_backup "$main_db_backup")
    [ "$S3_UPLOAD" = true ] && upload_to_s3 "$main_db_backup"

    # Backup AI database
    ai_db_backup=$(backup_ai_database)
    [ "$ENCRYPT" = true ] && ai_db_backup=$(encrypt_backup "$ai_db_backup")
    [ "$S3_UPLOAD" = true ] && upload_to_s3 "$ai_db_backup"

    # Backup Redis
    redis_backup=$(backup_redis)
    [ "$ENCRYPT" = true ] && redis_backup=$(encrypt_backup "$redis_backup")
    [ "$S3_UPLOAD" = true ] && upload_to_s3 "$redis_backup"

    # Create manifest
    create_backup_manifest

    # Cleanup old backups
    cleanup_old_backups

    echo "================================================================================"
    log_success "Backup complete!"
    echo "Backups saved to: $BACKUP_DIR"
    echo "================================================================================"
}

main
