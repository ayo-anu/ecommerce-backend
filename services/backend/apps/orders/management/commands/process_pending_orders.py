from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.orders.models import Order


class Command(BaseCommand):
    help = 'Process pending orders and cancel expired ones'
    
    def handle(self, *args, **kwargs):
        cutoff = timezone.now() - timedelta(hours=24)
        
        expired_orders = Order.objects.filter(
            status='pending',
            payment_status='pending',
            created_at__lt=cutoff
        )
        
        count = 0
        for order in expired_orders:
            for item in order.items.all():
                if item.variant:
                    item.variant.stock_quantity += item.quantity
                    item.variant.save()
                else:
                    item.product.stock_quantity += item.quantity
                    item.product.save()
            
            order.status = 'cancelled'
            order.save()
            count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'Cancelled {count} expired orders')
        )
