from django.contrib import admin
from .models import (
    DailySales, ProductAnalytics, CategoryAnalytics,
    UserActivity, CustomerSegment, SalesReport
)


@admin.register(DailySales)
class DailySalesAdmin(admin.ModelAdmin):
    list_display = ['date', 'total_revenue', 'total_orders', 'total_customers', 'average_order_value']
    list_filter = ['date']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'date'


@admin.register(ProductAnalytics)
class ProductAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['product', 'date', 'views', 'purchases', 'revenue', 'conversion_rate']
    list_filter = ['date']
    search_fields = ['product__name']
    date_hierarchy = 'date'


@admin.register(CategoryAnalytics)
class CategoryAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['category', 'date', 'views', 'total_orders', 'total_revenue']
    list_filter = ['date']
    search_fields = ['category__name']
    date_hierarchy = 'date'


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'product', 'timestamp']
    list_filter = ['action', 'timestamp']
    search_fields = ['user__email', 'product__name']
    date_hierarchy = 'timestamp'


@admin.register(CustomerSegment)
class CustomerSegmentAdmin(admin.ModelAdmin):
    list_display = ['user', 'segment_type', 'total_orders', 'total_spent', 'average_order_value']
    list_filter = ['segment_type']
    search_fields = ['user__email']


@admin.register(SalesReport)
class SalesReportAdmin(admin.ModelAdmin):
    list_display = ['report_type', 'start_date', 'end_date', 'total_revenue', 'created_at']
    list_filter = ['report_type', 'created_at']
    readonly_fields = ['created_at']