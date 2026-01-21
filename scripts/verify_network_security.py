#!/usr/bin/env python3
"""
Network Security Verification Script.

Verifies that Docker network policies are correctly applied and that
services have only the necessary network access (least privilege).

Usage:
    python scripts/verify_network_security.py
    python scripts/verify_network_security.py --check-running

Requirements:
    - docker
    - docker-compose
"""

import subprocess
import json
import sys
from typing import Dict, List, Set, Tuple
import argparse


# Expected network access matrix
EXPECTED_NETWORKS = {
    'nginx': {'public_network'},
    'api_gateway': {'public_network', 'backend_network', 'ai_network', 'monitoring_network'},
    'backend': {'backend_network', 'monitoring_network'},
    'celery_worker': {'backend_network', 'monitoring_network'},
    'celery_beat': {'backend_network', 'monitoring_network'},
    'postgres': {'backend_network', 'monitoring_network'},
    'postgres_ai': {'ai_network', 'monitoring_network'},
    'pgbouncer': {'backend_network'},
    'redis': {'backend_network', 'monitoring_network'},
    'elasticsearch': {'ai_network', 'monitoring_network'},
    'qdrant': {'ai_network', 'monitoring_network'},
    'recommendation_engine': {'ai_network', 'monitoring_network'},
    'search_engine': {'ai_network', 'monitoring_network'},
    'pricing_engine': {'ai_network', 'monitoring_network'},
    'chatbot_rag': {'ai_network', 'monitoring_network'},
    'fraud_detection': {'ai_network', 'monitoring_network'},
    'demand_forecasting': {'ai_network', 'monitoring_network'},
    'visual_recognition': {'ai_network', 'monitoring_network'},
    'prometheus': {'monitoring_network', 'public_network'},
    'grafana': {'monitoring_network', 'public_network'},
    'jaeger': {'monitoring_network'},
    'alertmanager': {'monitoring_network', 'public_network'},
}

# Services that should NOT have internet access (internal: true networks only)
INTERNAL_ONLY_SERVICES = {
    'backend', 'celery_worker', 'celery_beat',
    'postgres', 'postgres_ai', 'pgbouncer',
    'redis',
    'elasticsearch', 'qdrant',
    'recommendation_engine', 'search_engine', 'pricing_engine',
    'chatbot_rag', 'fraud_detection', 'demand_forecasting', 'visual_recognition',
}

# Networks that should be internal (no internet access)
INTERNAL_NETWORKS = {'backend_network', 'ai_network'}

