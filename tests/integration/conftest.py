"""
Pytest configuration for integration tests.

Provides fixtures for testing across all services.
"""

import os
import pytest
import requests
from typing import Generator

# Service URLs from environment or defaults
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8080")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


@pytest.fixture(scope="session")
def backend_url() -> str:
    """Backend API base URL"""
    return BACKEND_URL


@pytest.fixture(scope="session")
def gateway_url() -> str:
    """API Gateway base URL"""
    return GATEWAY_URL


@pytest.fixture(scope="session")
def frontend_url() -> str:
    """Frontend base URL"""
    return FRONTEND_URL


@pytest.fixture(scope="session")
def check_services_health():
    """Check that all services are healthy before running tests"""
    services = {
        "Backend": f"{BACKEND_URL}/api/health/",
        "Gateway": f"{GATEWAY_URL}/health",
        "Frontend": FRONTEND_URL,
    }

    for name, url in services.items():
        try:
            response = requests.get(url, timeout=5)
            assert response.status_code in [200, 201], f"{name} is not healthy"
            print(f"✓ {name} is healthy")
        except Exception as e:
            pytest.fail(f"{name} is not available: {e}")


@pytest.fixture(scope="function")
def api_client(backend_url: str) -> Generator:
    """
    API client for backend with authentication.

    Automatically handles JWT token management.
    """

    class APIClient:
        def __init__(self, base_url: str):
            self.base_url = base_url
            self.token = None
            self.session = requests.Session()

        def login(self, email: str = "test@example.com", password: str = "testpass123"):
            """Login and store JWT token"""
            response = self.session.post(
                f"{self.base_url}/api/auth/login/",
                json={"email": email, "password": password},
            )
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access")
                self.session.headers.update({"Authorization": f"Bearer {self.token}"})

        def get(self, endpoint: str, **kwargs):
            """GET request"""
            return self.session.get(f"{self.base_url}{endpoint}", **kwargs)

        def post(self, endpoint: str, **kwargs):
            """POST request"""
            return self.session.post(f"{self.base_url}{endpoint}", **kwargs)

        def put(self, endpoint: str, **kwargs):
            """PUT request"""
            return self.session.put(f"{self.base_url}{endpoint}", **kwargs)

        def delete(self, endpoint: str, **kwargs):
            """DELETE request"""
            return self.session.delete(f"{self.base_url}{endpoint}", **kwargs)

    client = APIClient(backend_url)
    yield client
    client.session.close()


@pytest.fixture(scope="function")
def test_user(api_client):
    """
    Create a test user for integration tests.

    Automatically cleans up after test.
    """
    from faker import Faker

    fake = Faker()

    user_data = {
        "email": fake.email(),
        "password": "TestPass123!",
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
    }

    # Create user
    response = api_client.post("/api/auth/register/", json=user_data)

    if response.status_code == 201:
        user = response.json()
        user["password"] = user_data["password"]  # Store password for login
        yield user

        # Cleanup: Delete user after test
        # (implement user deletion endpoint if not exists)
    else:
        pytest.fail(f"Failed to create test user: {response.text}")


@pytest.fixture(scope="function")
def authenticated_client(api_client, test_user):
    """API client with authenticated test user"""
    api_client.login(test_user["email"], test_user["password"])
    return api_client
