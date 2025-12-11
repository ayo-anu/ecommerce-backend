#!/bin/bash
# ==============================================================================
# Database Restore Script
# ==============================================================================
# This script restores PostgreSQL databases from backup files
#
# Usage:
#   ./scripts/restore_database.sh <backup_file> [OPTIONS]
#
# Options:
#   --main          Restore to main database (default)
#   --ai            Restore to AI database
#   --confirm       Skip confirmation prompt (use with caution!)
#
# Examples:
#   ./scripts/restore_database.sh backups/databases/main_db_20250128_120000.sql.gz
#   ./scripts/restore_database.sh backups/databases/ai_db_20250128_120000.sql.gz --ai
# ==============================================================================

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check arguments
if [ $# -lt 1 ]; then
    echo -e "${RED}Error: Backup file not specified${NC}"
    echo "Usage: $0 <backup_file> [--main|--ai] [--confirm]"
    exit 1
fi

BACKUP_FILE=$1
shift

# Configuration
POSTGRES_CONTAINER="ecommerce_postgres"
POSTGRES_AI_CONTAINER="ecommerce_postgres_ai"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-ecommerce}"
POSTGRES_AI_DB="${POSTGRES_AI_DB:-ecommerce_ai}"

# Parse options
RESTORE_TO="main"
SKIP_CONFIRM=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --main)
            RESTORE_TO="main"
            shift
            ;;
        --ai)
            RESTORE_TO="ai"
            shift
            ;;
        --confirm)
            SKIP_CONFIRM=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Determine target database
if [ "$RESTORE_TO" = "ai" ]; then
    CONTAINER=$POSTGRES_AI_CONTAINER
    DATABASE=$POSTGRES_AI_DB
    DB_NAME="AI Database"
else
    CONTAINER=$POSTGRES_CONTAINER
    DATABASE=$POSTGRES_DB
    DB_NAME="Main Database"
fi

# Banner
echo -e "${BLUE}===================================================================${NC}"
echo -e "${BLUE}Database Restore Script${NC}"
echo -e "${BLUE}===================================================================${NC}"
echo ""

# Verify backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}Error: Backup file not found: $BACKUP_FILE${NC}"
    exit 1
fi

# Check if container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
    echo -e "${RED}Error: Container ${CONTAINER} is not running${NC}"
    echo "Start the services first: make dev"
    exit 1
fi

# Display restore information
echo -e "Backup file: ${GREEN}$BACKUP_FILE${NC}"
echo -e "Target database: ${GREEN}$DB_NAME ($DATABASE)${NC}"
echo -e "Container: ${GREEN}$CONTAINER${NC}"
echo ""

# Get backup file size and date
BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
BACKUP_DATE=$(stat -c %y "$BACKUP_FILE" 2>/dev/null || stat -f %Sm "$BACKUP_FILE" 2>/dev/null || echo "Unknown")
echo -e "Backup size: $BACKUP_SIZE"
echo -e "Backup date: $BACKUP_DATE"
echo ""

# Warning
echo -e "${YELLOW}⚠️  WARNING ⚠️${NC}"
echo -e "${RED}This will REPLACE all data in the ${DB_NAME}!${NC}"
echo -e "${RED}All existing data will be permanently deleted!${NC}"
echo ""

# Confirmation
if [ "$SKIP_CONFIRM" = false ]; then
    read -p "Are you absolutely sure you want to continue? (type 'yes' to confirm): " confirmation
    if [ "$confirmation" != "yes" ]; then
        echo -e "${YELLOW}Restore cancelled${NC}"
        exit 0
    fi
fi

echo ""
echo -e "${BLUE}Starting restore process...${NC}"
echo ""

# Step 1: Create a safety backup of current database
echo -e "${BLUE}Step 1: Creating safety backup of current database...${NC}"
SAFETY_BACKUP="/tmp/${DATABASE}_pre_restore_$(date +%Y%m%d_%H%M%S).sql"
docker exec -t "$CONTAINER" pg_dump -U "$POSTGRES_USER" "$DATABASE" > "$SAFETY_BACKUP"
gzip "$SAFETY_BACKUP"
echo -e "${GREEN}✓ Safety backup created: ${SAFETY_BACKUP}.gz${NC}"
echo ""

# Step 2: Terminate all connections to database
echo -e "${BLUE}Step 2: Terminating all connections to database...${NC}"
docker exec -t "$CONTAINER" psql -U "$POSTGRES_USER" -d postgres -c \
    "SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity
     WHERE pg_stat_activity.datname = '$DATABASE' AND pid <> pg_backend_pid();" > /dev/null 2>&1 || true
echo -e "${GREEN}✓ Connections terminated${NC}"
echo ""

# Step 3: Drop and recreate database
echo -e "${BLUE}Step 3: Recreating database...${NC}"
docker exec -t "$CONTAINER" psql -U "$POSTGRES_USER" -d postgres -c "DROP DATABASE IF EXISTS $DATABASE;" > /dev/null
docker exec -t "$CONTAINER" psql -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE $DATABASE;" > /dev/null
echo -e "${GREEN}✓ Database recreated${NC}"
echo ""

# Step 4: Restore from backup
echo -e "${BLUE}Step 4: Restoring from backup...${NC}"

# Check if backup is compressed
if [[ "$BACKUP_FILE" == *.gz ]]; then
    echo "Decompressing and restoring..."
    gunzip -c "$BACKUP_FILE" | docker exec -i "$CONTAINER" psql -U "$POSTGRES_USER" -d "$DATABASE"
else
    echo "Restoring..."
    cat "$BACKUP_FILE" | docker exec -i "$CONTAINER" psql -U "$POSTGRES_USER" -d "$DATABASE"
fi

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Database restored successfully${NC}"
else
    echo -e "${RED}Error: Restore failed${NC}"
    echo ""
    echo -e "${YELLOW}Attempting to restore from safety backup...${NC}"
    gunzip -c "${SAFETY_BACKUP}.gz" | docker exec -i "$CONTAINER" psql -U "$POSTGRES_USER" -d "$DATABASE"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Original database restored from safety backup${NC}"
    fi
    exit 1
fi
echo ""

# Step 5: Verify restore
echo -e "${BLUE}Step 5: Verifying restore...${NC}"
TABLE_COUNT=$(docker exec -t "$CONTAINER" psql -U "$POSTGRES_USER" -d "$DATABASE" -t -c \
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")
echo -e "Tables in database: ${GREEN}${TABLE_COUNT}${NC}"

if [ "$TABLE_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ Verification passed${NC}"
else
    echo -e "${YELLOW}Warning: No tables found in database${NC}"
fi
echo ""

# Summary
echo -e "${BLUE}===================================================================${NC}"
echo -e "${GREEN}Restore Complete!${NC}"
echo -e "${BLUE}===================================================================${NC}"
echo ""
echo -e "Database: ${GREEN}$DB_NAME${NC}"
echo -e "Tables restored: ${GREEN}${TABLE_COUNT}${NC}"
echo ""
echo -e "Safety backup retained at:"
echo -e "  ${BLUE}${SAFETY_BACKUP}.gz${NC}"
echo ""
echo -e "${YELLOW}Note: You may need to restart your application services${NC}"
echo -e "Run: ${BLUE}make restart${NC}"
echo ""
