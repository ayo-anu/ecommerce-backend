#!/usr/bin/env python3
"""
Full Stack Validation Test Runner
Runs comprehensive tests and generates reports
"""
import subprocess
import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List


class TestRunner:
    """Orchestrates test execution and reporting"""

    def __init__(self):
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'tests': {},
            'summary': {},
            'errors': []
        }
        self.test_dir = Path(__file__).parent

    def run_test_file(self, test_file: str, markers: str = None) -> Dict:
        """Run a single test file"""
        print(f"\n{'='*70}")
        print(f"Running: {test_file}")
        print(f"{'='*70}\n")

        cmd = [
            'pytest',
            str(self.test_dir / test_file),
            '-v',
            '--tb=short',
            '--color=yes',
            f'--json-report',
            f'--json-report-file={self.test_dir}/reports/{test_file}.json',
        ]

        if markers:
            cmd.extend(['-m', markers])

        start_time = time.time()

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout per file
            )

            duration = time.time() - start_time

            return {
                'file': test_file,
                'returncode': result.returncode,
                'duration': duration,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'success': result.returncode == 0
            }

        except subprocess.TimeoutExpired:
            return {
                'file': test_file,
                'returncode': -1,
                'error': 'Test execution timeout',
                'success': False
            }
        except Exception as e:
            return {
                'file': test_file,
                'returncode': -1,
                'error': str(e),
                'success': False
            }

    def run_all_tests(self):
        """Run all test files"""
        # Create reports directory
        reports_dir = self.test_dir / 'reports'
        reports_dir.mkdir(exist_ok=True)

        test_files = [
            'test_endpoints.py',
            'test_db_integrity.py',
            'test_security.py',
        ]

        print("\n" + "="*70)
        print("FULL STACK VALIDATION TEST SUITE")
        print("="*70)

        for test_file in test_files:
            result = self.run_test_file(test_file)
            self.results['tests'][test_file] = result

            # Print summary
            status = "✅ PASSED" if result['success'] else "❌ FAILED"
            print(f"\n{status} - {test_file} ({result.get('duration', 0):.1f}s)")

        self.generate_summary()
        self.generate_report()

    def generate_summary(self):
        """Generate test summary"""
        total = len(self.results['tests'])
        passed = sum(1 for t in self.results['tests'].values() if t['success'])
        failed = total - passed

        self.results['summary'] = {
            'total_files': total,
            'passed': passed,
            'failed': failed,
            'success_rate': (passed / total * 100) if total > 0 else 0
        }

    def generate_report(self):
        """Generate comprehensive report"""
        report_path = self.test_dir / 'reports' / 'test_execution_report.md'

        with open(report_path, 'w') as f:
            f.write("# Full Stack Validation Test Report\n\n")
            f.write(f"**Date:** {self.results['timestamp']}\n\n")

            # Summary
            f.write("## Summary\n\n")
            summary = self.results['summary']
            f.write(f"- **Total Test Files:** {summary['total_files']}\n")
            f.write(f"- **Passed:** {summary['passed']}\n")
            f.write(f"- **Failed:** {summary['failed']}\n")
            f.write(f"- **Success Rate:** {summary['success_rate']:.1f}%\n\n")

            # Detailed Results
            f.write("## Detailed Results\n\n")

            for test_file, result in self.results['tests'].items():
                status = "✅ PASSED" if result['success'] else "❌ FAILED"
                f.write(f"### {test_file}\n\n")
                f.write(f"**Status:** {status}\n\n")

                if 'duration' in result:
                    f.write(f"**Duration:** {result['duration']:.2f}s\n\n")

                if 'error' in result:
                    f.write(f"**Error:** {result['error']}\n\n")

                f.write("---\n\n")

        print(f"\n📊 Report generated: {report_path}")

        # Also save JSON report
        json_report_path = self.test_dir / 'reports' / 'test_results.json'
        with open(json_report_path, 'w') as f:
            json.dump(self.results, f, indent=2)

        print(f"📊 JSON report: {json_report_path}")

    def generate_coverage_report(self):
        """Generate code coverage report"""
        print("\n📊 Generating coverage report...")

        cmd = [
            'pytest',
            str(self.test_dir),
            '--cov=services',
            '--cov-report=json',
            '--cov-report=html',
            '--cov-report=term',
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                print("✅ Coverage report generated")

                # Move coverage reports
                coverage_json = Path('coverage.json')
                if coverage_json.exists():
                    coverage_json.rename(self.test_dir / 'reports' / 'coverage_report.json')

                coverage_html = Path('htmlcov')
                if coverage_html.exists():
                    import shutil
                    shutil.move('htmlcov', self.test_dir / 'reports' / 'htmlcov')

            else:
                print("⚠️  Coverage report generation failed (pytest-cov may not be installed)")

        except Exception as e:
            print(f"⚠️  Could not generate coverage: {e}")


def main():
    """Main entry point"""
    runner = TestRunner()

    # Run all tests
    runner.run_all_tests()

    # Generate coverage (if available)
    if '--coverage' in sys.argv:
        runner.generate_coverage_report()

    # Exit with failure if any tests failed
    if runner.results['summary']['failed'] > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
