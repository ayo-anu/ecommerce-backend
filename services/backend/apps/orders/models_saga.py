"""
Saga Persistence Models

Tracks saga execution for audit, monitoring, and recovery.
"""

from django.db import models
from django.contrib.postgres.fields import JSONField
import uuid


class SagaExecution(models.Model):
    """
    Tracks saga execution history.

    Provides:
    - Audit trail of all saga executions
    - Recovery mechanism for failed sagas
    - Performance monitoring
    """

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('compensating', 'Compensating'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('aborted', 'Aborted'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    saga_type = models.CharField(max_length=100, db_index=True)  # e.g., 'checkout'
    saga_id = models.CharField(max_length=100, unique=True, db_index=True)

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)

    # Related entities
    order = models.ForeignKey(
        'Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='saga_executions'
    )
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='saga_executions'
    )

    # Execution details
    input_data = models.JSONField(default=dict)  # Initial saga data
    output_data = models.JSONField(default=dict)  # Final saga result
    context_data = models.JSONField(default=dict)  # Saga context
    step_results = models.JSONField(default=list)  # Results of each step

    # Steps tracking
    total_steps = models.IntegerField(default=0)
    completed_steps = models.IntegerField(default=0)
    failed_step = models.CharField(max_length=100, blank=True)

    # Error tracking
    error_message = models.TextField(blank=True)
    error_details = models.JSONField(default=dict, blank=True)

    # Timestamps
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.FloatField(null=True, blank=True)

    # Retry tracking
    retry_count = models.IntegerField(default=0)
    parent_execution = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='retries'
    )

    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['saga_type', '-started_at']),
            models.Index(fields=['status', '-started_at']),
            models.Index(fields=['order', '-started_at']),
            models.Index(fields=['user', '-started_at']),
        ]

    def __str__(self):
        return f"Saga {self.saga_type} - {self.status}"

    def calculate_duration(self):
        """Calculate and update duration"""
        if self.completed_at:
            delta = self.completed_at - self.started_at
            self.duration_seconds = delta.total_seconds()
            return self.duration_seconds
        return None


class SagaStepExecution(models.Model):
    """
    Tracks individual step execution within a saga.

    Provides detailed step-level information for debugging.
    """

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('compensating', 'Compensating'),
        ('compensated', 'Compensated'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    saga_execution = models.ForeignKey(
        SagaExecution,
        on_delete=models.CASCADE,
        related_name='steps'
    )

    # Step details
    step_name = models.CharField(max_length=100)
    step_order = models.IntegerField()  # Order in saga
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Execution details
    input_data = models.JSONField(default=dict)
    output_data = models.JSONField(default=dict)
    error_message = models.TextField(blank=True)

    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_ms = models.FloatField(null=True, blank=True)

    # Retry tracking
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)

    # Compensation
    compensation_executed = models.BooleanField(default=False)
    compensation_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['step_order']
        unique_together = [['saga_execution', 'step_name']]
        indexes = [
            models.Index(fields=['saga_execution', 'step_order']),
            models.Index(fields=['status', '-started_at']),
        ]

    def __str__(self):
        return f"{self.saga_execution.saga_type} - Step {self.step_name}"
