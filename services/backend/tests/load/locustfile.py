"""
Comprehensive Load Testing Suite for E-commerce Platform

This locustfile defines realistic user behavior patterns for load testing
all critical endpoints of the e-commerce platform.

Usage:
    # Run with web UI
    locust -f locustfile.py --host=http://localhost:8000

    # Run headless
    locust -f locustfile.py --host=http://localhost:8000 \
           --users 100 --spawn-rate 10 --run-time 10m --headless

    # Generate HTML report
    locust -f locustfile.py --host=http://localhost:8000 \
           --users 500 --spawn-rate 50 --run-time 10m --headless \
           --html=reports/load_test_report.html
"""

import random
import json
from locust import HttpUser, task, between, SequentialTaskSet, TaskSet
from locust.exception import RescheduleTask


# ==============================================================================
# Configuration
# ==============================================================================

# Product IDs range (adjust based on your database)
PRODUCT_ID_RANGE = (1, 1000)

# Sample product categories
CATEGORIES = ['electronics', 'clothing', 'books', 'home', 'sports']

# Sample search queries
SEARCH_QUERIES = [
    'laptop', 'phone', 'camera', 'headphones', 'keyboard',
    'shirt', 't-shirt', 'jeans', 'shoes', 'jacket',
    'novel', 'textbook', 'magazine', 'cookbook',
    'furniture', 'decor', 'kitchen', 'bedding',
    'fitness', 'outdoor', 'cycling', 'running'
]

# Sample user credentials for authenticated requests
TEST_USERS = [
    {'email': f'testuser{i}@example.com', 'password': 'testpass123'}
    for i in range(1, 11)
]


# ==============================================================================
# Helper Functions
# ==============================================================================

def random_product_id():
    """Generate a random product ID"""
    return random.randint(*PRODUCT_ID_RANGE)


def random_quantity():
    """Generate a realistic quantity (1-5 items)"""
    return random.randint(1, 5)


# ==============================================================================
# Task Sets
# ==============================================================================

class BrowsingBehavior(TaskSet):
    """
    Anonymous user browsing behavior
    Weight: 40% of users
    """

    @task(5)
    def browse_homepage(self):
        """Visit homepage"""
        self.client.get("/")

    @task(10)
    def browse_products(self):
        """Browse product listings"""
        page = random.randint(1, 10)
        self.client.get(f"/api/v1/products/?page={page}")

    @task(3)
    def browse_category(self):
        """Browse products by category"""
        category = random.choice(CATEGORIES)
        self.client.get(f"/api/v1/products/?category={category}")

    @task(8)
    def view_product_detail(self):
        """View individual product details"""
        product_id = random_product_id()
        with self.client.get(
            f"/api/v1/products/{product_id}/",
            catch_response=True
        ) as response:
            if response.status_code == 404:
                # Product doesn't exist, try another
                response.success()

    @task(2)
    def search_products(self):
        """Search for products"""
        query = random.choice(SEARCH_QUERIES)
        self.client.get(f"/api/v1/products/search/?q={query}")

    @task(1)
    def view_recommendations(self):
        """View AI-powered product recommendations"""
        product_id = random_product_id()
        with self.client.get(
            f"/api/v1/products/{product_id}/recommendations/",
            catch_response=True
        ) as response:
            if response.status_code == 404:
                response.success()


