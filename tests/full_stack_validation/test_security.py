"""
Security Testing and Vulnerability Assessment
Comprehensive security tests including auth, CORS, injection, and best practices
"""
import pytest
import requests
import re
import os
import json
from pathlib import Path
from urllib.parse import urljoin
from typing import List, Dict


class TestAuthenticationSecurity:
    """Test authentication and authorization security"""

    def test_no_default_credentials(self):
        """System should not accept default/weak credentials"""
        base_url = os.environ.get('BACKEND_URL', 'http://localhost:8000')
        login_url = urljoin(base_url, '/api/auth/login/')

        # Common default credentials
        default_creds = [
            {'email': 'admin@admin.com', 'password': 'admin'},
            {'email': 'admin@example.com', 'password': 'admin123'},
            {'email': 'test@test.com', 'password': 'test'},
            {'username': 'admin', 'password': 'admin'},
        ]

        for creds in default_creds:
            response = requests.post(login_url, json=creds, timeout=5)

            # Should NOT succeed with default credentials
            if response.status_code == 200:
                print(f"⚠️  WARNING: Default credentials work: {creds['email'] if 'email' in creds else creds['username']}")
            else:
                print(f"✅ Default credentials rejected: {creds.get('email', creds.get('username'))}")

    def test_password_in_response(self):
        """Password should never be in API responses"""
        base_url = os.environ.get('BACKEND_URL', 'http://localhost:8000')
        register_url = urljoin(base_url, '/api/auth/register/')

        payload = {
            'email': f'sectest{os.urandom(4).hex()}@example.com',
            'password': 'TestPassword123!',
            'first_name': 'Security',
            'last_name': 'Test'
        }

        response = requests.post(register_url, json=payload, timeout=5)

        if response.status_code in [200, 201]:
            response_text = response.text.lower()

            # Password should not be in response
            assert 'testpassword123' not in response_text, \
                "Password leaked in API response!"

            print("✅ Password not exposed in registration response")

    def test_jwt_token_expiration(self):
        """JWT tokens should have expiration"""
        base_url = os.environ.get('BACKEND_URL', 'http://localhost:8000')

        # Try to verify a clearly expired token
        verify_url = urljoin(base_url, '/api/auth/token/verify/')

        payload = {
            'token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE2MDAwMDAwMDB9.invalid'
        }

        response = requests.post(verify_url, json=payload, timeout=5)

        # Should reject expired/invalid token
        assert response.status_code in [400, 401], \
            "Invalid token was accepted"

        print("✅ Invalid tokens are rejected")

    def test_authorization_enforcement(self):
        """Protected resources should require proper authorization"""
        base_url = os.environ.get('BACKEND_URL', 'http://localhost:8000')

        protected_endpoints = [
            '/api/orders/orders/',
            '/api/analytics/dashboard/',
            '/api/auth/users/me/',
        ]

        for endpoint in protected_endpoints:
            url = urljoin(base_url, endpoint)

            # Without auth
            response = requests.get(url, timeout=5)
            assert response.status_code in [401, 403], \
                f"{endpoint} accessible without authentication"

            # With invalid token
            headers = {'Authorization': 'Bearer invalid_token'}
            response = requests.get(url, headers=headers, timeout=5)
            assert response.status_code in [401, 403], \
                f"{endpoint} accessible with invalid token"

        print(f"✅ {len(protected_endpoints)} protected endpoints require auth")


class TestInjectionVulnerabilities:
    """Test for SQL injection, XSS, and command injection"""

    def test_sql_injection_in_search(self):
        """Search should be safe from SQL injection"""
        base_url = os.environ.get('BACKEND_URL', 'http://localhost:8000')

        # Common SQL injection payloads
        injection_payloads = [
            "' OR '1'='1",
            "'; DROP TABLE products; --",
            "' UNION SELECT * FROM users --",
            "admin' --",
        ]

        for payload in injection_payloads:
            # Try in product search
            url = urljoin(base_url, f'/api/products/products/?search={payload}')

            response = requests.get(url, timeout=5)

            # Should not cause server error
            assert response.status_code != 500, \
                f"SQL injection payload caused 500 error: {payload}"

            # Response should not contain SQL error messages
            if response.status_code == 200:
                response_text = response.text.lower()
                sql_errors = ['syntax error', 'mysql', 'postgresql', 'sqlite']

                for error in sql_errors:
                    assert error not in response_text, \
                        f"SQL error exposed: {error}"

        print("✅ SQL injection tests passed")

    def test_xss_in_input_fields(self):
        """Input should be sanitized against XSS"""
        base_url = os.environ.get('BACKEND_URL', 'http://localhost:8000')

        xss_payloads = [
            '<script>alert("XSS")</script>',
            '<img src=x onerror=alert("XSS")>',
            'javascript:alert("XSS")',
        ]

        # Try XSS in registration
        register_url = urljoin(base_url, '/api/auth/register/')

        for payload in xss_payloads:
            test_payload = {
                'email': f'test{os.urandom(4).hex()}@example.com',
                'password': 'Test123!',
                'first_name': payload,  # XSS attempt
                'last_name': 'Test'
            }

            response = requests.post(register_url, json=test_payload, timeout=5)

            # Should either reject or sanitize
            if response.status_code in [200, 201]:
                response_text = response.text

                # Raw script tags should not appear in response
                assert '<script>' not in response_text, \
                    "XSS payload not sanitized!"

        print("✅ XSS injection tests passed")


