"""
==============================================================================
Load Testing with Locust
==============================================================================
This file defines load testing scenarios for the e-commerce platform.

Usage:
    # Basic load test
    locust -f tests/load/locustfile.py --host=http://localhost:8000

    # With web UI
    locust -f tests/load/locustfile.py --host=http://localhost:8000 --web-host=0.0.0.0

    # Headless mode
    locust -f tests/load/locustfile.py --host=http://localhost:8000 \
           --users 100 --spawn-rate 10 --run-time 5m --headless

    # With HTML report
    locust -f tests/load/locustfile.py --host=http://localhost:8000 \
           --users 100 --spawn-rate 10 --run-time 5m --headless \
           --html reports/load_test_report.html

Features:
    - Realistic user behavior patterns
    - Product browsing and search
    - Shopping cart operations
    - Checkout process
    - User authentication
    - AI service calls
==============================================================================
"""

from locust import HttpUser, task, between, SequentialTaskSet, tag
import random
import json


class UserBehavior(SequentialTaskSet):
    """
    Sequential task set representing realistic user journey
    """

    def on_start(self):
        """Setup - runs once per user at the start"""
        self.product_ids = []
        self.cart_id = None
        self.auth_token = None

    @task(1)
    @tag('auth')
    def register_or_login(self):
        """User registers or logs in"""
        # Try to login first
        email = f"loadtest_user_{random.randint(1, 1000)}@example.com"
        password = "TestPassword123!"

        # Attempt login
        response = self.client.post("/api/auth/login/", json={
            "email": email,
            "password": password
        }, name="/api/auth/login")

        if response.status_code == 200:
            self.auth_token = response.json().get('token')
        else:
            # Register if login fails
            response = self.client.post("/api/auth/register/", json={
                "email": email,
                "password": password,
                "first_name": "Load",
                "last_name": "Test"
            }, name="/api/auth/register")

            if response.status_code == 201:
                self.auth_token = response.json().get('token')

    @task(3)
    @tag('browsing')
    def browse_homepage(self):
        """User visits homepage"""
        self.client.get("/", name="Homepage")

    @task(5)
    @tag('browsing', 'products')
    def browse_products(self):
        """User browses product listings"""
        page = random.randint(1, 5)
        response = self.client.get(
            f"/api/products/?page={page}&page_size=20",
            name="/api/products/ (paginated)"
        )

        if response.status_code == 200:
            products = response.json().get('results', [])
            self.product_ids = [p['id'] for p in products[:10]]

    @task(4)
    @tag('browsing', 'products')
    def view_product_detail(self):
        """User views product details"""
        if not self.product_ids:
            return

        product_id = random.choice(self.product_ids)
        self.client.get(
            f"/api/products/{product_id}/",
            name="/api/products/[id]"
        )

    @task(3)
    @tag('search')
    def search_products(self):
        """User searches for products"""
        search_terms = ["laptop", "phone", "shoes", "watch", "headphones", "camera"]
        query = random.choice(search_terms)

        self.client.get(
            f"/api/products/search/?q={query}",
            name="/api/products/search"
        )

    @task(2)
    @tag('ai', 'recommendations')
    def get_recommendations(self):
        """User gets AI recommendations"""
        if not self.auth_token:
            return

        headers = {"Authorization": f"Bearer {self.auth_token}"}
        self.client.get(
            "/api/ai/recommendations/",
            headers=headers,
            name="/api/ai/recommendations"
        )

    @task(2)
    @tag('cart')
    def add_to_cart(self):
        """User adds product to cart"""
        if not self.product_ids:
            return

        product_id = random.choice(self.product_ids)
        quantity = random.randint(1, 3)

        headers = {}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        response = self.client.post(
            "/api/cart/items/",
            json={
                "product_id": product_id,
                "quantity": quantity
            },
            headers=headers,
            name="/api/cart/items/ (add)"
        )

        if response.status_code in [200, 201]:
            self.cart_id = response.json().get('cart_id')

    @task(1)
    @tag('cart')
    def view_cart(self):
        """User views shopping cart"""
        headers = {}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        self.client.get(
            "/api/cart/",
            headers=headers,
            name="/api/cart/ (view)"
        )

    @task(1)
    @tag('cart')
    def update_cart_quantity(self):
        """User updates item quantity in cart"""
        if not self.auth_token or not self.product_ids:
            return

        headers = {"Authorization": f"Bearer {self.auth_token}"}
        product_id = random.choice(self.product_ids)
        new_quantity = random.randint(1, 5)

        self.client.patch(
            f"/api/cart/items/{product_id}/",
            json={"quantity": new_quantity},
            headers=headers,
            name="/api/cart/items/[id] (update)"
        )

    @task(1)
    @tag('checkout', 'ai')
    def fraud_check(self):
        """Simulate fraud detection check during checkout"""
        if not self.auth_token:
            return

        headers = {"Authorization": f"Bearer {self.auth_token}"}
        self.client.post(
            "/api/ai/fraud-detection/",
            json={
                "amount": random.uniform(10, 500),
                "card_last4": "4242",
                "ip_address": f"192.168.1.{random.randint(1, 255)}"
            },
            headers=headers,
            name="/api/ai/fraud-detection"
        )

    @task(1)
    @tag('checkout')
    def initiate_checkout(self):
        """User initiates checkout (doesn't complete to avoid charges)"""
        if not self.auth_token:
            return

        headers = {"Authorization": f"Bearer {self.auth_token}"}
        self.client.get(
            "/api/checkout/",
            headers=headers,
            name="/api/checkout/ (initiate)"
        )


