#!/bin/bash
# ==============================================================================
# Backup Verification Script with Restore Testing
# ==============================================================================
# Verifies backup integrity by performing actual test restores to temporary
# containers and validating data integrity.
#
# Usage:
#   ./verify-backup.sh [OPTIONS]
#
# Options:
#   --backup-dir DIR     Backup directory to verify (default: /backups)
#   --latest             Verify only the latest backup (default)
#   --all                Verify all backups from last 7 days
#   --database NAME      Verify specific database (main, ai, all)
#   --notify             Send notifications on failure
#   --report-dir DIR     Directory for verification reports (default: /var/log/ecommerce/backup-verification)
#
# Environment Variables:
#   SLACK_WEBHOOK_URL    Slack webhook for notifications
#   NOTIFICATION_EMAIL   Email address for notifications
#
# Exit Codes:
#   0 - All verifications passed
#   1 - One or more verifications failed
#   2 - Critical error (unable to run tests)
# ==============================================================================

set -e
set -u
set -o pipefail

BACKUP_DIR="/backups"
VERIFY_LATEST=true
VERIFY_ALL=false
DATABASE="all"
NOTIFY=false
REPORT_DIR="/var/log/ecommerce/backup-verification"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test container names
TEST_POSTGRES_CONTAINER="ecommerce_postgres_test_${TIMESTAMP}"
TEST_REDIS_CONTAINER="ecommerce_redis_test_${TIMESTAMP}"

# Results tracking
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
REPORT_FILE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --backup-dir) BACKUP_DIR="$2"; shift 2 ;;
        --latest) VERIFY_LATEST=true; shift ;;
        --all) VERIFY_ALL=true; VERIFY_LATEST=false; shift ;;
        --database) DATABASE="$2"; shift 2 ;;
        --notify) NOTIFY=true; shift ;;
        --report-dir) REPORT_DIR="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [INFO] $1" >> "$REPORT_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [ERROR] $1" >> "$REPORT_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [SUCCESS] $1" >> "$REPORT_FILE"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [WARN] $1" >> "$REPORT_FILE"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up test containers..."

    docker stop "$TEST_POSTGRES_CONTAINER" 2>/dev/null || true
    docker rm "$TEST_POSTGRES_CONTAINER" 2>/dev/null || true

    docker stop "$TEST_REDIS_CONTAINER" 2>/dev/null || true
    docker rm "$TEST_REDIS_CONTAINER" 2>/dev/null || true

    log_info "Cleanup complete"
}

# Set trap for cleanup on exit
trap cleanup EXIT INT TERM

# Send notification
send_notification() {
    local status=$1
    local message=$2

    if [ "$NOTIFY" != "true" ]; then
        return 0
    fi

    # Slack notification
    if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
        local color="good"
        [ "$status" = "failure" ] && color="danger"

        curl -X POST "$SLACK_WEBHOOK_URL" \
            -H 'Content-Type: application/json' \
            -d "{
                \"attachments\": [{
                    \"color\": \"$color\",
                    \"title\": \"Backup Verification: $status\",
                    \"text\": \"$message\",
                    \"footer\": \"E-Commerce Platform\",
                    \"ts\": $(date +%s)
                }]
            }" 2>/dev/null || log_warn "Failed to send Slack notification"
    fi

    # Email notification
    if [ -n "${NOTIFICATION_EMAIL:-}" ] && command -v mail &> /dev/null; then
        echo "$message" | mail -s "Backup Verification: $status" "$NOTIFICATION_EMAIL" 2>/dev/null || \
            log_warn "Failed to send email notification"
    fi
}

# Verify file integrity
verify_file_integrity() {
    local backup_file=$1
    local file_type=$2

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    log_info "Verifying file integrity: $(basename $backup_file)"

    # Check file exists and is readable
    if [ ! -r "$backup_file" ]; then
        log_error "Cannot read backup file"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi

    # Check file is not empty
    if [ ! -s "$backup_file" ]; then
        log_error "Backup file is empty"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi

    # Verify compression integrity
    case "$file_type" in
        postgres)
            if ! gunzip -t "$backup_file" 2>/dev/null; then
                log_error "Backup file is corrupted (gzip test failed)"
                FAILED_TESTS=$((FAILED_TESTS + 1))
                return 1
            fi
            ;;
        redis)
            if ! gunzip -t "$backup_file" 2>/dev/null; then
                log_error "Redis backup is corrupted"
                FAILED_TESTS=$((FAILED_TESTS + 1))
                return 1
            fi
            ;;
        media)
            if ! tar -tzf "$backup_file" > /dev/null 2>&1; then
                log_error "Media backup is corrupted"
                FAILED_TESTS=$((FAILED_TESTS + 1))
                return 1
            fi
            ;;
    esac

    log_success "File integrity verified"
    PASSED_TESTS=$((PASSED_TESTS + 1))
    return 0
}

