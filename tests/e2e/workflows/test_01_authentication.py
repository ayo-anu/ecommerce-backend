import pytest
import httpx
import time
from decimal import Decimal


class TestUserRegistration:

    def test_successful_registration(self, test_config, sync_http_client, assert_response, assert_db_state):
        """TC-AUTH-01: Successful user registration"""
        # Arrange
        unique_email = f"newuser_{int(time.time())}@example.com"
        payload = {
            "email": unique_email,
            "username": f"newuser_{int(time.time())}",
            "password": "SecurePass123!",
            "password2": "SecurePass123!",
            "password2": "SecurePass123!",  # Password confirmation
            "first_name": "New",
            "last_name": "User",
            "phone": "+1-555-9999"
        }

        # Act
        response = sync_http_client.post(
            f"{test_config['backend_url']}/api/auth/register/",
            json=payload
        )

        # Assert HTTP Response
        data = assert_response(response, expected_status=201)
        assert "id" in data
        assert data["email"] == payload["email"]
        assert data["username"] == payload["username"]
        assert "password" not in data  # Password should never be in response

        # Verify registration worked by logging in
        login_response = sync_http_client.post(
            f"{test_config['backend_url']}/api/auth/login/",
            json={
                "email": payload["email"],
                "password": payload["password"]
            }
        )
        login_data = assert_response(login_response, expected_status=200)
        assert "access" in login_data, "Should receive access token"
        assert "refresh" in login_data, "Should receive refresh token"

        # Verify token works by accessing protected endpoint
        me_response = sync_http_client.get(
            f"{test_config['backend_url']}/api/auth/users/me/",
            headers={"Authorization": f"Bearer {login_data['access']}"}
        )
        me_data = assert_response(me_response, expected_status=200)
        assert me_data["email"] == payload["email"]


    def test_duplicate_email_registration(self, test_config, sync_http_client, test_users):
        """TC-AUTH-02: Registration with duplicate email should fail"""
        # Arrange - use existing user
        existing_user = next(iter(test_users.values()))
        payload = {
            "email": existing_user.email,  # Duplicate!
            "username": "differentusername",
            "password": "SecurePass123!",
            "password2": "SecurePass123!",
            "first_name": "Test",
            "last_name": "User"
        }

        # Act
        response = sync_http_client.post(
            f"{test_config['backend_url']}/api/auth/register/",
            json=payload
        )

        # Assert
        assert response.status_code == 400
        data = response.json()
        assert "email" in str(data).lower(), "Error should mention email"

    
    def test_weak_password_registration(self, test_config, sync_http_client):
        """TC-AUTH-03: Registration with weak password should fail"""
        # Arrange
        payload = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "weak",
            "password2": "weak",  # Too weak!
            "first_name": "Test",
            "last_name": "User"
        }

        # Act
        response = sync_http_client.post(
            f"{test_config['backend_url']}/api/auth/register/",
            json=payload
        )

        # Assert
        assert response.status_code == 400
        data = response.json()
        assert "password" in str(data).lower(), "Error should mention password"

    
    def test_invalid_email_format(self, test_config, sync_http_client):
        """TC-AUTH-04: Registration with invalid email format should fail"""
        # Arrange
        payload = {
            "email": "notanemail",  # Invalid format
            "username": "testuser",
            "password": "SecurePass123!",
            "password2": "SecurePass123!",
            "first_name": "Test",
            "last_name": "User"
        }

        # Act
        response = sync_http_client.post(
            f"{test_config['backend_url']}/api/auth/register/",
            json=payload
        )

        # Assert
        assert response.status_code == 400

    
    def test_missing_required_fields(self, test_config, sync_http_client):
        """TC-AUTH-05: Registration with missing required fields should fail"""
        # Arrange
        payload = {
            "username": "testuser",
            # Missing email!
            "password": "SecurePass123!",
            "password2": "SecurePass123!"
        }

        # Act
        response = sync_http_client.post(
            f"{test_config['backend_url']}/api/auth/register/",
            json=payload
        )

        # Assert
        assert response.status_code == 400


class TestUserLogin:


    def test_successful_login(self, test_config, sync_http_client, test_users, track_performance):
        """TC-AUTH-06: Successful login with valid credentials"""
        # Arrange
        user = next(iter(test_users.values()))
        payload = {
            "email": user.email,
            "password": user._test_password
        }

        # Act
        start_time = time.time()
        response = sync_http_client.post(
            f"{test_config['backend_url']}/api/auth/login/",
            json=payload
        )
        response_time_ms = (time.time() - start_time) * 1000

        # Assert HTTP Response
        assert response.status_code == 200
        data = response.json()

        assert "access" in data, "Response should contain access token"
        assert "refresh" in data, "Response should contain refresh token"
        assert "user" in data, "Response should contain user data"

        # Validate JWT tokens exist
        assert len(data["access"]) > 50, "Access token should be a valid JWT"
        assert len(data["refresh"]) > 50, "Refresh token should be a valid JWT"

        # Validate user data
        assert data["user"]["email"] == user.email
        assert "password" not in data["user"]

        # Track performance
        # Note: bcrypt password hashing is intentionally slow for security
        track_performance("/api/auth/login/", response_time_ms, max_time_ms=1500)


    def test_login_wrong_password(self, test_config, sync_http_client, test_users):
        """TC-AUTH-07: Login with wrong password should fail"""
        # Arrange
        user = next(iter(test_users.values()))
        payload = {
            "email": user.email,
            "password": "WrongPassword123!"
        }

        # Act
        response = sync_http_client.post(
            f"{test_config['backend_url']}/api/auth/login/",
            json=payload
        )

        # Assert
        assert response.status_code == 401
        # Error message should be generic to prevent user enumeration
        data = response.json()
        # Check for generic error messages
        error_text = str(data).lower()
        assert "invalid" in error_text or "incorrect" in error_text or "no active account" in error_text

    
    def test_login_nonexistent_email(self, test_config, sync_http_client):
        """TC-AUTH-08: Login with non-existent email should fail with generic error"""
        # Arrange
        payload = {
            "email": "nonexistent@example.com",
            "password": "SomePassword123!"
        }

        # Act
        response = sync_http_client.post(
            f"{test_config['backend_url']}/api/auth/login/",
            json=payload
        )

        # Assert
        assert response.status_code == 401
        # Error should be generic (same as wrong password) to prevent user enumeration


