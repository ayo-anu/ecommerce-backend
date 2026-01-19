
from django_filters import rest_framework as filters
from .models import Product, Category


class ProductFilter(filters.FilterSet):

    min_price = filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = filters.NumberFilter(field_name='price', lookup_expr='lte')

    in_stock = filters.BooleanFilter(method='filter_in_stock')

    category = filters.CharFilter(method='filter_category')
    category_id = filters.UUIDFilter(field_name='category__id')

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
        if value:
            return queryset.filter(stock_quantity__gt=0)
        else:
            return queryset.filter(stock_quantity=0)

    def filter_category(self, queryset, name, value):
        try:
            category = Category.objects.get(name__iexact=value)
            return queryset.filter(category=category)
        except Category.DoesNotExist:
            try:
                category = Category.objects.get(slug=value)
                return queryset.filter(category=category)
            except Category.DoesNotExist:
                return queryset.none()
