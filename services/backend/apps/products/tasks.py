from celery import shared_task
from django.db import models

from apps.notifications.tasks import send_low_stock_alert
from .models import Product


@shared_task
def check_low_stock():
    low_stock_products = Product.objects.filter(
        track_inventory=True,
        stock_quantity__lte=models.F('low_stock_threshold'),
        is_active=True
    )

    for product in low_stock_products:
        send_low_stock_alert.delay(str(product.id))

    return f"Checked {low_stock_products.count()} low stock products"
