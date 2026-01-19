"""
Pytest configuration and fixtures for full stack validation
"""
import pytest
import os
import sys
from pathlib import Path

# Load environment variables from .env.test
from dotenv import load_dotenv

env_file = Path(__file__).parent.parent.parent / '.env.test'
if env_file.exists():
    load_dotenv(env_file)
    print(f"✅ Loaded test environment from {env_file}")


# Add Django backend to Python path
backend_path = Path(__file__).parent.parent.parent / 'services' / 'backend'
if backend_path.exists():
    sys.path.insert(0, str(backend_path))


# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')


@pytest.fixture(scope='session')
def django_db_setup():
    """Setup Django database for testing"""
    try:
        import django
        django.setup()
    except Exception:
        return


@pytest.fixture
def base_url():
    """Base URL for Django backend"""
    return os.environ.get('BACKEND_URL', 'http://localhost:8000')


@pytest.fixture
def api_gateway_url():
    """Base URL for API Gateway"""
    return os.environ.get('GATEWAY_URL', 'http://localhost:8080')



@pytest.fixture(scope='session')
def test_user_credentials():
    """Test user credentials"""
    return {
        'email': os.environ.get('TEST_USER_EMAIL', 'test@example.com'),
        'password': os.environ.get('TEST_USER_PASSWORD', 'testpass123'),
    }


def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers", "django_db: mark test as requiring database access"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "security: mark test as security test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as performance test"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection"""
    for item in items:
        # Auto-mark tests based on file/function name
        if "security" in item.nodeid:
            item.add_marker(pytest.mark.security)
        if "performance" in item.nodeid or "load" in item.nodeid:
            item.add_marker(pytest.mark.performance)


@pytest.fixture(autouse=True)
def reset_db_state(django_db_setup, django_db_blocker):
    """Reset database state between tests"""
    # This runs before each test
    yield
    # Cleanup after test
