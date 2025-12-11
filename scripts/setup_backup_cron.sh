#!/bin/bash
# ==============================================================================
# Setup Automated Backup Cron Job
# ==============================================================================
# This script configures automated database backups using cron
#
# Usage:
#   ./scripts/setup_backup_cron.sh [OPTIONS]
#
# Options:
#   --daily         Run backups daily at 2 AM (default)
#   --hourly        Run backups every hour
#   --custom CRON   Use custom cron schedule (e.g., "0 */6 * * *")
#   --s3            Enable S3 uploads for backups
# ==============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default configuration
SCHEDULE="daily"
CRON_SCHEDULE="0 2 * * *"  # 2 AM daily
ENABLE_S3=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --daily)
            SCHEDULE="daily"
            CRON_SCHEDULE="0 2 * * *"
            shift
            ;;
        --hourly)
            SCHEDULE="hourly"
            CRON_SCHEDULE="0 * * * *"
            shift
            ;;
        --custom)
            SCHEDULE="custom"
            CRON_SCHEDULE="$2"
            shift 2
            ;;
        --s3)
            ENABLE_S3=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Get absolute path to project
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo -e "${BLUE}===================================================================${NC}"
echo -e "${BLUE}Automated Backup Setup${NC}"
echo -e "${BLUE}===================================================================${NC}"
echo ""
echo -e "Project directory: ${GREEN}$PROJECT_DIR${NC}"
echo -e "Schedule: ${GREEN}$SCHEDULE${NC}"
echo -e "Cron expression: ${GREEN}$CRON_SCHEDULE${NC}"
echo -e "S3 upload: ${GREEN}$([ "$ENABLE_S3" = true ] && echo "Enabled" || echo "Disabled")${NC}"
echo ""

# Make backup scripts executable
chmod +x "$PROJECT_DIR/scripts/backup_databases.sh"
chmod +x "$PROJECT_DIR/scripts/restore_database.sh"

# Create backup wrapper script
BACKUP_WRAPPER="$PROJECT_DIR/scripts/run_backup.sh"

cat > "$BACKUP_WRAPPER" << EOF
#!/bin/bash
# Auto-generated backup wrapper script

cd "$PROJECT_DIR"

# Load environment variables if .env exists
if [ -f "infrastructure/env/.env.production" ]; then
    set -a
    source infrastructure/env/.env.production
    set +a
fi

# Run backup with options
BACKUP_OPTIONS="--all --retain 30"
$([ "$ENABLE_S3" = true ] && echo 'BACKUP_OPTIONS="$BACKUP_OPTIONS --s3"')

./scripts/backup_databases.sh \$BACKUP_OPTIONS >> /var/log/ecommerce_backup.log 2>&1

# Check backup status
if [ \$? -eq 0 ]; then
    echo "\$(date): Backup completed successfully" >> /var/log/ecommerce_backup.log
else
    echo "\$(date): Backup failed" >> /var/log/ecommerce_backup.log
    # Send alert (optional - implement your notification method)
fi
EOF

chmod +x "$BACKUP_WRAPPER"

echo -e "${GREEN}✓ Backup wrapper script created${NC}"
echo ""

# Create log directory
sudo mkdir -p /var/log
sudo touch /var/log/ecommerce_backup.log
sudo chmod 666 /var/log/ecommerce_backup.log

echo -e "${GREEN}✓ Log file created: /var/log/ecommerce_backup.log${NC}"
echo ""

# Add cron job
CRON_COMMAND="$CRON_SCHEDULE $BACKUP_WRAPPER"

# Check if cron job already exists
(crontab -l 2>/dev/null | grep -v "$BACKUP_WRAPPER"; echo "$CRON_COMMAND") | crontab -

echo -e "${GREEN}✓ Cron job added${NC}"
echo ""

# Display current crontab
echo -e "${BLUE}Current cron jobs:${NC}"
crontab -l | grep -v "^#" | grep -v "^$" || echo "None"
echo ""

# Summary
echo -e "${BLUE}===================================================================${NC}"
echo -e "${GREEN}Automated Backup Setup Complete!${NC}"
echo -e "${BLUE}===================================================================${NC}"
echo ""
echo -e "Backups will run: ${GREEN}$SCHEDULE${NC}"
echo -e "Next backup: ${GREEN}$(date -d "$(echo "$CRON_SCHEDULE" | awk '{print $2":"$1}')" 2>/dev/null || echo "See cron schedule")${NC}"
echo ""
echo -e "To view backup logs:"
echo -e "  ${BLUE}tail -f /var/log/ecommerce_backup.log${NC}"
echo ""
echo -e "To manually run a backup:"
echo -e "  ${BLUE}./scripts/backup_databases.sh${NC}"
echo ""
echo -e "To remove automated backups:"
echo -e "  ${BLUE}crontab -e${NC} (and remove the line with run_backup.sh)"
echo ""
