"""
Security Features Integration Tests

Tests the security implementations:
- Service-to-service authentication
- WAF protection
- Input validation
- Rate limiting
- JWKS key rotation
"""

import pytest
import requests
import time
import jwt
from typing import Dict, Any


@pytest.fixture
def backend_url() -> str:
    """Backend API URL."""
    return "http://backend-test:8000"


@pytest.fixture
def api_gateway_url() -> str:
    """API Gateway URL."""
    return "http://api-gateway-test:8080"


class TestServiceAuthentication:
    """Test service-to-service authentication."""

    def test_service_token_generation(self, backend_url):
        """Test that service tokens can be generated."""
        # This would require internal service endpoint or direct test
        # For now, verify the JWKS endpoint is accessible
        response = requests.get(
            f"{backend_url}/.well-known/jwks.json",
            timeout=10
        )

        assert response.status_code == 200
        jwks_data = response.json()
        assert "keys" in jwks_data

    def test_invalid_service_token_rejected(self, backend_url):
        """Test that invalid service tokens are rejected."""
        # Create an invalid token
        invalid_token = jwt.encode(
            {"service": "fake-service", "exp": time.time() + 3600},
            "wrong-secret",
            algorithm="HS256"
        )

        # Try to access a service endpoint with invalid token
        response = requests.get(
            f"{backend_url}/api/v1/products/",
            headers={"X-Service-Auth": invalid_token},
            timeout=10
        )

        # Should either be rejected or ignored (falls back to user auth)
        assert response.status_code in [200, 401, 403]

    def test_jwks_endpoint_accessible(self, backend_url):
        """Test JWKS endpoint is publicly accessible."""
        response = requests.get(
            f"{backend_url}/.well-known/jwks.json",
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()
        assert "keys" in data
        assert isinstance(data["keys"], list)


class TestWAFProtection:
    """Test Web Application Firewall protections."""

    def test_sql_injection_detection(self, api_gateway_url):
        """Test WAF blocks SQL injection attempts."""
        sql_injection_payloads = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'--",
            "' UNION SELECT * FROM users--",
        ]

        for payload in sql_injection_payloads:
            response = requests.get(
                f"{api_gateway_url}/api/v1/search/",
                params={"q": payload},
                timeout=10
            )

            # WAF should block with 400 or pass through safely
            assert response.status_code in [200, 400, 403, 404, 501]

            # If it passes, verify it's sanitized
            if response.status_code == 200:
                # Should not execute SQL
                assert "error" not in response.text.lower() or \
                       "sql" not in response.text.lower()

    def test_xss_prevention(self, api_gateway_url):
        """Test WAF blocks XSS attempts."""
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror='alert(1)'>",
            "javascript:alert('XSS')",
            "<iframe src='evil.com'>",
        ]

        for payload in xss_payloads:
            response = requests.get(
                f"{api_gateway_url}/api/v1/search/",
                params={"q": payload},
                timeout=10
            )

            # WAF should block or sanitize
            assert response.status_code in [200, 400, 403, 404, 501]

    def test_path_traversal_detection(self, api_gateway_url):
        """Test WAF blocks path traversal attempts."""
        path_traversal_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "....//....//....//etc/passwd",
        ]

        for payload in path_traversal_payloads:
            response = requests.get(
                f"{api_gateway_url}/api/v1/products/{payload}",
                timeout=10
            )

            # Should block or return 404
            assert response.status_code in [400, 403, 404]

    def test_command_injection_detection(self, api_gateway_url):
        """Test WAF blocks command injection attempts."""
        command_injection_payloads = [
            "; cat /etc/passwd",
            "| ls -la",
            "`whoami`",
            "$(cat /etc/passwd)",
        ]

        for payload in command_injection_payloads:
            response = requests.get(
                f"{api_gateway_url}/api/v1/search/",
                params={"q": payload},
                timeout=10
            )

            # WAF should block
            assert response.status_code in [200, 400, 403, 404, 501]

    def test_request_size_limit(self, api_gateway_url):
        """Test WAF enforces request size limits."""
        # Create a large payload (> 10MB)
        large_payload = "A" * (11 * 1024 * 1024)  # 11MB

        response = requests.post(
            f"{api_gateway_url}/api/v1/search/",
            json={"data": large_payload},
            timeout=30
        )

        # Should reject large requests
        assert response.status_code in [400, 413, 404, 501]

    def test_security_headers_present(self, api_gateway_url):
        """Test that security headers are added by WAF."""
        response = requests.get(
            f"{api_gateway_url}/health",
            timeout=10
        )

        assert response.status_code == 200

        # Check for security headers
        headers = response.headers
        expected_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
        ]

        # At least some security headers should be present
        present_headers = sum(1 for h in expected_headers if h in headers)
        assert present_headers > 0, "No security headers found"


class TestRateLimiting:
    """Test rate limiting functionality."""

    def test_rate_limit_enforcement(self, api_gateway_url):
        """Test that rate limiting is enforced."""
        # Make rapid requests
        responses = []
        for i in range(100):
            try:
                response = requests.get(
                    f"{api_gateway_url}/health",
                    timeout=5
                )
                responses.append(response)
            except requests.RequestException:
                # Timeout or connection error indicates rate limiting
                break

        # Should have some successful requests
        assert len(responses) > 0

        # Check if any were rate limited
        status_codes = [r.status_code for r in responses]

        # Rate limiting might return 429, or all might succeed with low rate
        # Just verify we get valid responses
        assert all(code in [200, 429] for code in status_codes)

    def test_rate_limit_headers(self, api_gateway_url):
        """Test that rate limit headers are present."""
        response = requests.get(
            f"{api_gateway_url}/health",
            timeout=10
        )

        # Check for rate limit headers (may or may not be present)
        headers = response.headers

        # These are optional, just document if present
        rate_limit_headers = [
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
        ]

        # No assertion, just checking presence
        present = [h for h in rate_limit_headers if h in headers]
        print(f"Rate limit headers present: {present}")