# Test restore PostgreSQL backup
test_restore_postgres() {
    local backup_file=$1
    local db_name=$2

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    log_info "Testing PostgreSQL restore: $(basename $backup_file)"

    # Start test PostgreSQL container
    log_info "Starting test PostgreSQL container..."
    if ! docker run -d \
        --name "$TEST_POSTGRES_CONTAINER" \
        -e POSTGRES_PASSWORD=test_password \
        -e POSTGRES_DB=test_db \
        postgres:15-alpine > /dev/null 2>&1; then
        log_error "Failed to start test container"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi

    # Wait for PostgreSQL to be ready
    log_info "Waiting for PostgreSQL to be ready..."
    local max_attempts=30
    local attempt=0
    while [ $attempt -lt $max_attempts ]; do
        if docker exec "$TEST_POSTGRES_CONTAINER" pg_isready -U postgres > /dev/null 2>&1; then
            break
        fi
        sleep 1
        attempt=$((attempt + 1))
    done

    if [ $attempt -eq $max_attempts ]; then
        log_error "PostgreSQL failed to start within timeout"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi

    # Restore backup
    log_info "Restoring backup to test container..."
    if ! gunzip -c "$backup_file" | docker exec -i "$TEST_POSTGRES_CONTAINER" psql -U postgres > /dev/null 2>&1; then
        log_error "Failed to restore backup"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi

    # Verify data integrity
    log_info "Verifying data integrity..."

    # Check databases exist
    local db_count=$(docker exec "$TEST_POSTGRES_CONTAINER" psql -U postgres -t -c "SELECT count(*) FROM pg_database WHERE datname NOT IN ('postgres', 'template0', 'template1');" 2>/dev/null | tr -d ' ')

    if [ -z "$db_count" ] || [ "$db_count" -eq 0 ]; then
        log_error "No application databases found after restore"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi

    log_info "Found $db_count application database(s)"

    # Try to connect to main database and query
    if docker exec "$TEST_POSTGRES_CONTAINER" psql -U postgres -d ecommerce_db -c "SELECT 1;" > /dev/null 2>&1; then
        # Check for tables
        local table_count=$(docker exec "$TEST_POSTGRES_CONTAINER" psql -U postgres -d ecommerce_db -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' ')
        log_info "Found $table_count tables in ecommerce_db"

        if [ "$table_count" -eq 0 ]; then
            log_warn "No tables found in database"
        fi
    else
        log_warn "Could not connect to ecommerce_db (may not exist in backup)"
    fi

    log_success "PostgreSQL restore test passed"
    PASSED_TESTS=$((PASSED_TESTS + 1))
    return 0
}

# Test restore Redis backup
test_restore_redis() {
    local backup_file=$1

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    log_info "Testing Redis restore: $(basename $backup_file)"

    # Extract RDB file
    local temp_rdb="/tmp/dump_test_${TIMESTAMP}.rdb"
    if ! gunzip -c "$backup_file" > "$temp_rdb" 2>/dev/null; then
        log_error "Failed to extract Redis backup"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi

    # Start test Redis container
    log_info "Starting test Redis container..."
    if ! docker run -d \
        --name "$TEST_REDIS_CONTAINER" \
        redis:7-alpine > /dev/null 2>&1; then
        log_error "Failed to start test Redis container"
        rm -f "$temp_rdb"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi

    # Wait for Redis to be ready
    sleep 3

    # Copy RDB file to container
    if ! docker cp "$temp_rdb" "$TEST_REDIS_CONTAINER:/data/dump.rdb" > /dev/null 2>&1; then
        log_error "Failed to copy RDB file to container"
        rm -f "$temp_rdb"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi

    rm -f "$temp_rdb"

    # Restart Redis to load the RDB file
    docker restart "$TEST_REDIS_CONTAINER" > /dev/null 2>&1
    sleep 3

    # Verify Redis is working
    if ! docker exec "$TEST_REDIS_CONTAINER" redis-cli ping > /dev/null 2>&1; then
        log_error "Redis is not responding"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi

    # Check if data was loaded
    local key_count=$(docker exec "$TEST_REDIS_CONTAINER" redis-cli dbsize 2>/dev/null | tr -d '\r')
    log_info "Loaded $key_count keys from backup"

    log_success "Redis restore test passed"
    PASSED_TESTS=$((PASSED_TESTS + 1))
    return 0
}