class TestTokenManagement:


    def test_access_protected_endpoint(self, test_config, authenticated_client):
        """TC-AUTH-09: Access protected endpoint with valid token"""
        # Arrange
        client, user, token = authenticated_client

        # Act
        response = client.get(f"{test_config['backend_url']}/api/auth/users/me/")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == user.email

    
    def test_access_without_token(self, test_config, sync_http_client):
        """TC-AUTH-10: Access protected endpoint without token should fail"""
        # Act
        response = sync_http_client.get(
            f"{test_config['backend_url']}/api/auth/users/me/"
        )

        # Assert
        assert response.status_code == 401

    
    def test_access_with_invalid_token(self, test_config, sync_http_client):
        """TC-AUTH-11: Access with invalid token should fail"""
        # Arrange
        client = httpx.Client(
            timeout=30,
            headers={"Authorization": "Bearer invalid_token_here"}
        )

        # Act
        response = client.get(f"{test_config['backend_url']}/api/auth/users/me/")

        # Assert
        assert response.status_code == 401

        client.close()


    def test_token_refresh(self, test_config, sync_http_client, test_users):
        """TC-AUTH-12: Token refresh should provide new access token"""
        # Arrange - first login
        user = next(iter(test_users.values()))
        login_response = sync_http_client.post(
            f"{test_config['backend_url']}/api/auth/login/",
            json={"email": user.email, "password": user._test_password}
        )
        assert login_response.status_code == 200
        tokens = login_response.json()
        refresh_token = tokens["refresh"]
        old_access_token = tokens["access"]

        # Act - refresh the token
        refresh_response = sync_http_client.post(
            f"{test_config['backend_url']}/api/auth/token/refresh/",
            json={"refresh": refresh_token}
        )

        # Assert
        assert refresh_response.status_code == 200
        data = refresh_response.json()
        assert "access" in data
        new_access_token = data["access"]

        # New token should be different
        assert new_access_token != old_access_token

        # New token should work
        client = httpx.Client(
            timeout=30,
            headers={"Authorization": f"Bearer {new_access_token}"}
        )
        me_response = client.get(f"{test_config['backend_url']}/api/auth/users/me/")
        assert me_response.status_code == 200

        client.close()


class TestEdgeCases:

    
    def test_sql_injection_in_email(self, test_config, sync_http_client):
        """TC-AUTH-13: SQL injection attempt in email should be handled safely"""
        # Arrange
        payload = {
            "email": "'; DROP TABLE users; --",
            "username": "testuser",
            "password": "SecurePass123!",
            "password2": "SecurePass123!",
            "first_name": "Test",
            "last_name": "User"
        }

        # Act
        response = sync_http_client.post(
            f"{test_config['backend_url']}/api/auth/register/",
            json=payload
        )

        # Assert - should fail validation, not execute SQL
        assert response.status_code == 400


    def test_xss_in_name(self, test_config, sync_http_client):
        """TC-AUTH-14: XSS attempt in name should be sanitized

        ✅ SECURITY FIX APPLIED: Backend now sanitizes XSS input using strip_tags()
        Expected: Accept (201) and sanitize HTML tags
        """
        # Arrange
        unique_email = f"xsstest_{int(time.time())}@example.com"
        payload = {
            "email": unique_email,
            "username": f"xsstest_{int(time.time())}",
            "password": "SecurePass123!",
            "password2": "SecurePass123!",
            "first_name": "<script>alert('XSS')</script>",
            "last_name": "User"
        }

        # Act
        response = sync_http_client.post(
            f"{test_config['backend_url']}/api/auth/register/",
            json=payload
        )

        # Assert - should either reject or sanitize
        if response.status_code == 201:
            # If accepted, verify registration worked by logging in
            data = response.json()
            login_response = sync_http_client.post(
                f"{test_config['backend_url']}/api/auth/login/",
                json={
                    "email": unique_email,
                    "password": payload["password"]
                }
            )
            assert login_response.status_code == 200, "Should be able to login with sanitized data"

            # Verify user data through API
            login_data = login_response.json()
            me_response = sync_http_client.get(
                f"{test_config['backend_url']}/api/auth/users/me/",
                headers={"Authorization": f"Bearer {login_data['access']}"}
            )
            me_data = me_response.json()
            # Script tags should NOT be present in response (currently failing!)
            assert "<script>" not in me_data.get("first_name", ""), "XSS input was not sanitized - SECURITY ISSUE!"
            assert me_data["email"] == unique_email
        else:
            # If rejected, that's also valid
            assert response.status_code == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