class BrowsingUser(HttpUser):
    """
    User that mostly browses and searches
    """
    tasks = [UserBehavior]
    wait_time = between(1, 5)  # Wait 1-5 seconds between tasks
    weight = 10  # 10x more browsing users than buyers


class BuyingUser(HttpUser):
    """
    User that browses and makes purchases
    """
    tasks = [UserBehavior]
    wait_time = between(2, 8)  # Slower, more deliberate
    weight = 1  # Fewer buying users


class APIUser(HttpUser):
    """
    Direct API testing user (no browser simulation)
    """
    wait_time = between(0.5, 2)

    @task(10)
    @tag('api', 'products')
    def get_products(self):
        self.client.get("/api/products/")

    @task(5)
    @tag('api', 'search')
    def search(self):
        queries = ["laptop", "phone", "shirt"]
        self.client.get(f"/api/products/search/?q={random.choice(queries)}")

    @task(3)
    @tag('api', 'categories')
    def get_categories(self):
        self.client.get("/api/categories/")

    @task(2)
    @tag('api', 'ai')
    def ai_recommendation(self):
        self.client.get("/api/ai/recommendations/")


# Custom shape for realistic traffic patterns
from locust import LoadTestShape


class DailyTrafficShape(LoadTestShape):
    """
    Simulates daily traffic pattern:
    - Low traffic at night
    - Gradual increase in morning
    - Peak during business hours
    - Gradual decrease in evening
    """

    stages = [
        # (duration_seconds, users, spawn_rate)
        (60, 10, 2),      # Ramp up to 10 users
        (120, 50, 5),     # Increase to 50 users
        (180, 100, 10),   # Peak at 100 users
        (240, 100, 0),    # Maintain 100 users
        (300, 50, 5),     # Decrease to 50
        (360, 10, 2),     # Wind down to 10
    ]

    def tick(self):
        run_time = self.get_run_time()

        for duration, users, spawn_rate in self.stages:
            if run_time < duration:
                return (users, spawn_rate)

        return None  # End of test


class SpikeTrafficShape(LoadTestShape):
    """
    Simulates sudden traffic spikes (e.g., flash sale)
    """

    def tick(self):
        run_time = self.get_run_time()

        if run_time < 60:
            return (10, 2)  # Normal traffic
        elif run_time < 120:
            return (200, 50)  # Sudden spike
        elif run_time < 240:
            return (200, 0)  # Maintain spike
        elif run_time < 300:
            return (10, 5)  # Back to normal
        else:
            return None
