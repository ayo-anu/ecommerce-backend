"""
Input Validation Middleware and Utilities for AI Services.

Provides comprehensive input validation to prevent:
- Injection attacks
- Buffer overflows
- Malformed data
- Resource exhaustion
"""

import re
import logging
from typing import Optional, List, Any, Dict
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


# ==============================================================================
# Configuration
# ==============================================================================

class ValidationConfig:
    """Validation configuration constants."""

    # Request size limits
    MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_JSON_DEPTH = 10
    MAX_ARRAY_LENGTH = 1000
    MAX_STRING_LENGTH = 10000

    # Field limits
    MAX_TEXT_LENGTH = 50000  # For long text fields (e.g., product descriptions)
    MAX_USER_ID_LENGTH = 128
    MAX_PRODUCT_ID_LENGTH = 128

    # Numeric limits
    MIN_PRICE = 0.0
    MAX_PRICE = 1_000_000.0
    MIN_QUANTITY = 0
    MAX_QUANTITY = 10000

    # Regex patterns
    UUID_PATTERN = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    ALPHANUMERIC_PATTERN = r'^[a-zA-Z0-9_-]+$'

    # Dangerous patterns to block
    SQL_INJECTION_PATTERNS = [
        r"(\bUNION\b.*\bSELECT\b)",
        r"(\bDROP\b.*\bTABLE\b)",
        r"(\bINSERT\b.*\bINTO\b)",
        r"(\bDELETE\b.*\bFROM\b)",
        r"(--|\#|/\*|\*/)",
        r"(\bEXEC\b|\bEXECUTE\b)",
        r"(\bXP_\w+)",
    ]

    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe",
        r"<object",
        r"<embed",
    ]

    PATH_TRAVERSAL_PATTERNS = [
        r"\.\./",
        r"\.\.",
        r"~",
        r"/etc/passwd",
        r"\\windows\\system32",
    ]


# ==============================================================================
# Validation Functions
# ==============================================================================

def validate_string_length(value: str, max_length: int, field_name: str = "field") -> str:
    """Validate string length."""
    if len(value) > max_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} exceeds maximum length of {max_length} characters"
        )
    return value


def validate_no_sql_injection(value: str, field_name: str = "field") -> str:
    """Check for SQL injection patterns."""
    for pattern in ValidationConfig.SQL_INJECTION_PATTERNS:
        if re.search(pattern, value, re.IGNORECASE):
            logger.warning(
                f"Potential SQL injection attempt detected in {field_name}",
                extra={"pattern": pattern, "value": value[:100]}
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid input detected in {field_name}"
            )
    return value


def validate_no_xss(value: str, field_name: str = "field") -> str:
    """Check for XSS patterns."""
    for pattern in ValidationConfig.XSS_PATTERNS:
        if re.search(pattern, value, re.IGNORECASE):
            logger.warning(
                f"Potential XSS attempt detected in {field_name}",
                extra={"pattern": pattern, "value": value[:100]}
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid input detected in {field_name}"
            )
    return value


def validate_no_path_traversal(value: str, field_name: str = "field") -> str:
    """Check for path traversal patterns."""
    for pattern in ValidationConfig.PATH_TRAVERSAL_PATTERNS:
        if pattern.lower() in value.lower():
            logger.warning(
                f"Potential path traversal attempt detected in {field_name}",
                extra={"pattern": pattern, "value": value[:100]}
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid input detected in {field_name}"
            )
    return value


def sanitize_input(value: str, max_length: Optional[int] = None) -> str:
    """
    Sanitize user input by validating against common attack patterns.

    Args:
        value: Input string to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized string

    Raises:
        HTTPException: If input contains dangerous patterns
    """
    if not isinstance(value, str):
        return value

    # Strip whitespace
    value = value.strip()

    # Check length
    if max_length:
        value = validate_string_length(value, max_length, "input")

    # Check for attacks
    value = validate_no_sql_injection(value, "input")
    value = validate_no_xss(value, "input")
    value = validate_no_path_traversal(value, "input")

    return value


