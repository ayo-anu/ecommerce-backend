#!/bin/bash
# ==============================================================================
# Setup Automated Backup Cron Jobs
# ==============================================================================
# Configures cron jobs for automated backups
#
# Usage:
#   sudo ./setup-cron.sh [OPTIONS]
#
# Options:
#   --user USER          User to run cron jobs as (default: current user)
#   --s3-bucket BUCKET   S3 bucket for backups
#   --enable-encryption  Enable GPG encryption
#
# Schedule:
#   - Database backups: Daily at 2:00 AM
#   - Media backups: Daily at 3:00 AM
#   - Verification: Weekly on Sunday at 4:00 AM
# ==============================================================================

set -e
set -u

# Configuration
CRON_USER="${SUDO_USER:-$USER}"
S3_BUCKET=""
ENABLE_ENCRYPTION=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --user) CRON_USER="$2"; shift 2 ;;
        --s3-bucket) S3_BUCKET="$2"; shift 2 ;;
        --enable-encryption) ENABLE_ENCRYPTION=true; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

echo "================================================================================"
echo "Setting up automated backups"
echo "User: $CRON_USER"
echo "S3 Bucket: ${S3_BUCKET:-Not configured}"
echo "Encryption: $ENABLE_ENCRYPTION"
echo "================================================================================"

# Build backup command options
DB_BACKUP_OPTS="--retention-days 7"
MEDIA_BACKUP_OPTS="--retention-days 30"

if [ -n "$S3_BUCKET" ]; then
    DB_BACKUP_OPTS="$DB_BACKUP_OPTS --s3-upload --s3-bucket $S3_BUCKET"
    MEDIA_BACKUP_OPTS="$MEDIA_BACKUP_OPTS --s3-upload --s3-bucket $S3_BUCKET"
fi

if [ "$ENABLE_ENCRYPTION" = true ]; then
    DB_BACKUP_OPTS="$DB_BACKUP_OPTS --encrypt"
fi

# Create cron jobs
CRON_JOBS=$(cat <<EOF
# E-Commerce Platform Automated Backups
# Generated on: $(date)

# Database backups - Daily at 2:00 AM
0 2 * * * $SCRIPT_DIR/backup-databases.sh $DB_BACKUP_OPTS >> /var/log/backup-db.log 2>&1

# Media backups - Daily at 3:00 AM
0 3 * * * $SCRIPT_DIR/backup-media.sh $MEDIA_BACKUP_OPTS >> /var/log/backup-media.log 2>&1

# Backup verification - Weekly on Sunday at 4:00 AM
0 4 * * 0 $SCRIPT_DIR/verify-backup.sh >> /var/log/backup-verify.log 2>&1
EOF
)

# Install cron jobs
echo "$CRON_JOBS" | crontab -u "$CRON_USER" -

echo "Cron jobs installed successfully!"
echo ""
echo "Scheduled tasks:"
echo "  - Database backup: Daily at 2:00 AM"
echo "  - Media backup: Daily at 3:00 AM"
echo "  - Verification: Weekly on Sunday at 4:00 AM"
echo ""
echo "View cron jobs: crontab -u $CRON_USER -l"
echo "View logs:"
echo "  - Database: /var/log/backup-db.log"
echo "  - Media: /var/log/backup-media.log"
echo "  - Verification: /var/log/backup-verify.log"
echo "================================================================================"