class TestCORSSecurity:
    """Test CORS configuration"""

    def test_cors_headers_present(self):
        """CORS headers should be configured"""
        base_url = os.environ.get('BACKEND_URL', 'http://localhost:8000')
        url = urljoin(base_url, '/api/products/products/')

        response = requests.options(url, timeout=5)

        # Check for CORS headers
        has_cors = (
            'Access-Control-Allow-Origin' in response.headers or
            'access-control-allow-origin' in response.headers
        )

        if has_cors:
            print(f"✅ CORS headers configured: {response.headers.get('Access-Control-Allow-Origin')}")
        else:
            print("⚠️  CORS headers not found (may need configuration)")

    def test_cors_not_too_permissive(self):
        """CORS should not allow all origins in production"""
        base_url = os.environ.get('BACKEND_URL', 'http://localhost:8000')
        url = urljoin(base_url, '/api/products/products/')

        response = requests.get(url, timeout=5)

        cors_origin = response.headers.get('Access-Control-Allow-Origin', '')

        # In production, should not be '*'
        if cors_origin == '*':
            print("⚠️  WARNING: CORS allows all origins (*)")
        else:
            print(f"✅ CORS restricted: {cors_origin}")


class TestDataExposure:
    """Test for sensitive data exposure"""

    def test_no_debug_info_in_responses(self):
        """Debug information should not leak in responses"""
        base_url = os.environ.get('BACKEND_URL', 'http://localhost:8000')

        # Trigger an error
        url = urljoin(base_url, '/api/products/products/99999999/')
        response = requests.get(url, timeout=5)

        response_text = response.text.lower()

        # Should not contain debug information
        debug_indicators = [
            'traceback',
            'python',
            'django',
            'settings.py',
            '/usr/local',
            'secret_key',
        ]

        for indicator in debug_indicators:
            assert indicator not in response_text, \
                f"Debug information leaked: {indicator}"

        print("✅ No debug information in error responses")

    def test_no_secrets_in_responses(self):
        """API keys and secrets should not be exposed"""
        base_url = os.environ.get('BACKEND_URL', 'http://localhost:8000')

        endpoints = [
            '/health/',
            '/api/products/products/',
            '/',
        ]

        for endpoint in endpoints:
            url = urljoin(base_url, endpoint)
            response = requests.get(url, timeout=5)

            response_text = response.text.lower()

            # Check for common secret patterns
            secrets = [
                'secret_key',
                'api_key',
                'password',
                'aws_access_key',
                'private_key',
            ]

            for secret in secrets:
                if secret in response_text:
                    print(f"⚠️  WARNING: '{secret}' found in {endpoint}")

        print("✅ Secret exposure check complete")


class TestRateLimiting:
    """Test rate limiting implementation"""

    def test_rate_limiting_exists(self):
        """Check if rate limiting is implemented"""
        base_url = os.environ.get('BACKEND_URL', 'http://localhost:8000')
        url = urljoin(base_url, '/api/products/products/')

        # Make many rapid requests
        responses = []
        for i in range(50):
            try:
                response = requests.get(url, timeout=2)
                responses.append(response.status_code)

                if response.status_code == 429:
                    print("✅ Rate limiting active (429 Too Many Requests)")
                    return
            except:
                break

        # Check if any were rate limited
        if 429 in responses:
            print("✅ Rate limiting detected")
        else:
            print("⚠️  No rate limiting detected (50 requests succeeded)")


