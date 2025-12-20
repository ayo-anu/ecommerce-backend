#!/usr/bin/env python3
"""
Performance Regression Analysis Tool

This script analyzes load test results and compares them against performance
baselines to detect regressions.

Usage:
    python analyze_results.py <stats_csv_file> [--baseline baselines.json]

Examples:
    python analyze_results.py reports/load_test_load_20231220_150000_stats.csv
    python analyze_results.py reports/load_test_load_20231220_150000_stats.csv --baseline config/baselines.json
"""

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass


@dataclass
class EndpointMetrics:
    """Performance metrics for an endpoint"""
    name: str
    method: str
    request_count: int
    failure_count: int
    median_ms: float
    p95_ms: float
    p99_ms: float
    avg_ms: float
    min_ms: float
    max_ms: float
    rps: float
    error_rate: float


@dataclass
class RegressionResult:
    """Result of regression check"""
    endpoint: str
    metric: str
    baseline: float
    actual: float
    deviation_pct: float
    threshold: float
    is_regression: bool
    severity: str  # critical, high, medium, low


class Colors:
    """ANSI color codes"""
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    BLUE = '\033[0;34m'
    BOLD = '\033[1m'
    NC = '\033[0m'  # No Color


def parse_locust_stats(csv_file: Path) -> Dict[str, EndpointMetrics]:
    """Parse Locust stats CSV file"""
    metrics = {}

    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip aggregated rows
            if row['Type'] in ['None', 'Aggregated']:
                continue

            # Parse endpoint name (remove query parameters)
            endpoint = row['Name'].split('?')[0]

            metrics[endpoint] = EndpointMetrics(
                name=endpoint,
                method=row['Type'],
                request_count=int(row['Request Count']),
                failure_count=int(row['Failure Count']),
                median_ms=float(row['Median Response Time']),
                p95_ms=float(row['95%']),
                p99_ms=float(row['99%']),
                avg_ms=float(row['Average Response Time']),
                min_ms=float(row['Min Response Time']),
                max_ms=float(row['Max Response Time']),
                rps=float(row['Requests/s']),
                error_rate=float(row['Failure Count']) / float(row['Request Count'])
                if int(row['Request Count']) > 0 else 0.0
            )

    return metrics


def load_baselines(baseline_file: Path) -> Dict[str, Any]:
    """Load performance baselines from JSON file"""
    with open(baseline_file, 'r') as f:
        return json.load(f)


def check_regression(
    endpoint: str,
    actual_metrics: EndpointMetrics,
    baseline_config: Dict[str, Any]
) -> List[RegressionResult]:
    """Check if metrics exceed baseline thresholds"""
    results = []

    if endpoint not in baseline_config['endpoints']:
        return results  # No baseline defined for this endpoint

    baseline = baseline_config['endpoints'][endpoint]
    thresholds = baseline['thresholds']

    # Check P50 (median)
    if 'p50_ms' in thresholds:
        baseline_p50 = thresholds['p50_ms']
        actual_p50 = actual_metrics.median_ms
        deviation = ((actual_p50 - baseline_p50) / baseline_p50) * 100

        is_regression = actual_p50 > baseline_p50 * 1.2  # 20% tolerance
        severity = 'critical' if deviation > 100 else 'high' if deviation > 50 else 'medium'

        results.append(RegressionResult(
            endpoint=endpoint,
            metric='P50 Latency',
            baseline=baseline_p50,
            actual=actual_p50,
            deviation_pct=deviation,
            threshold=baseline_p50 * 1.2,
            is_regression=is_regression,
            severity=severity if is_regression else 'ok'
        ))

    # Check P95
    if 'p95_ms' in thresholds:
        baseline_p95 = thresholds['p95_ms']
        actual_p95 = actual_metrics.p95_ms
        deviation = ((actual_p95 - baseline_p95) / baseline_p95) * 100

        is_regression = actual_p95 > baseline_p95 * 1.2  # 20% tolerance

        results.append(RegressionResult(
            endpoint=endpoint,
            metric='P95 Latency',
            baseline=baseline_p95,
            actual=actual_p95,
            deviation_pct=deviation,
            threshold=baseline_p95 * 1.2,
            is_regression=is_regression,
            severity='high' if is_regression else 'ok'
        ))

    # Check P99
    if 'p99_ms' in thresholds:
        baseline_p99 = thresholds['p99_ms']
        actual_p99 = actual_metrics.p99_ms
        deviation = ((actual_p99 - baseline_p99) / baseline_p99) * 100

        is_regression = actual_p99 > baseline_p99 * 1.3  # 30% tolerance for P99

        results.append(RegressionResult(
            endpoint=endpoint,
            metric='P99 Latency',
            baseline=baseline_p99,
            actual=actual_p99,
            deviation_pct=deviation,
            threshold=baseline_p99 * 1.3,
            is_regression=is_regression,
            severity='medium' if is_regression else 'ok'
        ))

    # Check Error Rate
    if 'max_error_rate' in thresholds:
        baseline_error = thresholds['max_error_rate']
        actual_error = actual_metrics.error_rate

        is_regression = actual_error > baseline_error

        results.append(RegressionResult(
            endpoint=endpoint,
            metric='Error Rate',
            baseline=baseline_error * 100,  # Convert to percentage
            actual=actual_error * 100,
            deviation_pct=0,  # Not applicable for error rate
            threshold=baseline_error * 100,
            is_regression=is_regression,
            severity='critical' if is_regression else 'ok'
        ))

    return results


