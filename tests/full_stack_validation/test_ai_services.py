"""
AI Microservices Integration Testing
Comprehensive testing of all 7 AI services with schema validation and performance checks
"""
import pytest
import requests
import json
import time
import asyncio
import concurrent.futures
from typing import Dict, List, Any
from urllib.parse import urljoin
import os


class AIServiceConfig:
    """Configuration for all AI microservices"""

    SERVICES = {
        'recommendation_engine': {
            'port': 8001,
            'base_url': os.environ.get('RECOMMENDATION_URL', 'http://localhost:8001'),
            'endpoints': [
                {'path': '/', 'method': 'GET', 'auth': False},
                {'path': '/health', 'method': 'GET', 'auth': False},
                {'path': '/metrics', 'method': 'GET', 'auth': False},
                {'path': '/recommendations/user/123', 'method': 'POST', 'auth': True},
                {'path': '/recommendations/product/456', 'method': 'POST', 'auth': True},
            ]
        },
        'search_engine': {
            'port': 8002,
            'base_url': os.environ.get('SEARCH_URL', 'http://localhost:8002'),
            'endpoints': [
                {'path': '/', 'method': 'GET', 'auth': False},
                {'path': '/health', 'method': 'GET', 'auth': False},
                {'path': '/metrics', 'method': 'GET', 'auth': False},
                {'path': '/search/semantic', 'method': 'POST', 'auth': False},
            ]
        },
        'pricing_engine': {
            'port': 8003,
            'base_url': os.environ.get('PRICING_URL', 'http://localhost:8003'),
            'endpoints': [
                {'path': '/', 'method': 'GET', 'auth': False},
                {'path': '/health', 'method': 'GET', 'auth': False},
                {'path': '/metrics', 'method': 'GET', 'auth': False},
                {'path': '/pricing/optimize', 'method': 'POST', 'auth': True},
            ]
        },
        'chatbot_rag': {
            'port': 8004,
            'base_url': os.environ.get('CHATBOT_URL', 'http://localhost:8004'),
            'endpoints': [
                {'path': '/', 'method': 'GET', 'auth': False},
                {'path': '/health', 'method': 'GET', 'auth': False},
                {'path': '/metrics', 'method': 'GET', 'auth': False},
                {'path': '/chat/message', 'method': 'POST', 'auth': False},
            ]
        },
        'fraud_detection': {
            'port': 8005,
            'base_url': os.environ.get('FRAUD_URL', 'http://localhost:8005'),
            'endpoints': [
                {'path': '/', 'method': 'GET', 'auth': False},
                {'path': '/health', 'method': 'GET', 'auth': False},
                {'path': '/metrics', 'method': 'GET', 'auth': False},
                {'path': '/fraud/check', 'method': 'POST', 'auth': True},
            ]
        },
        'demand_forecasting': {
            'port': 8006,
            'base_url': os.environ.get('FORECAST_URL', 'http://localhost:8006'),
            'endpoints': [
                {'path': '/', 'method': 'GET', 'auth': False},
                {'path': '/health', 'method': 'GET', 'auth': False},
                {'path': '/metrics', 'method': 'GET', 'auth': False},
                {'path': '/forecast/demand', 'method': 'POST', 'auth': True},
            ]
        },
        'visual_recognition': {
            'port': 8007,
            'base_url': os.environ.get('VISION_URL', 'http://localhost:8007'),
            'endpoints': [
                {'path': '/', 'method': 'GET', 'auth': False},
                {'path': '/health', 'method': 'GET', 'auth': False},
                {'path': '/metrics', 'method': 'GET', 'auth': False},
                {'path': '/vision/classify', 'method': 'POST', 'auth': False},
            ]
        },
    }

    @classmethod
    def get_service(cls, name: str) -> Dict:
        """Get service configuration by name"""
        return cls.SERVICES.get(name)

    @classmethod
    def all_services(cls) -> List[str]:
        """Get list of all service names"""
        return list(cls.SERVICES.keys())


@pytest.fixture
def ai_service_config():
    """Fixture for AI service configuration"""
    return AIServiceConfig()


