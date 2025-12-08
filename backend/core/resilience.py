"""
Resilience utilities for Django backend

Provides circuit breakers, retry logic, and timeouts for external service calls.
This module is designed for synchronous Django views and tasks.
"""

import time
import logging
import random
from typing import Callable, Optional, Any, Dict
from functools import wraps
from dataclasses import dataclass
from enum import Enum
from collections import deque
from threading import Lock

import requests
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Service failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5  # Number of failures to open circuit
    success_threshold: int = 2  # Number of successes to close circuit
    timeout: int = 60  # Seconds to wait before trying again
    window_size: int = 100  # Size of sliding window for failure tracking


@dataclass
class RetryConfig:
    """Configuration for retry logic"""
    max_retries: int = 3
    base_delay: float = 0.1  # seconds
    max_delay: float = 10.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True
    # Which HTTP status codes should trigger retries
    retry_on_status: tuple = (408, 429, 500, 502, 503, 504)


@dataclass
class TimeoutConfig:
    """Configuration for request timeouts"""
    connect_timeout: float = 5.0  # seconds
    read_timeout: float = 30.0    # seconds


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open"""
    pass


class CircuitBreaker:
    """
    Thread-safe circuit breaker for synchronous calls.

    States:
    - CLOSED: All requests pass through
    - OPEN: All requests fail fast without calling service
    - HALF_OPEN: Allow limited requests to test if service recovered
    """

    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        """
        Initialize circuit breaker.

        Args:
            name: Name of the circuit (usually service name)
            config: Circuit breaker configuration
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.recent_calls = deque(maxlen=self.config.window_size)
        self._lock = Lock()

    def _should_attempt_reset(self) -> bool:
        """Check if we should try to reset the circuit"""
        if self.state != CircuitState.OPEN:
            return False

        if self.last_failure_time is None:
            return False

        time_since_failure = time.time() - self.last_failure_time
        return time_since_failure >= self.config.timeout

    def _record_success(self):
        """Record a successful call"""
        with self._lock:
            self.recent_calls.append(True)

            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1

                if self.success_count >= self.config.success_threshold:
                    # Recovered! Close the circuit
                    logger.info(
                        f"Circuit breaker '{self.name}' closing "
                        f"(success_count={self.success_count})"
                    )
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0

    def _record_failure(self):
        """Record a failed call"""
        with self._lock:
            self.recent_calls.append(False)
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.state == CircuitState.CLOSED:
                # Count recent failures in window
                recent_failures = sum(1 for call in self.recent_calls if not call)

                if recent_failures >= self.config.failure_threshold:
                    # Too many failures, open the circuit
                    logger.warning(
                        f"Circuit breaker '{self.name}' opening "
                        f"(failures={recent_failures}/{self.config.window_size})"
                    )
                    self.state = CircuitState.OPEN
                    self.success_count = 0

            elif self.state == CircuitState.HALF_OPEN:
                # Failed during recovery, go back to open
                logger.warning(
                    f"Circuit breaker '{self.name}' failed during recovery, "
                    "going back to OPEN"
                )
                self.state = CircuitState.OPEN
                self.success_count = 0

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerError: If circuit is open
            Exception: Original exception from function
        """
        # Check if we should attempt reset
        if self._should_attempt_reset():
            with self._lock:
                logger.info(
                    f"Circuit breaker '{self.name}' entering HALF_OPEN state "
                    "(attempting recovery)"
                )
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                self.failure_count = 0

        # Fail fast if circuit is open
        if self.state == CircuitState.OPEN:
            raise CircuitBreakerError(
                f"Circuit breaker '{self.name}' is OPEN "
                f"(wait {self.config.timeout}s before retry)"
            )

        # Try to execute the function
        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result

        except Exception as e:
            self._record_failure()
            raise

    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state"""
        with self._lock:
            return {
                "name": self.name,
                "state": self.state.value,
                "failure_count": self.failure_count,
                "success_count": self.success_count,
                "recent_failures": sum(1 for call in self.recent_calls if not call),
                "total_calls": len(self.recent_calls),
                "last_failure_time": self.last_failure_time,
            }


