#!/usr/bin/env python3
"""
Verify Monorepo Structure and Enforce Boundaries.

This script checks that the repository structure follows documented conventions
and enforces dependency boundaries between modules.

Usage:
    python scripts/verify_structure.py
    python scripts/verify_structure.py --fix  # Auto-fix some issues

Exit codes:
    0 - All checks passed
    1 - Structure violations found
    2 - Critical violations found
"""

import os
import sys
import re
import argparse
from pathlib import Path
from typing import List, Dict, Set, Tuple
from collections import defaultdict


# Color codes for output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_success(msg):
    print(f"{Colors.GREEN}✓{Colors.RESET} {msg}")


def print_warning(msg):
    print(f"{Colors.YELLOW}⚠{Colors.RESET}  {msg}")


def print_error(msg):
    print(f"{Colors.RED}✗{Colors.RESET} {msg}")


def print_info(msg):
    print(f"{Colors.BLUE}ℹ{Colors.RESET}  {msg}")


def print_header(msg):
    print(f"\n{Colors.BOLD}{msg}{Colors.RESET}")
    print("=" * len(msg))


class StructureVerifier:
    """Verify repository structure and boundaries."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.errors = []
        self.warnings = []
        self.info = []

    def run_all_checks(self) -> bool:
        """Run all verification checks."""
        print_header("E-Commerce Monorepo Structure Verification")

        checks = [
            ("Required directories", self.check_required_directories),
            ("File naming conventions", self.check_naming_conventions),
            ("Import boundaries", self.check_import_boundaries),
            ("Circular dependencies", self.check_circular_dependencies),
            ("Configuration files", self.check_config_files),
            ("Test organization", self.check_test_organization),
        ]

        for name, check_func in checks:
            print_header(name)
            try:
                check_func()
            except Exception as e:
                self.errors.append(f"Check '{name}' failed: {e}")
                print_error(f"Check failed with exception: {e}")

        # Print summary
        print_header("Summary")
        if self.errors:
            print_error(f"Found {len(self.errors)} error(s)")
            for error in self.errors:
                print(f"  {Colors.RED}•{Colors.RESET} {error}")

        if self.warnings:
            print_warning(f"Found {len(self.warnings)} warning(s)")
            for warning in self.warnings:
                print(f"  {Colors.YELLOW}•{Colors.RESET} {warning}")

        if self.info:
            print_info(f"{len(self.info)} informational message(s)")
            for info in self.info:
                print(f"  {Colors.BLUE}•{Colors.RESET} {info}")

        if not self.errors and not self.warnings:
            print_success("All checks passed!")
            return True

        return len(self.errors) == 0

    def check_required_directories(self):
        """Check that required directories exist."""
        required_dirs = [
            "backend",
            "backend/apps",
            "backend/config",
            "backend/core",
            "backend/requirements",
            "ai-services",
            "ai-services/api_gateway",
            "ai-services/services",
            "ai-services/shared",
            "infrastructure",
            "monitoring",
            "tests",
            "tests/integration",
            "docs",
            "scripts",
            ".github",
            ".github/workflows",
        ]

        for dir_path in required_dirs:
            full_path = self.repo_root / dir_path
            if not full_path.exists():
                self.errors.append(f"Required directory missing: {dir_path}")
            else:
                print_success(f"Found: {dir_path}")

    def check_naming_conventions(self):
        """Check file and directory naming conventions."""
        issues = []

        # Check Python files use snake_case
        for py_file in self.repo_root.glob("**/*.py"):
            if "migrations" in str(py_file):
                continue  # Skip migrations

            filename = py_file.stem
            if filename.startswith("test_"):
                continue  # Test files are OK

            # Check for camelCase or PascalCase in filenames
            if re.search(r'[A-Z]', filename):
                issues.append(f"Non-snake_case filename: {py_file.relative_to(self.repo_root)}")

        # Check documentation files are UPPERCASE
        docs_dir = self.repo_root / "docs"
        if docs_dir.exists():
            for md_file in docs_dir.glob("*.md"):
                filename = md_file.stem
                if filename != filename.upper():
                    issues.append(f"Documentation should be UPPERCASE: {md_file.name}")

        if issues:
            for issue in issues[:10]:  # Limit output
                self.warnings.append(issue)
            if len(issues) > 10:
                self.warnings.append(f"... and {len(issues) - 10} more naming issues")
        else:
            print_success("All files follow naming conventions")

    def check_import_boundaries(self):
        """Check that imports respect module boundaries."""
        violations = []

        backend_apps = self.repo_root / "backend" / "apps"
        if backend_apps.exists():
            for app_dir in backend_apps.iterdir():
                if not app_dir.is_dir() or app_dir.name.startswith("_"):
                    continue

                # Check views.py for cross-app view imports
                views_file = app_dir / "views.py"
                if views_file.exists():
                    content = views_file.read_text()

                    # Check for imports from other apps' views
                    pattern = r'from apps\.(\w+)\.views import'
                    matches = re.findall(pattern, content)

                    for imported_app in matches:
                        if imported_app != app_dir.name:
                            violations.append(
                                f"{app_dir.name}/views.py imports from {imported_app}/views.py "
                                f"(cross-app view dependency)"
                            )

        # Check AI services don't import from each other
        ai_services = self.repo_root / "ai-services" / "services"
        if ai_services.exists():
            for service_dir in ai_services.iterdir():
                if not service_dir.is_dir() or service_dir.name.startswith("_"):
                    continue

                for py_file in service_dir.glob("**/*.py"):
                    if py_file.name == "__init__.py":
                        continue

                    content = py_file.read_text()

                    # Check for imports from other services
                    pattern = r'from services\.(\w+)\.'
                    matches = re.findall(pattern, content)

                    for imported_service in matches:
                        if imported_service != service_dir.name:
                            violations.append(
                                f"{service_dir.name} imports from {imported_service} "
                                f"(services should be independent)"
                            )

        if violations:
            for violation in violations[:10]:
                self.errors.append(violation)
            if len(violations) > 10:
                self.errors.append(f"... and {len(violations) - 10} more boundary violations")
        else:
            print_success("No import boundary violations found")

    def check_circular_dependencies(self):
        """Detect circular dependencies between modules."""
        # Simple check: look for imports between core and apps
        core_files = (self.repo_root / "backend" / "core").glob("**/*.py")

        for core_file in core_files:
            content = core_file.read_text()

            # Check if core imports from apps
            if re.search(r'from apps\.\w+', content):
                self.errors.append(
                    f"{core_file.name} in core/ imports from apps/ "
                    f"(circular dependency risk)"
                )

        # Check shared imports from services
        shared_files = (self.repo_root / "ai-services" / "shared").glob("**/*.py")
        for shared_file in shared_files:
            if not shared_file.exists():
                continue

            content = shared_file.read_text()

            if re.search(r'from services\.\w+', content):
                self.errors.append(
                    f"{shared_file.name} in shared/ imports from services/ "
                    f"(circular dependency)"
                )

        if not self.errors:
            print_success("No circular dependencies detected")

    def check_config_files(self):
        """Check that required configuration files exist."""
        required_configs = [
            ".gitignore",
            ".dockerignore",
            "pyproject.toml",
            ".pre-commit-config.yaml",
            "Makefile",
            "README.md",
        ]

        for config_file in required_configs:
            path = self.repo_root / config_file
            if not path.exists():
                self.warnings.append(f"Missing config file: {config_file}")
            else:
                print_success(f"Found: {config_file}")

        # Check .env.example exists
        env_example = self.repo_root / "backend" / ".env.example"
        if not env_example.exists():
            self.errors.append("Missing backend/.env.example")
        else:
            print_success("Found backend/.env.example")

    def check_test_organization(self):
        """Check test file organization."""
        # Check that test files start with test_
        for test_file in self.repo_root.glob("**/test*.py"):
            if not test_file.name.startswith("test_"):
                self.warnings.append(
                    f"Test file should start with test_: {test_file.relative_to(self.repo_root)}"
                )

        # Check integration tests are in tests/integration
        integration_dir = self.repo_root / "tests" / "integration"
        if integration_dir.exists():
            test_files = list(integration_dir.glob("test_*.py"))
            if test_files:
                print_success(f"Found {len(test_files)} integration test file(s)")
            else:
                self.info.append("No integration tests found")
        else:
            self.warnings.append("Missing tests/integration directory")

    def check_dependency_files(self):
        """Check that dependency files are properly organized."""
        # Backend requirements
        req_dir = self.repo_root / "backend" / "requirements"
        required_req_files = ["base.txt", "dev.txt", "prod.txt"]

        for req_file in required_req_files:
            path = req_dir / req_file
            if not path.exists():
                self.warnings.append(f"Missing requirements file: backend/requirements/{req_file}")
            else:
                print_success(f"Found: backend/requirements/{req_file}")

        # AI services requirements
        ai_req = self.repo_root / "ai-services" / "requirements.txt"
        if not ai_req.exists():
            self.warnings.append("Missing ai-services/requirements.txt")
        else:
            print_success("Found: ai-services/requirements.txt")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Verify monorepo structure and enforce boundaries"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Attempt to auto-fix some issues (NOT IMPLEMENTED)"
    )
    args = parser.parse_args()

    # Find repository root
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent

    print_info(f"Repository root: {repo_root}")

    # Run verification
    verifier = StructureVerifier(repo_root)
    success = verifier.run_all_checks()

    # Exit with appropriate code
    if success:
        sys.exit(0)
    elif verifier.errors:
        sys.exit(2)  # Critical errors
    else:
        sys.exit(1)  # Warnings only


if __name__ == "__main__":
    main()
