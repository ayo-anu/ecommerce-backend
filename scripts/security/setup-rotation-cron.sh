#!/bin/bash
# ==============================================================================
# Setup Secrets Rotation Cron Job
# ==============================================================================
# This script sets up automated cron jobs for secrets rotation
#
# Usage:
#   ./scripts/security/setup-rotation-cron.sh [--remove]
#
# Options:
#   --remove    Remove existing cron job
#
# Schedule:
#   - Runs every Sunday at 2:00 AM
#   - Checks schedule and rotates appropriate secrets
#
# Prerequisites:
#   - rotate-secrets.sh must exist and be executable
#   - User must have permission to modify crontab
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
ROTATION_SCRIPT="${SCRIPT_DIR}/rotate-secrets.sh"
CRON_SCHEDULE="0 2 * * 0"  # Sunday at 2:00 AM
CRON_COMMENT="E-Commerce Platform - Automated Secrets Rotation"

# Check if rotation script exists
if [ ! -f "$ROTATION_SCRIPT" ]; then
    echo -e "${RED}Error: Rotation script not found at ${ROTATION_SCRIPT}${NC}"
    exit 1
fi

# Make sure rotation script is executable
chmod +x "$ROTATION_SCRIPT"

# Function to add cron job
add_cron() {
    echo -e "${BLUE}Setting up secrets rotation cron job...${NC}"

    # Check if cron job already exists
    if crontab -l 2>/dev/null | grep -F "$ROTATION_SCRIPT" > /dev/null; then
        echo -e "${YELLOW}Cron job already exists. Removing old entry...${NC}"
        crontab -l 2>/dev/null | grep -vF "$ROTATION_SCRIPT" | crontab -
    fi

    # Add new cron job with comment
    (
        crontab -l 2>/dev/null || true
        echo ""
        echo "# ${CRON_COMMENT}"
        echo "${CRON_SCHEDULE} ${ROTATION_SCRIPT} auto >> /var/log/ecommerce/rotation-cron.log 2>&1"
    ) | crontab -

    echo -e "${GREEN}Cron job installed successfully!${NC}"
    echo ""
    echo -e "${BLUE}Schedule:${NC}"
    echo "  - Every Sunday at 2:00 AM"
    echo "  - Automatic rotation based on schedule"
    echo ""
    echo -e "${BLUE}Logs:${NC}"
    echo "  - Application log: /var/log/ecommerce/secret-rotation.log"
    echo "  - Cron output: /var/log/ecommerce/rotation-cron.log"
    echo ""
    echo -e "${BLUE}Current crontab:${NC}"
    crontab -l | grep -A 1 "$CRON_COMMENT"
}

# Function to remove cron job
remove_cron() {
    echo -e "${BLUE}Removing secrets rotation cron job...${NC}"

    if ! crontab -l 2>/dev/null | grep -F "$ROTATION_SCRIPT" > /dev/null; then
        echo -e "${YELLOW}No cron job found for secrets rotation${NC}"
        exit 0
    fi

    # Remove cron job and its comment
    crontab -l 2>/dev/null \
        | grep -v "$CRON_COMMENT" \
        | grep -vF "$ROTATION_SCRIPT" \
        | crontab -

    echo -e "${GREEN}Cron job removed successfully${NC}"
}

# Main logic
main() {
    echo "============================================================"
    echo "  Secrets Rotation Cron Setup"
    echo "============================================================"
    echo ""

    # Check for --remove flag
    if [ "${1:-}" = "--remove" ]; then
        remove_cron
    else
        add_cron

        # Offer to verify cron service
        echo ""
        echo -e "${YELLOW}Verifying cron service...${NC}"
        if command -v systemctl &> /dev/null; then
            if systemctl is-active --quiet cron || systemctl is-active --quiet crond; then
                echo -e "${GREEN}Cron service is running${NC}"
            else
                echo -e "${RED}Warning: Cron service is not running${NC}"
                echo "Start it with: sudo systemctl start cron"
            fi
        else
            echo -e "${YELLOW}Cannot verify cron service (systemctl not available)${NC}"
        fi

        # Test run option
        echo ""
        echo -e "${BLUE}To test rotation manually:${NC}"
        echo "  ${ROTATION_SCRIPT} all"
        echo ""
        echo -e "${BLUE}To test rotation safely (dry run):${NC}"
        echo "  ${SCRIPT_DIR}/test-rotation.sh"
    fi

    echo ""
    echo "============================================================"
}

main "$@"
