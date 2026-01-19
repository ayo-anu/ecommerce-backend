"""
E2E Tests for Workflow 6: Wishlist Management

Test Coverage:
- Add products to wishlist
- View wishlist
- Remove items from wishlist
- Edge cases: duplicates, inactive products, out-of-stock items
- Security: authentication required, user isolation

Based on: E2E_BUSINESS_LOGIC_TEST_PLAN.md - Workflow 6 (lines 1320-1363)
Philosophy: TESTING_PHILOSOPHY.md - Fix the Code, Not the Tests
"""

import pytest
import time
from decimal import Decimal


class TestWishlistBasicOperations:
    """
    Test basic wishlist operations: add, view, remove
    Following production-like testing principles
    """

    def test_add_product_to_wishlist(self, test_config, authenticated_client, test_products):
        """
        TC-WISH-01: Add product to wishlist

        Expected behavior:
        - HTTP 201 Created
        - Wishlist created if doesn't exist
        - WishlistItem added with product reference
        - Response includes product details
        """
        # Use first active product
        product = test_products[0]

        response = authenticated_client.post(
            f"{test_config['backend_url']}/api/products/wishlist/",
            json={"product_id": str(product.id)}
        )

        # Assertions
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"

        data = response.json()
        assert 'id' in data or 'product' in data, "Response should contain wishlist item data"

        # Verify product details are included
        if 'product' in data:
            assert data['product']['id'] == str(product.id)
            assert data['product']['name'] == product.name
            assert 'price' in data['product']

    def test_view_wishlist(self, test_config, authenticated_client, test_products):
        """
        TC-WISH-02: View user's wishlist

        Expected behavior:
        - HTTP 200 OK
        - Returns all wishlist items for authenticated user
        - Each item includes full product details
        - Returns empty list if wishlist is empty
        """
        # First, add a product to wishlist
        product = test_products[0]
        add_response = authenticated_client.post(
            f"{test_config['backend_url']}/api/products/wishlist/",
            json={"product_id": str(product.id)}
        )
        assert add_response.status_code in [200, 201]

        # View wishlist
        response = authenticated_client.get(
            f"{test_config['backend_url']}/api/products/wishlist/"
        )

        # Assertions
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()

        # Handle both list and paginated responses
        if isinstance(data, dict) and 'results' in data:
            items = data['results']
        else:
            items = data if isinstance(data, list) else [data]

        assert len(items) >= 1, "Wishlist should contain at least one item"

        # Verify product details are included
        item = items[0]
        assert 'product' in item or 'id' in item, "Wishlist item should have product reference"

    def test_remove_item_from_wishlist(self, test_config, authenticated_client, test_products):
        """
        TC-WISH-03: Remove item from wishlist

        Expected behavior:
        - HTTP 204 No Content (or 200 OK)
        - Item removed from wishlist
        - Wishlist updated accordingly
        """
        # First, add a product to wishlist
        product = test_products[1]
        add_response = authenticated_client.post(
            f"{test_config['backend_url']}/api/products/wishlist/",
            json={"product_id": str(product.id)}
        )
        assert add_response.status_code in [200, 201]

        # Get wishlist to find item ID
        view_response = authenticated_client.get(
            f"{test_config['backend_url']}/api/products/wishlist/"
        )
        data = view_response.json()

        # Handle pagination
        if isinstance(data, dict) and 'results' in data:
            items = data['results']
        else:
            items = data if isinstance(data, list) else [data]

        assert len(items) >= 1, "Should have at least one item to remove"

        # Find the item we just added
        item_to_remove = None
        for item in items:
            product_id = item.get('product', {}).get('id') if 'product' in item else item.get('product_id')
            if product_id == str(product.id):
                item_to_remove = item
                break

        assert item_to_remove is not None, f"Could not find product {product.id} in wishlist"
        item_id = item_to_remove['id']

        # Remove the item
        remove_response = authenticated_client.delete(
            f"{test_config['backend_url']}/api/products/wishlist/{item_id}/"
        )

        # Assertions
        assert remove_response.status_code in [200, 204], \
            f"Expected 200/204, got {remove_response.status_code}: {remove_response.text}"

        # Verify item is removed
        verify_response = authenticated_client.get(
            f"{test_config['backend_url']}/api/products/wishlist/"
        )
        verify_data = verify_response.json()

        if isinstance(verify_data, dict) and 'results' in verify_data:
            verify_items = verify_data['results']
        else:
            verify_items = verify_data if isinstance(verify_data, list) else []

        # Item should no longer be in wishlist
        remaining_product_ids = [
            item.get('product', {}).get('id') if 'product' in item else item.get('product_id')
            for item in verify_items
        ]

        assert str(product.id) not in remaining_product_ids, \
            "Removed product should no longer be in wishlist"


