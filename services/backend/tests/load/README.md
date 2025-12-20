# Load Testing Suite

Comprehensive load testing infrastructure for the e-commerce platform using Locust.

## Quick Start

```bash
# Install dependencies
pip install -r requirements/dev.txt

# Run smoke test (quick validation)
cd tests/load
./run_load_test.sh smoke http://localhost:8000

# Run baseline test (establish performance metrics)
./run_load_test.sh baseline http://localhost:8000

# Analyze results
./analyze_results.py reports/latest_stats.csv
```

## Test Profiles

| Profile | Users | Duration | Purpose |
|---------|-------|----------|---------|
| **smoke** | 10 | 1 min | Quick validation, sanity check |
| **baseline** | 100 | 10 min | Establish performance baselines |
| **load** | 500 | 10 min | Standard load testing |
| **stress** | 1000 | 15 min | High load, find breaking points |
| **spike** | 2000 | 5 min | Rapid scaling, test autoscaling |
| **soak** | 200 | 60 min | Endurance test, memory leaks |

## User Behaviors

The test suite simulates 5 realistic user types:

1. **AnonymousUser** (40%) - Browsing without login
2. **ShopperUser** (30%) - Authenticated shopping
3. **BuyerUser** (10%) - Complete purchase flow
4. **AccountUser** (15%) - Account management
5. **PowerSearchUser** (5%) - Heavy search/filter usage

## Performance Baselines

Critical endpoints with target metrics:

| Endpoint | RPS | P50 | P95 | P99 |
|----------|-----|-----|-----|-----|
| Product List | 100 | <50ms | <100ms | <200ms |
| Product Detail | 200 | <30ms | <80ms | <150ms |
| Search | 50 | <100ms | <300ms | <500ms |
| Add to Cart | 50 | <80ms | <150ms | <300ms |
| Checkout | 20 | <200ms | <500ms | <1000ms |

## CI/CD Integration

Load tests run automatically:
- **Pull Requests**: Smoke test (quick validation)
- **Weekly**: Baseline test (track trends)
- **Manual**: Any profile via GitHub Actions

## Directory Structure

```
tests/load/
├── locustfile.py          # Main test scenarios
├── run_load_test.sh       # Test execution script
├── analyze_results.py     # Regression analysis
├── config/
│   └── baselines.json     # Performance thresholds
├── reports/               # Test results (gitignored)
└── README.md              # This file
```

## Running Tests

### Local Testing

```bash
# Start application
cd services/backend
docker-compose up -d

# Run tests
cd tests/load
./run_load_test.sh load http://localhost:8000

# View HTML report
open reports/latest.html
```

### CI/CD Testing

Tests run automatically on PRs. View results in GitHub Actions artifacts.

### Custom Testing

```bash
# Direct Locust execution
locust -f locustfile.py --host=http://localhost:8000

# Web UI (opens browser)
locust -f locustfile.py --host=http://localhost:8000 --web-host=0.0.0.0

# Headless with custom parameters
locust -f locustfile.py \
  --host=http://localhost:8000 \
  --users 1000 \
  --spawn-rate 100 \
  --run-time 15m \
  --headless \
  --html=my_report.html
```

## Analyzing Results

### Automatic Analysis

```bash
# Run with regression detection
./analyze_results.py reports/load_test_stats.csv

# Output as JSON
./analyze_results.py reports/load_test_stats.csv --json
```

### Exit Codes

- **0**: All metrics within baselines ✅
- **1**: Warning - high regressions detected ⚠️
- **2**: Critical - critical regressions detected ❌

### Manual Analysis

Open HTML report in browser for interactive charts and detailed metrics.

## Performance Regression Detection

The analysis tool compares results against baselines (`config/baselines.json`) and detects:

- **Latency regressions**: P50, P95, P99 > 20-30% threshold
- **Error rate regressions**: Errors exceed baseline
- **Throughput degradation**: RPS below target

## Updating Baselines

After performance improvements or intentional changes:

```bash
# 1. Run baseline test
./run_load_test.sh baseline http://localhost:8000

# 2. Review results
./analyze_results.py reports/latest_stats.csv

# 3. Update baselines (if appropriate)
vim config/baselines.json

# 4. Commit changes
git add config/baselines.json
git commit -m "chore: update performance baselines"
```

## Troubleshooting

### High Error Rates

- Check application logs: `docker-compose logs backend`
- Verify database connections
- Check Redis connectivity
- Review rate limiting settings

### Slow Performance

- Enable Django Debug Toolbar (dev only)
- Use django-silk for profiling
- Check database query counts (N+1)
- Review cache hit rates

### Tests Failing in CI

- Check GitHub Actions logs
- Verify service containers are healthy
- Ensure test data is created
- Review timeout settings

## Best Practices

1. **Run smoke tests** before committing
2. **Establish baselines** after major changes
3. **Monitor trends** via weekly scheduled runs
4. **Update baselines** when performance improves
5. **Investigate regressions** immediately

## Contributing

When adding new endpoints:

1. Add test scenario to `locustfile.py`
2. Define baseline in `config/baselines.json`
3. Run baseline test to validate
4. Update documentation

## Resources

- [Locust Documentation](https://docs.locust.io/)
- [Performance Testing Guide](../../../docs/LOAD_TESTING_GUIDE.md)
- [Phase 5 Execution Plan](../../../docs/PHASE_5_EXECUTION_PLAN.md)

---

**Maintainer**: QA Team
**Last Updated**: 2025-12-20
