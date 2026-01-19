import logging
import uuid
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from threading import Lock

from django.db import transaction
from django.core.cache import cache

logger = logging.getLogger(__name__)


class SagaStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPENSATING = "compensating"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    FAILED = "failed"


@dataclass
class SagaStep:
    name: str
    action: Callable
    compensate: Optional[Callable] = None
    timeout: float = 30.0
    max_retries: int = 3
    idempotent: bool = True


@dataclass
class SagaStepResult:
    step_name: str
    status: StepStatus
    result: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    retry_count: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SagaContext:
    saga_id: str
    data: Dict[str, Any] = field(default_factory=dict)
    step_results: List[SagaStepResult] = field(default_factory=list)

    def add_result(self, step_name: str, result: Any):
        self.data[f"{step_name}_result"] = result

    def get_result(self, step_name: str) -> Any:
        return self.data.get(f"{step_name}_result")


class SagaOrchestrator:

    def __init__(self, saga_id: Optional[str] = None):
        self.saga_id = saga_id or str(uuid.uuid4())
        self.steps: List[SagaStep] = []
        self.status = SagaStatus.PENDING
        self.context = SagaContext(saga_id=self.saga_id)
        self._lock = Lock()
        self.completed_steps: List[str] = []
        self.failed_step: Optional[str] = None
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

    def add_step(
        self,
        name: str,
        action: Callable,
        compensate: Optional[Callable] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        idempotent: bool = True,
    ):
        step = SagaStep(
            name=name,
            action=action,
            compensate=compensate,
            timeout=timeout,
            max_retries=max_retries,
            idempotent=idempotent,
        )
        self.steps.append(step)

    def execute(self, initial_data: Optional[Dict] = None) -> Dict[str, Any]:
        if initial_data:
            self.context.data.update(initial_data)

        with self._lock:
            self.status = SagaStatus.RUNNING
            self.start_time = datetime.utcnow()

        logger.info(
            f"🚀 Starting saga {self.saga_id} with {len(self.steps)} steps",
            extra={'saga_id': self.saga_id}
        )

        try:
            for step in self.steps:
                result = self._execute_step(step)

                if result.status == StepStatus.COMPLETED:
                    self.completed_steps.append(step.name)
                    logger.info(
                        f"✅ Step '{step.name}' completed successfully",
                        extra={'saga_id': self.saga_id, 'step': step.name}
                    )
                else:
                    self.failed_step = step.name
                    logger.error(
                        f"❌ Step '{step.name}' failed: {result.error}",
                        extra={'saga_id': self.saga_id, 'step': step.name}
                    )
                    self._compensate()
                    raise Exception(f"Saga failed at step '{step.name}': {result.error}")

            with self._lock:
                self.status = SagaStatus.COMPLETED
                self.end_time = datetime.utcnow()

            duration = (self.end_time - self.start_time).total_seconds()
            logger.info(
                f"🎉 Saga {self.saga_id} completed successfully in {duration:.2f}s",
                extra={'saga_id': self.saga_id, 'duration': duration}
            )

            return {
                'status': 'completed',
                'saga_id': self.saga_id,
                'duration_seconds': duration,
                'data': self.context.data,
            }

        except Exception as e:
            with self._lock:
                self.status = SagaStatus.FAILED
                self.end_time = datetime.utcnow()

            duration = (self.end_time - self.start_time).total_seconds() if self.end_time and self.start_time else 0

            logger.error(
                f"💥 Saga {self.saga_id} failed: {e}",
                extra={'saga_id': self.saga_id},
                exc_info=True
            )

            return {
                'status': 'failed',
                'saga_id': self.saga_id,
                'error': str(e),
                'failed_step': self.failed_step,
                'duration_seconds': duration,
            }

    def _execute_step(self, step: SagaStep) -> SagaStepResult:
        import time

        retry_count = 0
        last_error = None
        start_time = time.time()

        while retry_count <= step.max_retries:
            try:
                logger.debug(
                    f"Executing step '{step.name}' (attempt {retry_count + 1}/{step.max_retries + 1})",
                    extra={'saga_id': self.saga_id, 'step': step.name}
                )

                result = step.action(self.context)

                self.context.add_result(step.name, result)

                duration_ms = (time.time() - start_time) * 1000

                step_result = SagaStepResult(
                    step_name=step.name,
                    status=StepStatus.COMPLETED,
                    result=result,
                    duration_ms=duration_ms,
                    retry_count=retry_count,
                )

                self.context.step_results.append(step_result)
                return step_result

            except Exception as e:
                last_error = e
                retry_count += 1

                logger.warning(
                    f"Step '{step.name}' failed (attempt {retry_count}/{step.max_retries + 1}): {e}",
                    extra={'saga_id': self.saga_id, 'step': step.name}
                )

                if retry_count > step.max_retries:
                    break

                wait_time = min(2 ** retry_count, 30)  # Max 30 seconds
                time.sleep(wait_time)

        duration_ms = (time.time() - start_time) * 1000

        step_result = SagaStepResult(
            step_name=step.name,
            status=StepStatus.FAILED,
            error=str(last_error),
            duration_ms=duration_ms,
            retry_count=retry_count,
        )

        self.context.step_results.append(step_result)
        return step_result

    def _compensate(self):
        with self._lock:
            self.status = SagaStatus.COMPENSATING

        logger.warning(
            f"🔄 Starting compensation for saga {self.saga_id}",
            extra={'saga_id': self.saga_id, 'completed_steps': len(self.completed_steps)}
        )

        for step_name in reversed(self.completed_steps):
            step = next((s for s in self.steps if s.name == step_name), None)

            if not step or not step.compensate:
                logger.warning(
                    f"No compensation defined for step '{step_name}'",
                    extra={'saga_id': self.saga_id, 'step': step_name}
                )
                continue

            try:
                logger.info(
                    f"Compensating step '{step_name}'",
                    extra={'saga_id': self.saga_id, 'step': step_name}
                )

                step.compensate(self.context)

                logger.info(
                    f"✅ Successfully compensated step '{step_name}'",
                    extra={'saga_id': self.saga_id, 'step': step_name}
                )

            except Exception as e:
                logger.error(
                    f"❌ Compensation failed for step '{step_name}': {e}",
                    extra={'saga_id': self.saga_id, 'step': step_name},
                    exc_info=True
                )

    def get_status(self) -> Dict[str, Any]:
        """Current saga status."""
        return {
            'saga_id': self.saga_id,
            'status': self.status.value,
            'total_steps': len(self.steps),
            'completed_steps': len(self.completed_steps),
            'failed_step': self.failed_step,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
        }


class SagaRegistry:
    """Track active sagas."""

    def __init__(self):
        self._sagas: Dict[str, SagaOrchestrator] = {}
        self._lock = Lock()

    def register(self, saga: SagaOrchestrator):
        """Register a saga."""
        with self._lock:
            self._sagas[saga.saga_id] = saga

    def get_saga(self, saga_id: str) -> Optional[SagaOrchestrator]:
        """Get saga by ID."""
        return self._sagas.get(saga_id)

    def get_all_sagas(self) -> Dict[str, Dict[str, Any]]:
        """Get status for all sagas."""
        return {
            saga_id: saga.get_status()
            for saga_id, saga in self._sagas.items()
        }

    def remove(self, saga_id: str):
        """Remove a saga."""
        with self._lock:
            if saga_id in self._sagas:
                del self._sagas[saga_id]


saga_registry = SagaRegistry()