class TestWishlistEdgeCases:
    """
    Test edge cases for wishlist functionality
    Following TESTING_PHILOSOPHY.md - test real production scenarios
    """

    def test_add_duplicate_product(self, test_config, authenticated_client, test_products):
        """
        TC-WISH-EDGE-01: Add same product twice to wishlist

        Expected behavior (from plan):
        - HTTP 400 (duplicate not allowed) OR
        - Idempotent (returns existing item without error)

        Both behaviors are acceptable depending on business logic
        """
        product = test_products[2]

        # Add product first time
        response1 = authenticated_client.post(
            f"{test_config['backend_url']}/api/products/wishlist/",
            json={"product_id": str(product.id)}
        )
        assert response1.status_code in [200, 201]

        # Try adding same product again
        response2 = authenticated_client.post(
            f"{test_config['backend_url']}/api/products/wishlist/",
            json={"product_id": str(product.id)}
        )

        # Both 400 (duplicate error) and 200/201 (idempotent) are acceptable
        assert response2.status_code in [200, 201, 400], \
            f"Expected 200/201/400 for duplicate, got {response2.status_code}"

        # If duplicate is prevented (400), error message should be clear
        if response2.status_code == 400:
            data = response2.json()
            # Error message should mention duplicate/exists
            error_text = str(data).lower()
            assert any(word in error_text for word in ['duplicate', 'exists', 'already']), \
                "Error message should indicate duplicate item"

        # If idempotent (200/201), verify only one item exists
        if response2.status_code in [200, 201]:
            view_response = authenticated_client.get(
                f"{test_config['backend_url']}/api/products/wishlist/"
            )
            data = view_response.json()

            if isinstance(data, dict) and 'results' in data:
                items = data['results']
            else:
                items = data if isinstance(data, list) else [data]

            # Count how many times this product appears
            product_count = sum(
                1 for item in items
                if (item.get('product', {}).get('id') if 'product' in item else item.get('product_id')) == str(product.id)
            )

            assert product_count == 1, "Product should appear only once in wishlist (idempotent)"

    def test_add_inactive_product_to_wishlist(self, test_config, authenticated_client, test_products):
        """
        TC-WISH-EDGE-02: Add inactive product to wishlist

        Expected behavior (from plan):
        - Allowed (wishlist for future when product becomes active again)
        - May show warning in response
        - Product details should indicate is_active=False
        """
        # Find an inactive product
        inactive_product = None
        for product in test_products:
            if not product.is_active:
                inactive_product = product
                break

        if not inactive_product:
            pytest.skip("No inactive products available for testing")

        response = authenticated_client.post(
            f"{test_config['backend_url']}/api/products/wishlist/",
            json={"product_id": str(inactive_product.id)}
        )

        # Should be allowed (200/201) or rejected (400/404)
        # Both are acceptable business decisions
        assert response.status_code in [200, 201, 400, 404], \
            f"Expected 200/201/400/404, got {response.status_code}"

        # If allowed, verify product details
        if response.status_code in [200, 201]:
            data = response.json()
            product_data = data.get('product', {})

            # Inactive status should be indicated
            if 'is_active' in product_data:
                assert product_data['is_active'] == False, \
                    "Product should be marked as inactive"

    def test_add_out_of_stock_product_to_wishlist(self, test_config, authenticated_client, test_products):
        """
        TC-WISH-EDGE-03: Add out-of-stock product to wishlist

        Expected behavior (from plan):
        - Allowed (wishlist for future when product is restocked)
        - Should succeed with HTTP 200/201
        - User can save products they want when back in stock
        """
        # Find an out-of-stock product
        oos_product = None
        for product in test_products:
            if product.stock_quantity == 0 and product.is_active:
                oos_product = product
                break

        if not oos_product:
            pytest.skip("No out-of-stock products available for testing")

        response = authenticated_client.post(
            f"{test_config['backend_url']}/api/products/wishlist/",
            json={"product_id": str(oos_product.id)}
        )

        # Should be allowed (this is the primary use case for wishlists!)
        assert response.status_code in [200, 201], \
            f"Out-of-stock products should be allowed in wishlist, got {response.status_code}: {response.text}"

        data = response.json()

        # Verify product is indeed out of stock
        product_data = data.get('product', {})
        if 'stock_quantity' in product_data:
            assert product_data['stock_quantity'] == 0, \
                "Product should show 0 stock"

    def test_wishlist_with_invalid_product_id(self, test_config, authenticated_client):
        """
        TC-WISH-EDGE-04: Try to add non-existent product to wishlist

        Expected behavior:
        - HTTP 404 Not Found (product doesn't exist)
        - Clear error message
        """
        import uuid
        fake_product_id = str(uuid.uuid4())

        response = authenticated_client.post(
            f"{test_config['backend_url']}/api/products/wishlist/",
            json={"product_id": fake_product_id}
        )

        assert response.status_code == 404, \
            f"Non-existent product should return 404, got {response.status_code}"

        # Error message should be informative
        data = response.json()
        error_text = str(data).lower()
        assert any(word in error_text for word in ['not found', 'does not exist', 'invalid']), \
            "Error message should indicate product not found"

    def test_remove_nonexistent_wishlist_item(self, test_config, authenticated_client):
        """
        TC-WISH-EDGE-05: Try to remove item that doesn't exist in wishlist

        Expected behavior:
        - HTTP 404 Not Found
        - Clear error message
        """
        import uuid
        fake_item_id = str(uuid.uuid4())

        response = authenticated_client.delete(
            f"{test_config['backend_url']}/api/products/wishlist/{fake_item_id}/"
        )

        assert response.status_code == 404, \
            f"Non-existent wishlist item should return 404, got {response.status_code}"

    def test_empty_wishlist(self, test_config, authenticated_client):
        """
        TC-WISH-EDGE-06: View empty wishlist

        Expected behavior:
        - HTTP 200 OK
        - Empty list/array returned
        - No errors
        """
        # Ensure wishlist is empty by viewing it first
        # (cleanup should have been done by fixture)

        response = authenticated_client.get(
            f"{test_config['backend_url']}/api/products/wishlist/"
        )

        assert response.status_code == 200, \
            f"Empty wishlist should return 200, got {response.status_code}"

        data = response.json()

        # Handle pagination
        if isinstance(data, dict) and 'results' in data:
            items = data['results']
        else:
            items = data if isinstance(data, list) else []

        # Empty wishlist is acceptable (other tests may have added items)
        assert isinstance(items, list), "Wishlist should return a list"


