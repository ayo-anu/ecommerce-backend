from celery import shared_task
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from datetime import timedelta, datetime
from .models import DailySales, ProductAnalytics, CategoryAnalytics, SalesReport
from apps.orders.models import Order, OrderItem
from apps.products.models import Product


@shared_task
def update_daily_sales():
    """Update daily sales statistics (run daily)"""
    yesterday = timezone.now().date() - timedelta(days=1)
    
    orders = Order.objects.filter(
        created_at__date=yesterday,
        payment_status='paid'
    )
    
    if not orders.exists():
        return "No orders for yesterday"
    
    stats = orders.aggregate(
        total_revenue=Sum('total'),
        total_orders=Count('id'),
        average_order_value=Avg('total')
    )
    
    # Order status breakdown
    status_breakdown = orders.values('status').annotate(count=Count('id'))
    status_counts = {item['status']: item['count'] for item in status_breakdown}
    
    # Items sold
    items_sold = OrderItem.objects.filter(
        order__in=orders
    ).aggregate(total=Sum('quantity'))['total'] or 0
    
    # Customers
    unique_customers = orders.values('user').distinct().count()
    
    DailySales.objects.update_or_create(
        date=yesterday,
        defaults={
            'total_orders': stats['total_orders'],
            'total_revenue': stats['total_revenue'] or 0,
            'total_customers': unique_customers,
            'average_order_value': stats['average_order_value'] or 0,
            'total_items_sold': items_sold,
            'pending_orders': status_counts.get('pending', 0),
            'processing_orders': status_counts.get('processing', 0),
            'shipped_orders': status_counts.get('shipped', 0),
            'delivered_orders': status_counts.get('delivered', 0),
            'cancelled_orders': status_counts.get('cancelled', 0),
        }
    )
    
    return f"Updated daily sales for {yesterday}"


@shared_task
def update_product_analytics():
    """Update product analytics (run daily)"""
    yesterday = timezone.now().date() - timedelta(days=1)
    
    # Get all products with orders yesterday
    order_items = OrderItem.objects.filter(
        order__created_at__date=yesterday,
        order__payment_status='paid'
    ).select_related('product')
    
    product_stats = order_items.values('product').annotate(
        purchases=Count('id'),
        revenue=Sum(F('quantity') * F('unit_price')),
        units_sold=Sum('quantity')
    )
    
    for stat in product_stats:
        product_id = stat['product']
        
        # Get product views from UserActivity
        from .models import UserActivity
        views = UserActivity.objects.filter(
            product_id=product_id,
            action='view_product',
            timestamp__date=yesterday
        ).count()
        
        unique_views = UserActivity.objects.filter(
            product_id=product_id,
            action='view_product',
            timestamp__date=yesterday
        ).values('user').distinct().count()
        
        add_to_cart = UserActivity.objects.filter(
            product_id=product_id,
            action='add_to_cart',
            timestamp__date=yesterday
        ).count()
        
        conversion_rate = (stat['purchases'] / views * 100) if views > 0 else 0
        
        ProductAnalytics.objects.update_or_create(
            product_id=product_id,
            date=yesterday,
            defaults={
                'views': views,
                'unique_views': unique_views,
                'add_to_cart_count': add_to_cart,
                'purchases': stat['purchases'],
                'revenue': stat['revenue'],
                'units_sold': stat['units_sold'],
                'conversion_rate': conversion_rate,
            }
        )
    
    return f"Updated product analytics for {yesterday}"


@shared_task
def generate_sales_report(report_type, start_date_str, end_date_str, user_id):
    """Generate comprehensive sales report"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    user = User.objects.get(id=user_id)
    
    # Aggregate data
    orders = Order.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
        payment_status='paid'
    )
    
    stats = orders.aggregate(
        total_revenue=Sum('total'),
        total_orders=Count('id'),
        average_order_value=Avg('total')
    )
    
    unique_customers = orders.values('user').distinct().count()
    
    # Top products
    top_products = OrderItem.objects.filter(
        order__in=orders
    ).values('product__name').annotate(
        revenue=Sum(F('quantity') * F('unit_price'))
    ).order_by('-revenue')[:10]
    
    # Create report
    report = SalesReport.objects.create(
        report_type=report_type,
        start_date=start_date,
        end_date=end_date,
        total_orders=stats['total_orders'] or 0,
        total_revenue=stats['total_revenue'] or 0,
        total_customers=unique_customers,
        average_order_value=stats['average_order_value'] or 0,
        top_products=[item['product__name'] for item in top_products],
        generated_by=user
    )
    
    return f"Report generated: {report.id}"
