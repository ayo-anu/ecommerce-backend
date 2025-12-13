"""
Web Application Firewall (WAF) Implementation.

Provides request validation and security filtering:
- SQL injection detection
- XSS (Cross-Site Scripting) prevention
- Request body size limits
- Header validation
- Path traversal detection
- Command injection detection
- Suspicious pattern blocking
"""

import re
import logging
from typing import Optional, List
from fastapi import Request, HTTPException
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_413_REQUEST_ENTITY_TOO_LARGE
from starlette.datastructures import Headers

logger = logging.getLogger(__name__)


# ==============================================================================
# Security Patterns
# ==============================================================================

# SQL Injection patterns
SQL_INJECTION_PATTERNS = [
    r"(\%27)|(\')|(\-\-)|(\%23)|(#)",  # SQL meta-characters
    r"((\%3D)|(=))[^\n]*((\%27)|(\')|(\-\-)|(\%3B)|(;))",  # SQL operators
    r"\w*((\%27)|(\'))(\s|\%20)*((\%6F)|o|(\%4F))((\%72)|r|(\%52))",  # 'or' keyword
    r"((\%27)|(\'))union",  # UNION keyword
    r"exec(\s|\+)+(s|x)p\w+",  # Stored procedures
    r"UNION.*SELECT",  # UNION SELECT
    r"INSERT\s+INTO",  # INSERT
    r"DELETE\s+FROM",  # DELETE
    r"DROP\s+(TABLE|DATABASE)",  # DROP
    r"UPDATE\s+.*SET",  # UPDATE
]

# XSS patterns
XSS_PATTERNS = [
    r"<script[^>]*>.*?</script>",  # Script tags
    r"javascript:",  # JavaScript protocol
    r"on\w+\s*=",  # Event handlers
    r"<iframe",  # iframes
    r"<object",  # objects
    r"<embed",  # embeds
    r"eval\(",  # eval function
]

# Path traversal patterns
PATH_TRAVERSAL_PATTERNS = [
    r"\.\./",  # Directory traversal
    r"\.\.\\",  # Windows directory traversal
    r"/etc/passwd",  # Unix password file
    r"c:\\windows",  # Windows system directory
]

# Command injection patterns
COMMAND_INJECTION_PATTERNS = [
    r";.*\s*(ls|cat|wget|curl|nc|bash|sh|cmd|powershell)",  # Command chaining
    r"\|.*\s*(ls|cat|wget|curl|nc|bash|sh|cmd|powershell)",  # Pipe commands
    r"`.*`",  # Backtick execution
    r"\$\(.*\)",  # Command substitution
]