class CircuitBreakerRegistry:
    """Registry to manage multiple circuit breakers."""

    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._lock = Lock()

    def get_breaker(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
    ) -> CircuitBreaker:
        """Get or create a circuit breaker."""
        if name not in self._breakers:
            with self._lock:
                if name not in self._breakers:  # Double-check locking
                    self._breakers[name] = CircuitBreaker(name, config)

        return self._breakers[name]

    def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        """Get states of all circuit breakers"""
        return {name: breaker.get_state() for name, breaker in self._breakers.items()}

    def reset_breaker(self, name: str):
        """Force reset a circuit breaker"""
        if name in self._breakers:
            breaker = self._breakers[name]
            with breaker._lock:
                breaker.state = CircuitState.CLOSED
                breaker.failure_count = 0
                breaker.success_count = 0
                breaker.recent_calls.clear()
                logger.info(f"Circuit breaker '{name}' manually reset")


# Global registry
circuit_breaker_registry = CircuitBreakerRegistry()


def with_retry(
    retry_config: Optional[RetryConfig] = None,
    circuit_breaker_name: Optional[str] = None,
):
    """
    Decorator to add retry logic and circuit breaker to a function.

    Usage:
        @with_retry(circuit_breaker_name="recommendation-service")
        def call_recommendation_api():
            response = requests.get("http://service/api")
            return response.json()

    Args:
        retry_config: Retry configuration
        circuit_breaker_name: Name of circuit breaker to use
    """
    config = retry_config or RetryConfig()

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get circuit breaker if specified
            breaker = None
            if circuit_breaker_name:
                breaker = circuit_breaker_registry.get_breaker(circuit_breaker_name)

            # Wrapper function for circuit breaker
            def execute():
                retry_count = 0
                last_exception = None

                while retry_count <= config.max_retries:
                    try:
                        if retry_count > 0:
                            logger.info(
                                f"Retry attempt {retry_count}/{config.max_retries} "
                                f"for {func.__name__}"
                            )

                        # Execute the function
                        result = func(*args, **kwargs)
                        return result

                    except requests.exceptions.RequestException as e:
                        last_exception = e

                        # Check if we should retry
                        should_retry = False

                        if isinstance(e, requests.exceptions.Timeout):
                            should_retry = True
                            logger.warning(
                                f"Timeout in {func.__name__} "
                                f"(attempt {retry_count + 1}/{config.max_retries + 1})"
                            )
                        elif isinstance(e, requests.exceptions.ConnectionError):
                            should_retry = True
                            logger.warning(
                                f"Connection error in {func.__name__} "
                                f"(attempt {retry_count + 1}/{config.max_retries + 1})"
                            )
                        elif hasattr(e, 'response') and e.response is not None:
                            if e.response.status_code in config.retry_on_status:
                                should_retry = True
                                logger.warning(
                                    f"Retryable status {e.response.status_code} in {func.__name__} "
                                    f"(attempt {retry_count + 1}/{config.max_retries + 1})"
                                )

                        if not should_retry or retry_count >= config.max_retries:
                            raise

                    except Exception as e:
                        # Don't retry on unexpected errors
                        logger.error(f"Unexpected error in {func.__name__}: {e}")
                        raise

                    # Calculate retry delay with exponential backoff
                    delay = min(
                        config.base_delay * (config.exponential_base ** retry_count),
                        config.max_delay
                    )

                    # Add jitter to prevent thundering herd
                    if config.jitter:
                        delay = delay * (0.5 + random.random() * 0.5)

                    logger.debug(f"Waiting {delay:.2f}s before retry")
                    time.sleep(delay)

                    retry_count += 1

                # All retries exhausted
                logger.error(f"All retries exhausted for {func.__name__}")
                raise last_exception

            # Execute with or without circuit breaker
            if breaker:
                return breaker.call(execute)
            else:
                return execute()

        return wrapper

    return decorator