def print_report(metrics: Dict[str, EndpointMetrics], regressions: List[RegressionResult]):
    """Print formatted analysis report"""
    print()
    print(f"{Colors.BOLD}{'=' * 80}{Colors.NC}")
    print(f"{Colors.BOLD}Load Test Performance Analysis{Colors.NC}")
    print(f"{Colors.BOLD}{'=' * 80}{Colors.NC}")
    print()

    # Summary Statistics
    print(f"{Colors.BOLD}Summary Statistics:{Colors.NC}")
    print()

    total_requests = sum(m.request_count for m in metrics.values())
    total_failures = sum(m.failure_count for m in metrics.values())
    overall_error_rate = (total_failures / total_requests * 100) if total_requests > 0 else 0

    print(f"  Total Requests: {total_requests:,}")
    print(f"  Total Failures: {total_failures:,}")
    print(f"  Overall Error Rate: {overall_error_rate:.2f}%")
    print(f"  Unique Endpoints: {len(metrics)}")
    print()

    # Performance by Endpoint
    print(f"{Colors.BOLD}Performance by Endpoint:{Colors.NC}")
    print()
    print(f"{'Endpoint':<50} {'RPS':>8} {'P50':>8} {'P95':>8} {'P99':>8} {'Errors':>8}")
    print('-' * 110)

    for endpoint, m in sorted(metrics.items(), key=lambda x: x[1].p99_ms, reverse=True):
        error_color = Colors.RED if m.error_rate > 0.01 else Colors.GREEN
        print(f"{endpoint:<50} {m.rps:>8.1f} {m.median_ms:>7.0f}ms "
              f"{m.p95_ms:>7.0f}ms {m.p99_ms:>7.0f}ms "
              f"{error_color}{m.error_rate * 100:>7.2f}%{Colors.NC}")

    print()

    # Regression Analysis
    if regressions:
        print(f"{Colors.BOLD}Regression Analysis:{Colors.NC}")
        print()

        critical_regressions = [r for r in regressions if r.is_regression and r.severity == 'critical']
        high_regressions = [r for r in regressions if r.is_regression and r.severity == 'high']
        medium_regressions = [r for r in regressions if r.is_regression and r.severity == 'medium']

        if critical_regressions:
            print(f"{Colors.RED}{Colors.BOLD}CRITICAL REGRESSIONS ({len(critical_regressions)}):{Colors.NC}")
            for r in critical_regressions:
                print(f"  {Colors.RED}✗{Colors.NC} {r.endpoint} - {r.metric}")
                print(f"    Baseline: {r.baseline:.1f}, Actual: {r.actual:.1f}, "
                      f"Deviation: {r.deviation_pct:+.1f}%")
            print()

        if high_regressions:
            print(f"{Colors.YELLOW}{Colors.BOLD}HIGH REGRESSIONS ({len(high_regressions)}):{Colors.NC}")
            for r in high_regressions:
                print(f"  {Colors.YELLOW}⚠{Colors.NC} {r.endpoint} - {r.metric}")
                print(f"    Baseline: {r.baseline:.1f}, Actual: {r.actual:.1f}, "
                      f"Deviation: {r.deviation_pct:+.1f}%")
            print()

        if medium_regressions:
            print(f"{Colors.BLUE}MEDIUM REGRESSIONS ({len(medium_regressions)}):{Colors.NC}")
            for r in medium_regressions:
                print(f"  {Colors.BLUE}ⓘ{Colors.NC} {r.endpoint} - {r.metric}")
                print(f"    Baseline: {r.baseline:.1f}, Actual: {r.actual:.1f}, "
                      f"Deviation: {r.deviation_pct:+.1f}%")
            print()

        # Exit code based on regressions
        if critical_regressions:
            print(f"{Colors.RED}{Colors.BOLD}FAIL: Critical performance regressions detected{Colors.NC}")
            return 2  # Critical failure
        elif high_regressions:
            print(f"{Colors.YELLOW}{Colors.BOLD}WARN: High performance regressions detected{Colors.NC}")
            return 1  # Warning
        else:
            print(f"{Colors.GREEN}{Colors.BOLD}PASS: Performance within acceptable limits{Colors.NC}")
            return 0
    else:
        print(f"{Colors.GREEN}{Colors.BOLD}PASS: All metrics within baselines{Colors.NC}")
        return 0

    print()
    print(f"{Colors.BOLD}{'=' * 80}{Colors.NC}")
    print()


