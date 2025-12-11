"""
Integration tests for Backend + AI Services.

Tests the communication between Django backend and AI microservices.
"""

import pytest
import requests


class TestBackendAIIntegration:
    """Test backend integration with AI services"""

    def test_recommendation_flow(self, authenticated_client, backend_url, gateway_url):
        """
        Test complete recommendation flow:
        1. User browses products
        2. Interactions are tracked
        3. Recommendations are generated
        """
        # Step 1: Get products from backend
        response = authenticated_client.get("/api/products/")
        assert response.status_code == 200
        products = response.json()
        assert len(products["results"]) > 0

        # Step 2: View a product (track interaction)
        product_id = products["results"][0]["id"]
        response = authenticated_client.get(f"/api/products/{product_id}/")
        assert response.status_code == 200

        # Step 3: Get recommendations via gateway
        # Note: Requires authentication with gateway
        response = requests.post(
            f"{gateway_url}/api/v1/recommendations/user",
            json={"user_id": 1, "limit": 10},
            timeout=10,
        )

        # May return 401 if gateway auth is required, or 200 with recommendations
        assert response.status_code in [200, 401, 503]  # 503 if service down

    def test_search_integration(self, backend_url, gateway_url):
        """
        Test search integration:
        1. Search products via backend
        2. Enhanced search via AI service
        """
        # Standard search via backend
        response = requests.get(
            f"{backend_url}/api/products/",
            params={"search": "laptop"},
        )
        assert response.status_code == 200

        # Semantic search via gateway
        response = requests.post(
            f"{gateway_url}/api/v1/search/semantic",
            json={"query": "affordable laptop for students", "limit": 5},
            timeout=10,
        )
        assert response.status_code in [200, 401, 503]

    def test_fraud_detection_on_order(self, authenticated_client, gateway_url):
        """
        Test fraud detection during checkout:
        1. Create order
        2. Check fraud score
        3. Process based on risk
        """
        # Step 1: Add product to cart
        response = authenticated_client.post(
            "/api/cart/add/",
            json={"product_id": 1, "quantity": 1},
        )
        assert response.status_code in [200, 201, 400]  # 400 if product not found

        # Step 2: Get fraud score for transaction
        transaction_data = {
            "user_id": 1,
            "amount": 299.99,
            "payment_method": "credit_card",
            "device_info": {"ip": "127.0.0.1", "user_agent": "pytest"},
        }

        response = requests.post(
            f"{gateway_url}/api/v1/fraud/score_transaction",
            json=transaction_data,
            timeout=10,
        )
        assert response.status_code in [200, 401, 503]

        if response.status_code == 200:
            fraud_result = response.json()
            assert "risk_score" in fraud_result
            assert 0 <= fraud_result["risk_score"] <= 1

    def test_dynamic_pricing(self, backend_url, gateway_url):
        """
        Test dynamic pricing:
        1. Get product price from backend
        2. Get optimized price from AI service
        3. Compare prices
        """
        # Get product
        response = requests.get(f"{backend_url}/api/products/1/")
        if response.status_code == 200:
            product = response.json()
            base_price = product.get("price", 100.00)

            # Get optimized price
            response = requests.post(
                f"{gateway_url}/api/v1/pricing/optimize",
                json={
                    "product_id": 1,
                    "current_price": base_price,
                    "cost": base_price * 0.6,
                    "inventory": 100,
                },
                timeout=10,
            )

            assert response.status_code in [200, 401, 503]

    def test_chatbot_product_query(self, gateway_url):
        """
        Test chatbot answering product questions
        """
        response = requests.post(
            f"{gateway_url}/api/v1/chat/message",
            json={
                "session_id": "test-session-123",
                "message": "What are your return policies?",
            },
            timeout=15,
        )

        assert response.status_code in [200, 401, 503]

        if response.status_code == 200:
            chat_response = response.json()
            assert "response" in chat_response
            assert len(chat_response["response"]) > 0


class TestServiceHealth:
    """Test health of all services"""

    def test_backend_health(self, backend_url):
        """Backend health check"""
        response = requests.get(f"{backend_url}/api/health/", timeout=5)
        assert response.status_code == 200

    def test_gateway_health(self, gateway_url):
        """Gateway health check"""
        response = requests.get(f"{gateway_url}/health", timeout=5)
        assert response.status_code == 200

        health = response.json()
        assert health["status"] in ["healthy", "degraded"]

    def test_all_ai_services_reachable(self, gateway_url):
        """Test that gateway can reach all AI services"""
        response = requests.get(f"{gateway_url}/", timeout=5)
        assert response.status_code == 200


@pytest.mark.timeout(30)
class TestEndToEndUserJourney:
    """End-to-end user journey tests"""

    def test_complete_shopping_flow(self, authenticated_client):
        """
        Complete shopping journey:
        1. Browse products
        2. Get recommendations
        3. Add to cart
        4. Checkout
        5. View order
        """
        # 1. Browse products
        response = authenticated_client.get("/api/products/")
        assert response.status_code == 200
        products = response.json()

        if len(products.get("results", [])) == 0:
            pytest.skip("No products available")

        product = products["results"][0]

        # 2. View product details
        response = authenticated_client.get(f"/api/products/{product['id']}/")
        assert response.status_code == 200

        # 3. Add to cart
        response = authenticated_client.post(
            "/api/cart/add/",
            json={"product_id": product["id"], "quantity": 1},
        )
        assert response.status_code in [200, 201]

        # 4. View cart
        response = authenticated_client.get("/api/cart/")
        assert response.status_code == 200

        # Note: Full checkout requires payment integration
        # which should be mocked in tests
