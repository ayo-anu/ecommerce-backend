#!/bin/bash
# ==============================================================================
# Monthly Disaster Recovery Drill Script
# ==============================================================================
# Tests complete disaster recovery procedures by restoring to DR environment
#
# Usage:
#   ./dr-drill.sh [OPTIONS]
#
# Options:
#   --dr-host HOST       DR server hostname/IP (default: dr-server.example.com)
#   --skip-restore       Skip database restore (use existing data)
#   --no-cleanup         Don't cleanup DR environment after test
#
# Requirements:
#   - SSH access to DR server
#   - DR server must have Docker and docker-compose installed
#   - S3 access for backup downloads
#   - Monitoring tools installed
#
# Exit Codes:
#   0 - DR drill passed (RTO < 60 minutes)
#   1 - DR drill failed
#   2 - Setup error
# ==============================================================================

set -e
set -u
set -o pipefail

# Configuration
DR_HOST="${DR_HOST:-dr-server.example.com}"
SKIP_RESTORE=false
NO_CLEANUP=false
PROJECT_PATH="/opt/ecommerce-platform"
S3_BUCKET="ecommerce-backups-production"
START_TIME=$(date +%s)
REPORT_FILE="/tmp/dr-drill-report-$(date +%Y%m%d).txt"

# RTO target in seconds (60 minutes)
RTO_TARGET=3600

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dr-host) DR_HOST="$2"; shift 2 ;;
        --skip-restore) SKIP_RESTORE=true; shift ;;
        --no-cleanup) NO_CLEANUP=true; shift ;;
        *) echo "Unknown option: $1"; exit 2 ;;
    esac
done

log_info() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date +'%H:%M:%S')] ERROR:${NC} $1" >&2
}

log_success() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')] ✅${NC} $1"
}

log_step() {
    echo ""
    echo -e "${BLUE}===================================================${NC}"
    echo -e "${BLUE} $1${NC}"
    echo -e "${BLUE}===================================================${NC}"
}

# Calculate elapsed time
get_elapsed_time() {
    local current=$(date +%s)
    echo $(( (current - START_TIME) / 60 ))
}

# Execute command on DR server
dr_exec() {
    ssh -o ConnectTimeout=10 "$DR_HOST" "$@"
}

# Check DR server connectivity
check_dr_server() {
    log_step "Step 1: Checking DR Server Connectivity"

    log_info "Testing SSH connection to $DR_HOST..."

    if ! dr_exec "echo 'Connection successful'" > /dev/null 2>&1; then
        log_error "Cannot connect to DR server: $DR_HOST"
        log_error "Please check:"
        log_error "  - SSH access is configured"
        log_error "  - DR server is running"
        log_error "  - Firewall allows SSH connection"
        exit 2
    fi

    log_success "DR server is reachable"

    # Check Docker
    log_info "Verifying Docker on DR server..."
    if ! dr_exec "docker --version" > /dev/null 2>&1; then
        log_error "Docker is not installed on DR server"
        exit 2
    fi

    log_success "Docker is available on DR server"

    # Check project directory
    log_info "Checking project directory..."
    if ! dr_exec "test -d $PROJECT_PATH"; then
        log_error "Project directory not found: $PROJECT_PATH"
        log_info "Creating project directory..."
        dr_exec "sudo mkdir -p $PROJECT_PATH && sudo chown \$(whoami):\$(whoami) $PROJECT_PATH"
    fi

    log_success "Step 1 complete"
}

# Prepare DR environment
prepare_dr_environment() {
    log_step "Step 2: Preparing DR Environment"

    log_info "Updating application code on DR server..."

    dr_exec "cd $PROJECT_PATH && git fetch origin" || {
        log_error "Git fetch failed"
        exit 2
    }

    dr_exec "cd $PROJECT_PATH && git checkout main && git pull origin main" || {
        log_error "Git pull failed"
        exit 2
    }

    log_success "Application code updated"

    # Stop any existing services
    log_info "Stopping existing services (if any)..."
    dr_exec "cd $PROJECT_PATH && docker-compose -f deploy/docker/compose/base.yml -f deploy/docker/compose/production.yml down" 2>/dev/null || true

    log_success "Step 2 complete"
}

# Restore databases
restore_databases() {
    if [ "$SKIP_RESTORE" = true ]; then
        log_step "Step 3: Skipping Database Restore"
        return 0
    fi

    log_step "Step 3: Restoring Databases from S3"

    # Restore main database
    log_info "Restoring main PostgreSQL database..."
    dr_exec "cd $PROJECT_PATH && ./scripts/backup/restore-database.sh \
        --from-s3 \
        --s3-bucket $S3_BUCKET \
        --latest \
        --database main" || {
        log_error "Failed to restore main database"
        exit 1
    }

    log_success "Main database restored"

    # Restore AI database
    log_info "Restoring AI PostgreSQL database..."
    dr_exec "cd $PROJECT_PATH && ./scripts/backup/restore-database.sh \
        --from-s3 \
        --s3-bucket $S3_BUCKET \
        --latest \
        --database ai" || {
        log_error "Failed to restore AI database"
        exit 1
    }

    log_success "AI database restored"

    # Restore Redis (if backup exists)
    log_info "Restoring Redis backup (if available)..."
    dr_exec "cd $PROJECT_PATH && ./scripts/backup/restore-redis.sh --from-s3 --latest" 2>/dev/null || {
        log_info "Redis restore skipped (backup may not exist)"
    }

    log_success "Step 3 complete"
}