# ==============================================================================
# Pydantic Base Models with Validation
# ==============================================================================

class SafeString(BaseModel):
    """String field with built-in security validation."""
    value: str = Field(..., max_length=ValidationConfig.MAX_STRING_LENGTH)

    @validator('value')
    def validate_safe_string(cls, v):
        return sanitize_input(v, ValidationConfig.MAX_STRING_LENGTH)


class SafeText(BaseModel):
    """Long text field with validation (for descriptions, content, etc.)."""
    value: str = Field(..., max_length=ValidationConfig.MAX_TEXT_LENGTH)

    @validator('value')
    def validate_safe_text(cls, v):
        return sanitize_input(v, ValidationConfig.MAX_TEXT_LENGTH)


class UserIdInput(BaseModel):
    """Validated user ID input."""
    user_id: str = Field(..., max_length=ValidationConfig.MAX_USER_ID_LENGTH)

    @validator('user_id')
    def validate_user_id(cls, v):
        # Allow UUID or alphanumeric
        if not re.match(ValidationConfig.UUID_PATTERN, v, re.IGNORECASE):
            if not re.match(ValidationConfig.ALPHANUMERIC_PATTERN, v):
                raise ValueError("Invalid user ID format")
        return sanitize_input(v, ValidationConfig.MAX_USER_ID_LENGTH)


class ProductIdInput(BaseModel):
    """Validated product ID input."""
    product_id: str = Field(..., max_length=ValidationConfig.MAX_PRODUCT_ID_LENGTH)

    @validator('product_id')
    def validate_product_id(cls, v):
        # Allow UUID or alphanumeric
        if not re.match(ValidationConfig.UUID_PATTERN, v, re.IGNORECASE):
            if not re.match(ValidationConfig.ALPHANUMERIC_PATTERN, v):
                raise ValueError("Invalid product ID format")
        return sanitize_input(v, ValidationConfig.MAX_PRODUCT_ID_LENGTH)


class PriceInput(BaseModel):
    """Validated price input."""
    price: float = Field(
        ...,
        ge=ValidationConfig.MIN_PRICE,
        le=ValidationConfig.MAX_PRICE
    )


class QuantityInput(BaseModel):
    """Validated quantity input."""
    quantity: int = Field(
        ...,
        ge=ValidationConfig.MIN_QUANTITY,
        le=ValidationConfig.MAX_QUANTITY
    )


# ==============================================================================
# Request Validation Middleware
# ==============================================================================

class InputValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate all incoming requests.

    Validates:
    - Request size
    - Content type
    - Common attack patterns in query parameters

    Usage:
        from shared.validation import InputValidationMiddleware

        app = FastAPI()
        app.add_middleware(InputValidationMiddleware)
    """

    async def dispatch(self, request: Request, call_next):
        # Skip validation for health check endpoints
        if request.url.path in ["/health", "/health/live", "/health/ready", "/metrics"]:
            return await call_next(request)

        # Validate request size
        content_length = request.headers.get("content-length")
        if content_length:
            content_length = int(content_length)
            if content_length > ValidationConfig.MAX_REQUEST_SIZE:
                logger.warning(
                    f"Request size exceeds limit: {content_length} bytes",
                    extra={
                        "path": request.url.path,
                        "method": request.method,
                        "content_length": content_length
                    }
                )
                return JSONResponse(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    content={
                        "error": {
                            "code": "REQUEST_TOO_LARGE",
                            "message": f"Request size exceeds maximum of {ValidationConfig.MAX_REQUEST_SIZE} bytes"
                        }
                    }
                )

        # Validate query parameters
        try:
            for key, value in request.query_params.items():
                # Basic length check
                if len(str(value)) > ValidationConfig.MAX_STRING_LENGTH:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Query parameter '{key}' exceeds maximum length"
                    )

                # Security checks
                sanitize_input(str(value), ValidationConfig.MAX_STRING_LENGTH)

        except HTTPException as e:
            logger.warning(
                f"Invalid query parameter: {e.detail}",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "query_params": dict(request.query_params)
                }
            )
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": {
                        "code": "INVALID_QUERY_PARAMETER",
                        "message": e.detail
                    }
                }
            )

        # Process request
        response = await call_next(request)
        return response


# ==============================================================================
# Validation Utilities
# ==============================================================================

def validate_json_depth(data: Any, max_depth: int = ValidationConfig.MAX_JSON_DEPTH, current_depth: int = 0) -> None:
    """
    Validate JSON nesting depth to prevent DoS attacks.

    Args:
        data: JSON data to validate
        max_depth: Maximum allowed nesting depth
        current_depth: Current depth (used internally)

    Raises:
        HTTPException: If depth exceeds maximum
    """
    if current_depth > max_depth:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"JSON nesting depth exceeds maximum of {max_depth}"
        )

    if isinstance(data, dict):
        for value in data.values():
            validate_json_depth(value, max_depth, current_depth + 1)
    elif isinstance(data, list):
        for item in data:
            validate_json_depth(item, max_depth, current_depth + 1)


def validate_array_length(data: List, max_length: int = ValidationConfig.MAX_ARRAY_LENGTH, field_name: str = "array") -> None:
    """
    Validate array length to prevent resource exhaustion.

    Args:
        data: List to validate
        max_length: Maximum allowed length
        field_name: Name of the field for error messages

    Raises:
        HTTPException: If array exceeds maximum length
    """
    if len(data) > max_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} contains {len(data)} items, maximum is {max_length}"
        )


def validate_recommendation_request(user_id: str, limit: Optional[int] = None) -> None:
    """
    Validate recommendation request parameters.

    Args:
        user_id: User ID
        limit: Number of recommendations to return

    Raises:
        HTTPException: If parameters are invalid
    """
    # Validate user ID
    sanitize_input(user_id, ValidationConfig.MAX_USER_ID_LENGTH)

    # Validate limit
    if limit is not None:
        if not isinstance(limit, int) or limit < 1 or limit > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Limit must be between 1 and 100"
            )


def validate_search_query(query: str, filters: Optional[Dict] = None) -> None:
    """
    Validate search query parameters.

    Args:
        query: Search query string
        filters: Optional filters dictionary

    Raises:
        HTTPException: If parameters are invalid
    """
    # Validate query
    if not query or not query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query cannot be empty"
        )

    sanitize_input(query, ValidationConfig.MAX_STRING_LENGTH)

    # Validate filters
    if filters:
        validate_json_depth(filters)
        for key, value in filters.items():
            if isinstance(value, str):
                sanitize_input(value, ValidationConfig.MAX_STRING_LENGTH)


# ==============================================================================
# Example Usage in Pydantic Models
# ==============================================================================

class RecommendationRequest(BaseModel):
    """Example validated recommendation request."""
    user_id: str = Field(..., max_length=128)
    limit: int = Field(default=10, ge=1, le=100)
    context: Optional[Dict[str, Any]] = None

    @validator('user_id')
    def validate_user_id(cls, v):
        return sanitize_input(v, 128)

    @validator('context')
    def validate_context(cls, v):
        if v:
            validate_json_depth(v)
        return v


class SearchRequest(BaseModel):
    """Example validated search request."""
    query: str = Field(..., min_length=1, max_length=1000)
    filters: Optional[Dict[str, Any]] = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=10000)

    @validator('query')
    def validate_query(cls, v):
        return sanitize_input(v, 1000)

    @validator('filters')
    def validate_filters(cls, v):
        if v:
            validate_json_depth(v)
        return v


logger.info("✅ Input validation utilities loaded")
