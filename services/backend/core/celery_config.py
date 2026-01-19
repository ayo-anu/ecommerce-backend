"""
Celery Configuration with Production-Ready Settings.

Configures Celery with:
- Concurrency and worker settings
- Task timeouts and retries
- Queue routing
- Result backend configuration
- Security settings
"""

import os
from datetime import timedelta
from kombu import Exchange, Queue
from celery.schedules import crontab

# ==============================================================================
# Broker and Result Backend Configuration
# ==============================================================================

# Redis broker URL (with TLS support)
broker_url = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')

# Result backend
result_backend = os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')

# Broker connection settings
broker_connection_retry_on_startup = True
broker_connection_retry = True
broker_connection_max_retries = 10

# ==============================================================================
# Worker Configuration
# ==============================================================================

# Worker concurrency (number of worker processes/threads)
# Default: number of CPU cores
# Can be overridden with CELERY_WORKER_CONCURRENCY env var
worker_concurrency = int(os.getenv('CELERY_WORKER_CONCURRENCY', '4'))

# Worker prefetch multiplier
# How many messages a worker will reserve for itself
# Lower value = better load balancing, higher value = better throughput
# Recommended: 1 for long-running tasks, 4-10 for short tasks
worker_prefetch_multiplier = int(os.getenv('CELERY_WORKER_PREFETCH_MULTIPLIER', '4'))

# Worker pool type
# Options: prefork (multi-process), solo (single process), threads, gevent, eventlet
worker_pool = os.getenv('CELERY_WORKER_POOL', 'prefork')

# Maximum number of tasks a worker can execute before being replaced
# Helps prevent memory leaks
worker_max_tasks_per_child = int(os.getenv('CELERY_WORKER_MAX_TASKS_PER_CHILD', '1000'))

# Maximum memory per child process (in KB)
# Worker will be replaced if it exceeds this limit
worker_max_memory_per_child = int(os.getenv('CELERY_WORKER_MAX_MEMORY_PER_CHILD', str(200 * 1024)))  # 200 MB

# Enable worker autoscaling
# Format: max_concurrency,min_concurrency
# Example: 10,3 means scale between 3 and 10 workers
worker_autoscaler = os.getenv('CELERY_WORKER_AUTOSCALER')  # e.g., "10,3"

# ==============================================================================
# Task Execution Configuration
# ==============================================================================

# Task time limits
# Hard time limit - task will be killed if it exceeds this
task_time_limit = int(os.getenv('CELERY_TASK_TIME_LIMIT', str(30 * 60)))  # 30 minutes

# Soft time limit - task will receive SoftTimeLimitExceeded exception
task_soft_time_limit = int(os.getenv('CELERY_TASK_SOFT_TIME_LIMIT', str(25 * 60)))  # 25 minutes

# Task acknowledgement configuration
# Late ack: task is acknowledged AFTER execution (safer, but slower)
# Early ack: task is acknowledged BEFORE execution (faster, but may lose tasks on crash)
task_acks_late = True  # Enable late acknowledgement for reliability
task_reject_on_worker_lost = True  # Requeue task if worker crashes

# Task result expiration
# How long to keep task results in the result backend
result_expires = int(os.getenv('CELERY_RESULT_EXPIRES', str(24 * 3600)))  # 24 hours

# Task ignore result
# Set to True for tasks that don't need to store results (saves memory)
task_ignore_result = False

# Task result compression
result_compression = 'gzip'
result_extended = True

# ==============================================================================
# Task Retry Configuration
# ==============================================================================

# Default task retry settings
task_autoretry_for = (Exception,)  # Retry on any exception
task_retry_backoff = True  # Use exponential backoff
task_retry_backoff_max = 600  # Maximum backoff delay (10 minutes)
task_retry_jitter = True  # Add random jitter to prevent thundering herd

# Maximum retries for failed tasks
task_max_retries = int(os.getenv('CELERY_TASK_MAX_RETRIES', '3'))

# ==============================================================================
# Queue Configuration
# ==============================================================================

# Define exchanges
default_exchange = Exchange('default', type='direct')
priority_exchange = Exchange('priority', type='direct')

# Define queues with priorities
task_queues = (
    # High priority queue for critical tasks
    Queue(
        'high_priority',
        exchange=priority_exchange,
        routing_key='high_priority',
        queue_arguments={'x-max-priority': 10}
    ),

    # Default queue for normal tasks
    Queue(
        'default',
        exchange=default_exchange,
        routing_key='default',
        queue_arguments={'x-max-priority': 5}
    ),

    # Low priority queue for background tasks
    Queue(
        'low_priority',
        exchange=default_exchange,
        routing_key='low_priority',
        queue_arguments={'x-max-priority': 1}
    ),

    # Email queue
    Queue(
        'email',
        exchange=default_exchange,
        routing_key='email',
        queue_arguments={'x-max-priority': 3}
    ),

    # AI/ML processing queue (may need more resources)
    Queue(
        'ai_processing',
        exchange=default_exchange,
        routing_key='ai_processing',
        queue_arguments={'x-max-priority': 5}
    ),

    # Reports and exports (long-running tasks)
    Queue(
        'reports',
        exchange=default_exchange,
        routing_key='reports',
        queue_arguments={'x-max-priority': 2}
    ),
)

# Default queue
task_default_queue = 'default'
task_default_exchange = 'default'
task_default_routing_key = 'default'

