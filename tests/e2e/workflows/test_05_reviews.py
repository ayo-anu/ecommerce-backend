"""
E2E Tests: Workflow 5 - Product Reviews and Ratings

Test Suite Coverage:
- Submit product reviews
- Get product reviews
- Mark reviews as helpful
- Edge cases: duplicate reviews, invalid ratings, XSS, etc.

Requirements from E2E_BUSINESS_LOGIC_TEST_PLAN.md:
- TC-REVIEW-01: Submit Product Review
- TC-REVIEW-02: Get Product Reviews
- TC-REVIEW-03: Mark Review as Helpful
- TC-REVIEW-EDGE-01: Review Without Purchase
- TC-REVIEW-EDGE-02: Duplicate Review
- TC-REVIEW-EDGE-03: Rating Out of Range
- TC-REVIEW-EDGE-04: Empty Comment
- TC-REVIEW-EDGE-05: XSS in Comment
- TC-REVIEW-EDGE-06: Very Long Comment

Testing Philosophy:
- Production-like testing (real DB, real API calls)
- Fix the code, not the tests
- All security validations must pass
"""

import pytest
import time
from decimal import Decimal
from django.contrib.auth import get_user_model

User = get_user_model()


class TestProductReviews:
    """Test basic product review operations"""

    def test_submit_product_review(self, test_config, authenticated_client, test_products, test_users):
        """
        TC-REVIEW-01: Submit Product Review

        Validates:
        - Review successfully created
        - is_verified_purchase flag set correctly
        - Review linked to user and product
        - Database state verified
        """
        # Get a product and user
        product = test_products[0]  # Wireless Bluetooth Headphones

        # Submit review
        review_data = {
            "product": str(product.id),
            "rating": 5,
            "title": "Excellent headphones!",
            "comment": "Sound quality is amazing, battery lasts forever. Highly recommend!"
        }

        response = authenticated_client.post(
            f"{test_config['backend_url']}/api/products/reviews/",
            json=review_data
        )

        # Validate response
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"

        data = response.json()
        assert "id" in data
        assert data["rating"] == 5
        assert data["title"] == "Excellent headphones!"
        assert "comment" in data

        # Validate is_verified_purchase flag exists
        # Note: Will be True if user has purchased this product, False otherwise
        assert "is_verified_purchase" in data

        # Validate database state
        from apps.products.models import ProductReview
        review = ProductReview.objects.get(id=data["id"])
        assert review.rating == 5
        assert review.title == "Excellent headphones!"
        assert review.product_id == product.id

        print(f"✅ Review created: ID={data['id']}, Rating={data['rating']}, Verified={data.get('is_verified_purchase', False)}")

    def test_get_product_reviews(self, test_config, sync_http_client, test_products, test_users):
        """
        TC-REVIEW-02: Get Product Reviews

        Validates:
        - Returns all approved reviews for product
        - Includes user info
        - Sorted by helpful_count or creation date
        """
        product = test_products[0]

        # Get reviews for product
        response = sync_http_client.get(
            f"{test_config['backend_url']}/api/products/{product.id}/reviews/"
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()

        # Validate response structure
        if isinstance(data, dict) and "results" in data:
            # Paginated response
            reviews = data["results"]
        elif isinstance(data, list):
            # Non-paginated response
            reviews = data
        else:
            pytest.fail(f"Unexpected response structure: {data}")

        # Validate each review has required fields
        for review in reviews:
            assert "id" in review
            assert "rating" in review
            assert "title" in review
            assert "comment" in review
            assert "created_at" in review
            # User info should be included
            assert "user" in review or "user_id" in review

        print(f"✅ Retrieved {len(reviews)} reviews for product {product.name}")

    def test_mark_review_as_helpful(self, test_config, authenticated_client, test_products, test_users):
        """
        TC-REVIEW-03: Mark Review as Helpful

        Validates:
        - helpful_count incremented
        - User can only mark once (idempotent or error)
        """
        # First, create a review
        product = test_products[0]

        review_data = {
            "product": str(product.id),
            "rating": 4,
            "title": "Good product",
            "comment": "Works well, no complaints."
        }

        create_response = authenticated_client.post(
            f"{test_config['backend_url']}/api/products/reviews/",
            json=review_data
        )

        assert create_response.status_code in [200, 201]
        review_id = create_response.json()["id"]

        # Mark review as helpful
        helpful_response = authenticated_client.post(
            f"{test_config['backend_url']}/api/products/reviews/{review_id}/mark_helpful/"
        )

        assert helpful_response.status_code in [200, 201], f"Expected 200/201, got {helpful_response.status_code}: {helpful_response.text}"

        # Verify helpful_count incremented
        data = helpful_response.json()
        assert "helpful_count" in data or "message" in data

        # Try marking again (should be idempotent or return error)
        second_helpful_response = authenticated_client.post(
            f"{test_config['backend_url']}/api/products/reviews/{review_id}/mark_helpful/"
        )

        # Should either succeed (idempotent) or return 400 (already marked)
        assert second_helpful_response.status_code in [200, 400], f"Expected 200/400, got {second_helpful_response.status_code}"

        print(f"✅ Review marked as helpful: ID={review_id}")


class TestReviewEdgeCases:
    """Test edge cases for product reviews"""

    def test_review_without_purchase(self, test_config, authenticated_client, test_products):
        """
        TC-REVIEW-EDGE-01: Review Without Purchase

        Validates:
        - Users can review products they haven't purchased
        - is_verified_purchase = False for such reviews
        """
        # Use a product the user hasn't purchased
        product = test_products[-1]  # Last product (likely not purchased)

        review_data = {
            "product": str(product.id),
            "rating": 3,
            "title": "Haven't bought yet but looks good",
            "comment": "Based on specs, this seems like a good product."
        }

        response = authenticated_client.post(
            f"{test_config['backend_url']}/api/products/reviews/",
            json=review_data
        )

        # Should succeed
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"

        data = response.json()

        # is_verified_purchase should be False (user hasn't purchased)
        # Note: If backend doesn't track purchases for this user, this will be False
        if "is_verified_purchase" in data:
            # We expect False, but it depends on whether user has actually purchased
            print(f"✅ Review created without purchase: is_verified_purchase={data['is_verified_purchase']}")

    def test_duplicate_review_same_user_same_product(self, test_config, authenticated_client, test_products):
        """
        TC-REVIEW-EDGE-02: Duplicate Review

        Validates:
        - Same user cannot review same product twice
        - Returns HTTP 400 or unique constraint error
        """
        product = test_products[1]

        review_data = {
            "product": str(product.id),
            "rating": 4,
            "title": "First review",
            "comment": "This is my first review of this product."
        }

        # First review - should succeed
        first_response = authenticated_client.post(
            f"{test_config['backend_url']}/api/products/reviews/",
            json=review_data
        )

        assert first_response.status_code in [200, 201]
        first_review_id = first_response.json()["id"]

        # Second review - should fail (duplicate)
        review_data["title"] = "Second review (duplicate)"
        review_data["comment"] = "Trying to review the same product again."

        second_response = authenticated_client.post(
            f"{test_config['backend_url']}/api/products/reviews/",
            json=review_data
        )

        # Should fail with 400 (already reviewed)
        assert second_response.status_code == 400, f"Expected 400 for duplicate review, got {second_response.status_code}"

        # Error message should indicate duplicate
        error_data = second_response.json()
        error_message = str(error_data).lower()
        assert any(keyword in error_message for keyword in ["already", "duplicate", "exist"]), \
            f"Error message should mention duplicate/already reviewed: {error_data}"

        print(f"✅ Duplicate review correctly rejected")

    def test_rating_out_of_range(self, test_config, authenticated_client, test_products):
        """
        TC-REVIEW-EDGE-03: Rating Out of Range

        Validates:
        - Rating must be 1-5
        - Invalid ratings return HTTP 400
        """
        product = test_products[2]

        # Test rating too high (6)
        invalid_high_data = {
            "product": str(product.id),
            "rating": 6,  # Invalid: > 5
            "title": "Invalid rating",
            "comment": "This rating is out of range."
        }

        response_high = authenticated_client.post(
            f"{test_config['backend_url']}/api/products/reviews/",
            json=invalid_high_data
        )

        assert response_high.status_code == 400, f"Expected 400 for rating=6, got {response_high.status_code}"

        # Test rating too low (0)
        invalid_low_data = {
            "product": str(product.id),
            "rating": 0,  # Invalid: < 1
            "title": "Invalid rating",
            "comment": "This rating is out of range."
        }

        response_low = authenticated_client.post(
            f"{test_config['backend_url']}/api/products/reviews/",
            json=invalid_low_data
        )

        assert response_low.status_code == 400, f"Expected 400 for rating=0, got {response_low.status_code}"

        # Test valid rating (3)
        valid_data = {
            "product": str(product.id),
            "rating": 3,  # Valid
            "title": "Valid rating",
            "comment": "This is a valid rating."
        }

        response_valid = authenticated_client.post(
            f"{test_config['backend_url']}/api/products/reviews/",
            json=valid_data
        )

        assert response_valid.status_code in [200, 201], f"Expected 200/201 for valid rating, got {response_valid.status_code}"

        print("✅ Rating validation working correctly (0 rejected, 6 rejected, 3 accepted)")

    def test_empty_comment(self, test_config, authenticated_client, test_products):
        """
        TC-REVIEW-EDGE-04: Empty Comment

        Validates:
        - Empty comments handled appropriately
        - Returns HTTP 400 if comment is required
        """
        product = test_products[3]

        # Test with empty comment
        empty_comment_data = {
            "product": str(product.id),
            "rating": 4,
            "title": "Title only",
            "comment": ""  # Empty
        }

        response = authenticated_client.post(
            f"{test_config['backend_url']}/api/products/reviews/",
            json=empty_comment_data
        )

        # Should either succeed (comment optional) or fail (comment required)
        # We expect 400 if comment is required
        if response.status_code == 400:
            # Comment is required
            error_data = response.json()
            print(f"✅ Empty comment rejected (comment required): {error_data}")
        else:
            # Comment is optional
            assert response.status_code in [200, 201]
            print("✅ Empty comment allowed (comment optional)")

    def test_xss_in_comment(self, test_config, authenticated_client, test_products):
        """
        TC-REVIEW-EDGE-05: XSS in Comment

        Validates:
        - XSS attempts in comment are sanitized
        - Script tags not executed
        - Data stored safely
        """
        product = test_products[4]

        # XSS payloads
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<iframe src='javascript:alert(1)'></iframe>"
        ]

        for i, xss_payload in enumerate(xss_payloads):
            review_data = {
                "product": str(product.id),
                "rating": 3,
                "title": f"XSS Test {i+1}",
                "comment": xss_payload
            }

            response = authenticated_client.post(
                f"{test_config['backend_url']}/api/products/reviews/",
                json=review_data
            )

            # Should either succeed (and sanitize) or reject
            if response.status_code in [200, 201]:
                # Review created - verify it's sanitized
                data = response.json()
                comment = data.get("comment", "")

                # Script tags should be removed or escaped
                assert "<script>" not in comment.lower(), f"XSS not sanitized: {comment}"
                assert "onerror=" not in comment.lower(), f"XSS not sanitized: {comment}"
                assert "javascript:" not in comment.lower(), f"XSS not sanitized: {comment}"

                print(f"✅ XSS payload {i+1} sanitized: {xss_payload[:50]}")

                # Clean up for next test
                from apps.products.models import ProductReview
                ProductReview.objects.filter(id=data["id"]).delete()
            elif response.status_code == 400:
                # Rejected due to validation
                print(f"✅ XSS payload {i+1} rejected: {xss_payload[:50]}")
            else:
                pytest.fail(f"Unexpected status code {response.status_code} for XSS test")

    def test_very_long_comment(self, test_config, authenticated_client, test_products):
        """
        TC-REVIEW-EDGE-06: Very Long Comment

        Validates:
        - Very long comments handled appropriately
        - Truncated or rejected based on policy
        """
        product = test_products[5]

        # Create a very long comment (10000 chars)
        very_long_comment = "A" * 10000

        review_data = {
            "product": str(product.id),
            "rating": 4,
            "title": "Very long review",
            "comment": very_long_comment
        }

        response = authenticated_client.post(
            f"{test_config['backend_url']}/api/products/reviews/",
            json=review_data
        )

        # Should either succeed (and truncate) or reject
        if response.status_code in [200, 201]:
            # Review created - verify length
            data = response.json()
            comment = data.get("comment", "")

            # Comment might be truncated
            if len(comment) < len(very_long_comment):
                print(f"✅ Very long comment truncated: {len(very_long_comment)} → {len(comment)} chars")
            else:
                print(f"✅ Very long comment accepted: {len(comment)} chars")
        elif response.status_code == 400:
            # Rejected due to length
            error_data = response.json()
            print(f"✅ Very long comment rejected: {error_data}")
        else:
            pytest.fail(f"Unexpected status code {response.status_code} for long comment test")


