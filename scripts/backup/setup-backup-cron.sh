#!/bin/bash
# ==============================================================================
# Setup Automated Backup and Verification Cron Jobs
# ==============================================================================
# This script configures automated backup and verification tasks
#
# Usage:
#   sudo ./setup-backup-cron.sh [OPTIONS]
#
# Options:
#   --s3-bucket BUCKET   S3 bucket for backups (required)
#   --notify-email EMAIL Email for notifications
#   --slack-webhook URL  Slack webhook URL for notifications
#   --uninstall          Remove all backup cron jobs
#
# Requirements:
#   - Must be run as root
#   - Docker must be installed
#   - AWS CLI must be configured (for S3 backups)
# ==============================================================================

set -e
set -u
set -o pipefail

# Default values
S3_BUCKET=""
NOTIFY_EMAIL=""
SLACK_WEBHOOK=""
UNINSTALL=false
PROJECT_ROOT="/opt/ecommerce-platform"
CRON_FILE="/etc/cron.d/ecommerce-backups"
LOG_DIR="/var/log/ecommerce"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --s3-bucket) S3_BUCKET="$2"; shift 2 ;;
        --notify-email) NOTIFY_EMAIL="$2"; shift 2 ;;
        --slack-webhook) SLACK_WEBHOOK="$2"; shift 2 ;;
        --uninstall) UNINSTALL=true; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    log_error "This script must be run as root"
    log_info "Please run: sudo $0"
    exit 1
fi

# Uninstall cron jobs
uninstall_cron() {
    log_info "Removing backup cron jobs..."

    if [ -f "$CRON_FILE" ]; then
        rm -f "$CRON_FILE"
        log_success "Cron file removed: $CRON_FILE"
    else
        log_warn "Cron file not found: $CRON_FILE"
    fi

    # Restart cron service
    if command -v systemctl &> /dev/null; then
        systemctl restart cron 2>/dev/null || systemctl restart cronie 2>/dev/null || true
    fi

    log_success "Backup cron jobs uninstalled"
    exit 0
}

# Validate requirements
validate_requirements() {
    log_info "Validating requirements..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi

    if ! docker ps > /dev/null 2>&1; then
        log_error "Cannot connect to Docker daemon"
        exit 1
    fi

    # Check project directory
    if [ ! -d "$PROJECT_ROOT" ]; then
        log_warn "Project directory not found at $PROJECT_ROOT"
        log_info "Detecting current directory..."
        SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
        log_info "Using project root: $PROJECT_ROOT"
    fi

    # Check backup scripts exist
    if [ ! -f "$PROJECT_ROOT/scripts/backup/backup-databases.sh" ]; then
        log_error "Backup script not found: $PROJECT_ROOT/scripts/backup/backup-databases.sh"
        exit 1
    fi

    if [ ! -f "$PROJECT_ROOT/scripts/backup/verify-backup.sh" ]; then
        log_error "Verification script not found: $PROJECT_ROOT/scripts/backup/verify-backup.sh"
        exit 1
    fi

    # Check AWS CLI for S3 backups
    if [ -n "$S3_BUCKET" ]; then
        if ! command -v aws &> /dev/null; then
            log_error "AWS CLI is not installed (required for S3 backups)"
            exit 1
        fi

        # Test AWS credentials
        if ! aws s3 ls > /dev/null 2>&1; then
            log_error "AWS CLI is not configured properly"
            log_info "Run: aws configure"
            exit 1
        fi
    fi

    log_success "All requirements validated"
}

# Create log directory
setup_logging() {
    log_info "Setting up logging directory..."

    mkdir -p "$LOG_DIR"
    mkdir -p "$LOG_DIR/backup-verification"

    # Set permissions
    chmod 755 "$LOG_DIR"
    chmod 755 "$LOG_DIR/backup-verification"

    log_success "Logging configured at: $LOG_DIR"
}