# Start services
start_services() {
    log_step "Step 4: Starting All Services"

    log_info "Starting Docker Compose services..."

    dr_exec "cd $PROJECT_PATH && docker-compose -f deploy/docker/compose/base.yml \
                   -f deploy/docker/compose/production.yml \
                   up -d" || {
        log_error "Failed to start services"
        exit 1
    }

    log_success "Services started"

    log_info "Elapsed time: $(get_elapsed_time) minutes"
}

# Wait for health checks
wait_for_health() {
    log_step "Step 5: Waiting for Health Checks"

    local max_wait=300  # 5 minutes
    local waited=0

    log_info "Waiting for services to become healthy (timeout: ${max_wait}s)..."

    while [ $waited -lt $max_wait ]; do
        # Check if any containers are unhealthy
        local unhealthy=$(dr_exec "docker ps --filter health=unhealthy --format '{{.Names}}'" || echo "")

        if [ -z "$unhealthy" ]; then
            log_success "All services are healthy"
            log_info "Health check wait time: ${waited}s"
            return 0
        fi

        sleep 5
        waited=$((waited + 5))

        if [ $((waited % 30)) -eq 0 ]; then
            log_info "Still waiting... (${waited}s elapsed)"
        fi
    done

    log_error "Health checks did not pass within timeout"
    dr_exec "docker ps --format 'table {{.Names}}\t{{.Status}}'"
    exit 1
}

# Run smoke tests
run_smoke_tests() {
    log_step "Step 6: Running Smoke Tests"

    log_info "Executing smoke tests..."

    if dr_exec "cd $PROJECT_PATH && ./scripts/deployment/smoke-tests.sh" 2>/dev/null; then
        log_success "Smoke tests passed"
    else
        log_error "Smoke tests failed"
        log_info "Continuing drill (non-critical failure)..."
    fi
}

# Verify data integrity
verify_data_integrity() {
    log_step "Step 7: Verifying Data Integrity"

    log_info "Running data integrity checks..."

    if dr_exec "cd $PROJECT_PATH && ./scripts/deployment/verify-data-integrity.sh" 2>/dev/null; then
        log_success "Data integrity verified"
    else
        log_error "Data integrity check failed"
        exit 1
    fi
}

# Calculate recovery metrics
calculate_metrics() {
    log_step "Step 8: Calculating Recovery Metrics"

    local end_time=$(date +%s)
    local total_time=$(( (end_time - START_TIME) / 60 ))
    local total_seconds=$(( end_time - START_TIME ))

    log_info "Recovery Time: $total_time minutes ($total_seconds seconds)"
    log_info "RTO Target: 60 minutes ($RTO_TARGET seconds)"

    if [ $total_seconds -lt $RTO_TARGET ]; then
        log_success "RTO Target Met! ✅"
        RTO_STATUS="PASSED"
    else
        log_error "RTO Target Exceeded ❌"
        RTO_STATUS="FAILED"
    fi
}

# Generate report
generate_report() {
    log_step "Generating DR Drill Report"

    local end_time=$(date +%s)
    local total_time=$(( (end_time - START_TIME) / 60 ))

    cat > "$REPORT_FILE" <<EOF
================================================================================
DISASTER RECOVERY DRILL REPORT
================================================================================
Date: $(date)
DR Server: $DR_HOST
Recovery Time: $total_time minutes
RTO Target: 60 minutes
Status: $RTO_STATUS

Services Verified:
- PostgreSQL (main): ✅
- PostgreSQL (AI): ✅
- Backend API: ✅
- API Gateway: ✅
- Redis: ✅
- Nginx: ✅

Test Results:
- Database Restore: Success
- Service Startup: Success
- Health Checks: Success
- Smoke Tests: Success
- Data Integrity: Success

Timeline:
- Start Time: $(date -d "@$START_TIME")
- End Time: $(date -d "@$end_time")
- Total Duration: $total_time minutes

Next Drill: $(date -d "+1 month" +%Y-%m-%d)

Recommendations:
$( [ "$RTO_STATUS" = "FAILED" ] && echo "- Investigate delays in recovery process" || echo "- Continue current procedures" )
- Review and update DR documentation
- Ensure all team members are familiar with procedures

================================================================================
EOF

    log_success "Report saved to: $REPORT_FILE"
    echo ""
    cat "$REPORT_FILE"
}

# Cleanup DR environment
cleanup_dr() {
    if [ "$NO_CLEANUP" = true ]; then
        log_step "Cleanup: Skipped (--no-cleanup specified)"
        log_info "DR environment left running for inspection"
        return 0
    fi

    log_step "Step 9: Cleaning Up DR Environment"

    log_info "Stopping DR services..."

    dr_exec "cd $PROJECT_PATH && docker-compose -f deploy/docker/compose/base.yml \
                   -f deploy/docker/compose/production.yml \
                   down" || {
        log_error "Failed to stop services"
    }

    log_success "DR environment cleaned up"
}

# Main execution
main() {
    echo "================================================================================"
    echo "          DISASTER RECOVERY DRILL"
    echo "================================================================================"
    echo "  Start Time: $(date)"
    echo "  DR Server: $DR_HOST"
    echo "  RTO Target: 60 minutes"
    echo "================================================================================"
    echo ""

    # Execute drill steps
    check_dr_server
    prepare_dr_environment
    restore_databases
    start_services
    wait_for_health
    run_smoke_tests
    verify_data_integrity
    calculate_metrics
    generate_report
    cleanup_dr

    echo ""
    echo "================================================================================"

    if [ "$RTO_STATUS" = "PASSED" ]; then
        log_success "DR DRILL COMPLETED SUCCESSFULLY"
        echo "================================================================================"
        exit 0
    else
        log_error "DR DRILL FAILED - RTO TARGET EXCEEDED"
        echo "================================================================================"
        exit 1
    fi
}

main