def main():
    parser = argparse.ArgumentParser(description='Analyze load test results')
    parser.add_argument('stats_file', type=Path, help='Locust stats CSV file')
    parser.add_argument('--baseline', type=Path,
                        default=Path(__file__).parent / 'config' / 'baselines.json',
                        help='Baseline configuration JSON file')
    parser.add_argument('--json', action='store_true',
                        help='Output results as JSON')

    args = parser.parse_args()

    # Validate files exist
    if not args.stats_file.exists():
        print(f"Error: Stats file not found: {args.stats_file}", file=sys.stderr)
        sys.exit(1)

    if not args.baseline.exists():
        print(f"Warning: Baseline file not found: {args.baseline}", file=sys.stderr)
        print("Skipping regression analysis", file=sys.stderr)
        baselines = None
    else:
        baselines = load_baselines(args.baseline)

    # Parse metrics
    metrics = parse_locust_stats(args.stats_file)

    # Check regressions
    all_regressions = []
    if baselines:
        for endpoint, endpoint_metrics in metrics.items():
            regressions = check_regression(endpoint, endpoint_metrics, baselines)
            all_regressions.extend(regressions)

    # Output results
    if args.json:
        output = {
            'metrics': {
                endpoint: {
                    'rps': m.rps,
                    'p50_ms': m.median_ms,
                    'p95_ms': m.p95_ms,
                    'p99_ms': m.p99_ms,
                    'error_rate': m.error_rate
                }
                for endpoint, m in metrics.items()
            },
            'regressions': [
                {
                    'endpoint': r.endpoint,
                    'metric': r.metric,
                    'baseline': r.baseline,
                    'actual': r.actual,
                    'deviation_pct': r.deviation_pct,
                    'is_regression': r.is_regression,
                    'severity': r.severity
                }
                for r in all_regressions
            ]
        }
        print(json.dumps(output, indent=2))
        sys.exit(0)
    else:
        exit_code = print_report(metrics, all_regressions)
        sys.exit(exit_code)


if __name__ == '__main__':
    main()
