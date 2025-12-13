from celery import shared_task
from .models import Product
from apps.notifications.tasks import send_low_stock_alert


@shared_task
def check_low_stock():
    """Check for low stock products and send alerts"""
    low_stock_products = Product.objects.filter(
        track_inventory=True,
        stock_quantity__lte=models.F('low_stock_threshold'),
        is_active=True
    )
    
    for product in low_stock_products:
        send_low_stock_alert.delay(str(product.id))
    
    return f"Checked {low_stock_products.count()} low stock products"


@shared_task
def update_product_rankings():
    """Update product popularity rankings"""
    from apps.analytics.models import ProductAnalytics
    from django.utils import timezone
    from datetime import timedelta
    
    # Calculate rankings based on last 30 days
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    # This would update product rankings in cache or database
    # Implementation depends on your ranking algorithm
    pass