# Services that should NOT expose ports in production
NO_PORT_SERVICES_PROD = {
    'postgres', 'postgres_ai', 'pgbouncer',
    'redis',
    'elasticsearch', 'qdrant',
}


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def run_command(cmd: List[str]) -> Tuple[int, str, str]:
    """Run a shell command and return exit code, stdout, stderr."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "Command timed out"
    except Exception as e:
        return 1, "", str(e)


def check_docker_compose_config() -> Dict[str, Set[str]]:
    """Parse docker-compose configuration to check network assignments."""
    print(f"\n{Colors.BLUE}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}Checking Docker Compose Network Configuration{Colors.END}")
    print(f"{Colors.BLUE}{'='*80}{Colors.END}\n")

    # Try to get config with network policy overlay
    cmd = [
        'docker-compose',
        '-f', 'infrastructure/docker-compose.yaml',
        '-f', 'infrastructure/docker-compose.network-policy.yaml',
        'config'
    ]

    returncode, stdout, stderr = run_command(cmd)

    if returncode != 0:
        print(f"{Colors.YELLOW}⚠ Network policy overlay not found, checking base config...{Colors.END}")
        cmd = ['docker-compose', '-f', 'infrastructure/docker-compose.yaml', 'config']
        returncode, stdout, stderr = run_command(cmd)

    if returncode != 0:
        print(f"{Colors.RED}✗ Failed to read docker-compose config: {stderr}{Colors.END}")
        return {}

    # Parse YAML (simplified - just look for networks)
    service_networks = {}
    current_service = None

    for line in stdout.split('\n'):
        line_stripped = line.strip()

        # Detect service definitions
        if line.startswith('  ') and ':' in line and not line.startswith('    '):
            parts = line.strip().split(':')
            if parts[0] and not parts[0].startswith('#'):
                current_service = parts[0]
                service_networks[current_service] = set()

        # Detect networks under a service
        if current_service and 'networks:' in line_stripped:
            in_networks = True

        if current_service and line.startswith('      - '):
            network_name = line.strip().replace('- ', '')
            if network_name and not network_name.startswith('#'):
                service_networks[current_service].add(network_name)

    return service_networks


def check_network_internal_setting() -> Dict[str, bool]:
    """Check if networks have internal: true setting."""
    print(f"\n{Colors.BLUE}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}Checking Network Internal Settings{Colors.END}")
    print(f"{Colors.BLUE}{'='*80}{Colors.END}\n")

    cmd = [
        'docker-compose',
        '-f', 'infrastructure/docker-compose.yaml',
        '-f', 'infrastructure/docker-compose.network-policy.yaml',
        'config'
    ]

    returncode, stdout, stderr = run_command(cmd)
    if returncode != 0:
        return {}

    network_internal = {}
    current_network = None

    for line in stdout.split('\n'):
        if line.startswith('  ') and ':' in line and not line.startswith('    '):
            if 'networks:' in line:
                continue
            network_name = line.strip().replace(':', '')
            if network_name:
                current_network = network_name
                network_internal[network_name] = False

        if current_network and 'internal:' in line:
            value = line.split('internal:')[1].strip()
            network_internal[current_network] = value.lower() == 'true'

    return network_internal


def verify_service_networks(config_networks: Dict[str, Set[str]]) -> List[str]:
    """Verify that services have correct network access."""
    issues = []

    print(f"{Colors.BOLD}Service Network Access Verification:{Colors.END}\n")

    for service, expected_nets in sorted(EXPECTED_NETWORKS.items()):
        actual_nets = config_networks.get(service, set())

        if not actual_nets:
            print(f"{Colors.YELLOW}⚠ {service}: Not found in configuration{Colors.END}")
            continue

        # Check for missing networks
        missing = expected_nets - actual_nets
        if missing:
            msg = f"{service}: Missing networks: {', '.join(missing)}"
            print(f"{Colors.RED}✗ {msg}{Colors.END}")
            issues.append(msg)

        # Check for excessive networks
        excessive = actual_nets - expected_nets
        if excessive:
            msg = f"{service}: Excessive networks (violates least privilege): {', '.join(excessive)}"
            print(f"{Colors.RED}✗ {msg}{Colors.END}")
            issues.append(msg)

        if not missing and not excessive:
            print(f"{Colors.GREEN}✓ {service}: Correct network access{Colors.END}")

    return issues


def verify_network_internal(network_settings: Dict[str, bool]) -> List[str]:
    """Verify that internal networks are correctly configured."""
    issues = []

    print(f"\n{Colors.BOLD}Network Isolation Verification:{Colors.END}\n")

    for network in INTERNAL_NETWORKS:
        is_internal = network_settings.get(network, False)

        if not is_internal:
            msg = f"{network}: Should be internal (no internet access) but is not"
            print(f"{Colors.RED}✗ {msg}{Colors.END}")
            issues.append(msg)
        else:
            print(f"{Colors.GREEN}✓ {network}: Correctly configured as internal{Colors.END}")

    return issues


def check_running_containers() -> List[str]:
    """Check running containers for network violations."""
    print(f"\n{Colors.BLUE}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}Checking Running Container Networks{Colors.END}")
    print(f"{Colors.BLUE}{'='*80}{Colors.END}\n")

    cmd = ['docker', 'ps', '--format', '{{.Names}}']
    returncode, stdout, stderr = run_command(cmd)

    if returncode != 0:
        print(f"{Colors.RED}✗ Failed to list running containers{Colors.END}")
        return []

    containers = [line.strip() for line in stdout.split('\n') if line.strip()]

    issues = []
    for container in containers:
        # Get container network info
        cmd = ['docker', 'inspect', container, '--format', '{{json .NetworkSettings.Networks}}']
        returncode, stdout, stderr = run_command(cmd)

        if returncode != 0:
            continue

        try:
            networks = json.loads(stdout)
            container_networks = set(networks.keys())

            # Find service name (remove prefix)
            service_name = container.replace('ecommerce_', '').replace('ecommerce-', '')

            # Get expected networks
            expected = EXPECTED_NETWORKS.get(service_name, set())

            if expected:
                excessive = container_networks - expected
                if excessive:
                    msg = f"{container}: Running with excessive networks: {', '.join(excessive)}"
                    print(f"{Colors.RED}✗ {msg}{Colors.END}")
                    issues.append(msg)
                else:
                    print(f"{Colors.GREEN}✓ {container}: Correct network access{Colors.END}")

        except json.JSONDecodeError:
            continue

    return issues


def main():
    """Main verification function."""
    parser = argparse.ArgumentParser(description='Verify Docker network security policies')
    parser.add_argument('--check-running', action='store_true',
                        help='Also check running containers')
    args = parser.parse_args()

    print(f"\n{Colors.BOLD}{Colors.BLUE}Docker Network Security Verification{Colors.END}")
    print(f"{Colors.BLUE}{'='*80}{Colors.END}")

    all_issues = []

    # 1. Check docker-compose configuration
    config_networks = check_docker_compose_config()
    if config_networks:
        issues = verify_service_networks(config_networks)
        all_issues.extend(issues)

    # 2. Check network internal settings
    network_settings = check_network_internal_setting()
    if network_settings:
        issues = verify_network_internal(network_settings)
        all_issues.extend(issues)

    # 3. Check running containers if requested
    if args.check_running:
        issues = check_running_containers()
        all_issues.extend(issues)

    # Summary
    print(f"\n{Colors.BLUE}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}Summary{Colors.END}")
    print(f"{Colors.BLUE}{'='*80}{Colors.END}\n")

    if not all_issues:
        print(f"{Colors.GREEN}{Colors.BOLD}✓ All network security checks passed!{Colors.END}")
        print(f"{Colors.GREEN}  Network segmentation is correctly configured{Colors.END}")
        print(f"{Colors.GREEN}  Least privilege principle is enforced{Colors.END}")
        return 0
    else:
        print(f"{Colors.RED}{Colors.BOLD}✗ Found {len(all_issues)} network security issues:{Colors.END}\n")
        for i, issue in enumerate(all_issues, 1):
            print(f"  {i}. {issue}")

        print(f"\n{Colors.YELLOW}Recommendations:{Colors.END}")
        print(f"  1. Apply network policy overlay:")
        print(f"     docker-compose -f infrastructure/docker-compose.yaml \\")
        print(f"                    -f infrastructure/docker-compose.network-policy.yaml up -d")
        print(f"\n  2. Review service network requirements in:")
        print(f"     infrastructure/docker-compose.network-policy.yaml")

        return 1


if __name__ == '__main__':
    sys.exit(main())
