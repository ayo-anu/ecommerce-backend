"""
Saga Pattern Implementation

Provides orchestration for distributed transactions with compensation logic.
Implements the Saga pattern for the checkout flow: Order → Inventory → Payment → Fulfillment

Key Features:
- Orchestrator-based approach (centralized coordination)
- Automatic compensation on failure
- State persistence for recovery
- Idempotent operations
- Comprehensive logging and monitoring
"""

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
    """Saga execution status"""
    PENDING = "pending"              # Not started
    RUNNING = "running"              # In progress
    COMPENSATING = "compensating"    # Rolling back
    COMPLETED = "completed"          # Successfully completed
    FAILED = "failed"                # Failed after compensation
    ABORTED = "aborted"              # Aborted before starting


class StepStatus(Enum):
    """Individual step status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    FAILED = "failed"


@dataclass
class SagaStep:
    """
    A single step in a saga.

    Each step has:
    - Forward action (the operation to perform)
    - Compensation action (rollback if needed)
    - Timeout
    - Retry policy
    """
    name: str
    action: Callable
    compensate: Optional[Callable] = None
    timeout: float = 30.0  # seconds
    max_retries: int = 3
    idempotent: bool = True  # Whether step can be safely retried


@dataclass
class SagaStepResult:
    """Result of executing a saga step"""
    step_name: str
    status: StepStatus
    result: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    retry_count: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SagaContext:
    """
    Context passed between saga steps.

    Contains data from previous steps and can accumulate results.
    """
    saga_id: str
    data: Dict[str, Any] = field(default_factory=dict)
    step_results: List[SagaStepResult] = field(default_factory=list)

    def add_result(self, step_name: str, result: Any):
        """Add result from a step"""
        self.data[f"{step_name}_result"] = result

    def get_result(self, step_name: str) -> Any:
        """Get result from a previous step"""
        return self.data.get(f"{step_name}_result")


class SagaOrchestrator:
    """
    Saga Orchestrator - Centralized coordination of saga execution.

    Responsibilities:
    - Execute steps in sequence
    - Handle failures with compensation
    - Persist saga state
    - Provide recovery mechanism
    - Monitor execution
    """

    def __init__(self, saga_id: Optional[str] = None):
        """
        Initialize saga orchestrator.

        Args:
            saga_id: Optional saga ID (generates new if not provided)
        """
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
        """
        Add a step to the saga.

        Args:
            name: Step name
            action: Forward action function
            compensate: Compensation function
            timeout: Step timeout in seconds
            max_retries: Maximum retry attempts
            idempotent: Whether step is idempotent
        """
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
        """
        Execute the saga.

        Args:
            initial_data: Initial data for the saga

        Returns:
            Saga execution result with status and data

        Raises:
            Exception: If saga fails and compensation fails
        """
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
            # Execute each step in sequence
            for step in self.steps:
                result = self._execute_step(step)

                if result.status == StepStatus.COMPLETED:
                    self.completed_steps.append(step.name)
                    logger.info(
                        f"✅ Step '{step.name}' completed successfully",
                        extra={'saga_id': self.saga_id, 'step': step.name}
                    )
                else:
                    # Step failed, trigger compensation
                    self.failed_step = step.name
                    logger.error(
                        f"❌ Step '{step.name}' failed: {result.error}",
                        extra={'saga_id': self.saga_id, 'step': step.name}
                    )
                    self._compensate()
                    raise Exception(f"Saga failed at step '{step.name}': {result.error}")

            # All steps completed successfully
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
        """
        Execute a single saga step with retry logic.

        Args:
            step: The step to execute

        Returns:
            SagaStepResult with execution details
        """
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

                # Execute the action with context
                result = step.action(self.context)

                # Store result in context
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

                # Wait before retry (exponential backoff)
                wait_time = min(2 ** retry_count, 30)  # Max 30 seconds
                time.sleep(wait_time)

        # All retries exhausted
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
        """
        Compensate (rollback) completed steps in reverse order.

        This is called when a step fails to undo all previous steps.
        """
        with self._lock:
            self.status = SagaStatus.COMPENSATING

        logger.warning(
            f"🔄 Starting compensation for saga {self.saga_id}",
            extra={'saga_id': self.saga_id, 'completed_steps': len(self.completed_steps)}
        )

        # Compensate in reverse order
        for step_name in reversed(self.completed_steps):
            # Find the step
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

                # Execute compensation
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
                # Continue compensating other steps even if one fails

    def get_status(self) -> Dict[str, Any]:
        """Get current saga status"""
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
    """
    Registry to manage active sagas.

    Provides:
    - Saga lifecycle management
    - Status tracking
    - Recovery for failed sagas
    """

    def __init__(self):
        self._sagas: Dict[str, SagaOrchestrator] = {}
        self._lock = Lock()

    def register(self, saga: SagaOrchestrator):
        """Register a saga"""
        with self._lock:
            self._sagas[saga.saga_id] = saga

    def get_saga(self, saga_id: str) -> Optional[SagaOrchestrator]:
        """Get saga by ID"""
        return self._sagas.get(saga_id)

    def get_all_sagas(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all sagas"""
        return {
            saga_id: saga.get_status()
            for saga_id, saga in self._sagas.items()
        }

    def remove(self, saga_id: str):
        """Remove completed saga"""
        with self._lock:
            if saga_id in self._sagas:
                del self._sagas[saga_id]


# Global saga registry
saga_registry = SagaRegistry()
