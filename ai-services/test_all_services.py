#!/usr/bin/env python3
"""
Automated Test Suite for E-commerce AI Platform
Tests all 7 microservices systematically
"""
import requests
import json
import time
from datetime import date, timedelta
from typing import Dict, List
import base64
from io import BytesIO
from PIL import Image


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


class ServiceTester:
    """Test runner for microservices"""
    
    def __init__(self):
        self.results = {
            'passed': 0,
            'failed': 0,
            'total': 0
        }
        self.service_results = {}
    
    def test_service(self, service_name: str, port: int, tests: List[Dict]) -> Dict:
        """Run tests for a specific service"""
        print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}Testing: {service_name} (Port {port}){Colors.END}")
        print(f"{Colors.CYAN}{'='*70}{Colors.END}\n")
        
        service_results = {
            'service': service_name,
            'port': port,
            'tests_passed': 0,
            'tests_failed': 0,
            'tests': []
        }
        
        for test in tests:
            result = self.run_test(test, port)
            service_results['tests'].append(result)
            
            if result['passed']:
                service_results['tests_passed'] += 1
                self.results['passed'] += 1
            else:
                service_results['tests_failed'] += 1
                self.results['failed'] += 1
            
            self.results['total'] += 1
        
        # Summary for this service
        print(f"\n{Colors.BOLD}Service Summary:{Colors.END}")
        print(f"  Passed: {Colors.GREEN}{service_results['tests_passed']}{Colors.END}")
        print(f"  Failed: {Colors.RED}{service_results['tests_failed']}{Colors.END}")
        
        self.service_results[service_name] = service_results
        return service_results
    
    def run_test(self, test: Dict, port: int) -> Dict:
        """Run a single test"""
        test_name = test['name']
        method = test['method']
        endpoint = test['endpoint']
        data = test.get('data')
        expected_status = test.get('expected_status', 200)
        
        url = f"http://localhost:{port}{endpoint}"
        
        print(f"{Colors.YELLOW}► {test_name}{Colors.END}")
        print(f"  URL: {url}")
        
        try:
            start_time = time.time()
            
            if method == 'GET':
                response = requests.get(url, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            elapsed = (time.time() - start_time) * 1000  # ms
            
            passed = response.status_code == expected_status
            
            if passed:
                print(f"  {Colors.GREEN}✓ PASSED{Colors.END} ({elapsed:.0f}ms)")
                print(f"  Status: {response.status_code}")
            else:
                print(f"  {Colors.RED}✗ FAILED{Colors.END}")
                print(f"  Expected: {expected_status}, Got: {response.status_code}")
                print(f"  Response: {response.text[:200]}")
            
            return {
                'name': test_name,
                'passed': passed,
                'status_code': response.status_code,
                'elapsed_ms': elapsed,
                'response': response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
            }
            
        except requests.exceptions.ConnectionError:
            print(f"  {Colors.RED}✗ FAILED - Connection Refused{Colors.END}")
            print(f"  {Colors.YELLOW}Service may not be running on port {port}{Colors.END}")
            return {
                'name': test_name,
                'passed': False,
                'error': 'Connection refused',
                'status_code': 0
            }
        except Exception as e:
            print(f"  {Colors.RED}✗ FAILED - {str(e)}{Colors.END}")
            return {
                'name': test_name,
                'passed': False,
                'error': str(e),
                'status_code': 0
            }
    
    def print_final_report(self):
        """Print final test report"""
        print(f"\n{Colors.BOLD}{Colors.MAGENTA}{'='*70}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.MAGENTA}FINAL TEST REPORT{Colors.END}")
        print(f"{Colors.MAGENTA}{'='*70}{Colors.END}\n")
        
        for service_name, results in self.service_results.items():
            status_color = Colors.GREEN if results['tests_failed'] == 0 else Colors.RED
            print(f"{status_color}● {service_name}{Colors.END} (Port {results['port']})")
            print(f"  Passed: {results['tests_passed']}/{results['tests_passed'] + results['tests_failed']}")
        
        print(f"\n{Colors.BOLD}Overall Statistics:{Colors.END}")
        print(f"  Total Tests: {self.results['total']}")
        print(f"  {Colors.GREEN}Passed: {self.results['passed']}{Colors.END}")
        print(f"  {Colors.RED}Failed: {self.results['failed']}{Colors.END}")
        
        success_rate = (self.results['passed'] / self.results['total'] * 100) if self.results['total'] > 0 else 0
        print(f"  Success Rate: {success_rate:.1f}%")
        
        if self.results['failed'] == 0:
            print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 ALL TESTS PASSED! 🎉{Colors.END}")
        else:
            print(f"\n{Colors.YELLOW}⚠️  Some tests failed. Review details above.{Colors.END}")


def create_sample_image_base64() -> str:
    """Create a simple test image"""
    img = Image.new('RGB', (100, 100), color='red')
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    img_bytes = buffer.getvalue()
    return base64.b64encode(img_bytes).decode('utf-8')


def main():
    """Main test execution"""
    print(f"{Colors.BOLD}{Colors.BLUE}")
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║     E-COMMERCE AI PLATFORM - AUTOMATED TEST SUITE                ║")
    print("║     Testing all 7 microservices                                  ║")
    print("╚══════════════════════════════════════════════════════════════════╝")
    print(Colors.END)
    
    tester = ServiceTester()
    
    # Prepare test data
    sample_image = create_sample_image_base64()
    today = date.today()
    
    # ========== SERVICE 1: RECOMMENDATION ENGINE (8001) ==========
    recommendation_tests = [
        {
            'name': 'Health Check',
            'method': 'GET',
            'endpoint': '/health',
            'expected_status': 200
        },
        {
            'name': 'Root Endpoint',
            'method': 'GET',
            'endpoint': '/',
            'expected_status': 200
        },
        {
            'name': 'Get Statistics',
            'method': 'GET',
            'endpoint': '/recommendations/stats',
            'expected_status': 200
        }
    ]
    tester.test_service("Recommendation Engine", 8001, recommendation_tests)
    
    # ========== SERVICE 2: SEARCH ENGINE (8002) ==========
    search_tests = [
        {
            'name': 'Health Check',
            'method': 'GET',
            'endpoint': '/health',
            'expected_status': 200
        },
        {
            'name': 'Root Endpoint',
            'method': 'GET',
            'endpoint': '/',
            'expected_status': 200
        },
        {
            'name': 'Initialize Index',
            'method': 'POST',
            'endpoint': '/search/initialize',
            'data': {
                'products': [
                    {
                        'product_id': 'test_001',
                        'name': 'Test Product',
                        'description': 'A test product for testing',
                        'price': 29.99,
                        'category': 'test'
                    }
                ]
            },
            'expected_status': 200
        },
        {
            'name': 'Text Search',
            'method': 'POST',
            'endpoint': '/search/text',
            'data': {
                'query': 'test product',
                'limit': 5
            },
            'expected_status': 200
        },
        {
            'name': 'Get Search Stats',
            'method': 'GET',
            'endpoint': '/search/stats',
            'expected_status': 200
        }
    ]
    tester.test_service("Search Engine", 8002, search_tests)
    
    # ========== SERVICE 3: FRAUD DETECTION (8003) ==========
    fraud_tests = [
        {
            'name': 'Health Check',
            'method': 'GET',
            'endpoint': '/health',
            'expected_status': 200
        },
        {
            'name': 'Root Endpoint',
            'method': 'GET',
            'endpoint': '/',
            'expected_status': 200
        },
        {
            'name': 'Analyze Transaction',
            'method': 'POST',
            'endpoint': '/fraud/analyze',
            'data': {
                'transaction_id': 'test_txn_001',
                'user_id': 'test_user_123',
                'amount': 150.00,
                'currency': 'USD',
                'merchant': 'Test Store',
                'card_number': '4532********1234',
                'device_id': 'test_device_001',
                'ip_address': '192.168.1.100',
                'billing_country': 'US',
                'shipping_country': 'US'
            },
            'expected_status': 200
        },
        {
            'name': 'Get Fraud Rules',
            'method': 'GET',
            'endpoint': '/fraud/rules',
            'expected_status': 200
        },
        {
            'name': 'Get Fraud Stats',
            'method': 'GET',
            'endpoint': '/fraud/stats',
            'expected_status': 200
        }
    ]
    tester.test_service("Fraud Detection", 8003, fraud_tests)
    
    # ========== SERVICE 4: CHATBOT RAG (8004) ==========
    chatbot_tests = [
        {
            'name': 'Health Check',
            'method': 'GET',
            'endpoint': '/health',
            'expected_status': 200
        },
        {
            'name': 'Root Endpoint',
            'method': 'GET',
            'endpoint': '/',
            'expected_status': 200
        },
        {
            'name': 'Get Available Intents',
            'method': 'GET',
            'endpoint': '/chat/intents',
            'expected_status': 200
        },
        {
            'name': 'Get Knowledge Categories',
            'method': 'GET',
            'endpoint': '/chat/knowledge/categories',
            'expected_status': 200
        },
        {
            'name': 'Get Chat Stats',
            'method': 'GET',
            'endpoint': '/chat/stats',
            'expected_status': 200
        }
    ]
    tester.test_service("Chatbot RAG", 8004, chatbot_tests)
    
    # ========== SERVICE 5: PRICING ENGINE (8005) ==========
    pricing_tests = [
        {
            'name': 'Health Check',
            'method': 'GET',
            'endpoint': '/health',
            'expected_status': 200
        },
        {
            'name': 'Root Endpoint',
            'method': 'GET',
            'endpoint': '/',
            'expected_status': 200
        },
        {
            'name': 'Get Pricing Rules',
            'method': 'GET',
            'endpoint': '/pricing/rules',
            'expected_status': 200
        },
        {
            'name': 'Price Recommendation',
            'method': 'POST',
            'endpoint': '/pricing/recommend',
            'data': {
                'product_id': 'test_prod_001',
                'base_cost': 50.00,
                'current_price': 79.99,
                'current_stock': 150,
                'units_sold_7d': 45,
                'units_sold_30d': 180,
                'competitor_prices': [75.00, 82.00, 79.00]
            },
            'expected_status': 200
        },
        {
            'name': 'Get Pricing Stats',
            'method': 'GET',
            'endpoint': '/pricing/stats',
            'expected_status': 200
        }
    ]
    tester.test_service("Pricing Engine", 8005, pricing_tests)
    
    # ========== SERVICE 6: DEMAND FORECASTING (8006) ==========
    forecast_tests = [
        {
            'name': 'Health Check',
            'method': 'GET',
            'endpoint': '/health',
            'expected_status': 200
        },
        {
            'name': 'Root Endpoint',
            'method': 'GET',
            'endpoint': '/',
            'expected_status': 200
        },
        {
            'name': 'Generate Forecast',
            'method': 'POST',
            'endpoint': '/forecast/demand',
            'data': {
                'product_id': 'test_prod_001',
                'historical_data': [
                    {'date': str(today - timedelta(days=i)), 'demand': 100 + i*2}
                    for i in range(7, 0, -1)
                ],
                'forecast_periods': 7,
                'method': 'exponential_smoothing'
            },
            'expected_status': 200
        },
        {
            'name': 'Get Forecast Stats',
            'method': 'GET',
            'endpoint': '/forecast/stats',
            'expected_status': 200
        }
    ]
    tester.test_service("Demand Forecasting", 8006, forecast_tests)
    
    # ========== SERVICE 7: VISUAL RECOGNITION (8007) ==========
    visual_tests = [
        {
            'name': 'Health Check',
            'method': 'GET',
            'endpoint': '/health',
            'expected_status': 200
        },
        {
            'name': 'Root Endpoint',
            'method': 'GET',
            'endpoint': '/',
            'expected_status': 200
        },
        {
            'name': 'Image Quality Assessment',
            'method': 'POST',
            'endpoint': '/vision/quality',
            'data': {
                'image_base64': sample_image
            },
            'expected_status': 200
        },
        {
            'name': 'Get Vision Stats',
            'method': 'GET',
            'endpoint': '/vision/stats',
            'expected_status': 200
        }
    ]
    tester.test_service("Visual Recognition", 8007, visual_tests)
    
    # ========== API GATEWAY (8000) ==========
    gateway_tests = [
        {
            'name': 'Health Check',
            'method': 'GET',
            'endpoint': '/health',
            'expected_status': 200
        },
        {
            'name': 'Root Endpoint',
            'method': 'GET',
            'endpoint': '/',
            'expected_status': 200
        }
    ]
    tester.test_service("API Gateway", 8000, gateway_tests)
    
    # Print final report
    tester.print_final_report()
    
    # Return exit code
    return 0 if tester.results['failed'] == 0 else 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