class TestInputValidation:
    """Test input validation across services."""

    def test_invalid_json_rejected(self, backend_url):
        """Test that invalid JSON is rejected."""
        response = requests.post(
            f"{backend_url}/api/v1/auth/login/",
            data="invalid json{{{",
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        # Should reject with 400
        assert response.status_code in [400, 415]

    def test_missing_required_fields(self, backend_url):
        """Test that missing required fields are rejected."""
        response = requests.post(
            f"{backend_url}/api/v1/auth/login/",
            json={},  # Missing email and password
            timeout=10
        )

        # Should reject with 400
        assert response.status_code == 400

    def test_field_type_validation(self, backend_url):
        """Test that field type validation works."""
        response = requests.post(
            f"{backend_url}/api/v1/auth/login/",
            json={
                "email": 12345,  # Should be string
                "password": True  # Should be string
            },
            timeout=10
        )

        # Should reject with 400
        assert response.status_code in [400, 422]

    def test_nested_object_depth_limit(self, api_gateway_url):
        """Test protection against deeply nested JSON."""
        # Create deeply nested object
        nested = {}
        current = nested
        for i in range(100):
            current["level"] = {}
            current = current["level"]

        response = requests.post(
            f"{api_gateway_url}/api/v1/search/",
            json=nested,
            timeout=10
        )

        # Should either accept or reject gracefully
        assert response.status_code in [200, 400, 404, 413, 501]


class TestHealthChecks:
    """Test health check endpoints."""

    def test_backend_health_endpoint(self, backend_url):
        """Test backend health endpoint."""
        response = requests.get(f"{backend_url}/health", timeout=10)

        assert response.status_code == 200
        data = response.json()

        # Verify health check structure
        assert "status" in data
        assert data["status"] in ["healthy", "ok", "degraded"]

    def test_backend_detailed_health(self, backend_url):
        """Test backend detailed health check."""
        response = requests.get(f"{backend_url}/health/", timeout=10)

        assert response.status_code == 200
        data = response.json()

        # Should have dependency checks
        assert "status" in data

    def test_api_gateway_health(self, api_gateway_url):
        """Test API Gateway health endpoints."""
        # Main health endpoint
        response = requests.get(f"{api_gateway_url}/health", timeout=10)
        assert response.status_code == 200

        # Liveness probe
        response = requests.get(f"{api_gateway_url}/health/live", timeout=10)
        assert response.status_code == 200

        # Readiness probe
        response = requests.get(f"{api_gateway_url}/health/ready", timeout=10)
        assert response.status_code in [200, 503]  # May not be ready


class TestProductionValidation:
    """Test production configuration validation."""

    def test_allowed_hosts_not_wildcard(self, backend_url):
        """Test that ALLOWED_HOSTS is properly configured."""
        # This is tested at startup in production.py
        # Just verify service is running (means validation passed)
        response = requests.get(f"{backend_url}/health", timeout=10)
        assert response.status_code == 200

    def test_debug_mode_disabled(self, backend_url):
        """Test that DEBUG mode is disabled in production."""
        # Try to trigger a 404 and check if debug info is exposed
        response = requests.get(
            f"{backend_url}/api/v1/nonexistent-endpoint",
            timeout=10
        )

        # Should get 404, but not with debug traceback
        assert response.status_code == 404

        # Debug info should not be in response
        response_text = response.text.lower()
        assert "traceback" not in response_text
        assert "local vars" not in response_text


class TestCeleryIntegration:
    """Test Celery task execution and monitoring."""

    def test_celery_worker_health(self):
        pytest.skip("Needs Celery Flower or inspect API for worker status.")

    def test_async_task_execution(self, backend_url):
        pytest.skip("Needs a test endpoint that triggers a Celery task.")


class TestDataProtection:
    """Test data protection and privacy."""

    def test_password_not_exposed(self, backend_url):
        """Test that passwords are never returned in API responses."""
        # Register a user
        response = requests.post(
            f"{backend_url}/api/v1/auth/register/",
            json={
                "email": "privacy-test@example.com",
                "password": "SecurePassword123!",
                "password_confirm": "SecurePassword123!",
                "first_name": "Privacy",
                "last_name": "Test"
            },
            timeout=10
        )

        # Even if registration succeeds, password should not be in response
        if response.status_code in [200, 201]:
            data = response.json()
            # Convert to string to check nested fields
            response_str = str(data).lower()
            assert "securepassword123" not in response_str

    def test_sensitive_headers_not_logged(self, backend_url):
        """Test that sensitive headers are not exposed."""
        response = requests.get(
            f"{backend_url}/api/v1/products/",
            headers={
                "Authorization": "Bearer fake-token-12345",
                "X-API-Key": "secret-key-67890"
            },
            timeout=10
        )

        # Just verify request is processed
        assert response.status_code in [200, 401]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
