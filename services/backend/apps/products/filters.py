"""
Custom filters for Product API

Provides advanced filtering capabilities for products including:
- Price range filtering
- Stock status filtering
- Category name filtering
"""

from django_filters import rest_framework as filters
from .models import Product, Category


class ProductFilter(filters.FilterSet):
    """Custom filter for Product model"""

    # Price range filters
    min_price = filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = filters.NumberFilter(field_name='price', lookup_expr='lte')

    # Stock filters
    in_stock = filters.BooleanFilter(method='filter_in_stock')

    # Category filters (support both ID and name)
    category = filters.CharFilter(method='filter_category')
    category_id = filters.UUIDFilter(field_name='category__id')

    # Feature filters
    is_active = filters.BooleanFilter(field_name='is_active')
    is_featured = filters.BooleanFilter(field_name='is_featured')
    is_on_sale = filters.BooleanFilter(field_name='is_on_sale')

    class Meta:
        model = Product
        fields = [
            'min_price', 'max_price', 'in_stock',
            'category', 'category_id',
            'is_active', 'is_featured', 'is_on_sale'
        ]

    def filter_in_stock(self, queryset, name, value):
        """
        Filter products by stock status

        Args:
            value: True = in stock (stock_quantity > 0), False = out of stock
        """
        if value:
            return queryset.filter(stock_quantity__gt=0)
        else:
            return queryset.filter(stock_quantity=0)

    def filter_category(self, queryset, name, value):
        """
        Filter by category name or slug

        Supports filtering by:
        - Category name (e.g., "Electronics")
        - Category slug (e.g., "electronics")
        """
        # Try to find category by name or slug
        try:
            category = Category.objects.get(name__iexact=value)
            return queryset.filter(category=category)
        except Category.DoesNotExist:
            try:
                category = Category.objects.get(slug=value)
                return queryset.filter(category=category)
            except Category.DoesNotExist:
                # Return empty queryset if category doesn't exist
                return queryset.none()