# Install cron jobs
install_cron() {
    log_info "Installing backup cron jobs..."

    # Build environment variables for cron
    local env_vars=""
    if [ -n "$NOTIFY_EMAIL" ]; then
        env_vars="${env_vars}NOTIFICATION_EMAIL=\"$NOTIFY_EMAIL\"\n"
    fi
    if [ -n "$SLACK_WEBHOOK" ]; then
        env_vars="${env_vars}SLACK_WEBHOOK_URL=\"$SLACK_WEBHOOK\"\n"
    fi

    # Build S3 upload flag
    local s3_flag=""
    if [ -n "$S3_BUCKET" ]; then
        s3_flag="--s3-upload --s3-bucket $S3_BUCKET"
    fi

    # Create cron file
    cat > "$CRON_FILE" << EOF
# ==============================================================================
# E-Commerce Platform - Automated Backup and Verification
# ==============================================================================
# Generated on: $(date)
# Project: $PROJECT_ROOT
# S3 Bucket: ${S3_BUCKET:-Not configured}
# ==============================================================================

SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
${env_vars}

# PostgreSQL backup every 6 hours (00:00, 06:00, 12:00, 18:00)
0 */6 * * * root $PROJECT_ROOT/scripts/backup/backup-databases.sh $s3_flag >> $LOG_DIR/backup.log 2>&1

# Redis backup daily at 04:00 AM
0 4 * * * root $PROJECT_ROOT/scripts/backup/backup-redis.sh $s3_flag >> $LOG_DIR/backup.log 2>&1 || true

# Media files backup daily at 02:00 AM
0 2 * * * root $PROJECT_ROOT/scripts/backup/backup-media.sh $s3_flag >> $LOG_DIR/backup.log 2>&1 || true

# Backup verification every Sunday at 03:00 AM (weekly restore tests)
0 3 * * 0 root $PROJECT_ROOT/scripts/backup/verify-backup.sh --latest --notify >> $LOG_DIR/backup-verification.log 2>&1

# Cleanup old verification reports (keep last 30 days)
0 5 1 * * root find $LOG_DIR/backup-verification -name "verification_*.log" -mtime +30 -delete

# Health check: Verify backups exist (daily at 08:00 AM)
0 8 * * * root [ -d /backups/postgres ] && find /backups/postgres -name "*.sql.gz" -mtime -1 | grep -q . || echo "WARNING: No recent PostgreSQL backups found" >> $LOG_DIR/backup.log

EOF

    # Set proper permissions
    chmod 644 "$CRON_FILE"

    log_success "Cron file created: $CRON_FILE"
}

# Restart cron service
restart_cron() {
    log_info "Restarting cron service..."

    if command -v systemctl &> /dev/null; then
        systemctl restart cron 2>/dev/null || systemctl restart cronie 2>/dev/null || {
            log_warn "Could not restart cron service automatically"
            log_info "Please restart cron manually: sudo systemctl restart cron"
            return 1
        }
    else
        log_warn "systemctl not found - cron service may need manual restart"
        return 1
    fi

    log_success "Cron service restarted"
}

# Display cron schedule
display_schedule() {
    log_info "Backup Schedule:"
    echo ""
    echo "  PostgreSQL Backups:  Every 6 hours (00:00, 06:00, 12:00, 18:00)"
    echo "  Redis Backups:       Daily at 04:00 AM"
    echo "  Media Backups:       Daily at 02:00 AM"
    echo "  Verification Tests:  Weekly on Sunday at 03:00 AM"
    echo "  Health Checks:       Daily at 08:00 AM"
    echo ""
    echo "  Log File:            $LOG_DIR/backup.log"
    echo "  Verification Logs:   $LOG_DIR/backup-verification.log"
    echo "  Verification Reports: $LOG_DIR/backup-verification/"
    echo ""
    if [ -n "$S3_BUCKET" ]; then
        echo "  S3 Bucket:           s3://$S3_BUCKET"
    fi
    if [ -n "$NOTIFY_EMAIL" ]; then
        echo "  Email Notifications: $NOTIFY_EMAIL"
    fi
    if [ -n "$SLACK_WEBHOOK" ]; then
        echo "  Slack Notifications: Enabled"
    fi
    echo ""
}

# Test backup script
test_backup() {
    log_info "Testing backup script (dry run)..."

    if $PROJECT_ROOT/scripts/backup/backup-databases.sh --help > /dev/null 2>&1; then
        log_success "Backup script is working"
    else
        log_warn "Backup script test returned non-zero exit code"
    fi
}

main() {
    echo "================================================================================"
    echo "  E-Commerce Platform - Backup Automation Setup"
    echo "================================================================================"

    # Handle uninstall
    if [ "$UNINSTALL" = true ]; then
        uninstall_cron
        exit 0
    fi

    # Check S3 bucket is provided
    if [ -z "$S3_BUCKET" ]; then
        log_warn "No S3 bucket specified - backups will only be stored locally"
        log_info "For offsite backups, use: --s3-bucket your-bucket-name"
        echo ""
        read -p "Continue without S3 backups? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Setup cancelled"
            exit 0
        fi
    fi

    # Validate requirements
    validate_requirements

    # Setup logging
    setup_logging

    # Install cron jobs
    install_cron

    # Restart cron service
    restart_cron

    # Test backup script
    test_backup

    # Display schedule
    echo "================================================================================"
    log_success "Backup automation installed successfully!"
    echo "================================================================================"
    display_schedule

    echo "================================================================================"
    log_info "Next Steps:"
    echo ""
    echo "  1. Verify cron jobs: sudo crontab -l"
    echo "  2. Check cron file:  cat $CRON_FILE"
    echo "  3. Monitor logs:     tail -f $LOG_DIR/backup.log"
    echo "  4. Test backup now:  sudo $PROJECT_ROOT/scripts/backup/backup-databases.sh"
    echo "  5. Test verification: sudo $PROJECT_ROOT/scripts/backup/verify-backup.sh --latest"
    echo ""
    echo "  To remove cron jobs: sudo $0 --uninstall"
    echo "================================================================================"
}

main