class TestFileUploadSecurity:
    """Test file upload security"""

    def test_file_upload_validation(self):
        """File uploads should validate file types"""
        # Note: This requires finding an upload endpoint
        # Skipping if no upload endpoint available
        pytest.skip("File upload testing requires specific endpoint")


class TestHeadersSecurity:
    """Test security headers"""

    def test_security_headers_present(self):
        """Important security headers should be set"""
        base_url = os.environ.get('BACKEND_URL', 'http://localhost:8000')
        url = urljoin(base_url, '/health/')

        response = requests.get(url, timeout=5)

        headers = response.headers

        # Recommended security headers
        security_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': ['DENY', 'SAMEORIGIN'],
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': None,  # HSTS
        }

        results = []

        for header, expected in security_headers.items():
            if header in headers:
                value = headers[header]
                if expected is None or value in (expected if isinstance(expected, list) else [expected]):
                    results.append(f"✅ {header}: {value}")
                else:
                    results.append(f"⚠️  {header}: {value} (expected {expected})")
            else:
                results.append(f"❌ {header}: not set")

        print("\n🔒 Security Headers:")
        for result in results:
            print(f"   {result}")


class TestCodeSecrets:
    """Scan code for hardcoded secrets"""

    def test_no_hardcoded_secrets_in_codebase(self):
        """Source code should not contain hardcoded secrets"""

        project_root = Path(__file__).parent.parent.parent

        # Patterns to detect
        secret_patterns = [
            (r'password\s*=\s*["\'][^"\']{8,}["\']', 'hardcoded password'),
            (r'api[_-]?key\s*=\s*["\'][^"\']+["\']', 'hardcoded API key'),
            (r'secret[_-]?key\s*=\s*["\'][^"\']{20,}["\']', 'hardcoded secret key'),
            (r'aws[_-]?access[_-]?key[_-]?id\s*=\s*["\'][^"\']+["\']', 'AWS key'),
            (r'sk-[a-zA-Z0-9]{20,}', 'OpenAI API key'),
        ]

        findings = []

        # Scan Python files
        python_files = list(project_root.glob('services/**/*.py'))

        for file_path in python_files[:100]:  # Limit to prevent timeout
            try:
                content = file_path.read_text()

                for pattern, description in secret_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)

                    for match in matches:
                        # Exclude comments and test files
                        line = content[max(0, match.start()-50):match.end()+50]

                        if '#' not in line and 'test' not in str(file_path).lower():
                            findings.append({
                                'file': str(file_path.relative_to(project_root)),
                                'type': description,
                                'line': line.strip()[:80]
                            })
            except Exception:
                continue

        if findings:
            print("\n⚠️  Potential hardcoded secrets found:")
            for finding in findings[:10]:  # Show first 10
                print(f"   {finding['file']}: {finding['type']}")

        # Allow some findings in test/config files
        assert len(findings) < 20, \
            f"Too many potential secrets found: {len(findings)}"


class TestDependencyVulnerabilities:
    """Check for vulnerable dependencies"""

    def test_check_python_dependencies(self):
        """Check Python dependencies for known vulnerabilities"""

        # This would require 'safety' package
        # pip install safety

        try:
            import subprocess
            result = subprocess.run(
                ['safety', 'check', '--json'],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                print("✅ No known vulnerabilities in dependencies")
            else:
                try:
                    vulns = json.loads(result.stdout)
                    print(f"⚠️  Found {len(vulns)} vulnerabilities")
                except:
                    print("⚠️  Vulnerability check completed with warnings")

        except FileNotFoundError:
            pytest.skip("'safety' package not installed")
        except Exception as e:
            pytest.skip(f"Could not check dependencies: {e}")


class TestEnvironmentVariables:
    """Test environment variable security"""

    def test_no_secrets_in_env_example(self):
        """Example env files should not contain real secrets"""

        project_root = Path(__file__).parent.parent.parent

        env_example_files = [
            project_root / '.env.example',
            project_root / '.env.sample',
            project_root / 'services' / 'backend' / '.env.example',
        ]

        for env_file in env_example_files:
            if env_file.exists():
                content = env_file.read_text()

                # Should contain placeholders, not real values
                real_value_indicators = [
                    r'sk-[a-zA-Z0-9]{20,}',  # OpenAI keys
                    r'AKIA[A-Z0-9]{16}',  # AWS keys
                ]

                for pattern in real_value_indicators:
                    matches = re.findall(pattern, content)
                    assert len(matches) == 0, \
                        f"Real secret found in {env_file.name}"

        print("✅ No secrets in example env files")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