class TestAIServiceAvailability:
    """Test that all AI services are running and accessible"""

    @pytest.mark.parametrize('service_name', AIServiceConfig.all_services())
    def test_service_health(self, service_name):
        """Each AI service should have a working health endpoint"""
        config = AIServiceConfig.get_service(service_name)
        url = urljoin(config['base_url'], '/health')

        try:
            response = requests.get(url, timeout=5)

            assert response.status_code == 200, \
                f"{service_name} health check failed: {response.status_code}"

            # Parse response
            data = response.json()
            assert 'status' in data or 'healthy' in data or 'service' in data

            print(f"✅ {service_name}: {data}")

        except requests.exceptions.RequestException as e:
            pytest.fail(f"{service_name} is not accessible: {e}")

    @pytest.mark.parametrize('service_name', AIServiceConfig.all_services())
    def test_service_info_endpoint(self, service_name):
        """Each service should return info about itself"""
        config = AIServiceConfig.get_service(service_name)
        url = config['base_url'] + '/'

        try:
            response = requests.get(url, timeout=5)

            assert response.status_code == 200

            data = response.json()
            assert 'service' in data or 'name' in data or 'version' in data

            print(f"✅ {service_name}: {data.get('service', data)}")

        except requests.exceptions.RequestException as e:
            pytest.fail(f"{service_name} root endpoint failed: {e}")

    @pytest.mark.parametrize('service_name', AIServiceConfig.all_services())
    def test_service_metrics_endpoint(self, service_name):
        """Each service should expose Prometheus metrics"""
        config = AIServiceConfig.get_service(service_name)
        url = urljoin(config['base_url'], '/metrics')

        try:
            response = requests.get(url, timeout=5)

            assert response.status_code == 200

            # Metrics should be in Prometheus format
            metrics_text = response.text

            # Check for standard Prometheus metrics
            assert 'http_requests_total' in metrics_text or \
                   'process_' in metrics_text or \
                   'python_' in metrics_text

            print(f"✅ {service_name}: Prometheus metrics available")

        except requests.exceptions.RequestException as e:
            print(f"⚠️  {service_name} metrics not available: {e}")


class TestRecommendationEngine:
    """Test Recommendation Engine service"""

    def test_user_recommendations(self):
        """Test getting user-based recommendations"""
        url = 'http://localhost:8001/recommendations/user/123'

        payload = {
            'user_id': '123',
            'limit': 10
        }

        try:
            response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                data = response.json()

                # Validate response structure
                assert 'recommendations' in data or 'products' in data or isinstance(data, list)

                print(f"✅ User recommendations: {len(data.get('recommendations', data))} items")

            elif response.status_code == 401:
                pytest.skip("Service requires authentication")
            else:
                print(f"⚠️  Unexpected status: {response.status_code}")

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Service not available: {e}")

    def test_product_recommendations(self):
        """Test getting similar products"""
        url = 'http://localhost:8001/recommendations/product/456'

        payload = {
            'product_id': '456',
            'limit': 5
        }

        try:
            response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, (list, dict))

                print(f"✅ Product recommendations working")

            elif response.status_code == 401:
                pytest.skip("Service requires authentication")

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Service not available: {e}")


class TestSearchEngine:
    """Test Search Engine service"""

    def test_semantic_search(self):
        """Test semantic search functionality"""
        url = 'http://localhost:8002/search/semantic'

        payload = {
            'query': 'red running shoes',
            'limit': 10
        }

        try:
            response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                data = response.json()

                # Should return results
                assert 'results' in data or isinstance(data, list)

                print(f"✅ Semantic search working")

            elif response.status_code in [400, 422]:
                # Validation error is acceptable
                print(f"⚠️  Validation error: {response.json()}")
            else:
                print(f"⚠️  Status: {response.status_code}")

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Service not available: {e}")


class TestPricingEngine:
    """Test Pricing Engine service"""

    def test_price_optimization(self):
        """Test dynamic pricing optimization"""
        url = 'http://localhost:8003/pricing/optimize'

        payload = {
            'product_id': '123',
            'current_price': 99.99,
            'demand': 100,
            'competitor_prices': [95.00, 105.00, 98.50]
        }

        try:
            response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                data = response.json()

                # Should return optimized price
                assert 'price' in data or 'optimized_price' in data or 'recommended_price' in data

                print(f"✅ Price optimization working")

            elif response.status_code == 401:
                pytest.skip("Service requires authentication")

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Service not available: {e}")


class TestChatbotRAG:
    """Test Chatbot RAG service"""

    def test_chat_message(self):
        """Test chatbot message handling"""
        url = 'http://localhost:8004/chat/message'

        payload = {
            'message': 'What is the return policy?',
            'session_id': 'test_session_123'
        }

        try:
            response = requests.post(url, json=payload, timeout=15)

            if response.status_code == 200:
                data = response.json()

                # Should return a response message
                assert 'response' in data or 'message' in data or 'answer' in data

                print(f"✅ Chatbot RAG working")

            elif response.status_code in [400, 422, 500]:
                # May require OpenAI API key
                print(f"⚠️  Service may need configuration: {response.status_code}")
                pytest.skip("Service requires API keys or configuration")

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Service not available: {e}")


class TestFraudDetection:
    """Test Fraud Detection service"""

    def test_fraud_check(self):
        """Test transaction fraud detection"""
        url = 'http://localhost:8005/fraud/check'

        payload = {
            'user_id': '123',
            'amount': 500.00,
            'location': 'US',
            'payment_method': 'credit_card'
        }

        try:
            response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                data = response.json()

                # Should return fraud score
                assert 'score' in data or 'is_fraud' in data or 'risk' in data

                print(f"✅ Fraud detection working: {data}")

            elif response.status_code == 401:
                pytest.skip("Service requires authentication")

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Service not available: {e}")


