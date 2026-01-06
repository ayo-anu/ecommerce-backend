from rest_framework import serializers
from django.core.cache import cache
from .models import Product, ProductImage, Category, ProductVariant, ProductReview, ReviewHelpful, Wishlist, WishlistItem


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
            'category_name', 'stock_quantity', 'is_low_stock',
            'is_active', 'is_featured'  # Added for filtering and tests
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


class ProductReviewSerializer(serializers.ModelSerializer):
    """Serializer for product reviews"""
    user_name = serializers.SerializerMethodField()
    user_email = serializers.EmailField(source='user.email', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = ProductReview
        fields = [
            'id', 'product', 'product_name', 'user', 'user_name', 'user_email',
            'rating', 'title', 'comment', 'is_verified_purchase',
            'is_approved', 'helpful_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['user', 'is_verified_purchase', 'helpful_count', 'is_approved']

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username


class CreateReviewSerializer(serializers.ModelSerializer):
    """Serializer for creating product reviews"""

    class Meta:
        model = ProductReview
        fields = ['id', 'product', 'rating', 'title', 'comment', 'is_verified_purchase', 'is_approved', 'helpful_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'is_verified_purchase', 'is_approved', 'helpful_count', 'created_at', 'updated_at']

    def validate_title(self, value):
        """Sanitize title to prevent XSS attacks"""
        from django.utils.html import strip_tags
        sanitized = strip_tags(value).strip()
        if not sanitized:
            raise serializers.ValidationError("Title cannot be empty")
        return sanitized

    def validate_comment(self, value):
        """Sanitize comment to prevent XSS attacks"""
        from django.utils.html import strip_tags
        import re

        # First, strip HTML tags
        sanitized = strip_tags(value).strip()

        # Remove dangerous protocols (javascript:, data:, vbscript:, etc.)
        dangerous_protocols = ['javascript:', 'data:', 'vbscript:', 'file:', 'about:']
        for protocol in dangerous_protocols:
            sanitized = re.sub(re.escape(protocol), '', sanitized, flags=re.IGNORECASE)

        # Clean up any remaining whitespace
        sanitized = sanitized.strip()

        if not sanitized:
            raise serializers.ValidationError("Comment cannot be empty")

        # Limit comment length
        if len(sanitized) > 5000:
            return sanitized[:5000]

        return sanitized

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5")
        return value

    def validate(self, data):
        # Check if user already reviewed this product
        user = self.context['request'].user
        product = data.get('product')

        if ProductReview.objects.filter(user=user, product=product).exists():
            raise serializers.ValidationError("You have already reviewed this product")

        return data


class WishlistItemSerializer(serializers.ModelSerializer):
    """Serializer for wishlist items"""
    product = ProductListSerializer(read_only=True)
    product_id = serializers.UUIDField(write_only=True)
    variant_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = WishlistItem
        fields = ['id', 'product', 'product_id', 'variant', 'variant_id', 'added_at', 'notes']
        read_only_fields = ['added_at']


class WishlistSerializer(serializers.ModelSerializer):
    """Serializer for wishlist"""
    items = WishlistItemSerializer(many=True, read_only=True)
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = Wishlist
        fields = ['id', 'user', 'items', 'item_count', 'created_at', 'updated_at']
        read_only_fields = ['user', 'created_at', 'updated_at']

    def get_item_count(self, obj):
        return obj.items.count()