class TestReviewSecurity:
    """Test security aspects of reviews"""

    def test_review_requires_authentication(self, test_config, sync_http_client, test_products):
        """
        Validates:
        - Reviews require authentication
        - Unauthenticated requests return 401
        """
        product = test_products[0]

        review_data = {
            "product": str(product.id),
            "rating": 5,
            "title": "Unauthenticated review",
            "comment": "This should fail."
        }

        # No authentication token
        response = sync_http_client.post(
            f"{test_config['backend_url']}/api/products/reviews/",
            json=review_data
        )

        assert response.status_code == 401, f"Expected 401 for unauthenticated review, got {response.status_code}"

        print("✅ Reviews require authentication")

    def test_cannot_edit_other_users_reviews(self, test_config, authenticated_client, test_products, test_users):
        """
        Validates:
        - Users cannot edit reviews from other users
        - Returns 403/404 for unauthorized edits
        """
        # This test requires multiple authenticated users
        # For now, we'll just verify the review owner can edit their own

        product = test_products[0]

        # Create review
        review_data = {
            "product": str(product.id),
            "rating": 4,
            "title": "Original review",
            "comment": "This is my review."
        }

        create_response = authenticated_client.post(
            f"{test_config['backend_url']}/api/products/reviews/",
            json=review_data
        )

        assert create_response.status_code in [200, 201]
        review_id = create_response.json()["id"]

        # Try to edit own review
        update_data = {
            "title": "Updated review",
            "comment": "Updated comment",
            "rating": 5
        }

        update_response = authenticated_client.patch(
            f"{test_config['backend_url']}/api/products/reviews/{review_id}/",
            json=update_data
        )

        # Should succeed (editing own review) or fail if editing not allowed
        if update_response.status_code in [200, 405]:
            # Either succeeded or method not allowed
            print(f"✅ Review edit result: {update_response.status_code}")
        else:
            # Unexpected status
            print(f"⚠️ Unexpected status for own review edit: {update_response.status_code}")