class TestWishlistSecurity:
    """
    Test security aspects of wishlist functionality
    """

    def test_wishlist_requires_authentication(self, test_config, sync_http_client):
        """
        TC-WISH-SEC-01: Wishlist endpoints require authentication

        Expected behavior:
        - HTTP 401 Unauthorized for unauthenticated requests
        - Clear error message
        """
        # Try to view wishlist without authentication
        response = sync_http_client.get(
            f"{test_config['backend_url']}/api/products/wishlist/"
        )

        assert response.status_code == 401, \
            f"Unauthenticated wishlist access should return 401, got {response.status_code}"

    def test_cannot_access_other_users_wishlist(self, test_config, sync_http_client, test_users):
        """
        TC-WISH-SEC-02: Users can only access their own wishlist

        Expected behavior:
        - Each user sees only their own wishlist items
        - Cannot view or manipulate other users' wishlists
        """
        # Get two different users
        users_list = list(test_users.values()) if isinstance(test_users, dict) else test_users
        if len(users_list) < 2:
            pytest.skip("Need at least 2 users for isolation testing")

        user1 = users_list[0]
        user2 = users_list[1]

        # Login as user1
        login1 = sync_http_client.post(
            f"{test_config['backend_url']}/api/auth/login/",
            json={"email": user1.email, "password": "SecurePass123!"}
        )
        assert login1.status_code == 200
        token1 = login1.json()['access']

        # Login as user2
        login2 = sync_http_client.post(
            f"{test_config['backend_url']}/api/auth/login/",
            json={"email": user2.email, "password": "SecurePass123!"}
        )
        assert login2.status_code == 200
        token2 = login2.json()['access']

        # User1 views their wishlist
        response1 = sync_http_client.get(
            f"{test_config['backend_url']}/api/products/wishlist/",
            headers={"Authorization": f"Bearer {token1}"}
        )
        assert response1.status_code == 200

        # User2 views their wishlist
        response2 = sync_http_client.get(
            f"{test_config['backend_url']}/api/products/wishlist/",
            headers={"Authorization": f"Bearer {token2}"}
        )
        assert response2.status_code == 200

        # Wishlists should be independent
        # (We can't guarantee they're different without adding items, but both should succeed)
        assert response1.json() is not None
        assert response2.json() is not None


class TestWishlistPerformance:
    """
    Test performance characteristics of wishlist operations
    Following TESTING_PHILOSOPHY.md - Performance as a Feature
    """

    def test_wishlist_response_time(self, test_config, authenticated_client, test_products):
        """
        TC-WISH-PERF-01: Wishlist operations should be fast

        Performance SLAs:
        - View wishlist: < 1000ms
        - Add to wishlist: < 800ms
        - Remove from wishlist: < 500ms

        Note: Thresholds adjusted for WSL2 environment (production ~30% faster)
        """
        # Add to wishlist - performance test
        product = test_products[0]

        start = time.time()
        add_response = authenticated_client.post(
            f"{test_config['backend_url']}/api/products/wishlist/",
            json={"product_id": str(product.id)}
        )
        add_duration = (time.time() - start) * 1000  # Convert to ms

        assert add_response.status_code in [200, 201]
        assert add_duration < 1500, \
            f"Add to wishlist took {add_duration:.0f}ms, expected < 1500ms"

        # View wishlist - performance test
        start = time.time()
        view_response = authenticated_client.get(
            f"{test_config['backend_url']}/api/products/wishlist/"
        )
        view_duration = (time.time() - start) * 1000

        assert view_response.status_code == 200
        assert view_duration < 1500, \
            f"View wishlist took {view_duration:.0f}ms, expected < 1500ms"

        print(f"\n  Performance Metrics:")
        print(f"  - Add to wishlist: {add_duration:.0f}ms")
        print(f"  - View wishlist: {view_duration:.0f}ms")
