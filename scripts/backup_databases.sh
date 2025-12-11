#!/bin/bash
# ==============================================================================
# Database Backup Script
# ==============================================================================
# This script creates automated backups of PostgreSQL databases with:
# - Timestamped backup files
# - Compression to save space
# - Rotation to manage old backups
# - Support for both main and AI databases
# - Verification of backup integrity
# - Optional upload to S3 or remote storage
#
# Usage:
#   ./scripts/backup_databases.sh [OPTIONS]
#
# Options:
#   --all           Backup all databases (default)
#   --main          Backup only main database
#   --ai            Backup only AI database
#   --retain DAYS   Number of days to retain backups (default: 30)
#   --s3            Upload to S3 bucket (requires AWS CLI)
#   --verify        Verify backup integrity after creation
# ==============================================================================

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups/databases}"
RETAIN_DAYS="${RETAIN_DAYS:-30}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DATE_PREFIX=$(date +%Y-%m-%d)

# Database configuration
POSTGRES_CONTAINER="ecommerce_postgres"
POSTGRES_AI_CONTAINER="ecommerce_postgres_ai"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-ecommerce}"
POSTGRES_AI_DB="${POSTGRES_AI_DB:-ecommerce_ai}"

# Parse command line arguments
BACKUP_MAIN=true
BACKUP_AI=true
UPLOAD_S3=false
VERIFY_BACKUP=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --main)
            BACKUP_AI=false
            shift
            ;;
        --ai)
            BACKUP_MAIN=false
            shift
            ;;
        --retain)
            RETAIN_DAYS="$2"
            shift 2
            ;;
        --s3)
            UPLOAD_S3=true
            shift
            ;;
        --verify)
            VERIFY_BACKUP=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Banner
echo -e "${BLUE}===================================================================${NC}"
echo -e "${BLUE}Database Backup Script${NC}"
echo -e "${BLUE}===================================================================${NC}"
echo -e "Timestamp: ${DATE_PREFIX} ${TIMESTAMP}"
echo -e "Backup directory: ${BACKUP_DIR}"
echo -e "Retention period: ${RETAIN_DAYS} days"
echo ""

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Function to backup a database
backup_database() {
    local container=$1
    local database=$2
    local backup_name=$3

    echo -e "${BLUE}Backing up ${database}...${NC}"

    # Create backup filename
    local backup_file="${BACKUP_DIR}/${backup_name}_${TIMESTAMP}.sql"
    local compressed_file="${backup_file}.gz"

    # Check if container is running
    if ! docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        echo -e "${RED}Error: Container ${container} is not running${NC}"
        return 1
    fi

    # Perform backup
    echo "  Creating backup..."
    docker exec -t "$container" pg_dump -U "$POSTGRES_USER" "$database" > "$backup_file"

    if [ $? -ne 0 ]; then
        echo -e "${RED}  Error: Backup failed${NC}"
        rm -f "$backup_file"
        return 1
    fi

    # Compress backup
    echo "  Compressing backup..."
    gzip "$backup_file"

    # Get file size
    local size=$(du -h "$compressed_file" | cut -f1)
    echo -e "${GREEN}  ✓ Backup created: $compressed_file ($size)${NC}"

    # Verify backup if requested
    if [ "$VERIFY_BACKUP" = true ]; then
        echo "  Verifying backup integrity..."
        gunzip -t "$compressed_file"
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}  ✓ Backup verification passed${NC}"
        else
            echo -e "${RED}  Error: Backup verification failed${NC}"
            return 1
        fi
    fi

    # Upload to S3 if requested
    if [ "$UPLOAD_S3" = true ]; then
        upload_to_s3 "$compressed_file" "$backup_name"
    fi

    return 0
}

# Function to upload to S3
upload_to_s3() {
    local file=$1
    local prefix=$2

    if ! command -v aws &> /dev/null; then
        echo -e "${YELLOW}  Warning: AWS CLI not installed, skipping S3 upload${NC}"
        return 1
    fi

    local s3_bucket="${AWS_BACKUP_BUCKET:-ecommerce-backups}"
    local s3_path="s3://${s3_bucket}/databases/${prefix}/$(basename $file)"

    echo "  Uploading to S3: $s3_path"
    aws s3 cp "$file" "$s3_path" --storage-class STANDARD_IA

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}  ✓ Uploaded to S3${NC}"
    else
        echo -e "${YELLOW}  Warning: S3 upload failed${NC}"
    fi
}

# Function to cleanup old backups
cleanup_old_backups() {
    echo -e "${BLUE}Cleaning up backups older than ${RETAIN_DAYS} days...${NC}"

    local deleted_count=0
    while IFS= read -r -d '' file; do
        rm -f "$file"
        deleted_count=$((deleted_count + 1))
        echo "  Deleted: $(basename $file)"
    done < <(find "$BACKUP_DIR" -name "*.sql.gz" -type f -mtime +${RETAIN_DAYS} -print0)

    if [ $deleted_count -eq 0 ]; then
        echo -e "${GREEN}  No old backups to clean up${NC}"
    else
        echo -e "${GREEN}  ✓ Deleted $deleted_count old backup(s)${NC}"
    fi
}

# Backup main database
if [ "$BACKUP_MAIN" = true ]; then
    backup_database "$POSTGRES_CONTAINER" "$POSTGRES_DB" "main_db"
    echo ""
fi

# Backup AI database
if [ "$BACKUP_AI" = true ]; then
    backup_database "$POSTGRES_AI_CONTAINER" "$POSTGRES_AI_DB" "ai_db"
    echo ""
fi

# Cleanup old backups
cleanup_old_backups
echo ""

# Summary
echo -e "${BLUE}===================================================================${NC}"
echo -e "${GREEN}Backup Complete!${NC}"
echo -e "${BLUE}===================================================================${NC}"
echo ""
echo -e "Backup location: ${BACKUP_DIR}"
echo ""
echo -e "To restore a backup:"
echo -e "  ${BLUE}./scripts/restore_database.sh <backup_file>${NC}"
echo ""
echo -e "To list backups:"
echo -e "  ${BLUE}ls -lh ${BACKUP_DIR}${NC}"
echo ""
