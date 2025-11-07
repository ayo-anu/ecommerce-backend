from rest_framework import serializers
from .models import DailySales, ProductAnalytics, CategoryAnalytics, UserActivity, SalesReport


class DailySalesSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailySales
        fields = '__all__'


class ProductAnalyticsSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    
    class Meta:
        model = ProductAnalytics
        fields = '__all__'


class CategoryAnalyticsSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = CategoryAnalytics
        fields = '__all__'


class UserActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = UserActivity
        fields = ['id', 'action', 'product', 'category', 'metadata', 'timestamp']
        read_only_fields = ['id', 'timestamp']


class SalesReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesReport
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'generated_by']


class DashboardStatsSerializer(serializers.Serializer):
    """Serializer for dashboard overview statistics"""
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_orders = serializers.IntegerField()
    total_customers = serializers.IntegerField()
    average_order_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    revenue_growth = serializers.FloatField()
    order_growth = serializers.FloatField()
    customer_growth = serializers.FloatField()
    
    top_products = serializers.ListField()
    top_categories = serializers.ListField()
    recent_orders = serializers.ListField()
    
    sales_chart_data = serializers.DictField()

