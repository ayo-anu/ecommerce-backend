

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

logger = logging.getLogger(__name__)



class CircuitState(Enum):

    CLOSED = "closed"

    OPEN = "open"

    HALF_OPEN = "half_open"



@dataclass

class CircuitBreakerConfig:

    failure_threshold: int = 5

    success_threshold: int = 2

    timeout: int = 60

    window_size: int = 100



@dataclass

class RetryConfig:

    max_retries: int = 3

    base_delay: float = 0.1

    max_delay: float = 10.0

    exponential_base: float = 2.0

    jitter: bool = True

    retry_on_status: tuple = (408, 429, 500, 502, 503, 504)



@dataclass

class TimeoutConfig:

    connect_timeout: float = 5.0

    read_timeout: float = 30.0



class CircuitBreakerError(Exception):



class CircuitBreaker:


    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):

        self.name = name

        self.config = config or CircuitBreakerConfig()

        self.state = CircuitState.CLOSED

        self.failure_count = 0

        self.success_count = 0

        self.last_failure_time = None

        self.recent_calls = deque(maxlen=self.config.window_size)

        self._lock = Lock()


    def _should_attempt_reset(self) -> bool:

        if self.state != CircuitState.OPEN:

            return False


        if self.last_failure_time is None:

            return False


        time_since_failure = time.time() - self.last_failure_time

        return time_since_failure >= self.config.timeout


    def _record_success(self):

        with self._lock:

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

        with self._lock:

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


    def call(self, func: Callable, *args, **kwargs) -> Any:

        if self._should_attempt_reset():

            with self._lock:

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

            result = func(*args, **kwargs)

            self._record_success()

            return result


        except Exception:

            self._record_failure()

            raise


    def get_state(self) -> Dict[str, Any]:

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


    def __init__(self):

        self._breakers: Dict[str, CircuitBreaker] = {}

        self._lock = Lock()


    def get_breaker(

        self,

        name: str,

        config: Optional[CircuitBreakerConfig] = None,

    ) -> CircuitBreaker:

        if name not in self._breakers:

            with self._lock:

                if name not in self._breakers:

                    self._breakers[name] = CircuitBreaker(name, config)


        return self._breakers[name]


    def get_all_states(self) -> Dict[str, Dict[str, Any]]:

        return {name: breaker.get_state() for name, breaker in self._breakers.items()}


    def reset_breaker(self, name: str):

        if name in self._breakers:

            breaker = self._breakers[name]

            with breaker._lock:

                breaker.state = CircuitState.CLOSED

                breaker.failure_count = 0

                breaker.success_count = 0

                breaker.recent_calls.clear()

                logger.info(f"Circuit breaker '{name}' manually reset")



circuit_breaker_registry = CircuitBreakerRegistry()



def with_retry(

    retry_config: Optional[RetryConfig] = None,

    circuit_breaker_name: Optional[str] = None,

):

    config = retry_config or RetryConfig()


    def decorator(func: Callable) -> Callable:

        @wraps(func)

        def wrapper(*args, **kwargs):

            breaker = None

            if circuit_breaker_name:

                breaker = circuit_breaker_registry.get_breaker(circuit_breaker_name)


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


                        result = func(*args, **kwargs)

                        return result


                    except requests.exceptions.RequestException as e:

                        last_exception = e


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

                        logger.error(f"Unexpected error in {func.__name__}: {e}")

                        raise


                    delay = min(

                        config.base_delay * (config.exponential_base ** retry_count),

                        config.max_delay

                    )


                    if config.jitter:

                        delay = delay * (0.5 + random.random() * 0.5)


                    logger.debug(f"Waiting {delay:.2f}s before retry")

                    time.sleep(delay)


                    retry_count += 1


                logger.error(f"All retries exhausted for {func.__name__}")

                raise last_exception


            if breaker:

                return breaker.call(execute)

            else:

                return execute()


        return wrapper


    return decorator



class ResilientAPIClient:


    def __init__(

        self,

        service_name: str,

        circuit_config: Optional[CircuitBreakerConfig] = None,

        retry_config: Optional[RetryConfig] = None,

        timeout_config: Optional[TimeoutConfig] = None,

    ):

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

        retry_count = 0

        last_exception = None


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


            delay = min(

                self.retry_config.base_delay * (

                    self.retry_config.exponential_base ** retry_count

                ),

                self.retry_config.max_delay

            )


            if self.retry_config.jitter:

                delay = delay * (0.5 + random.random() * 0.5)


            time.sleep(delay)

            retry_count += 1


        raise last_exception or Exception("Request failed after all retries")


    def get(self, url: str, **kwargs) -> requests.Response:

        return self.circuit_breaker.call(self._execute_request, "GET", url, **kwargs)


    def post(self, url: str, **kwargs) -> requests.Response:

        return self.circuit_breaker.call(self._execute_request, "POST", url, **kwargs)


    def put(self, url: str, **kwargs) -> requests.Response:

        return self.circuit_breaker.call(self._execute_request, "PUT", url, **kwargs)


    def delete(self, url: str, **kwargs) -> requests.Response:

        return self.circuit_breaker.call(self._execute_request, "DELETE", url, **kwargs)



def get_ai_service_client(service_name: str) -> ResilientAPIClient:

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