class WAF:
    """Web Application Firewall."""

    def __init__(
        self,
        max_body_size: int = 10 * 1024 * 1024,  # 10MB default
        max_header_size: int = 8 * 1024,  # 8KB default
        enable_sql_injection_check: bool = True,
        enable_xss_check: bool = True,
        enable_path_traversal_check: bool = True,
        enable_command_injection_check: bool = True,
    ):
        """
        Initialize WAF.

        Args:
            max_body_size: Maximum request body size in bytes
            max_header_size: Maximum header size in bytes
            enable_sql_injection_check: Enable SQL injection detection
            enable_xss_check: Enable XSS detection
            enable_path_traversal_check: Enable path traversal detection
            enable_command_injection_check: Enable command injection detection
        """
        self.max_body_size = max_body_size
        self.max_header_size = max_header_size
        self.enable_sql_injection_check = enable_sql_injection_check
        self.enable_xss_check = enable_xss_check
        self.enable_path_traversal_check = enable_path_traversal_check
        self.enable_command_injection_check = enable_command_injection_check

        # Compile patterns for performance
        self.sql_patterns = [re.compile(p, re.IGNORECASE) for p in SQL_INJECTION_PATTERNS]
        self.xss_patterns = [re.compile(p, re.IGNORECASE) for p in XSS_PATTERNS]
        self.path_patterns = [re.compile(p, re.IGNORECASE) for p in PATH_TRAVERSAL_PATTERNS]
        self.cmd_patterns = [re.compile(p, re.IGNORECASE) for p in COMMAND_INJECTION_PATTERNS]

    def check_sql_injection(self, value: str) -> Optional[str]:
        """Check for SQL injection patterns."""
        if not self.enable_sql_injection_check:
            return None

        for pattern in self.sql_patterns:
            if pattern.search(value):
                return f"SQL injection pattern detected: {pattern.pattern}"
        return None

    def check_xss(self, value: str) -> Optional[str]:
        """Check for XSS patterns."""
        if not self.enable_xss_check:
            return None

        for pattern in self.xss_patterns:
            if pattern.search(value):
                return f"XSS pattern detected: {pattern.pattern}"
        return None

    def check_path_traversal(self, value: str) -> Optional[str]:
        """Check for path traversal patterns."""
        if not self.enable_path_traversal_check:
            return None

        for pattern in self.path_patterns:
            if pattern.search(value):
                return f"Path traversal pattern detected"
        return None

    def check_command_injection(self, value: str) -> Optional[str]:
        """Check for command injection patterns."""
        if not self.enable_command_injection_check:
            return None

        for pattern in self.cmd_patterns:
            if pattern.search(value):
                return f"Command injection pattern detected"
        return None

    def check_value(self, value: str) -> Optional[str]:
        """
        Check a string value against all patterns.

        Returns:
            Error message if malicious pattern detected, None otherwise
        """
        checks = [
            self.check_sql_injection(value),
            self.check_xss(value),
            self.check_path_traversal(value),
            self.check_command_injection(value),
        ]

        for error in checks:
            if error:
                return error

        return None

    async def validate_request(self, request: Request) -> None:
        """
        Validate incoming request.

        Args:
            request: FastAPI request

        Raises:
            HTTPException: If request is malicious or invalid
        """
        # 1. Check request body size
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_body_size:
            logger.warning(
                f"Request body too large: {content_length} bytes "
                f"(max: {self.max_body_size})"
            )
            raise HTTPException(
                status_code=HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Request body too large. Max size: {self.max_body_size} bytes"
            )

        # 2. Check headers size
        headers_size = sum(len(k) + len(v) for k, v in request.headers.items())
        if headers_size > self.max_header_size:
            logger.warning(
                f"Request headers too large: {headers_size} bytes "
                f"(max: {self.max_header_size})"
            )
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="Request headers too large"
            )

        # 3. Validate URL path
        path = str(request.url.path)
        error = self.check_value(path)
        if error:
            logger.warning(f"Malicious pattern in URL path: {error}")
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="Invalid request: malicious pattern detected in URL"
            )

        # 4. Validate query parameters
        for key, value in request.query_params.items():
            error = self.check_value(str(key)) or self.check_value(str(value))
            if error:
                logger.warning(
                    f"Malicious pattern in query param '{key}': {error}"
                )
                raise HTTPException(
                    status_code=HTTP_400_BAD_REQUEST,
                    detail=f"Invalid request: malicious pattern detected in query parameter"
                )

        # 5. Validate specific headers that might contain user input
        suspicious_headers = ["referer", "user-agent", "x-forwarded-for"]
        for header_name in suspicious_headers:
            header_value = request.headers.get(header_name, "")
            if header_value:
                error = self.check_value(header_value)
                if error:
                    logger.warning(
                        f"Malicious pattern in header '{header_name}': {error}"
                    )
                    # Don't block on suspicious headers, just log
                    # as they might have false positives
                    continue

        # 6. Validate Host header (prevent host header injection)
        host = request.headers.get("host", "")
        if host:
            # Check for suspicious characters in Host header
            if re.search(r"[<>\"'`]", host):
                logger.warning(f"Suspicious Host header: {host}")
                raise HTTPException(
                    status_code=HTTP_400_BAD_REQUEST,
                    detail="Invalid Host header"
                )


# ==============================================================================
# Additional Security Headers
# ==============================================================================

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none';"
    ),
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}


def add_security_headers(headers: dict) -> dict:
    """
    Add security headers to response.

    Args:
        headers: Existing headers dict

    Returns:
        Updated headers dict
    """
    return {**headers, **SECURITY_HEADERS}


# ==============================================================================
# IP Blocking
# ==============================================================================

class IPBlocker:
    """IP address blocking."""

    def __init__(self, blocked_ips: Optional[List[str]] = None):
        """
        Initialize IP blocker.

        Args:
            blocked_ips: List of IP addresses to block
        """
        self.blocked_ips = set(blocked_ips or [])

    def is_blocked(self, ip: str) -> bool:
        """Check if IP is blocked."""
        return ip in self.blocked_ips

    def block_ip(self, ip: str):
        """Add IP to blocked list."""
        self.blocked_ips.add(ip)
        logger.info(f"Blocked IP: {ip}")

    def unblock_ip(self, ip: str):
        """Remove IP from blocked list."""
        self.blocked_ips.discard(ip)
        logger.info(f"Unblocked IP: {ip}")

    async def validate_request(self, request: Request):
        """
        Validate request IP.

        Raises:
            HTTPException: If IP is blocked
        """
        client_ip = request.client.host if request.client else "unknown"

        # Check X-Forwarded-For header
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()

        if self.is_blocked(client_ip):
            logger.warning(f"Blocked request from IP: {client_ip}")
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="Access denied"
            )
