"""
Pytest configuration and fixtures for E2E testing
"""
import pytest
import os
import sys
from pathlib import Path
import asyncio
import httpx
from typing import Dict, Any, Optional
import psycopg2
from decimal import Decimal
import json

# Add project root to path
project_root = Path(__file__).parent.parent.parent
backend_path = project_root / "services" / "backend"

# Insert paths at beginning
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Set working directory to backend
os.chdir(str(backend_path))

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Try to import Django
try:
    import django
    django.setup()
except Exception as e:
    print(f"Warning: Could not set up Django: {e}")
    # Continue anyway for non-Django tests

from django.contrib.auth import get_user_model
from apps.products.models import Product, Category, ProductVariant, ProductImage, Tag
from apps.orders.models import Order, OrderItem, Cart, CartItem
from apps.payments.models import Payment, PaymentMethod
from apps.accounts.models import Address

User = get_user_model()


# ============================================================
# CONFIGURATION
# ============================================================

@pytest.fixture(scope="session")
def test_config():
    """Test configuration"""
    return {
        "backend_url": os.getenv("BACKEND_URL", "http://localhost:8000"),
        "gateway_url": os.getenv("GATEWAY_URL", "http://localhost:8080"),
        "db_host": os.getenv("DB_HOST", "localhost"),
        "db_port": os.getenv("DB_PORT", "5432"),
        "db_name": os.getenv("DB_NAME", "ecommerce_db"),
        "db_user": os.getenv("DB_USER", "postgres"),
        "db_password": os.getenv("DB_PASSWORD", "postgres"),
        "timeout": 120,
        "max_retries": 3,
    }


# ============================================================
# HTTP CLIENT FIXTURES
# ============================================================

@pytest.fixture
async def http_client(test_config):
    """Async HTTP client for API requests"""
    async with httpx.AsyncClient(timeout=test_config["timeout"]) as client:
        yield client


@pytest.fixture
def sync_http_client(test_config):
    """Synchronous HTTP client for API requests"""
    with httpx.Client(timeout=test_config["timeout"]) as client:
        yield client


# ============================================================
# DATABASE FIXTURES
# ============================================================

@pytest.fixture(scope="session")
def db_connection(test_config):
    """PostgreSQL database connection"""
    conn = psycopg2.connect(
        host=test_config["db_host"],
        port=test_config["db_port"],
        database=test_config["db_name"],
        user=test_config["db_user"],
        password=test_config["db_password"]
    )
    yield conn
    conn.close()


@pytest.fixture
def db_cursor(db_connection):
    """Database cursor for queries"""
    cursor = db_connection.cursor()
    yield cursor
    cursor.close()
    db_connection.rollback()  # Rollback any changes


# ============================================================
# AUTHENTICATION FIXTURES
# ============================================================

@pytest.fixture
def test_users(django_db_blocker):
    """
    Returns test users from production database as a dictionary

    Users are created by the populate_production_db fixture.
    This fixture retrieves them and adds the test password for authentication.

    Returns dict with keys: alice, bob, charlie, new_user, vip, admin
    """
    with django_db_blocker.unblock():
        from django.contrib.auth import get_user_model
        User = get_user_model()

        # Known test passwords (from TestDataFactory)
        user_passwords = {
            "alice@example.com": "SecurePass123!",
            "bob@example.com": "SecurePass123!",
            "charlie@example.com": "SecurePass123!",
            "new.user@example.com": "Pass123!",
            "vip@example.com": "VIP123!",
            "admin@example.com": "Admin123!"
        }

        users = {}
        for email, password in user_passwords.items():
            try:
                user = User.objects.get(email=email)
                # Attach test password for authentication tests
                user._test_password = password
                # Extract name from email (alice@example.com -> alice, new.user -> new_user)
                name = email.split('@')[0].replace('.', '_')
                users[name] = user
            except User.DoesNotExist:
                # User not created yet, skip
                continue

        return users


@pytest.fixture(scope="session", autouse=True)
def populate_production_db(django_db_blocker):
    """
    Populate PRODUCTION database with E2E test data

    IMPORTANT: This uses the actual production database, not a test database.
    This provides true production-like E2E testing.

    Creates:
    - Users (alice, bob, charlie, admin, etc.)
    - Categories (Electronics, Clothing, Books, etc.)
    - Products (12 products including edge cases)
    - Tags and other test data

    Cleanup happens after all tests complete.
    """
    with django_db_blocker.unblock():
        # Import here to avoid Django setup issues
        import os
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
        import django
        django.setup()

        from factories.test_data_factory import TestDataFactory

        print("\n" + "="*70)
        print("🚀 Populating PRODUCTION database with E2E test data...")
        print("   Database: ecommerce (production)")
        print("   Mode: Production-like E2E testing")
        print("="*70)

        factory = TestDataFactory()
        created_data = factory.create_all()

        print("\n✅ Production database populated successfully!")
        print("="*70 + "\n")

        yield created_data

        # Cleanup after all tests complete
        print("\n" + "="*70)
        print("🧹 Cleaning up E2E test data from production database...")
        print("="*70)
        factory.cleanup()
        print("✅ Cleanup complete!")
        print("="*70 + "\n")


@pytest.fixture
def test_products():
    """
    Returns all active products from production database

    This queries the actual production database to get test products.
    Products are ordered by creation time for consistent indexing in tests.
    """
    from apps.products.models import Product
    products = list(Product.objects.filter(is_active=True).order_by('created_at', 'id'))
    return products


