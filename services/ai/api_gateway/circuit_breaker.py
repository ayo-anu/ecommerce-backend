"""Circuit breaker for async calls."""

import time
import asyncio
from enum import Enum
from typing import Callable, Any
from dataclasses import dataclass, field
from collections import deque
import logging

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker settings."""
    failure_threshold: int = 5
    success_threshold: int = 2
    timeout: int = 60
    window_size: int = 100


class CircuitBreaker:
    """Circuit breaker to prevent cascading failures."""

    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.recent_calls = deque(maxlen=self.config.window_size)

    def _should_attempt_reset(self) -> bool:
        """Check whether to attempt reset."""
        if self.state != CircuitState.OPEN:
            return False

        if self.last_failure_time is None:
            return False

        time_since_failure = time.time() - self.last_failure_time
        return time_since_failure >= self.config.timeout

    def _record_success(self):
        """Record a successful call."""
        self.recent_calls.append(True)

        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1

            if self.success_count >= self.config.success_threshold:
                logger.info(
                    f"Circuit breaker '{self.name}' closing "
                    f"(success_count={self.success_count})"
                )
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0

    def _record_failure(self):
        """Record a failed call."""
        self.recent_calls.append(False)
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.CLOSED:
            recent_failures = sum(1 for call in self.recent_calls if not call)

            if recent_failures >= self.config.failure_threshold:
                logger.warning(
                    f"Circuit breaker '{self.name}' opening "
                    f"(failures={recent_failures}/{self.config.window_size})"
                )
                self.state = CircuitState.OPEN
                self.success_count = 0

        elif self.state == CircuitState.HALF_OPEN:
            logger.warning(
                f"Circuit breaker '{self.name}' failed during recovery, "
                "going back to OPEN"
            )
            self.state = CircuitState.OPEN
            self.success_count = 0

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute a call with circuit breaker protection."""
        if self._should_attempt_reset():
            logger.info(
                f"Circuit breaker '{self.name}' entering HALF_OPEN state "
                "(attempting recovery)"
            )
            self.state = CircuitState.HALF_OPEN
            self.success_count = 0
            self.failure_count = 0

        if self.state == CircuitState.OPEN:
            raise CircuitBreakerError(
                f"Circuit breaker '{self.name}' is OPEN "
                f"(wait {self.config.timeout}s before retry)"
            )

        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result

        except Exception:
            self._record_failure()
            raise

    def get_state(self) -> dict:
        """Get current circuit breaker state."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "recent_failures": sum(1 for call in self.recent_calls if not call),
            "total_calls": len(self.recent_calls),
            "last_failure_time": self.last_failure_time,
        }


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""


class CircuitBreakerRegistry:
    """Registry for circuit breakers."""

    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}

    def get_breaker(
        self,
        name: str,
        config: CircuitBreakerConfig = None,
    ) -> CircuitBreaker:
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name, config)

        return self._breakers[name]

    def get_all_states(self) -> dict:
        """Get states of all circuit breakers."""
        return {name: breaker.get_state() for name, breaker in self._breakers.items()}

    def reset_breaker(self, name: str):
        """Force reset a circuit breaker."""
        if name in self._breakers:
            breaker = self._breakers[name]
            breaker.state = CircuitState.CLOSED
            breaker.failure_count = 0
            breaker.success_count = 0
            breaker.recent_calls.clear()
            logger.info(f"Circuit breaker '{name}' manually reset")


circuit_breaker_registry = CircuitBreakerRegistry()