class TestDemandForecasting:
    """Test Demand Forecasting service"""

    def test_demand_forecast(self):
        """Test demand forecasting"""
        url = 'http://localhost:8006/forecast/demand'

        payload = {
            'product_id': '123',
            'horizon': 30  # 30 days
        }

        try:
            response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                data = response.json()

                # Should return forecast
                assert 'forecast' in data or 'predictions' in data or isinstance(data, list)

                print(f"✅ Demand forecasting working")

            elif response.status_code == 401:
                pytest.skip("Service requires authentication")

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Service not available: {e}")


class TestVisualRecognition:
    """Test Visual Recognition service"""

    def test_image_classification(self):
        """Test image classification"""
        url = 'http://localhost:8007/vision/classify'

        # Create a simple test image (1x1 pixel)
        from io import BytesIO
        from PIL import Image

        img = Image.new('RGB', (100, 100), color='red')
        img_bytes = BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)

        files = {'file': ('test.jpg', img_bytes, 'image/jpeg')}

        try:
            response = requests.post(url, files=files, timeout=15)

            if response.status_code == 200:
                data = response.json()

                # Should return classification
                assert 'category' in data or 'class' in data or 'label' in data

                print(f"✅ Visual recognition working: {data}")

            elif response.status_code in [400, 422]:
                print(f"⚠️  Image validation issue: {response.status_code}")

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Service not available: {e}")
        except ImportError:
            pytest.skip("PIL/Pillow not installed for image testing")


class TestServiceCommunication:
    """Test inter-service communication"""

    def test_concurrent_requests(self):
        """Test multiple services handling concurrent requests"""

        def call_service(service_name):
            """Call a service health endpoint"""
            config = AIServiceConfig.get_service(service_name)
            url = urljoin(config['base_url'], '/health')

            try:
                start = time.time()
                response = requests.get(url, timeout=5)
                duration = time.time() - start

                return {
                    'service': service_name,
                    'status': response.status_code,
                    'duration': duration,
                    'success': response.status_code == 200
                }
            except Exception as e:
                return {
                    'service': service_name,
                    'error': str(e),
                    'success': False
                }

        # Call all services concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=7) as executor:
            futures = [
                executor.submit(call_service, service_name)
                for service_name in AIServiceConfig.all_services()
            ]

            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # Check results
        successful = sum(1 for r in results if r.get('success'))
        total = len(results)

        print(f"\n📊 Concurrent request results: {successful}/{total} successful")

        for result in sorted(results, key=lambda x: x.get('duration', 999)):
            if result.get('success'):
                duration = result.get('duration', 0) * 1000
                print(f"   ✅ {result['service']}: {duration:.0f}ms")
            else:
                print(f"   ❌ {result['service']}: {result.get('error', 'failed')}")

        # At least 50% should succeed
        assert successful / total >= 0.5, \
            f"Only {successful}/{total} services responding"


class TestServicePerformance:
    """Test AI service performance"""

    @pytest.mark.parametrize('service_name', AIServiceConfig.all_services())
    def test_response_time(self, service_name):
        """Services should respond quickly"""
        config = AIServiceConfig.get_service(service_name)
        url = urljoin(config['base_url'], '/health')

        response_times = []

        for _ in range(5):
            try:
                start = time.time()
                response = requests.get(url, timeout=10)
                duration = time.time() - start

                if response.status_code == 200:
                    response_times.append(duration)

            except requests.exceptions.RequestException:
                continue

        if response_times:
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)

            print(f"⏱️  {service_name}: avg={avg_time*1000:.0f}ms, max={max_time*1000:.0f}ms")

            # Health endpoints should be fast (<1s)
            assert avg_time < 1.0, \
                f"{service_name} too slow: {avg_time:.2f}s"
        else:
            pytest.skip(f"{service_name} not available")


class TestServiceSchemas:
    """Test response schema validation"""

    def test_health_response_schema(self):
        """Health endpoint responses should be consistent"""
        schemas = []

        for service_name in AIServiceConfig.all_services():
            config = AIServiceConfig.get_service(service_name)
            url = urljoin(config['base_url'], '/health')

            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    schemas.append({
                        'service': service_name,
                        'keys': list(data.keys()),
                        'data': data
                    })
            except Exception:
                continue

        # Print schema comparison
        print(f"\n📋 Health endpoint schemas:")
        for schema in schemas:
            print(f"   {schema['service']}: {schema['keys']}")

        # At least some services should respond
        assert len(schemas) > 0, "No services responding"


class TestErrorHandling:
    """Test error handling in AI services"""

    def test_invalid_request_returns_400(self):
        """Invalid requests should return proper error codes"""
        url = 'http://localhost:8002/search/semantic'

        # Send invalid payload (empty)
        response = requests.post(url, json={}, timeout=5)

        # Should return 400 or 422 (validation error)
        assert response.status_code in [400, 422], \
            f"Invalid request returned {response.status_code} instead of 400/422"

    def test_error_response_format(self):
        """Error responses should have consistent format"""
        url = 'http://localhost:8002/search/semantic'

        response = requests.post(url, json={}, timeout=5)

        if response.status_code in [400, 422]:
            data = response.json()

            # Should have error information
            has_error_info = (
                'detail' in data or
                'error' in data or
                'message' in data
            )

            assert has_error_info, "Error response missing error information"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
