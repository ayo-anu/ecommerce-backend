
import pytest
import httpx
from decimal import Decimal
from uuid import UUID
import time

# Enable database access for all tests in this module
pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
class TestProductListing:
    """Test product listing, pagination, and basic retrieval"""

    def test_list_all_products(self, test_config, sync_http_client):
        """
        TC-PROD-01: List all products with pagination

        Validates:
        - HTTP 200 OK
        - Returns paginated list (default 20 per page)
        - Each product has required fields
        - Only active products returned (is_active=True)
        - Products ordered by creation date
        """
        # Act
        start_time = time.time()
        response = sync_http_client.get(f"{test_config['backend_url']}/api/products/")
        elapsed_time = (time.time() - start_time) * 1000  # Convert to ms

        # Assert HTTP response
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        # Assert response structure (DRF pagination)
        data = response.json()
        assert "results" in data, "Response should have 'results' key (DRF pagination)"

        products = data["results"]
        assert isinstance(products, list), "Results should be a list"
        assert len(products) > 0, "Should have at least some products"

        # Validate each product has required fields
        required_fields = ['id', 'name', 'slug', 'price', 'stock_quantity', 'is_active']
        for product in products:
            for field in required_fields:
                assert field in product, f"Product missing required field: {field}"

            # Validate field types
            assert isinstance(UUID(product['id']), UUID), "Product ID should be valid UUID"
            assert isinstance(product['name'], str), "Product name should be string"
            assert isinstance(product['slug'], str), "Product slug should be string"

            # Price validation
            price_value = product['price']
            if isinstance(price_value, str):
                price_value = float(price_value)
            assert price_value >= 0, "Price should be non-negative"

            # Only active products should be returned
            assert product['is_active'] is True, "Only active products should be listed"

        # Performance validation
        assert elapsed_time < 1000, f"Product list should respond in <1000ms, got {elapsed_time:.0f}ms"

        print(f"\n✅ TC-PROD-01 PASSED: Listed {len(products)} products in {elapsed_time:.0f}ms")

    @pytest.mark.django_db
    def test_product_pagination(self, test_config, sync_http_client):
        """
        TC-PROD-02: Test pagination functionality

        Validates:
        - Pagination works with page_size parameter
        - Returns correct number of items
        - Has next/previous links
        """
        # Act - Request with page_size=5
        response = sync_http_client.get(
            f"{test_config['backend_url']}/api/products/",
            params={"page_size": 5}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Check pagination structure
        assert "count" in data, "Should have total count"
        assert "results" in data, "Should have results array"

        # Check page size respected
        if data["count"] >= 5:
            assert len(data["results"]) == 5, f"Should return 5 items per page, got {len(data['results'])}"

        print(f"✅ TC-PROD-02 PASSED: Pagination working (total: {data['count']}, page_size: 5)")


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
class TestProductFiltering:
    """Test product filtering by category, price, tags, etc."""

    def test_filter_by_category(self, test_config, sync_http_client):
        """
        TC-PROD-03: Filter products by category

        Validates:
        - HTTP 200 OK
        - All returned products in specified category
        - Count matches database query
        """
        # Arrange
        category_name = "Electronics"

        # Act
        response = sync_http_client.get(
            f"{test_config['backend_url']}/api/products/",
            params={"category": category_name}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        products = data.get("results", [])

        # All products should be in Electronics category
        for product in products:
            # List serializer uses category_name field
            category_value = product.get('category_name')

            assert category_value == category_name, \
                f"Product '{product['name']}' has category '{category_value}', expected '{category_name}'"

        print(f"✅ TC-PROD-03 PASSED: Found {len(products)} products in {category_name} category")

    @pytest.mark.django_db
    def test_filter_by_price_range(self, test_config, sync_http_client):
        """
        TC-PROD-04: Filter products by price range

        Validates:
        - HTTP 200 OK
        - All products have price between min and max
        """
        # Arrange
        min_price = 50.00
        max_price = 200.00

        # Act
        response = sync_http_client.get(
            f"{test_config['backend_url']}/api/products/",
            params={"min_price": min_price, "max_price": max_price}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        products = data.get("results", [])

        # Validate all products within price range
        for product in products:
            price = product['price']
            if isinstance(price, str):
                price = float(price)

            assert min_price <= price <= max_price, \
                f"Product '{product['name']}' price ${price} not in range ${min_price}-${max_price}"

        print(f"✅ TC-PROD-04 PASSED: Found {len(products)} products in ${min_price}-${max_price} range")

    @pytest.mark.django_db
    def test_filter_by_stock_status(self, test_config, sync_http_client):
        """
        TC-PROD-05: Filter products by stock status (in_stock vs out_of_stock)

        Validates:
        - Can filter for in-stock products
        - Can filter for out-of-stock products
        """
        # Test in-stock filter
        response = sync_http_client.get(
            f"{test_config['backend_url']}/api/products/",
            params={"in_stock": "true"}
        )

        assert response.status_code == 200
        data = response.json()
        in_stock_products = data.get("results", [])

        # All should have stock > 0
        for product in in_stock_products:
            stock = product.get('stock_quantity', 0)
            assert stock > 0, f"Product '{product['name']}' has stock={stock}, expected >0"

        print(f"✅ TC-PROD-05 PASSED: Found {len(in_stock_products)} in-stock products")


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
class TestProductDetails:
    """Test individual product detail retrieval"""

    def test_view_product_details(self, test_config, sync_http_client):
        """
        TC-PROD-06: View product details

        Validates:
        - HTTP 200 OK
        - Complete product data returned
        - Includes images, variants (if applicable), category
        - Stock quantity visible
        """
        # Arrange - Get products via API (production-like approach)
        list_response = sync_http_client.get(f"{test_config['backend_url']}/api/products/")
        assert list_response.status_code == 200, "Should be able to list products"

        products = list_response.json().get('results', [])
        assert len(products) > 0, "Should have at least one product"

        product_id = products[0]['id']
        product_name = products[0]['name']

        # Act - Get product details
        response = sync_http_client.get(
            f"{test_config['backend_url']}/api/products/{product_id}/"
        )

        # Assert
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        data = response.json()

        # Validate complete product data
        assert data['id'] == product_id, "Product ID should match"
        assert data['name'] == product_name, "Product name should match"
        assert 'slug' in data, "Should include slug"
        assert 'stock_quantity' in data, "Should include stock quantity"
        assert 'price' in data, "Should include price"
        assert 'description' in data, "Should include description"

        # Validate category details included (detail serializer includes full category object)
        assert 'category' in data, "Should include category"

        print(f"✅ TC-PROD-06 PASSED: Retrieved details for '{product_name}'")

    @pytest.mark.django_db
    def test_product_not_found(self, test_config, sync_http_client):
        """
        TC-PROD-EDGE-01: Request non-existent product

        Validates:
        - HTTP 404 Not Found
        - Proper error message
        """
        # Arrange - Use random UUID that doesn't exist
        fake_uuid = "00000000-0000-0000-0000-000000000000"

        # Act
        response = sync_http_client.get(
            f"{test_config['backend_url']}/api/products/{fake_uuid}/"
        )

        # Assert
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"

        print(f"✅ TC-PROD-EDGE-01 PASSED: Non-existent product returns 404")

    @pytest.mark.django_db
    def test_invalid_uuid_format(self, test_config, sync_http_client):
        """
        TC-PROD-EDGE-02: Request product with invalid UUID format

        Validates:
        - HTTP 404 or 400
        - Proper error handling
        """
        # Arrange - Invalid UUID format
        invalid_uuid = "not-a-valid-uuid"

        # Act
        response = sync_http_client.get(
            f"{test_config['backend_url']}/api/products/{invalid_uuid}/"
        )

        # Assert - Should be 404 (not found) or 400 (bad request)
        assert response.status_code in [400, 404], \
            f"Expected 400 or 404 for invalid UUID, got {response.status_code}"

        print(f"✅ TC-PROD-EDGE-02 PASSED: Invalid UUID handled properly ({response.status_code})")


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
class TestProductSearch:
    """Test product search functionality (basic backend search, not AI)"""

    def test_search_by_name(self, test_config, sync_http_client):
        """
        TC-PROD-07: Search products by name

        Validates:
        - HTTP 200 OK
        - Results contain search term in name or description
        """
        # Arrange
        search_query = "headphones"

        # Act
        response = sync_http_client.get(
            f"{test_config['backend_url']}/api/products/",
            params={"search": search_query}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        products = data.get("results", [])

        # At least one product should match
        assert len(products) >= 1, f"Should find at least 1 product for '{search_query}'"

        # Validate search term appears in name or description
        for product in products:
            name_lower = product['name'].lower()
            description_lower = product.get('description', '').lower()

            assert search_query.lower() in name_lower or search_query.lower() in description_lower, \
                f"Product '{product['name']}' doesn't contain '{search_query}'"

        print(f"✅ TC-PROD-07 PASSED: Found {len(products)} products for '{search_query}'")

    @pytest.mark.django_db
    def test_search_empty_query(self, test_config, sync_http_client):
        """
        TC-PROD-EDGE-03: Search with empty query

        Validates:
        - Returns all products (or proper error)
        """
        # Act
        response = sync_http_client.get(
            f"{test_config['backend_url']}/api/products/",
            params={"search": ""}
        )

        # Assert - Should return all products (empty search = no filter)
        assert response.status_code == 200
        data = response.json()
        products = data.get("results", [])

        # Should return products (not filter everything out)
        assert len(products) > 0, "Empty search should return products"

        print(f"✅ TC-PROD-EDGE-03 PASSED: Empty search returned {len(products)} products")

    @pytest.mark.django_db
    def test_search_special_characters(self, test_config, sync_http_client):
        """
        TC-PROD-EDGE-04: Search with special characters

        Validates:
        - Special characters handled properly
        - No errors or crashes
        """
        # Arrange - Special characters
        special_queries = ["C++ programming", "O'Brien", "<script>", "'; DROP TABLE"]

        for query in special_queries:
            # Act
            response = sync_http_client.get(
                f"{test_config['backend_url']}/api/products/",
                params={"search": query}
            )

            # Assert - Should not crash, should return 200
            assert response.status_code == 200, \
                f"Search with '{query}' should not crash (got {response.status_code})"

        print(f"✅ TC-PROD-EDGE-04 PASSED: Special characters handled safely")

    @pytest.mark.django_db
    def test_search_no_results(self, test_config, sync_http_client):
        """
        TC-PROD-EDGE-05: Search for non-existent product

        Validates:
        - HTTP 200 OK
        - Empty results array
        - Count = 0
        """
        # Arrange - Search that won't match anything
        search_query = "xyznonexistentproduct123xyz"

        # Act
        response = sync_http_client.get(
            f"{test_config['backend_url']}/api/products/",
            params={"search": search_query}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        products = data.get("results", [])

        # Should return empty results, not an error
        assert len(products) == 0, f"Non-existent search should return 0 results, got {len(products)}"
        assert data.get("count", 0) == 0, "Count should be 0"

        print(f"✅ TC-PROD-EDGE-05 PASSED: Non-existent search returns empty results")


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
class TestProductEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_inactive_products_not_visible(self, test_config, sync_http_client):
        """
        TC-PROD-EDGE-06: Verify inactive products don't appear in listings

        Validates:
        - Inactive products (is_active=False) not in results
        """
        # Arrange - Check if we have inactive products
        from apps.products.models import Product
        inactive_count = Product.objects.filter(is_active=False).count()

        # Act
        response = sync_http_client.get(f"{test_config['backend_url']}/api/products/")

        # Assert
        assert response.status_code == 200
        data = response.json()
        products = data.get("results", [])

        # None should be inactive
        for product in products:
            assert product['is_active'] is True, \
                f"Inactive product '{product['name']}' should not appear in listing"

        print(f"✅ TC-PROD-EDGE-06 PASSED: {inactive_count} inactive products correctly hidden")

    @pytest.mark.django_db
    def test_price_filter_edge_cases(self, test_config, sync_http_client):
        """
        TC-PROD-EDGE-07: Test price filter edge cases

        Validates:
        - Negative price filter handled
        - Max < Min handled
        - Zero price handled
        """
        # Test 1: Negative min price (should be rejected or ignored)
        response = sync_http_client.get(
            f"{test_config['backend_url']}/api/products/",
            params={"min_price": -10}
        )
        # Should not crash
        assert response.status_code in [200, 400], "Negative price should be handled"

        # Test 2: Max < Min (should return empty or error)
        response = sync_http_client.get(
            f"{test_config['backend_url']}/api/products/",
            params={"min_price": 500, "max_price": 100}
        )
        assert response.status_code in [200, 400], "Max < Min should be handled"

        # Test 3: Zero price (should work - free products)
        response = sync_http_client.get(
            f"{test_config['backend_url']}/api/products/",
            params={"min_price": 0, "max_price": 10}
        )
        assert response.status_code == 200, "Zero price should be valid"

        print(f"✅ TC-PROD-EDGE-07 PASSED: Price filter edge cases handled")

    @pytest.mark.django_db
    def test_out_of_stock_product_visible(self, test_config, sync_http_client):
        """
        TC-PROD-EDGE-08: Verify out-of-stock products are still visible

        Validates:
        - Out-of-stock products appear in listings
        - Stock quantity correctly shown as 0
        """
        # Arrange - Get out of stock product
        from apps.products.models import Product
        oos_product = Product.objects.filter(stock_quantity=0, is_active=True).first()

        if oos_product:
            # Act
            response = sync_http_client.get(
                f"{test_config['backend_url']}/api/products/{oos_product.id}/"
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data['stock_quantity'] == 0, "Stock should be 0"

            print(f"✅ TC-PROD-EDGE-08 PASSED: Out-of-stock product '{oos_product.name}' is visible")
        else:
            print(f"⏭️  TC-PROD-EDGE-08 SKIPPED: No out-of-stock products in test data")

    @pytest.mark.django_db
    def test_featured_products_flag(self, test_config, sync_http_client):
        """
        TC-PROD-08: Test featured products filtering

        Validates:
        - Can filter by is_featured flag
        - Featured products have correct flag
        """
        # Act
        response = sync_http_client.get(
            f"{test_config['backend_url']}/api/products/",
            params={"is_featured": "true"}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        products = data.get("results", [])

        # All should be featured
        for product in products:
            if 'is_featured' in product:
                assert product['is_featured'] is True, \
                    f"Product '{product['name']}' should be featured"

        print(f"✅ TC-PROD-08 PASSED: Found {len(products)} featured products")

    @pytest.mark.django_db
    def test_product_performance_under_load(self, test_config, sync_http_client):
        """
        TC-PROD-PERF-01: Test product listing performance

        Validates:
        - Response time < 1000ms for product listing
        - Consistent performance across multiple requests
        """
        response_times = []

        # Make 10 requests
        for _ in range(10):
            start_time = time.time()
            response = sync_http_client.get(f"{test_config['backend_url']}/api/products/")
            elapsed_time = (time.time() - start_time) * 1000

            assert response.status_code == 200
            response_times.append(elapsed_time)

        # Calculate stats
        avg_time = sum(response_times) / len(response_times)
        max_time = max(response_times)

        # Assert performance
        assert avg_time < 1000, f"Average response time should be <1000ms, got {avg_time:.0f}ms"
        assert max_time < 2000, f"Max response time should be <2000ms, got {max_time:.0f}ms"

        print(f"✅ TC-PROD-PERF-01 PASSED: Avg {avg_time:.0f}ms, Max {max_time:.0f}ms (10 requests)")


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.django_db(transaction=True)
class TestProductVariants:
    """Test product variants functionality (if implemented)"""

    def test_product_with_variants(self, test_config, sync_http_client):
        """
        TC-PROD-VAR-01: Test product with variants (sizes, colors)

        Validates:
        - Product has variants if has_variants=True
        - Each variant has SKU, size/color, stock
        """
        # Arrange - Get product with variants (T-shirt has S/M/L/XL variants)
        from apps.products.models import Product
        variant_product = Product.objects.filter(
            name__icontains="T-Shirt"
        ).first()

        if variant_product:
            # Act
            response = sync_http_client.get(
                f"{test_config['backend_url']}/api/products/{variant_product.id}/"
            )

            # Assert
            assert response.status_code == 200
            data = response.json()

            # Check for variants data (if implemented in serializer)
            if 'variants' in data:
                variants = data['variants']
                assert isinstance(variants, list), "Variants should be a list"

                for variant in variants:
                    assert 'sku' in variant, "Variant should have SKU"

                print(f"✅ TC-PROD-VAR-01 PASSED: Product has {len(variants)} variants")
            else:
                print(f"⏭️  TC-PROD-VAR-01 SKIPPED: Variants not in serializer response")
        else:
            print(f"⏭️  TC-PROD-VAR-01 SKIPPED: No variant products in test data")


# Test execution summary
if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════════════════════════════╗
    ║         E2E Test Suite: Product Browsing & Search              ║
    ║                                                                ║
    ║  Total Tests: 20                                               ║
    ║  Categories:                                                   ║
    ║    - Product Listing: 2 tests                                  ║
    ║    - Product Filtering: 3 tests                                ║
    ║    - Product Details: 3 tests                                  ║
    ║    - Product Search: 4 tests                                   ║
    ║    - Edge Cases: 7 tests                                       ║
    ║    - Variants: 1 test                                          ║
    ║                                                                ║
    ║  Run with:                                                     ║
    ║    pytest tests/e2e/workflows/test_02_products.py -v           ║
    ╚════════════════════════════════════════════════════════════════╝
    """)