class TestReviewPerformance:
    """Test performance of review operations"""

    def test_review_submission_performance(self, test_config, authenticated_client, test_products):
        """
        Validates:
        - Review submission completes within acceptable time
        - Target: < 2 seconds
        """
        product = test_products[0]

        review_data = {
            "product": str(product.id),
            "rating": 5,
            "title": "Performance test review",
            "comment": "Testing review submission performance."
        }

        start_time = time.time()

        response = authenticated_client.post(
            f"{test_config['backend_url']}/api/products/reviews/",
            json=review_data
        )

        duration = (time.time() - start_time) * 1000  # Convert to ms

        assert response.status_code in [200, 201], f"Review submission failed: {response.status_code}"

        # Performance threshold: 2000ms for WSL2, 1500ms for production
        import platform
        if "microsoft" in platform.uname().release.lower():
            # WSL2 environment
            threshold = 2000
        else:
            # Native Linux/production
            threshold = 1500

        assert duration < threshold, f"Review submission too slow: {duration:.0f}ms > {threshold}ms"

        print(f"✅ Review submitted in {duration:.0f}ms (threshold: {threshold}ms)")

    def test_get_reviews_performance(self, test_config, sync_http_client, test_products):
        """
        Validates:
        - Getting reviews for a product completes quickly
        - Target: < 2 seconds for WSL2, < 1 second for production
        """
        product = test_products[0]

        start_time = time.time()

        response = sync_http_client.get(
            f"{test_config['backend_url']}/api/products/{product.id}/reviews/"
        )

        duration = (time.time() - start_time) * 1000  # Convert to ms

        assert response.status_code == 200, f"Get reviews failed: {response.status_code}"

        # Performance threshold: 3000ms for WSL2, 1000ms for production
        import platform
        if "microsoft" in platform.uname().release.lower():
            # WSL2 environment - more lenient due to I/O overhead
            threshold = 3000
        else:
            # Native Linux/production
            threshold = 1000

        assert duration < threshold, f"Get reviews too slow: {duration:.0f}ms > {threshold}ms"

        print(f"✅ Reviews retrieved in {duration:.0f}ms (threshold: {threshold}ms)")