class ShoppingBehavior(SequentialTaskSet):
    """
    Authenticated user shopping flow
    Weight: 30% of users

    Follows a realistic shopping journey:
    1. Login
    2. Browse products
    3. Add to cart
    4. View cart
    5. Update cart
    6. Proceed to checkout
    7. Logout
    """

    def on_start(self):
        """Login before shopping"""
        user = random.choice(TEST_USERS)
        response = self.client.post("/api/v1/auth/login/", json={
            "email": user['email'],
            "password": user['password']
        }, catch_response=True)

        if response.status_code == 200:
            # Store auth token
            self.token = response.json().get('access_token')
            self.headers = {'Authorization': f'Bearer {self.token}'}
        else:
            # If login fails, reschedule to try again
            raise RescheduleTask()

    @task
    def browse_products(self):
        """Browse products (authenticated)"""
        for _ in range(random.randint(3, 7)):
            page = random.randint(1, 5)
            self.client.get(
                f"/api/v1/products/?page={page}",
                headers=self.headers
            )

    @task
    def view_product_details(self):
        """View multiple product details"""
        for _ in range(random.randint(2, 5)):
            product_id = random_product_id()
            self.client.get(
                f"/api/v1/products/{product_id}/",
                headers=self.headers,
                catch_response=True
            )

    @task
    def add_to_cart(self):
        """Add products to cart"""
        for _ in range(random.randint(1, 3)):
            self.client.post(
                "/api/v1/cart/items/",
                headers=self.headers,
                json={
                    "product_id": random_product_id(),
                    "quantity": random_quantity()
                },
                catch_response=True
            )

    @task
    def view_cart(self):
        """View shopping cart"""
        self.client.get("/api/v1/cart/", headers=self.headers)

    @task
    def update_cart(self):
        """Update cart quantities"""
        # Get cart first
        response = self.client.get("/api/v1/cart/", headers=self.headers)
        if response.status_code == 200:
            cart = response.json()
            if cart.get('items'):
                # Update first item quantity
                item_id = cart['items'][0]['id']
                self.client.patch(
                    f"/api/v1/cart/items/{item_id}/",
                    headers=self.headers,
                    json={"quantity": random_quantity()}
                )

    @task
    def view_checkout(self):
        """View checkout page"""
        self.client.get("/api/v1/checkout/", headers=self.headers)

    @task
    def logout(self):
        """Logout"""
        self.client.post("/api/v1/auth/logout/", headers=self.headers)
        self.interrupt()  # End this task set


class CheckoutBehavior(SequentialTaskSet):
    """
    Complete purchase flow
    Weight: 10% of users

    Simulates the complete checkout and payment process.
    """

    def on_start(self):
        """Login and setup cart"""
        user = random.choice(TEST_USERS)
        response = self.client.post("/api/v1/auth/login/", json={
            "email": user['email'],
            "password": user['password']
        })

        if response.status_code == 200:
            self.token = response.json().get('access_token')
            self.headers = {'Authorization': f'Bearer {self.token}'}

            # Add items to cart
            for _ in range(random.randint(1, 3)):
                self.client.post(
                    "/api/v1/cart/items/",
                    headers=self.headers,
                    json={
                        "product_id": random_product_id(),
                        "quantity": random_quantity()
                    }
                )
        else:
            raise RescheduleTask()

    @task
    def view_cart(self):
        """Review cart before checkout"""
        self.client.get("/api/v1/cart/", headers=self.headers)

    @task
    def start_checkout(self):
        """Initiate checkout process"""
        self.client.get("/api/v1/checkout/", headers=self.headers)

    @task
    def add_shipping_address(self):
        """Add shipping address"""
        self.client.post(
            "/api/v1/checkout/shipping/",
            headers=self.headers,
            json={
                "address_line1": "123 Test St",
                "city": "Test City",
                "state": "TS",
                "zip_code": "12345",
                "country": "US"
            }
        )

    @task
    def select_payment_method(self):
        """Select payment method"""
        self.client.post(
            "/api/v1/checkout/payment/",
            headers=self.headers,
            json={
                "payment_method": "credit_card",
                "card_token": "tok_visa"  # Test token
            }
        )

    @task
    def place_order(self):
        """Place the order"""
        response = self.client.post(
            "/api/v1/orders/",
            headers=self.headers,
            json={
                "payment_method": "credit_card"
            },
            catch_response=True
        )

        if response.status_code in [200, 201]:
            response.success()
        else:
            # Order failed, but don't fail the test
            response.failure(f"Order failed: {response.status_code}")

        self.interrupt()  # End this task set


