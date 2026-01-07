"""
Resilient HTTP Proxy with Circuit Breakers and Retry Logic

Provides fault-tolerant HTTP proxying with:
- Circuit breakers to prevent cascading failures
- Exponential backoff retry logic
- Configurable timeouts
- Comprehensive error handling
- Request/response metrics
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

import httpx
from fastapi import Request
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram

from .circuit_breaker import (
    circuit_breaker_registry,
    CircuitBreakerConfig,
    CircuitBreakerError,
)

logger = logging.getLogger(__name__)


# Prometheus metrics
proxy_requests_total = Counter(
    'gateway_proxy_requests_total',
    'Total proxy requests',
    ['service', 'method', 'status']
)

proxy_request_duration = Histogram(
    'gateway_proxy_request_duration_seconds',
    'Proxy request duration',
    ['service', 'method']
)

proxy_retries_total = Counter(
    'gateway_proxy_retries_total',
    'Total retry attempts',
    ['service']
)

circuit_breaker_state = Counter(
    'gateway_circuit_breaker_state_changes',
    'Circuit breaker state changes',
    ['service', 'state']
)


@dataclass
class RetryConfig:
    """Configuration for retry logic"""
    max_retries: int = 3
    base_delay: float = 0.1  # seconds
    max_delay: float = 10.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True


@dataclass
class TimeoutConfig:
    """Configuration for request timeouts"""
    connect_timeout: float = 5.0  # seconds
    read_timeout: float = 30.0    # seconds
    write_timeout: float = 10.0   # seconds
    pool_timeout: float = 5.0     # seconds


class ResilientProxy:
    """
    Resilient HTTP proxy with circuit breakers and retry logic.

    Features:
    - Circuit breaker per service
    - Exponential backoff retry
    - Configurable timeouts
    - Automatic failover
    - Request/response logging
    - Prometheus metrics
    """

    def __init__(
        self,
        service_name: str,
        service_auth_secret: Optional[str] = None,
        circuit_config: Optional[CircuitBreakerConfig] = None,
        retry_config: Optional[RetryConfig] = None,
        timeout_config: Optional[TimeoutConfig] = None,
    ):
        """
        Initialize resilient proxy.

        Args:
            service_name: Name of the service (for circuit breaker and metrics)
            service_auth_secret: Secret for X-Service-Auth header (zero-trust)
            circuit_config: Circuit breaker configuration
            retry_config: Retry configuration
            timeout_config: Timeout configuration
        """
        self.service_name = service_name
        self.service_auth_secret = service_auth_secret
        self.circuit_breaker = circuit_breaker_registry.get_breaker(
            service_name, circuit_config
        )
        self.retry_config = retry_config or RetryConfig()
        self.timeout_config = timeout_config or TimeoutConfig()

        # Log warning if service auth secret is not configured
        if not self.service_auth_secret:
            logger.warning(
                f"⚠️  Service auth secret not configured for {service_name}. "
                "Internal requests will be rejected by the service."
            )

    async def proxy_request(
        self,
        request: Request,
        target_url: str,
        allow_retries: bool = True,
    ) -> JSONResponse:
        """
        Proxy request to target service with resilience patterns.

        Args:
            request: FastAPI request object
            target_url: Target service URL
            allow_retries: Whether to retry on failure

        Returns:
            JSONResponse with proxied response or error
        """
        correlation_id = getattr(request.state, 'correlation_id', 'unknown')

        try:
            # Execute with circuit breaker protection
            result = await self.circuit_breaker.call(
                self._execute_request,
                request,
                target_url,
                correlation_id,
                allow_retries,
            )

            # Track successful request
            proxy_requests_total.labels(
                service=self.service_name,
                method=request.method,
                status='success'
            ).inc()

            return result

        except CircuitBreakerError as e:
            # Circuit is open - fail fast
            logger.warning(
                f"Circuit breaker open for {self.service_name}: {e}",
                extra={'correlation_id': correlation_id}
            )

            proxy_requests_total.labels(
                service=self.service_name,
                method=request.method,
                status='circuit_open'
            ).inc()

            return JSONResponse(
                status_code=503,
                content={
                    "error": {
                        "type": "service_unavailable",
                        "message": f"Service {self.service_name} is temporarily unavailable",
                        "detail": str(e),
                        "correlation_id": correlation_id,
                    }
                }
            )

        except Exception as e:
            # Unexpected error
            logger.error(
                f"Unexpected error proxying to {self.service_name}: {e}",
                extra={'correlation_id': correlation_id},
                exc_info=True
            )

            proxy_requests_total.labels(
                service=self.service_name,
                method=request.method,
                status='error'
            ).inc()

            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "type": "internal_error",
                        "message": "An unexpected error occurred",
                        "correlation_id": correlation_id,
                    }
                }
            )

    async def _execute_request(
        self,
        request: Request,
        target_url: str,
        correlation_id: str,
        allow_retries: bool,
    ) -> JSONResponse:
        """
        Execute the actual HTTP request with retry logic.

        Args:
            request: FastAPI request
            target_url: Target URL
            correlation_id: Request correlation ID
            allow_retries: Whether retries are allowed

        Returns:
            JSONResponse

        Raises:
            Exception: If all retries fail
        """
        retry_count = 0
        last_exception = None

        # Configure httpx client with timeouts
        timeout = httpx.Timeout(
            connect=self.timeout_config.connect_timeout,
            read=self.timeout_config.read_timeout,
            write=self.timeout_config.write_timeout,
            pool=self.timeout_config.pool_timeout,
        )

        while retry_count <= (self.retry_config.max_retries if allow_retries else 0):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    # Get request body
                    body = await request.body()

                    # Prepare headers (add correlation ID)
                    headers = dict(request.headers)
                    headers['X-Correlation-ID'] = correlation_id

                    # ============================================================
                    # ZERO-TRUST: Inject X-Service-Auth header
                    # ============================================================
                    if self.service_auth_secret:
                        headers['X-Service-Auth'] = self.service_auth_secret
                        logger.debug(
                            f"Injected X-Service-Auth header for {self.service_name}",
                            extra={'correlation_id': correlation_id}
                        )
                    else:
                        logger.warning(
                            f"No service auth secret configured for {self.service_name}",
                            extra={'correlation_id': correlation_id}
                        )

                    # Inject trace context for distributed tracing
                    try:
                        from opentelemetry.propagate import inject
                        inject(headers)
                    except ImportError:
                        pass  # OpenTelemetry not installed

                    # Remove problematic headers
                    headers.pop('host', None)
                    headers.pop('content-length', None)

                    # NEVER leak internal auth headers to external clients
                    headers.pop('authorization', None)

                    # Log request attempt
                    if retry_count > 0:
                        logger.info(
                            f"Retry attempt {retry_count}/{self.retry_config.max_retries} "
                            f"for {self.service_name}",
                            extra={'correlation_id': correlation_id}
                        )
                        proxy_retries_total.labels(service=self.service_name).inc()

                    # Execute request with timing
                    with proxy_request_duration.labels(
                        service=self.service_name,
                        method=request.method
                    ).time():
                        response = await client.request(
                            method=request.method,
                            url=target_url,
                            content=body,
                            headers=headers,
                            params=dict(request.query_params),
                        )

                    # Log successful response
                    logger.info(
                        f"Successful proxy to {self.service_name}: "
                        f"{response.status_code}",
                        extra={'correlation_id': correlation_id}
                    )

                    # Return response
                    return JSONResponse(
                        content=response.json() if response.text else {},
                        status_code=response.status_code,
                        headers={
                            'X-Correlation-ID': correlation_id,
                            'X-Proxied-By': 'api-gateway',
                        }
                    )

            except httpx.TimeoutException as e:
                last_exception = e
                logger.warning(
                    f"Timeout calling {self.service_name} "
                    f"(attempt {retry_count + 1}/{self.retry_config.max_retries + 1}): {e}",
                    extra={'correlation_id': correlation_id}
                )

            except httpx.ConnectError as e:
                last_exception = e
                logger.warning(
                    f"Connection error to {self.service_name} "
                    f"(attempt {retry_count + 1}/{self.retry_config.max_retries + 1}): {e}",
                    extra={'correlation_id': correlation_id}
                )

            except httpx.RequestError as e:
                last_exception = e
                logger.warning(
                    f"Request error to {self.service_name} "
                    f"(attempt {retry_count + 1}/{self.retry_config.max_retries + 1}): {e}",
                    extra={'correlation_id': correlation_id}
                )

            except Exception as e:
                last_exception = e
                logger.error(
                    f"Unexpected error calling {self.service_name}: {e}",
                    extra={'correlation_id': correlation_id},
                    exc_info=True
                )
                # Don't retry on unexpected errors
                raise

            # Calculate retry delay with exponential backoff
            if retry_count < self.retry_config.max_retries and allow_retries:
                delay = min(
                    self.retry_config.base_delay * (
                        self.retry_config.exponential_base ** retry_count
                    ),
                    self.retry_config.max_delay
                )

                # Add jitter to prevent thundering herd
                if self.retry_config.jitter:
                    import random
                    delay = delay * (0.5 + random.random() * 0.5)

                logger.debug(
                    f"Waiting {delay:.2f}s before retry",
                    extra={'correlation_id': correlation_id}
                )
                await asyncio.sleep(delay)

            retry_count += 1

        # All retries exhausted
        logger.error(
            f"All retries exhausted for {self.service_name} "
            f"after {retry_count} attempts",
            extra={'correlation_id': correlation_id}
        )

        # Raise last exception to trigger circuit breaker
        raise last_exception or Exception("Request failed after all retries")


class ProxyRegistry:
    """
    Registry to manage resilient proxies for multiple services.

    Usage:
        registry = ProxyRegistry()
        proxy = registry.get_proxy("recommendation-service")
        response = await proxy.proxy_request(request, url)
    """

    def __init__(self):
        self._proxies: Dict[str, ResilientProxy] = {}

    def get_proxy(
        self,
        service_name: str,
        service_auth_secret: Optional[str] = None,
        circuit_config: Optional[CircuitBreakerConfig] = None,
        retry_config: Optional[RetryConfig] = None,
        timeout_config: Optional[TimeoutConfig] = None,
    ) -> ResilientProxy:
        """
        Get or create a resilient proxy for a service.

        Args:
            service_name: Service name
            service_auth_secret: Service authentication secret for X-Service-Auth
            circuit_config: Optional circuit breaker config
            retry_config: Optional retry config
            timeout_config: Optional timeout config

        Returns:
            ResilientProxy instance
        """
        if service_name not in self._proxies:
            self._proxies[service_name] = ResilientProxy(
                service_name,
                service_auth_secret,
                circuit_config,
                retry_config,
                timeout_config,
            )

        return self._proxies[service_name]

    def get_all_circuit_states(self) -> Dict[str, Any]:
        """Get circuit breaker states for all proxies"""
        return {
            name: proxy.circuit_breaker.get_state()
            for name, proxy in self._proxies.items()
        }


# Global proxy registry
proxy_registry = ProxyRegistry()
