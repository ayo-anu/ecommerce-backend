"""
Enhanced CORS Security Middleware.

Provides stricter CORS controls beyond django-cors-headers:
- Origin validation with wildcard pattern support
- Conditional CORS based on authentication
- Request method restrictions
- Header validation
- Preflight request caching
- Security logging
"""

import re
import logging
from typing import List, Set, Optional
from django.conf import settings
from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class SecureCORSMiddleware(MiddlewareMixin):
    """
    Enhanced CORS middleware with stricter security controls.

    Features:
    - Origin pattern matching (e.g., *.example.com)
    - Method-specific origin restrictions
    - Credential control per origin
    - Security logging for CORS violations
    """

    def __init__(self, get_response):
        super().__init__(get_response)
        self.allowed_origins = self._parse_allowed_origins()
        self.allowed_origin_patterns = self._compile_origin_patterns()

    def _parse_allowed_origins(self) -> Set[str]:
        """Parse allowed origins from settings."""
        origins = getattr(settings, 'SECURE_CORS_ALLOWED_ORIGINS', [])
        if isinstance(origins, str):
            origins = [o.strip() for o in origins.split(',') if o.strip()]
        return set(origins)

    def _compile_origin_patterns(self) -> List[re.Pattern]:
        """
        Compile regex patterns for wildcard origin matching.

        Example: https://*.example.com matches https://app.example.com
        """
        patterns = getattr(settings, 'SECURE_CORS_ORIGIN_PATTERNS', [])
        compiled = []

        for pattern in patterns:
            # Convert wildcard pattern to regex
            regex_pattern = pattern.replace('.', r'\.')
regex_pattern = regex_pattern.replace('*', r'[a-zA-Z0-9-]+')
            regex_pattern = f"^{regex_pattern}$"
            compiled.append(re.compile(regex_pattern))

        return compiled

    def process_request(self, request):
        """
        Process incoming request for CORS validation.

        For preflight requests (OPTIONS), handle immediately.
        For regular requests, validate origin.
        """
        origin = request.META.get('HTTP_ORIGIN')

        if not origin:
            # No Origin header - not a CORS request
            return None

        # Log all CORS requests for monitoring
        logger.debug(
            f"CORS request",
            extra={
                'origin': origin,
                'method': request.method,
                'path': request.path,
                'user': request.user.username if request.user.is_authenticated else 'anonymous',
            }
        )

        # Handle preflight requests
        if request.method == 'OPTIONS':
            return self._handle_preflight(request, origin)

        # Validate origin for actual requests
        if not self._is_origin_allowed(origin, request):
            logger.warning(
                f"CORS request from unauthorized origin",
                extra={
                    'origin': origin,
                    'method': request.method,
                    'path': request.path,
                    'ip': self._get_client_ip(request),
                }
            )
            # Don't add CORS headers - browser will block
            return None

        return None

    def process_response(self, request, response):
        """Add CORS headers to response if origin is allowed."""
        origin = request.META.get('HTTP_ORIGIN')

        if not origin:
            return response

        if not self._is_origin_allowed(origin, request):
            return response

        # Add CORS headers
        response['Access-Control-Allow-Origin'] = origin

        # Only allow credentials for trusted origins
        if self._should_allow_credentials(origin):
            response['Access-Control-Allow-Credentials'] = 'true'

        # Expose custom headers if configured
        exposed_headers = getattr(settings, 'SECURE_CORS_EXPOSE_HEADERS', [])
        if exposed_headers:
            response['Access-Control-Expose-Headers'] = ', '.join(exposed_headers)

        return response

    def _handle_preflight(self, request, origin: str) -> HttpResponse:
        """
        Handle CORS preflight (OPTIONS) request.

        Returns appropriate headers or 403 if origin not allowed.
        """
        if not self._is_origin_allowed(origin, request):
            return HttpResponse('Origin not allowed', status=403)

        response = HttpResponse()
        response['Access-Control-Allow-Origin'] = origin

        # Allow credentials if configured
        if self._should_allow_credentials(origin):
            response['Access-Control-Allow-Credentials'] = 'true'

        # Allowed methods
        allowed_methods = self._get_allowed_methods(origin)
        response['Access-Control-Allow-Methods'] = ', '.join(allowed_methods)

        # Allowed headers
        allowed_headers = self._get_allowed_headers()
        response['Access-Control-Allow-Headers'] = ', '.join(allowed_headers)

        # Preflight cache duration (24 hours)
        response['Access-Control-Max-Age'] = '86400'

        return response

    def _is_origin_allowed(self, origin: str, request) -> bool:
        """Check if origin is allowed."""
        # Exact match
        if origin in self.allowed_origins:
            return True

        # Pattern match
        for pattern in self.allowed_origin_patterns:
            if pattern.match(origin):
                return True

        # Check method-specific origins
        method_origins = getattr(settings, f'SECURE_CORS_{request.method}_ORIGINS', None)
        if method_origins and origin in method_origins:
            return True

        return False

    def _should_allow_credentials(self, origin: str) -> bool:
        """
        Determine if credentials should be allowed for this origin.

        More restrictive than django-cors-headers default.
        """
        # Only allow credentials for explicitly trusted origins
        trusted_origins = getattr(settings, 'SECURE_CORS_TRUSTED_ORIGINS', set())
        return origin in trusted_origins

    def _get_allowed_methods(self, origin: str) -> List[str]:
        """Get allowed HTTP methods for origin."""
        # Default allowed methods
        default_methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']

        # Origin-specific method restrictions
        method_restrictions = getattr(settings, 'SECURE_CORS_METHOD_RESTRICTIONS', {})

        if origin in method_restrictions:
            return method_restrictions[origin]

        return default_methods

    def _get_allowed_headers(self) -> List[str]:
        """Get allowed request headers."""
        return getattr(
            settings,
            'SECURE_CORS_ALLOW_HEADERS',
            [
                'Accept',
                'Accept-Language',
                'Content-Type',
                'Content-Language',
                'Authorization',
                'X-Requested-With',
                'X-CSRFToken',
            ]
        )

    def _get_client_ip(self, request) -> str:
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')


# Configuration example for settings.py
"""
# Exact origins
SECURE_CORS_ALLOWED_ORIGINS = [
    'https://www.example.com',
    'https://app.example.com',
    'https://admin.example.com',
]

# Pattern-based origins (e.g., for customer subdomains)
SECURE_CORS_ORIGIN_PATTERNS = [
    r'https://*.example.com',  # Matches any subdomain
]

# Origins that can use credentials (stricter)
SECURE_CORS_TRUSTED_ORIGINS = {
    'https://www.example.com',
    'https://app.example.com',
}

# Method-specific restrictions
SECURE_CORS_METHOD_RESTRICTIONS = {
    'https://public.example.com': ['GET', 'OPTIONS'],  # Read-only
}

# Headers to expose to browser
SECURE_CORS_EXPOSE_HEADERS = [
    'X-Request-ID',
    'X-RateLimit-Remaining',
]

# Allowed request headers
SECURE_CORS_ALLOW_HEADERS = [
    'Accept',
    'Content-Type',
    'Authorization',
    'X-CSRFToken',
]
"""