class AccountManagementBehavior(TaskSet):
    """
    User account management activities
    Weight: 15% of users
    """

    def on_start(self):
        """Login"""
        user = random.choice(TEST_USERS)
        response = self.client.post("/api/v1/auth/login/", json={
            "email": user['email'],
            "password": user['password']
        })

        if response.status_code == 200:
            self.token = response.json().get('access_token')
            self.headers = {'Authorization': f'Bearer {self.token}'}
        else:
            raise RescheduleTask()

    @task(3)
    def view_profile(self):
        """View user profile"""
        self.client.get("/api/v1/accounts/profile/", headers=self.headers)

    @task(1)
    def update_profile(self):
        """Update profile information"""
        self.client.patch(
            "/api/v1/accounts/profile/",
            headers=self.headers,
            json={
                "first_name": "Test",
                "last_name": "User"
            }
        )

    @task(2)
    def view_order_history(self):
        """View past orders"""
        self.client.get("/api/v1/orders/", headers=self.headers)

    @task(1)
    def view_order_detail(self):
        """View specific order details"""
        # Get orders first
        response = self.client.get("/api/v1/orders/", headers=self.headers)
        if response.status_code == 200:
            orders = response.json().get('results', [])
            if orders:
                order_id = orders[0]['id']
                self.client.get(
                    f"/api/v1/orders/{order_id}/",
                    headers=self.headers
                )

    @task(1)
    def view_wishlist(self):
        """View wishlist"""
        self.client.get("/api/v1/wishlist/", headers=self.headers)


class SearchAndFilterBehavior(TaskSet):
    """
    Heavy search and filtering behavior
    Weight: 5% of users

    Simulates users extensively using search and filter features.
    """

    @task(3)
    def search_products(self):
        """Perform product searches"""
        query = random.choice(SEARCH_QUERIES)
        self.client.get(f"/api/v1/products/search/?q={query}")

    @task(2)
    def filter_by_category(self):
        """Filter products by category"""
        category = random.choice(CATEGORIES)
        self.client.get(f"/api/v1/products/?category={category}")

    @task(2)
    def filter_by_price(self):
        """Filter products by price range"""
        min_price = random.choice([0, 10, 50, 100])
        max_price = min_price + random.choice([50, 100, 500])
        self.client.get(
            f"/api/v1/products/?min_price={min_price}&max_price={max_price}"
        )

    @task(1)
    def complex_filter(self):
        """Apply multiple filters"""
        category = random.choice(CATEGORIES)
        min_price = random.choice([10, 50, 100])
        max_price = min_price + 200
        sort = random.choice(['price', '-price', 'created_at'])

        self.client.get(
            f"/api/v1/products/?category={category}"
            f"&min_price={min_price}&max_price={max_price}&ordering={sort}"
        )


# ==============================================================================
# User Classes
# ==============================================================================

class AnonymousUser(HttpUser):
    """
    Anonymous users browsing the site
    Weight: 40%
    """
    weight = 40
    wait_time = between(2, 5)
    tasks = [BrowsingBehavior]


class ShopperUser(HttpUser):
    """
    Authenticated users shopping
    Weight: 30%
    """
    weight = 30
    wait_time = between(3, 8)
    tasks = [ShoppingBehavior]


class BuyerUser(HttpUser):
    """
    Users completing purchases
    Weight: 10%
    """
    weight = 10
    wait_time = between(5, 15)
    tasks = [CheckoutBehavior]


class AccountUser(HttpUser):
    """
    Users managing their account
    Weight: 15%
    """
    weight = 15
    wait_time = between(3, 10)
    tasks = [AccountManagementBehavior]


class PowerSearchUser(HttpUser):
    """
    Users heavily using search and filters
    Weight: 5%
    """
    weight = 5
    wait_time = between(1, 3)
    tasks = [SearchAndFilterBehavior]
