#!/bin/bash
# ==============================================================================
# Connection Pool Tuning Script
# ==============================================================================
# This script helps determine optimal connection pool sizes by running
# load tests at different pool configurations
#
# Usage: ./scripts/tune_connection_pools.sh
# ==============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "===================================================================="
echo "Connection Pool Tuning Script"
echo "===================================================================="
echo ""

# Check if running in correct directory
if [ ! -f "deploy/docker/compose/production.yml" ]; then
    echo -e "${RED}Error: Must run from project root${NC}"
    exit 1
fi

# Configuration
POOL_SIZES=(10 15 20 25 30 40 50)
RESULTS_DIR="reports/pool_tuning_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RESULTS_DIR"

echo "Results will be saved to: $RESULTS_DIR"
echo ""

# Function to update PgBouncer pool size
update_pool_size() {
    local pool_size=$1
    echo -e "${YELLOW}Setting pool size to: $pool_size${NC}"

    # Update pgbouncer.ini
    sed -i "s/^default_pool_size = .*/default_pool_size = $pool_size/" \
        infrastructure/docker/pgbouncer/pgbouncer.ini

    # Restart PgBouncer
    docker-compose -f deploy/docker/compose/production.yml restart pgbouncer
    sleep 5  # Wait for restart
}

# Function to run load test
run_load_test() {
    local pool_size=$1
    local output_file="$RESULTS_DIR/pool_${pool_size}.html"

    echo -e "${GREEN}Running load test with pool size: $pool_size${NC}"

    # Run locust test
    locust -f tests/load/locustfile.py \
        --host=http://localhost:8000 \
        --users 500 \
        --spawn-rate 50 \
        --run-time 3m \
        --headless \
        --html "$output_file" \
        --csv "$RESULTS_DIR/pool_${pool_size}"

    echo -e "${GREEN}Load test complete${NC}"
    echo ""
}

# Function to collect pool stats
collect_pool_stats() {
    local pool_size=$1
    local stats_file="$RESULTS_DIR/pool_${pool_size}_stats.txt"

    echo "Collecting pool statistics..."

    # Get PostgreSQL stats
    docker exec postgres psql -U postgres -d ecommerce -c "
        SELECT
            count(*) as total_connections,
            count(*) FILTER (WHERE state = 'active') as active,
            count(*) FILTER (WHERE state = 'idle') as idle,
            (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') as max_conn
        FROM pg_stat_activity;
    " > "$stats_file"

    echo "Stats saved to: $stats_file"
    echo ""
}

# Main tuning loop
echo "Starting pool tuning tests..."
echo "This will test pool sizes: ${POOL_SIZES[*]}"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted"
    exit 1
fi

for pool_size in "${POOL_SIZES[@]}"; do
    echo ""
    echo "===================================================================="
    echo "Testing pool size: $pool_size"
    echo "===================================================================="

    update_pool_size "$pool_size"
    run_load_test "$pool_size"
    collect_pool_stats "$pool_size"

    echo "Waiting 30 seconds before next test..."
    sleep 30
done

# Generate summary report
echo ""
echo "===================================================================="
echo "Generating summary report..."
echo "===================================================================="

cat > "$RESULTS_DIR/summary.md" << 'EOF'
# Connection Pool Tuning Results

## Test Configuration

- Users: 500
- Spawn Rate: 50/second
- Duration: 3 minutes per test
- Pool Sizes Tested: POOL_SIZES_PLACEHOLDER

## Results

| Pool Size | RPS | P50 Latency | P95 Latency | P99 Latency | Failures |
|-----------|-----|-------------|-------------|-------------|----------|
EOF

# Parse results and add to summary
for pool_size in "${POOL_SIZES[@]}"; do
    csv_file="$RESULTS_DIR/pool_${pool_size}_stats.csv"

    if [ -f "$csv_file" ]; then
        # Extract metrics from CSV (simplified - adjust based on actual Locust output)
        # This is a placeholder - actual parsing depends on Locust CSV format
        echo "| $pool_size | - | - | - | - | - |" >> "$RESULTS_DIR/summary.md"
    fi
done

cat >> "$RESULTS_DIR/summary.md" << 'EOF'

## Recommendations

Based on the results above:

1. **Optimal Pool Size**: [To be determined based on results]
2. **Reasoning**: [Why this size is optimal]
3. **Trade-offs**: [Consider connection overhead vs availability]

### Configuration Changes

Update `infrastructure/docker/pgbouncer/pgbouncer.ini`:

```ini
default_pool_size = [RECOMMENDED_SIZE]
min_pool_size = [RECOMMENDED_SIZE * 0.2]
reserve_pool_size = [RECOMMENDED_SIZE * 0.4]
```

### Next Steps

1. Apply recommended configuration
2. Monitor in production for 1 week
3. Adjust based on actual traffic patterns
4. Document final configuration
EOF

# Replace placeholder
sed -i "s/POOL_SIZES_PLACEHOLDER/${POOL_SIZES[*]}/" "$RESULTS_DIR/summary.md"

echo -e "${GREEN}Tuning complete!${NC}"
echo ""
echo "Results saved to: $RESULTS_DIR"
echo "Summary report: $RESULTS_DIR/summary.md"
echo ""
echo "Next steps:"
echo "1. Review the summary report"
echo "2. Choose optimal pool size based on:"
echo "   - Lowest P95 latency"
echo "   - Highest RPS"
echo "   - Lowest failure rate"
echo "3. Update pgbouncer.ini with recommended values"
echo "4. Restart PgBouncer"
echo ""