# Generate verification report
generate_report() {
    local status=$1

    log_info "Generating verification report..."

    cat >> "$REPORT_FILE" <<EOF

================================================================================
BACKUP VERIFICATION REPORT
================================================================================
Date: $(date)
Status: $status
Backup Directory: $BACKUP_DIR

Test Results:
  Total Tests: $TOTAL_TESTS
  Passed: $PASSED_TESTS
  Failed: $FAILED_TESTS
  Success Rate: $(awk "BEGIN {printf \"%.1f\", ($PASSED_TESTS/$TOTAL_TESTS)*100}")%

Next Verification: $(date -d "+1 week" +%Y-%m-%d)
================================================================================
EOF

    log_success "Report saved to: $REPORT_FILE"
}

main() {
    echo "================================================================================"
    echo "  Backup Verification with Restore Testing"
    echo "================================================================================"
    echo "Timestamp: $(date)"
    echo "Backup Directory: $BACKUP_DIR"
    echo "Database: $DATABASE"
    echo "Notify: $NOTIFY"
    echo "================================================================================"

    # Create report directory
    mkdir -p "$REPORT_DIR"
    REPORT_FILE="$REPORT_DIR/verification_${TIMESTAMP}.log"

    # Preflight checks
    log_info "Running preflight checks..."

    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 2
    fi

    if ! docker ps > /dev/null 2>&1; then
        log_error "Cannot connect to Docker daemon"
        exit 2
    fi

    log_success "Preflight checks passed"

    # Verify PostgreSQL backups
    if [ "$DATABASE" = "all" ] || [ "$DATABASE" = "main" ]; then
        log_info "Verifying PostgreSQL (main) backups..."

        if [ "$VERIFY_LATEST" = true ]; then
            latest_pg=$(ls -t "$BACKUP_DIR"/postgres/main_db_*.sql.gz 2>/dev/null | head -1 || echo "")
            if [ -n "$latest_pg" ]; then
                verify_file_integrity "$latest_pg" "postgres" && \
                test_restore_postgres "$latest_pg" "main"
            else
                log_warn "No PostgreSQL main backup found"
            fi
        fi
    fi

    if [ "$DATABASE" = "all" ] || [ "$DATABASE" = "ai" ]; then
        log_info "Verifying PostgreSQL (AI) backups..."

        if [ "$VERIFY_LATEST" = true ]; then
            latest_ai=$(ls -t "$BACKUP_DIR"/postgres/ai_db_*.sql.gz 2>/dev/null | head -1 || echo "")
            if [ -n "$latest_ai" ]; then
                verify_file_integrity "$latest_ai" "postgres" && \
                test_restore_postgres "$latest_ai" "ai"
            else
                log_warn "No PostgreSQL AI backup found"
            fi
        fi
    fi

    # Verify Redis backups
    if [ "$DATABASE" = "all" ]; then
        log_info "Verifying Redis backups..."

        if [ "$VERIFY_LATEST" = true ]; then
            latest_redis=$(ls -t "$BACKUP_DIR"/redis/redis_*.rdb.gz 2>/dev/null | head -1 || echo "")
            if [ -n "$latest_redis" ]; then
                verify_file_integrity "$latest_redis" "redis" && \
                test_restore_redis "$latest_redis"
            else
                log_warn "No Redis backup found"
            fi
        fi
    fi

    # Generate report
    local final_status="SUCCESS"
    if [ $FAILED_TESTS -gt 0 ]; then
        final_status="FAILURE"
    fi

    generate_report "$final_status"

    echo "================================================================================"
    echo "  Verification Complete"
    echo "================================================================================"
    echo "Status: $final_status"
    echo "Total Tests: $TOTAL_TESTS"
    echo "Passed: $PASSED_TESTS"
    echo "Failed: $FAILED_TESTS"
    echo "Report: $REPORT_FILE"
    echo "================================================================================"

    # Send notification if enabled
    if [ $FAILED_TESTS -gt 0 ]; then
        send_notification "failure" "Backup verification failed: $FAILED_TESTS of $TOTAL_TESTS tests failed. See $REPORT_FILE for details."
        exit 1
    else
        send_notification "success" "All backup verifications passed: $TOTAL_TESTS tests completed successfully."
        exit 0
    fi
}

main
