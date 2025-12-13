from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import Order


@shared_task(bind=True, max_retries=3)
def send_order_confirmation_email(self, order_id):
    """Send order confirmation email"""
    try:
        order = Order.objects.select_related('user').prefetch_related('items__product').get(id=order_id)
        
        context = {
            'order': order,
            'user': order.user,
            'items': order.items.all()
        }
        
        html_message = render_to_string('emails/order_confirmation.html', context)
        
        send_mail(
            subject=f'Order Confirmation - {order.order_number}',
            message='',
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.shipping_email],
            fail_silently=False
        )
        
        return f"Email sent for order {order.order_number}"
    
    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task
def send_order_cancellation_email(order_id):
    """Send order cancellation email"""
    order = Order.objects.get(id=order_id)
    
    context = {'order': order}
    html_message = render_to_string('emails/order_cancelled.html', context)
    
    send_mail(
        subject=f'Order Cancelled - {order.order_number}',
        message='',
        html_message=html_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[order.shipping_email],
        fail_silently=False
    )


@shared_task
def send_low_stock_alert(product_id):
    """Alert admin when product is low on stock"""
    from apps.products.models import Product
    
    product = Product.objects.get(id=product_id)
    
    if product.is_low_stock:
        send_mail(
            subject=f'Low Stock Alert: {product.name}',
            message=f'Product {product.name} (SKU: {product.sku}) has only {product.stock_quantity} items left.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.ADMIN_EMAIL],
            fail_silently=True
        )


@shared_task
def update_analytics(order_id):
    """Update analytics after order creation"""
    from apps.analytics.models import DailySales
    from django.utils import timezone
    
    order = Order.objects.get(id=order_id)
    today = timezone.now().date()
    
    DailySales.objects.update_or_create(
        date=today,
        defaults={
            'total_orders': models.F('total_orders') + 1,
            'total_revenue': models.F('total_revenue') + order.total
        }
    )


@shared_task
def cleanup_abandoned_carts():
    """Delete carts that haven't been updated in 30 days"""
    from datetime import timedelta
    from django.utils import timezone
    from apps.orders.models import Cart
    
    cutoff_date = timezone.now() - timedelta(days=30)
    deleted_count = Cart.objects.filter(updated_at__lt=cutoff_date).delete()[0]
    
    return f"Deleted {deleted_count} abandoned carts"


@shared_task
def generate_daily_report():
    """Generate daily sales report"""
    from django.utils import timezone
    from apps.analytics.models import DailySales
    
    yesterday = timezone.now().date() - timedelta(days=1)
    
    orders = Order.objects.filter(
        created_at__date=yesterday,
        payment_status='paid'
    )
    
    total_orders = orders.count()
    total_revenue = orders.aggregate(total=models.Sum('total'))['total'] or 0
    
    DailySales.objects.update_or_create(
        date=yesterday,
        defaults={
            'total_orders': total_orders,
            'total_revenue': total_revenue
        }
    )
    
    return f"Report generated for {yesterday}: {total_orders} orders, ${total_revenue}"