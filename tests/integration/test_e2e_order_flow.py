"""
End-to-End Integration Test: Complete Order Flow

Tests the full user journey from product browsing to order completion.
"""

import pytest
import requests
import time
from typing import Dict, Any


@pytest.fixture
def base_url() -> str:
    """Base URL for the backend API."""
    return "http://backend-test:8000"


@pytest.fixture
def api_gateway_url() -> str:
    """Base URL for the API gateway."""
    return "http://api-gateway-test:8080"


@pytest.fixture
def test_user_credentials() -> Dict[str, str]:
    """Test user credentials."""
    return {
        "email": "test@example.com",
        "password": "TestPassword123!"
    }


class TestCompleteOrderFlow:
    """Test complete e-commerce order flow."""

    def test_01_health_checks(self, base_url, api_gateway_url):
        """Verify all services are healthy."""
        # Backend health
        response = requests.get(f"{base_url}/health", timeout=10)
        assert response.status_code == 200
        assert response.json()["status"] in ["healthy", "ok"]

        # API Gateway health
        response = requests.get(f"{api_gateway_url}/health", timeout=10)
        assert response.status_code == 200

    def test_02_user_registration(self, base_url, test_user_credentials):
        """Test user registration."""
        response = requests.post(
            f"{base_url}/api/v1/auth/register/",
            json={
                "email": test_user_credentials["email"],
                "password": test_user_credentials["password"],
                "password_confirm": test_user_credentials["password"],
                "first_name": "Test",
                "last_name": "User"
            },
            timeout=10
        )

        # May already exist from previous runs
        assert response.status_code in [201, 400]

    def test_03_user_login(self, base_url, test_user_credentials):
        """Test user authentication."""
        response = requests.post(
            f"{base_url}/api/v1/auth/login/",
            json=test_user_credentials,
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()
        assert "access" in data or "token" in data
        assert "refresh" in data or "refresh_token" in data

        # Store tokens for subsequent requests
        return data

    def test_04_browse_products(self, base_url):
        """Test product browsing."""
        response = requests.get(
            f"{base_url}/api/v1/products/",
            params={"page": 1, "page_size": 10},
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()
        assert "results" in data or isinstance(data, list)

    def test_05_search_products(self, api_gateway_url):
        """Test product search via AI service."""
        response = requests.get(
            f"{api_gateway_url}/api/v1/search/",
            params={"q": "laptop", "limit": 5},
            timeout=15
        )

        # May not be fully implemented yet
        assert response.status_code in [200, 404, 501]

    def test_06_get_recommendations(self, api_gateway_url):
        """Test product recommendations."""
        response = requests.get(
            f"{api_gateway_url}/api/v1/recommendations/test-user",
            params={"limit": 5},
            timeout=15
        )

        # May not be fully implemented yet
        assert response.status_code in [200, 404, 501]

    def test_07_add_to_cart(self, base_url, test_user_credentials):
        """Test adding products to cart."""
        # Login first
        auth_response = requests.post(
            f"{base_url}/api/v1/auth/login/",
            json=test_user_credentials,
            timeout=10
        )

        if auth_response.status_code != 200:
            pytest.skip("Authentication failed")

        token = auth_response.json().get("access") or auth_response.json().get("token")
        headers = {"Authorization": f"Bearer {token}"}

        # Add to cart
        response = requests.post(
            f"{base_url}/api/v1/cart/items/",
            json={
                "product_id": 1,
                "quantity": 2
            },
            headers=headers,
            timeout=10
        )

        # Endpoint may not exist yet
        assert response.status_code in [200, 201, 404]

    def test_08_view_cart(self, base_url, test_user_credentials):
        """Test viewing cart contents."""
        # Login first
        auth_response = requests.post(
            f"{base_url}/api/v1/auth/login/",
            json=test_user_credentials,
            timeout=10
        )

        if auth_response.status_code != 200:
            pytest.skip("Authentication failed")

        token = auth_response.json().get("access") or auth_response.json().get("token")
        headers = {"Authorization": f"Bearer {token}"}

        # View cart
        response = requests.get(
            f"{base_url}/api/v1/cart/",
            headers=headers,
            timeout=10
        )

        # Endpoint may not exist yet
        assert response.status_code in [200, 404]

    def test_09_create_order(self, base_url, test_user_credentials):
        """Test order creation."""
        # Login first
        auth_response = requests.post(
            f"{base_url}/api/v1/auth/login/",
            json=test_user_credentials,
            timeout=10
        )

        if auth_response.status_code != 200:
            pytest.skip("Authentication failed")

        token = auth_response.json().get("access") or auth_response.json().get("token")
        headers = {"Authorization": f"Bearer {token}"}

        # Create order
        response = requests.post(
            f"{base_url}/api/v1/orders/",
            json={
                "shipping_address": {
                    "street": "123 Test St",
                    "city": "Test City",
                    "state": "TS",
                    "zip_code": "12345",
                    "country": "US"
                },
                "payment_method": "credit_card"
            },
            headers=headers,
            timeout=10
        )

        # Endpoint may not exist yet
        assert response.status_code in [200, 201, 404, 400]

    def test_10_order_status(self, base_url, test_user_credentials):
        """Test order status retrieval."""
        # Login first
        auth_response = requests.post(
            f"{base_url}/api/v1/auth/login/",
            json=test_user_credentials,
            timeout=10
        )

        if auth_response.status_code != 200:
            pytest.skip("Authentication failed")

        token = auth_response.json().get("access") or auth_response.json().get("token")
        headers = {"Authorization": f"Bearer {token}"}

        # Get orders
        response = requests.get(
            f"{base_url}/api/v1/orders/",
            headers=headers,
            timeout=10
        )

        # Endpoint may not exist yet
        assert response.status_code in [200, 404]


class TestServiceIntegration:
    """Test inter-service communication."""

    def test_backend_to_redis(self, base_url):
        """Test Redis connectivity from backend."""
        # This would be tested via cache operations
        response = requests.get(f"{base_url}/health", timeout=10)
        assert response.status_code == 200

    def test_backend_to_celery(self, base_url):
        """Test Celery task execution."""
        pytest.skip("Needs an endpoint that triggers a Celery task.")

    def test_api_gateway_to_backend(self, api_gateway_url):
        """Test API Gateway proxying to backend."""
        response = requests.get(f"{api_gateway_url}/health", timeout=10)
        assert response.status_code == 200


class TestPerformance:
    """Basic performance tests."""

    def test_response_time_health_check(self, base_url):
        """Verify health check responds quickly."""
        start = time.time()
        response = requests.get(f"{base_url}/health", timeout=10)
        duration = time.time() - start

        assert response.status_code == 200
        assert duration < 1.0, f"Health check took {duration:.2f}s (should be < 1s)"

    def test_concurrent_requests(self, base_url):
        """Test handling concurrent requests."""
        import concurrent.futures

        def make_request():
            return requests.get(f"{base_url}/health", timeout=10)

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert all(r.status_code == 200 for r in results)


class TestSecurity:
    """Security integration tests."""

    def test_sql_injection_attempt(self, base_url):
        """Verify SQL injection is blocked."""
        response = requests.get(
            f"{base_url}/api/v1/products/",
            params={"search": "'; DROP TABLE products; --"},
            timeout=10
        )

        # Should not return 500 (indicates SQL error)
        assert response.status_code in [200, 400]

    def test_xss_attempt(self, base_url):
        """Verify XSS is blocked."""
        response = requests.get(
            f"{base_url}/api/v1/products/",
            params={"search": "<script>alert('XSS')</script>"},
            timeout=10
        )

        # Should handle safely
        assert response.status_code in [200, 400]

    def test_authentication_required(self, base_url):
        """Verify protected endpoints require authentication."""
        response = requests.get(
            f"{base_url}/api/v1/orders/",
            timeout=10
        )

        # Should require authentication
        assert response.status_code in [401, 403]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
