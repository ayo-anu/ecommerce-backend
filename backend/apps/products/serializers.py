from rest_framework import serializers
from django.core.cache import cache
from .models import Product, ProductImage, Category, ProductVariant


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'alt_text', 'is_primary', 'position']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'parent']


class ProductVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = ['id', 'name', 'sku', 'price', 'stock_quantity', 'is_active', 'attributes']


class ProductListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for product lists"""
    primary_image = serializers.SerializerMethodField()
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'price', 'compare_at_price', 
            'is_on_sale', 'discount_percentage', 'primary_image',
            'category_name', 'stock_quantity', 'is_low_stock'
        ]
    
    def get_primary_image(self, obj):
        # Use select_related in view to avoid N+1 queries
        primary = obj.images.filter(is_primary=True).first()
        return primary.image.url if primary else None


class ProductDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for single product view"""
    images = ProductImageSerializer(many=True, read_only=True)
    category = CategorySerializer(read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    tags = serializers.StringRelatedField(many=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'description', 'price', 'compare_at_price',
            'cost_per_item', 'sku', 'stock_quantity', 'low_stock_threshold',
            'track_inventory', 'category', 'tags', 'meta_title', 'meta_description',
            'is_active', 'is_featured', 'is_on_sale', 'discount_percentage',
            'is_low_stock', 'images', 'variants', 'created_at', 'updated_at'
        ]
    
    def to_representation(self, instance):
        # Try to get from cache first
        cache_key = f'product_detail_{instance.id}'
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data
        
        data = super().to_representation(instance)
        cache.set(cache_key, data, 60 * 15)  # Cache for 15 minutes
        return data


class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating products"""
    
    class Meta:
        model = Product
        fields = [
            'name', 'description', 'price', 'compare_at_price',
            'cost_per_item', 'sku', 'stock_quantity', 'low_stock_threshold',
            'track_inventory', 'category', 'tags', 'meta_title', 'meta_description',
            'is_active', 'is_featured'
        ]
    
    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Price cannot be negative")
        return value
    
    def validate_sku(self, value):
        if self.instance and self.instance.sku == value:
            return value
        if Product.objects.filter(sku=value).exists():
            raise serializers.ValidationError("SKU already exists")
        return value
    
    def create(self, validated_data):
        tags = validated_data.pop('tags', [])
        product = Product.objects.create(**validated_data)
        if tags:
            product.tags.set(tags)
        return product
    
    def update(self, instance, validated_data):
        tags = validated_data.pop('tags', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if tags is not None:
            instance.tags.set(tags)
        
        # Invalidate cache
        cache.delete(f'product_detail_{instance.id}')
        
        return instance