@pytest.fixture
def authenticated_client(sync_http_client, test_config, test_users):
    """
    HTTP client with authentication token

    Uses the first available user from test_users dictionary.
    Tests can access test_users directly to use specific users if needed.
    """
    # Use first available user from dictionary
    if not test_users:
        pytest.skip("No test users available")

    user = next(iter(test_users.values()))

    login_response = sync_http_client.post(
        f"{test_config['backend_url']}/api/auth/login/",
        json={
            "email": user.email,
            "password": user._test_password
        }
    )

    if login_response.status_code == 200:
        data = login_response.json()
        token = data.get("access")

        # Create new client with auth header
        client = httpx.Client(
            timeout=test_config["timeout"],
            headers={"Authorization": f"Bearer {token}"}
        )
        # Store user and token as attributes for tests that need them
        client._test_user = user
        client._test_token = token
        yield client  # Return client directly for backward compatibility
        client.close()
    else:
        pytest.skip(f"Could not authenticate: {login_response.text}")


# ============================================================
# DATA CLEANUP FIXTURES
# ============================================================

@pytest.fixture(autouse=True)
def cleanup_test_data(django_db_blocker):
    """Cleanup test data after each test"""
    yield

    # Cleanup in reverse order of dependencies
    with django_db_blocker.unblock():
        from apps.orders.models import OrderItem, Order, Cart, CartItem
        from apps.payments.models import Payment, Transaction
        from apps.products.models import ProductReview, ReviewHelpful, WishlistItem, Wishlist

        # Clean up wishlist items and wishlists
        WishlistItem.objects.filter(wishlist__user__email__contains="@example.com").delete()
        Wishlist.objects.filter(user__email__contains="@example.com").delete()

        # Clean up reviews and their dependencies
        ReviewHelpful.objects.filter(user__email__contains="@example.com").delete()
        ProductReview.objects.filter(user__email__contains="@example.com").delete()

        # Clean up in order: transactions → payments → order items → orders → cart items
        # Each has PROTECT FK to the next, so delete in reverse dependency order
        Transaction.objects.filter(payment__user__email__contains="@example.com").delete()
        Payment.objects.filter(user__email__contains="@example.com").delete()
        OrderItem.objects.filter(order__user__email__contains="@example.com").delete()
        Order.objects.filter(user__email__contains="@example.com").delete()
        CartItem.objects.filter(cart__user__email__contains="@example.com").delete()
        # Note: Don't delete Cart objects, just their items - carts will be reused

    # Don't delete users/products as they're needed across tests


# ============================================================
# ASSERTION HELPERS
# ============================================================

@pytest.fixture
def assert_response():
    """Helper for asserting API responses"""

    def _assert(response, expected_status=200, has_data=True):
        """Assert response status and structure"""
        assert response.status_code == expected_status, \
            f"Expected status {expected_status}, got {response.status_code}. Response: {response.text}"

        if expected_status < 400 and has_data:
            try:
                data = response.json()
                return data
            except json.JSONDecodeError:
                pytest.fail(f"Response is not valid JSON: {response.text}")

        return response

    return _assert


@pytest.fixture
def assert_db_state():
    """Helper for asserting database state"""

    def _assert(model, filter_kwargs, expected_count=None, **checks):
        """Assert database state"""
        queryset = model.objects.filter(**filter_kwargs)

        if expected_count is not None:
            actual_count = queryset.count()
            assert actual_count == expected_count, \
                f"Expected {expected_count} {model.__name__} objects, got {actual_count}"

        if checks:
            for obj in queryset:
                for field, expected_value in checks.items():
                    actual_value = getattr(obj, field)
                    assert actual_value == expected_value, \
                        f"Expected {field}={expected_value}, got {actual_value}"

        return queryset

    return _assert


# ============================================================
# PERFORMANCE TRACKING
# ============================================================

@pytest.fixture
def track_performance():
    """Track API response times"""
    timings = []

    def _track(endpoint, response_time_ms, max_time_ms=None):
        """Track response time"""
        timings.append({
            "endpoint": endpoint,
            "response_time_ms": response_time_ms,
            "max_time_ms": max_time_ms
        })

        if max_time_ms and response_time_ms > max_time_ms:
            pytest.fail(
                f"Endpoint {endpoint} took {response_time_ms}ms, "
                f"exceeds max {max_time_ms}ms"
            )

    yield _track

    # Print summary at end
    if timings:
        print("\n\n=== Performance Summary ===")
        for timing in timings:
            status = "✓" if not timing["max_time_ms"] or \
                     timing["response_time_ms"] <= timing["max_time_ms"] else "✗"
            print(f"{status} {timing['endpoint']}: {timing['response_time_ms']}ms")


# ============================================================
# TEST RESULT TRACKING
# ============================================================

@pytest.fixture(scope="session")
def test_results():
    """Track test results across session"""
    results = {
        "passed": [],
        "failed": [],
        "skipped": [],
        "errors": []
    }
    yield results


# ============================================================
# PYTEST CONFIGURATION
# ============================================================

def pytest_configure(config):
    """Pytest configuration"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end tests"
    )
    config.addinivalue_line(
        "markers", "security: marks tests as security tests"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection"""
    for item in items:
        # Add e2e marker to all tests in this directory
        if "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