# Task routing
task_routes = {
    # High priority tasks
    'apps.orders.tasks.process_payment': {'queue': 'high_priority', 'priority': 10},
    'apps.orders.tasks.send_order_confirmation': {'queue': 'high_priority', 'priority': 9},

    # Email tasks
    'apps.notifications.tasks.*': {'queue': 'email', 'priority': 5},

    # AI/ML tasks
    'apps.products.tasks.generate_recommendations': {'queue': 'ai_processing', 'priority': 5},
    'apps.products.tasks.analyze_product_images': {'queue': 'ai_processing', 'priority': 4},

    # Reports (long-running)
    'apps.analytics.tasks.generate_sales_report': {'queue': 'reports', 'priority': 2},
    'apps.analytics.tasks.export_data': {'queue': 'reports', 'priority': 1},

    # Background tasks
    'apps.products.tasks.update_search_index': {'queue': 'low_priority', 'priority': 1},
    'apps.products.tasks.cleanup_old_data': {'queue': 'low_priority', 'priority': 1},
}

# ==============================================================================
# Beat Schedule Configuration (Periodic Tasks)
# ==============================================================================

beat_schedule = {
    # Run every hour
    'cleanup-expired-sessions': {
        'task': 'apps.users.tasks.cleanup_expired_sessions',
        'schedule': crontab(minute=0),  # Every hour
        'options': {'queue': 'low_priority'}
    },

    # Run every day at 2 AM
    'daily-sales-report': {
        'task': 'apps.analytics.tasks.generate_daily_sales_report',
        'schedule': crontab(hour=2, minute=0),
        'options': {'queue': 'reports'}
    },

    # Run every 15 minutes
    'update-product-recommendations': {
        'task': 'apps.products.tasks.update_product_recommendations',
        'schedule': timedelta(minutes=15),
        'options': {'queue': 'ai_processing'}
    },

    # Run every 5 minutes
    'process-pending-notifications': {
        'task': 'apps.notifications.tasks.process_pending_notifications',
        'schedule': timedelta(minutes=5),
        'options': {'queue': 'email'}
    },

    # Run every day at 3 AM
    'cleanup-old-logs': {
        'task': 'apps.core.tasks.cleanup_old_logs',
        'schedule': crontab(hour=3, minute=0),
        'options': {'queue': 'low_priority'}
    },

    # Run every Monday at 1 AM
    'weekly-analytics-report': {
        'task': 'apps.analytics.tasks.generate_weekly_report',
        'schedule': crontab(hour=1, minute=0, day_of_week=1),
        'options': {'queue': 'reports'}
    },
}

# Timezone for beat schedule
timezone = 'UTC'
enable_utc = True

# ==============================================================================
# Security Configuration
# ==============================================================================

# Accept only JSON content (more secure than pickle)
task_serializer = 'json'
accept_content = ['json']
result_serializer = 'json'

# Task message security
task_always_eager = False  # Never use eager mode in production

# ==============================================================================
# Monitoring and Logging
# ==============================================================================

# Enable task events for monitoring
worker_send_task_events = True
task_send_sent_event = True

# Track task start
task_track_started = True

# Store task metadata
task_store_eager_result = False

# ==============================================================================
# Performance Tuning
# ==============================================================================

# Disable rate limiting (use external rate limiting if needed)
task_default_rate_limit = None

# Connection pool configuration
broker_pool_limit = int(os.getenv('CELERY_BROKER_POOL_LIMIT', '10'))
broker_heartbeat = 30
broker_heartbeat_checkrate = 2

# Result backend settings
result_backend_transport_options = {
    'master_name': os.getenv('REDIS_SENTINEL_MASTER', 'mymaster'),
}

# Redis backend specific settings
redis_backend_health_check_interval = 30
redis_socket_keepalive = True
redis_socket_timeout = 5.0

# ==============================================================================
# Task Execution Hooks
# ==============================================================================

# Task annotations for fine-grained control
task_annotations = {
    # Example: Override settings for specific tasks
    'apps.orders.tasks.process_payment': {
        'rate_limit': '100/m',  # 100 tasks per minute
        'time_limit': 300,  # 5 minutes
        'soft_time_limit': 240,  # 4 minutes
        'max_retries': 5,
    },
    'apps.analytics.tasks.generate_sales_report': {
        'time_limit': 3600,  # 1 hour
        'soft_time_limit': 3300,  # 55 minutes
        'max_retries': 1,
    },
}

# ==============================================================================
# Development vs Production Settings
# ==============================================================================

if os.getenv('DJANGO_ENV') == 'development':
    # Development settings
    task_always_eager = False  # Still use async in development
    task_eager_propagates = True
    worker_concurrency = 2
    worker_prefetch_multiplier = 1

# ==============================================================================
# Celery App Configuration Function
# ==============================================================================

def configure_celery(app):
    """Configure a Celery app from this module."""
    app.config_from_object(__name__)

    app.autodiscover_tasks()

    return app


# ==============================================================================
# Task Base Classes
# ==============================================================================

class BaseTask:
    """Base task class with common configuration."""

    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 3}
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True


class CriticalTask(BaseTask):
    """Base class for critical tasks that need immediate execution."""

    queue = 'high_priority'
    priority = 10
    max_retries = 5
    time_limit = 600  # 10 minutes
    soft_time_limit = 540  # 9 minutes


class BackgroundTask(BaseTask):
    """Base class for low-priority background tasks."""

    queue = 'low_priority'
    priority = 1
    ignore_result = True
    time_limit = 3600  # 1 hour
    soft_time_limit = 3300  # 55 minutes
