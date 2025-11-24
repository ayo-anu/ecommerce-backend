# apps/analytics/models.py - CORRECTED VERSION

from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class DailySales(models.Model):
    """Daily sales aggregation"""
    date = models.DateField(unique=True, db_index=True)
    total_orders = models.IntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_customers = models.IntegerField(default=0)
    average_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Product metrics
    total_items_sold = models.IntegerField(default=0)
    
    # Payment breakdown
    successful_payments = models.IntegerField(default=0)
    failed_payments = models.IntegerField(default=0)
    
    # Order status breakdown
    pending_orders = models.IntegerField(default=0)
    processing_orders = models.IntegerField(default=0)
    shipped_orders = models.IntegerField(default=0)
    delivered_orders = models.IntegerField(default=0)
    cancelled_orders = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date']
        verbose_name_plural = 'Daily sales'
        indexes = [
            models.Index(fields=['-date']),
        ]
    
    def __str__(self):
        return f"Sales for {self.date}"


class ProductAnalytics(models.Model):
    """Product-level analytics"""
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='analytics')
    date = models.DateField(db_index=True)
    
    # Views and engagement
    views = models.IntegerField(default=0)
    unique_views = models.IntegerField(default=0)
    add_to_cart_count = models.IntegerField(default=0)
    
    # Sales metrics
    purchases = models.IntegerField(default=0)
    revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    units_sold = models.IntegerField(default=0)
    
    # Conversion metrics
    conversion_rate = models.FloatField(default=0.0)  # purchases / views
    cart_abandonment_rate = models.FloatField(default=0.0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['product', 'date']
        ordering = ['-date', '-revenue']
        indexes = [
            models.Index(fields=['date', '-revenue']),
            models.Index(fields=['product', '-date']),
        ]
    
    def __str__(self):
        return f"{self.product.name} - {self.date}"


class CategoryAnalytics(models.Model):
    """Category-level analytics"""
    category = models.ForeignKey('products.Category', on_delete=models.CASCADE, related_name='analytics')
    date = models.DateField(db_index=True)
    
    views = models.IntegerField(default=0)
    total_orders = models.IntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_items_sold = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['category', 'date']
        ordering = ['-date', '-total_revenue']  # FIXED: changed from 'revenue' to 'total_revenue'
        verbose_name_plural = 'Category analytics'
        indexes = [
            models.Index(fields=['date', '-total_revenue']),
        ]
    
    def __str__(self):
        return f"{self.category.name} - {self.date}"


class UserActivity(models.Model):
    """Track user activities for analytics"""
    ACTION_CHOICES = [
        ('view_product', 'View Product'),
        ('add_to_cart', 'Add to Cart'),
        ('remove_from_cart', 'Remove from Cart'),
        ('purchase', 'Purchase'),
        ('search', 'Search'),
        ('view_category', 'View Category'),
        ('wishlist_add', 'Add to Wishlist'),
        ('review_submit', 'Submit Review'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='activities')
    session_id = models.CharField(max_length=100, db_index=True)  # For anonymous users
    
    action = models.CharField(max_length=50, choices=ACTION_CHOICES, db_index=True)
    
    # Related objects
    product = models.ForeignKey('products.Product', on_delete=models.SET_NULL, null=True, blank=True)
    category = models.ForeignKey('products.Category', on_delete=models.SET_NULL, null=True, blank=True)
    order = models.ForeignKey('orders.Order', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    # Request info
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    referrer = models.URLField(blank=True)
    
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['action', '-timestamp']),
            models.Index(fields=['product', '-timestamp']),
            models.Index(fields=['session_id', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.action} - {self.timestamp}"


class CustomerSegment(models.Model):
    """Customer segmentation for marketing"""
    SEGMENT_TYPES = [
        ('high_value', 'High Value'),
        ('frequent_buyer', 'Frequent Buyer'),
        ('at_risk', 'At Risk'),
        ('new_customer', 'New Customer'),
        ('inactive', 'Inactive'),
        ('vip', 'VIP'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='segments')
    segment_type = models.CharField(max_length=50, choices=SEGMENT_TYPES)
    
    # Metrics
    total_orders = models.IntegerField(default=0)
    total_spent = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    average_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    days_since_last_order = models.IntegerField(default=0)
    
    assigned_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'segment_type']
        indexes = [
            models.Index(fields=['segment_type', '-total_spent']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.segment_type}"


class SalesReport(models.Model):
    """Generated sales reports"""
    REPORT_TYPES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
        ('custom', 'Custom'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    start_date = models.DateField()
    end_date = models.DateField()
    
    # Aggregated data
    total_orders = models.IntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_customers = models.IntegerField(default=0)
    average_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Top performers
    top_products = models.JSONField(default=list)
    top_categories = models.JSONField(default=list)
    
    # Growth metrics
    revenue_growth_percentage = models.FloatField(default=0.0)
    order_growth_percentage = models.FloatField(default=0.0)
    
    # Report file
    report_file = models.FileField(upload_to='reports/%Y/%m/', null=True, blank=True)
    
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['report_type', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.report_type} Report: {self.start_date} to {self.end_date}"