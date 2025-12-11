#!/usr/bin/env python3
"""
Health Check Script for E-Commerce Platform
Checks the health of all services in the monorepo
"""

import argparse
import json
import sys
import time
from typing import Dict, List, Tuple
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

# Service definitions
SERVICES = {
    "Backend API": "http://localhost:8000/api/health/",
    "Frontend": "http://localhost:3000",
    "API Gateway": "http://localhost:8080/health",
    "Recommendation Service": "http://localhost:8001/health",
    "Search Service": "http://localhost:8002/health",
    "Pricing Service": "http://localhost:8003/health",
    "Chatbot Service": "http://localhost:8004/health",
    "Fraud Detection": "http://localhost:8005/health",
    "Demand Forecasting": "http://localhost:8006/health",
    "Visual Recognition": "http://localhost:8007/health",
    "PostgreSQL": "http://localhost:5432",  # TCP check
    "Redis": "http://localhost:6379",  # TCP check
    "Elasticsearch": "http://localhost:9200",
    "Qdrant": "http://localhost:6333/health",
    "RabbitMQ": "http://localhost:15672",
    "Prometheus": "http://localhost:9090/-/healthy",
    "Grafana": "http://localhost:3001/api/health",
}

def create_session() -> requests.Session:
    """Create a requests session with retry logic"""
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.3,
        status_forcelist=[500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def check_http_service(url: str, timeout: int = 5) -> Tuple[bool, str, float]:
    """
    Check if an HTTP service is healthy

    Returns:
        Tuple of (is_healthy, status_message, response_time_ms)
    """
    session = create_session()
    start_time = time.time()

    try:
        response = session.get(url, timeout=timeout, verify=False)
        response_time = (time.time() - start_time) * 1000  # Convert to milliseconds

        if response.status_code == 200:
            return True, f"OK ({response.status_code})", response_time
        else:
            return False, f"HTTP {response.status_code}", response_time

    except requests.exceptions.ConnectionError:
        return False, "Connection refused", 0
    except requests.exceptions.Timeout:
        return False, "Timeout", timeout * 1000
    except requests.exceptions.RequestException as e:
        return False, f"Error: {str(e)[:50]}", 0

def check_tcp_service(host: str, port: int, timeout: int = 5) -> Tuple[bool, str]:
    """Check if a TCP service is listening"""
    import socket

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()

        if result == 0:
            return True, "Port open"
        else:
            return False, "Port closed"

    except socket.error as e:
        return False, f"Error: {str(e)}"

def print_header():
    """Print the header"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'=' * 80}{Colors.END}")
    print(f"{Colors.BLUE}{Colors.BOLD}E-Commerce Platform - Health Check{Colors.END}")
    print(f"{Colors.BLUE}{Colors.BOLD}{'=' * 80}{Colors.END}\n")

def print_service_status(name: str, is_healthy: bool, status: str, response_time: float = None):
    """Print the status of a service"""
    status_icon = f"{Colors.GREEN}✓{Colors.END}" if is_healthy else f"{Colors.RED}✗{Colors.END}"
    status_color = Colors.GREEN if is_healthy else Colors.RED

    # Format service name with padding
    name_padded = f"{name}".ljust(25)

    # Format response time
    time_str = f"({response_time:.0f}ms)" if response_time else ""

    print(f"{status_icon} {name_padded} {status_color}{status}{Colors.END} {Colors.YELLOW}{time_str}{Colors.END}")

def check_all_services(verbose: bool = False) -> Dict[str, bool]:
    """
    Check all services and return their status

    Returns:
        Dictionary mapping service names to their health status
    """
    results = {}

    for name, url in SERVICES.items():
        parsed = urlparse(url)

        # Special handling for TCP-only services
        if name in ["PostgreSQL", "Redis"]:
            port = parsed.port or (5432 if name == "PostgreSQL" else 6379)
            is_healthy, status = check_tcp_service("localhost", port)
            print_service_status(name, is_healthy, status)
            results[name] = is_healthy
        else:
            is_healthy, status, response_time = check_http_service(url)
            print_service_status(name, is_healthy, status, response_time)
            results[name] = is_healthy

            if verbose and is_healthy:
                try:
                    response = requests.get(url, timeout=5)
                    if response.headers.get('content-type', '').startswith('application/json'):
                        data = response.json()
                        print(f"  {Colors.BLUE}→{Colors.END} {json.dumps(data, indent=2)}")
                except:
                    pass

    return results

def print_summary(results: Dict[str, bool]):
    """Print a summary of the health check"""
    total = len(results)
    healthy = sum(results.values())
    unhealthy = total - healthy

    print(f"\n{Colors.BLUE}{Colors.BOLD}{'=' * 80}{Colors.END}")
    print(f"{Colors.BOLD}Summary:{Colors.END}")
    print(f"  Total services: {total}")
    print(f"  {Colors.GREEN}Healthy: {healthy}{Colors.END}")
    print(f"  {Colors.RED}Unhealthy: {unhealthy}{Colors.END}")
    print(f"  Health percentage: {(healthy/total*100):.1f}%")
    print(f"{Colors.BLUE}{Colors.BOLD}{'=' * 80}{Colors.END}\n")

    if unhealthy > 0:
        print(f"{Colors.YELLOW}⚠ Warning: Some services are unhealthy!{Colors.END}")
        print(f"{Colors.YELLOW}Unhealthy services:{Colors.END}")
        for name, is_healthy in results.items():
            if not is_healthy:
                print(f"  {Colors.RED}✗{Colors.END} {name}")
        print()

def wait_for_services(timeout: int = 300, check_interval: int = 5):
    """
    Wait for all services to become healthy

    Args:
        timeout: Maximum time to wait in seconds
        check_interval: Time between checks in seconds
    """
    print(f"{Colors.YELLOW}Waiting for services to become healthy (timeout: {timeout}s)...{Colors.END}\n")

    start_time = time.time()

    while True:
        elapsed = time.time() - start_time

        if elapsed > timeout:
            print(f"\n{Colors.RED}Timeout reached! Not all services are healthy.{Colors.END}\n")
            return False

        results = check_all_services()

        if all(results.values()):
            print(f"\n{Colors.GREEN}✓ All services are healthy!{Colors.END}\n")
            return True

        unhealthy_count = sum(not v for v in results.values())
        print(f"\n{Colors.YELLOW}Still waiting for {unhealthy_count} service(s)... ({elapsed:.0f}s elapsed){Colors.END}")
        print(f"{Colors.YELLOW}Checking again in {check_interval}s...{Colors.END}\n")

        time.time.sleep(check_interval)

def main():
    parser = argparse.ArgumentParser(
        description="Health check for E-Commerce Platform services"
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show verbose output including service responses'
    )
    parser.add_argument(
        '-w', '--wait',
        action='store_true',
        help='Wait for all services to become healthy'
    )
    parser.add_argument(
        '-t', '--timeout',
        type=int,
        default=300,
        help='Timeout in seconds when waiting (default: 300)'
    )
    parser.add_argument(
        '-j', '--json',
        action='store_true',
        help='Output results in JSON format'
    )

    args = parser.parse_args()

    if not args.json:
        print_header()

    if args.wait:
        success = wait_for_services(timeout=args.timeout)
        sys.exit(0 if success else 1)
    else:
        results = check_all_services(verbose=args.verbose)

        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print_summary(results)

        # Exit with error code if any service is unhealthy
        sys.exit(0 if all(results.values()) else 1)

if __name__ == "__main__":
    main()
