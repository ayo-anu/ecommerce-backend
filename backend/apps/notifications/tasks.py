from celery import shared_task
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from .models import EmailLog, EmailTemplate, Notification
from django.contrib.auth import get_user_model

User = get_user_model()


@shared_task(bind=True, max_retries=3)
def send_email_task(self, recipient_email, subject, html_content, text_content='', template_type=''):
    """Generic email sending task"""
    email_log = EmailLog.objects.create(
        recipient_email=recipient_email,
        subject=subject,
        template_type=template_type,
        status='pending'
    )
    
    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content or html_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient_email]
        )
        
        if html_content:
            msg.attach_alternative(html_content, "text/html")
        
        msg.send()
        
        email_log.status = 'sent'
        email_log.sent_at = timezone.now()
        email_log.save()
        
        return f"Email sent to {recipient_email}"
    
    except Exception as exc:
        email_log.status = 'failed'
        email_log.error_message = str(exc)
        email_log.save()
        
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task
def send_order_confirmation_email(order_id):
    """Send order confirmation email"""
    from apps.orders.models import Order
    
    order = Order.objects.select_related('user').prefetch_related('items__product').get(id=order_id)
    
    context = {
        'order': order,
        'user': order.user,
        'items': order.items.all(),
        'site_name': 'E-Commerce Store'
    }
    
    html_content = render_to_string('emails/order_confirmation.html', context)
    text_content = render_to_string('emails/order_confirmation.txt', context)
    
    send_email_task.delay(
        recipient_email=order.shipping_email,
        subject=f'Order Confirmation - #{order.order_number}',
        html_content=html_content,
        text_content=text_content,
        template_type='order_confirmation'
    )
    
    # Create in-app notification
    Notification.objects.create(
        user=order.user,
        notification_type='order',
        title='Order Confirmed',
        message=f'Your order #{order.order_number} has been confirmed.',
        link=f'/orders/{order.id}'
    )


@shared_task
def send_order_shipped_email(order_id):
    """Send order shipped email"""
    from apps.orders.models import Order
    
    order = Order.objects.select_related('user').get(id=order_id)
    
    context = {
        'order': order,
        'user': order.user,
        'tracking_number': getattr(order, 'tracking_number', 'N/A')
    }
    
    html_content = render_to_string('emails/order_shipped.html', context)
    
    send_email_task.delay(
        recipient_email=order.shipping_email,
        subject=f'Order Shipped - #{order.order_number}',
        html_content=html_content,
        template_type='order_shipped'
    )
    
    Notification.objects.create(
        user=order.user,
        notification_type='order',
        title='Order Shipped',
        message=f'Your order #{order.order_number} has been shipped.',
        link=f'/orders/{order.id}'
    )


@shared_task
def send_order_cancellation_email(order_id):
    """Send order cancellation email"""
    from apps.orders.models import Order
    
    order = Order.objects.select_related('user').get(id=order_id)
    
    context = {'order': order, 'user': order.user}
    html_content = render_to_string('emails/order_cancelled.html', context)
    
    send_email_task.delay(
        recipient_email=order.shipping_email,
        subject=f'Order Cancelled - #{order.order_number}',
        html_content=html_content,
        template_type='order_cancelled'
    )
    
    Notification.objects.create(
        user=order.user,
        notification_type='order',
        title='Order Cancelled',
        message=f'Your order #{order.order_number} has been cancelled.',
        link=f'/orders/{order.id}'
    )


@shared_task
def send_verification_email(user_id):
    """Send email verification"""
    from django.utils.crypto import get_random_string
    
    user = User.objects.get(id=user_id)
    token = get_random_string(64)
    
    user.email_verification_token = token
    user.save()
    
    verification_link = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    
    context = {
        'user': user,
        'verification_link': verification_link
    }
    
    html_content = render_to_string('emails/email_verification.html', context)
    
    send_email_task.delay(
        recipient_email=user.email,
        subject='Verify Your Email Address',
        html_content=html_content,
        template_type='email_verification'
    )


@shared_task
def send_password_reset_email(user_id, token):
    """Send password reset email"""
    user = User.objects.get(id=user_id)
    reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    
    context = {
        'user': user,
        'reset_link': reset_link
    }
    
    html_content = render_to_string('emails/password_reset.html', context)
    
    send_email_task.delay(
        recipient_email=user.email,
        subject='Password Reset Request',
        html_content=html_content,
        template_type='password_reset'
    )


@shared_task
def send_welcome_email(user_id):
    """Send welcome email to new users"""
    user = User.objects.get(id=user_id)
    
    context = {'user': user}
    html_content = render_to_string('emails/welcome.html', context)
    
    send_email_task.delay(
        recipient_email=user.email,
        subject='Welcome to Our Store!',
        html_content=html_content,
        template_type='welcome'
    )


@shared_task
def send_low_stock_alert(product_id):
    """Alert admin about low stock"""
    from apps.products.models import Product
    
    product = Product.objects.get(id=product_id)
    
    if product.is_low_stock:
        html_content = f"""
        <h2>Low Stock Alert</h2>
        <p>Product: {product.name}</p>
        <p>SKU: {product.sku}</p>
        <p>Current Stock: {product.stock_quantity}</p>
        <p>Threshold: {product.low_stock_threshold}</p>
        """
        
        send_email_task.delay(
            recipient_email=settings.ADMIN_EMAIL,
            subject=f'Low Stock Alert: {product.name}',
            html_content=html_content,
            template_type='system'
        )


@shared_task
def cleanup_old_notifications():
    """Delete read notifications older than 30 days"""
    from datetime import timedelta
    from django.utils import timezone
    
    cutoff_date = timezone.now() - timedelta(days=30)
    deleted_count = Notification.objects.filter(
        is_read=True,
        read_at__lt=cutoff_date
    ).delete()[0]
    
    return f"Deleted {deleted_count} old notifications"