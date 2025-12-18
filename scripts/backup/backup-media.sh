#!/bin/bash
# ==============================================================================
# Media Files Backup Script
# ==============================================================================
# Backs up uploaded media files and static assets
#
# Usage:
#   ./backup-media.sh [OPTIONS]
#
# Options:
#   --output-dir DIR     Backup output directory (default: /backups/media)
#   --retention-days N   Number of days to keep backups (default: 30)
#   --s3-upload          Upload to S3
#   --s3-bucket BUCKET   S3 bucket name
# ==============================================================================

set -e
set -u
set -o pipefail

# Configuration
BACKUP_DIR="${BACKUP_OUTPUT_DIR:-/backups/media}"
RETENTION_DAYS=30
S3_UPLOAD=false
S3_BUCKET=""
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DATE_ONLY=$(date +%Y%m%d)

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --output-dir) BACKUP_DIR="$2"; shift 2 ;;
        --retention-days) RETENTION_DAYS="$2"; shift 2 ;;
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

backup_media_files() {
    local backup_file="$BACKUP_DIR/media_${TIMESTAMP}.tar.gz"

    log_info "Backing up media files..."

    # Copy media files from docker volume
    docker run --rm \
        -v backend_media:/media:ro \
        -v "$BACKUP_DIR:/backup" \
        alpine \
        tar czf "/backup/$(basename $backup_file)" -C /media .

    if [ $? -eq 0 ]; then
        local size=$(du -h "$backup_file" | cut -f1)
        log_info "Media backup complete: $backup_file ($size)"
        echo "$backup_file"
    else
        log_error "Failed to backup media files"
        exit 1
    fi
}

backup_static_files() {
    local backup_file="$BACKUP_DIR/static_${TIMESTAMP}.tar.gz"

    log_info "Backing up static files..."

    docker run --rm \
        -v backend_static:/static:ro \
        -v "$BACKUP_DIR:/backup" \
        alpine \
        tar czf "/backup/$(basename $backup_file)" -C /static .

    if [ $? -eq 0 ]; then
        local size=$(du -h "$backup_file" | cut -f1)
        log_info "Static backup complete: $backup_file ($size)"
        echo "$backup_file"
    else
        log_error "Failed to backup static files"
        exit 1
    fi
}

upload_to_s3() {
    local file=$1

    if [ "$S3_UPLOAD" = false ]; then
        return 0
    fi

    log_info "Uploading to S3..."

    if command -v aws &> /dev/null; then
        aws s3 cp "$file" "s3://$S3_BUCKET/media/$DATE_ONLY/" --storage-class STANDARD_IA
    else
        docker run --rm \
            -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" \
            -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" \
            -v "$BACKUP_DIR:/backups" \
            amazon/aws-cli \
            s3 cp "/backups/$(basename $file)" "s3://$S3_BUCKET/media/$DATE_ONLY/" \
            --storage-class STANDARD_IA
    fi
}

cleanup_old_backups() {
    log_info "Cleaning up backups older than $RETENTION_DAYS days..."
    find "$BACKUP_DIR" -name "*.tar.gz" -type f -mtime +$RETENTION_DAYS -delete
}

main() {
    echo "================================================================================"
    echo "Media Files Backup"
    echo "================================================================================"

    mkdir -p "$BACKUP_DIR"

    # Backup media
    media_backup=$(backup_media_files)
    [ "$S3_UPLOAD" = true ] && upload_to_s3 "$media_backup"

    # Backup static
    static_backup=$(backup_static_files)
    [ "$S3_UPLOAD" = true ] && upload_to_s3 "$static_backup"

    # Cleanup
    cleanup_old_backups

    log_info "Media backup complete!"
}

main
