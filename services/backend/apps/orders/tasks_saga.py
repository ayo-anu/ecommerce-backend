"""
Celery Tasks for Saga Execution

Provides async saga execution and post-processing tasks.
"""

import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=0,  # Saga handles retries internally
    time_limit=300,  # 5 minutes max
)
def execute_checkout_saga_async(self, checkout_data: dict) -> dict:
    """
    Execute checkout saga asynchronously.

    Args:
        checkout_data: Checkout data dictionary

    Returns:
        Saga execution result
    """
    from core.checkout_saga import CheckoutSaga
    from apps.orders.models_saga import SagaExecution

    logger.info(f"Starting async checkout saga for user {checkout_data.get('user_id')}")

    # Create saga execution record
    saga_execution = SagaExecution.objects.create(
        saga_type='checkout',
        saga_id=f"checkout_{timezone.now().timestamp()}",
        status='running',
        user_id=checkout_data.get('user_id'),
        input_data=checkout_data,
        total_steps=5,
    )

    try:
        # Execute saga
        result = CheckoutSaga.execute(checkout_data)

        # Update saga execution
        saga_execution.status = result['status']
        saga_execution.output_data = result
        saga_execution.completed_at = timezone.now()
        saga_execution.calculate_duration()

        if result['status'] == 'completed':
            # Extract order ID from result
            order_id = result['data'].get('confirm_order_result', {}).get('order_id')
            if order_id:
                from apps.orders.models import Order
                try:
                    order = Order.objects.get(id=order_id)
                    saga_execution.order = order
                except Order.DoesNotExist:
                    pass

            # Trigger post-checkout tasks
            send_order_confirmation_email.delay(order_id)
            update_analytics.delay(order_id)

        saga_execution.save()

        logger.info(
            f"Checkout saga completed with status: {result['status']}",
            extra={'saga_id': saga_execution.saga_id, 'status': result['status']}
        )

        return result

    except Exception as e:
        # Update saga execution with error
        saga_execution.status = 'failed'
        saga_execution.error_message = str(e)
        saga_execution.completed_at = timezone.now()
        saga_execution.calculate_duration()
        saga_execution.save()

        logger.error(
            f"Checkout saga failed: {e}",
            extra={'saga_id': saga_execution.saga_id},
            exc_info=True
        )

        raise


@shared_task(bind=True, max_retries=3)
def send_order_confirmation_email(self, order_id: str):
    """
    Send order confirmation email.

    Args:
        order_id: Order ID
    """
    from apps.orders.models import Order
    from apps.notifications.tasks import send_email

    try:
        order = Order.objects.get(id=order_id)

        logger.info(f"Sending confirmation email for order {order.order_number}")

        # Send email
        send_email.delay(
            template='order_confirmation',
            to_email=order.shipping_email,
            context={
                'order': {
                    'order_number': order.order_number,
                    'total': float(order.total),
                    'items': [
                        {
                            'name': item.product_name,
                            'quantity': item.quantity,
                            'price': float(item.price),
                        }
                        for item in order.items.all()
                    ],
                },
                'shipping_address': {
                    'name': order.shipping_name,
                    'address_line1': order.shipping_address_line1,
                    'city': order.shipping_city,
                    'state': order.shipping_state,
                    'postal_code': order.shipping_postal_code,
                },
            }
        )

        logger.info(f"Confirmation email sent for order {order.order_number}")

    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found")
    except Exception as e:
        logger.error(f"Failed to send confirmation email: {e}", exc_info=True)
        raise self.retry(exc=e, countdown=60)