class ResilientAPIClient:
    """
    Resilient HTTP client with circuit breaker and retry logic.

    Usage:
        client = ResilientAPIClient("recommendation-service")
        response = client.get("http://service/api/recommendations")
    """

    def __init__(
        self,
        service_name: str,
        circuit_config: Optional[CircuitBreakerConfig] = None,
        retry_config: Optional[RetryConfig] = None,
        timeout_config: Optional[TimeoutConfig] = None,
    ):
        """
        Initialize resilient API client.

        Args:
            service_name: Name of the service (for circuit breaker)
            circuit_config: Circuit breaker configuration
            retry_config: Retry configuration
            timeout_config: Timeout configuration
        """
        self.service_name = service_name
        self.circuit_breaker = circuit_breaker_registry.get_breaker(
            service_name, circuit_config
        )
        self.retry_config = retry_config or RetryConfig()
        self.timeout_config = timeout_config or TimeoutConfig()

    def _execute_request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> requests.Response:
        """
        Execute HTTP request with retry logic.

        Args:
            method: HTTP method
            url: Request URL
            **kwargs: Additional request arguments

        Returns:
            Response object

        Raises:
            Exception: If all retries fail
        """
        retry_count = 0
        last_exception = None

        # Set timeout if not provided
        if 'timeout' not in kwargs:
            kwargs['timeout'] = (
                self.timeout_config.connect_timeout,
                self.timeout_config.read_timeout
            )

        while retry_count <= self.retry_config.max_retries:
            try:
                if retry_count > 0:
                    logger.info(
                        f"Retry attempt {retry_count}/{self.retry_config.max_retries} "
                        f"for {self.service_name}"
                    )

                response = requests.request(method, url, **kwargs)

                # Check if status code should trigger retry
                if response.status_code in self.retry_config.retry_on_status:
                    raise requests.exceptions.RequestException(
                        f"Retryable status code: {response.status_code}"
                    )

                return response

            except requests.exceptions.RequestException as e:
                last_exception = e
                logger.warning(
                    f"Request error to {self.service_name} "
                    f"(attempt {retry_count + 1}/{self.retry_config.max_retries + 1}): {e}"
                )

                if retry_count >= self.retry_config.max_retries:
                    raise

            except Exception as e:
                logger.error(
                    f"Unexpected error calling {self.service_name}: {e}",
                    exc_info=True
                )
                raise

            # Calculate retry delay with exponential backoff
            delay = min(
                self.retry_config.base_delay * (
                    self.retry_config.exponential_base ** retry_count
                ),
                self.retry_config.max_delay
            )

            # Add jitter
            if self.retry_config.jitter:
                delay = delay * (0.5 + random.random() * 0.5)

            time.sleep(delay)
            retry_count += 1

        raise last_exception or Exception("Request failed after all retries")

    def get(self, url: str, **kwargs) -> requests.Response:
        """Execute GET request with circuit breaker"""
        return self.circuit_breaker.call(self._execute_request, "GET", url, **kwargs)

    def post(self, url: str, **kwargs) -> requests.Response:
        """Execute POST request with circuit breaker"""
        return self.circuit_breaker.call(self._execute_request, "POST", url, **kwargs)

    def put(self, url: str, **kwargs) -> requests.Response:
        """Execute PUT request with circuit breaker"""
        return self.circuit_breaker.call(self._execute_request, "PUT", url, **kwargs)

    def delete(self, url: str, **kwargs) -> requests.Response:
        """Execute DELETE request with circuit breaker"""
        return self.circuit_breaker.call(self._execute_request, "DELETE", url, **kwargs)


# Pre-configured clients for each AI service
def get_ai_service_client(service_name: str) -> ResilientAPIClient:
    """
    Get a resilient client for an AI service.

    Args:
        service_name: Name of the AI service

    Returns:
        ResilientAPIClient configured for the service
    """
    return ResilientAPIClient(
        service_name=service_name,
        circuit_config=CircuitBreakerConfig(
            failure_threshold=5,
            success_threshold=2,
            timeout=60,
            window_size=100,
        ),
        retry_config=RetryConfig(
            max_retries=3,
            base_delay=0.1,
            max_delay=5.0,
        ),
        timeout_config=TimeoutConfig(
            connect_timeout=5.0,
            read_timeout=30.0,
        ),
    )