@shared_task
def update_analytics(order_id: str):
    """
    Update analytics after successful order.

    Args:
        order_id: Order ID
    """
    from apps.orders.models import Order
    from apps.analytics.models import DailySales, ProductAnalytics

    try:
        order = Order.objects.get(id=order_id)

        logger.info(f"Updating analytics for order {order.order_number}")

        # Update daily sales
        date = order.created_at.date()
        daily_sales, created = DailySales.objects.get_or_create(date=date)
        daily_sales.orders_count += 1
        daily_sales.revenue += order.total
        daily_sales.save()

        # Update product analytics
        for item in order.items.all():
            analytics, created = ProductAnalytics.objects.get_or_create(
                product=item.product
            )
            analytics.purchase_count += item.quantity
            analytics.revenue += item.total
            analytics.save()

        logger.info(f"Analytics updated for order {order.order_number}")

    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found")
    except Exception as e:
        logger.error(f"Failed to update analytics: {e}", exc_info=True)


@shared_task
def cleanup_failed_sagas():
    """
    Cleanup old failed saga executions.

    Runs daily to cleanup sagas older than 30 days.
    """
    from apps.orders.models_saga import SagaExecution
    from datetime import timedelta
    from django.utils import timezone

    cutoff_date = timezone.now() - timedelta(days=30)

    deleted_count = SagaExecution.objects.filter(
        status__in=['failed', 'aborted'],
        started_at__lt=cutoff_date
    ).delete()[0]

    logger.info(f"Cleaned up {deleted_count} old failed saga executions")

    return {'deleted_count': deleted_count}


@shared_task
def retry_failed_saga(saga_execution_id: str):
    """
    Retry a failed saga execution.

    Args:
        saga_execution_id: Saga execution ID to retry
    """
    from apps.orders.models_saga import SagaExecution

    try:
        saga_execution = SagaExecution.objects.get(id=saga_execution_id)

        if saga_execution.status not in ['failed', 'aborted']:
            logger.warning(f"Saga {saga_execution_id} is not in failed/aborted state")
            return

        logger.info(f"Retrying failed saga {saga_execution_id}")

        # Create new saga execution as retry
        result = execute_checkout_saga_async.delay(saga_execution.input_data)

        # Link to parent
        if result:
            # Update retry tracking
            saga_execution.retry_count += 1
            saga_execution.save()

        return {'status': 'retry_initiated', 'task_id': result.id if result else None}

    except SagaExecution.DoesNotExist:
        logger.error(f"Saga execution {saga_execution_id} not found")
    except Exception as e:
        logger.error(f"Failed to retry saga: {e}", exc_info=True)
        raise


@shared_task
def monitor_saga_health():
    """
    Monitor saga execution health.

    Checks for:
    - Long-running sagas
    - High failure rates
    - Stuck sagas
    """
    from apps.orders.models_saga import SagaExecution
    from datetime import timedelta
    from django.utils import timezone
    from django.db.models import Count, Q

    logger.info("Running saga health check")

    # Check for long-running sagas (> 10 minutes)
    long_running_cutoff = timezone.now() - timedelta(minutes=10)
    long_running = SagaExecution.objects.filter(
        status='running',
        started_at__lt=long_running_cutoff
    )

    if long_running.exists():
        logger.warning(f"Found {long_running.count()} long-running sagas")

    # Check failure rate in last hour
    one_hour_ago = timezone.now() - timedelta(hours=1)
    recent_sagas = SagaExecution.objects.filter(started_at__gte=one_hour_ago)

    stats = recent_sagas.aggregate(
        total=Count('id'),
        failed=Count('id', filter=Q(status='failed')),
        completed=Count('id', filter=Q(status='completed')),
    )

    failure_rate = (stats['failed'] / stats['total'] * 100) if stats['total'] > 0 else 0

    logger.info(
        f"Saga health: {stats['completed']}/{stats['total']} completed, "
        f"failure rate: {failure_rate:.2f}%"
    )

    # Alert if failure rate > 10%
    if failure_rate > 10:
        logger.error(f"HIGH FAILURE RATE: {failure_rate:.2f}%")

    return {
        'long_running_count': long_running.count(),
        'recent_stats': stats,
        'failure_rate': failure_rate,
    }
