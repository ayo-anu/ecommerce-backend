from rest_framework import serializers
from django.db import transaction
from .models import Order, OrderItem, Cart, CartItem
from apps.products.models import Product, ProductVariant
from decimal import Decimal
import bleach


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(read_only=True)
    
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'variant', 'product_name', 'variant_name', 
                  'quantity', 'unit_price', 'total_price']
        read_only_fields = ['product_name', 'variant_name', 'unit_price', 'total_price']


class OrderListSerializer(serializers.ModelSerializer):
    items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = ['id', 'order_number', 'status', 'payment_status', 'total', 
                  'items_count', 'created_at']
    
    def get_items_count(self, obj):
        return obj.items.count()


class OrderDetailSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = Order
        fields = '__all__'


class ShippingAddressSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255)
    email = serializers.EmailField() 
    phone = serializers.CharField(max_length=20)
    address_line1 = serializers.CharField(max_length=255)
    address_line2 = serializers.CharField(max_length=255, required=False, allow_blank=True)
    city = serializers.CharField(max_length=100)
    state = serializers.CharField(max_length=100)
    country = serializers.CharField(max_length=100)
    postal_code = serializers.CharField(max_length=20)


class OrderCreateSerializer(serializers.Serializer):
    items = serializers.ListField(child=serializers.DictField())
    shipping_address = ShippingAddressSerializer()
    billing_address = serializers.DictField(required=False)
    customer_notes = serializers.CharField(required=False, allow_blank=True)


    def validate_customer_notes(self, value):
        """Sanitize customer notes to prevent XSS"""
        if value:
            return bleach.clean(value, strip=True)
        return value
    
    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError("Order must contain at least one item")
        
        for item in items:
            if 'product_id' not in item or 'quantity' not in item:
                raise serializers.ValidationError("Each item must have product_id and quantity")
            
            if item['quantity'] < 1:
                raise serializers.ValidationError("Quantity must be at least 1")
        
        return items

    
    @transaction.atomic
    def create(self, validated_data):
        user = self.context['request'].user
        items_data = validated_data['items']
        shipping_address = validated_data['shipping_address']
        
        # Calculate totals
        subtotal = 0
        order_items = []
        
    @transaction.atomic
    def create(self, validated_data):
        user = self.context['request'].user
        items_data = validated_data['items']
        shipping_address = validated_data['shipping_address']
        
        
        product_ids = [item['product_id'] for item in items_data]
        variant_ids = [item.get('variant_id') for item in items_data if 'variant_id' in item]
        
        # Fetch all at once with select_for_update
        products = {
            str(p.id): p 
            for p in Product.objects.select_for_update().filter(id__in=product_ids)
        }
        
        variants = {}
        if variant_ids:
            variants = {
                str(v.id): v 
                for v in ProductVariant.objects.select_for_update().filter(id__in=variant_ids)
            }
        
        # Calculate totals
        subtotal = 0
        order_items = []
    
    @transaction.atomic
    def create(self, validated_data):
        user = self.context['request'].user
        items_data = validated_data['items']
        shipping_address = validated_data['shipping_address']
        
        product_ids = [item['product_id'] for item in items_data]
        variant_ids = [item.get('variant_id') for item in items_data if 'variant_id' in item]
        
        # Fetch all at once with select_for_update
        products = {
            str(p.id): p 
            for p in Product.objects.select_for_update().filter(id__in=product_ids)
        }
        
        variants = {}
        if variant_ids:
            variants = {
                str(v.id): v 
                for v in ProductVariant.objects.select_for_update().filter(id__in=variant_ids)
            }
        
        # Calculate totals
        subtotal = 0
        order_items = []
        
        for item_data in items_data:
            product = products.get(str(item_data['product_id']))
            if not product:
                raise serializers.ValidationError(f"Product {item_data['product_id']} not found")
            
            variant = None
            if 'variant_id' in item_data:
                variant = variants.get(str(item_data['variant_id']))
                if not variant:
                    raise serializers.ValidationError(f"Variant {item_data['variant_id']} not found")
                price = variant.price or product.price
                stock_source = variant
            else:
                price = product.price
                stock_source = product
            
            quantity = item_data['quantity']
            
            # Check stock
            if product.track_inventory and stock_source.stock_quantity < quantity:
                raise serializers.ValidationError(
                    f"Insufficient stock for {product.name}. Available: {stock_source.stock_quantity}"
                )
            
            # Reserve inventory
            stock_source.stock_quantity -= quantity
            stock_source.save()
            
            subtotal += price * quantity
            
            order_items.append({
                'product': product,
                'variant': variant,
                'product_name': product.name,
                'product_sku': product.sku,
                'variant_name': variant.name if variant else '',
                'quantity': quantity,
                'unit_price': price,
                'total_price': price * quantity
            })


        # Calculate tax and total (simplified)
        tax = subtotal * Decimal('0.1')
        shipping_cost = 10.00 if subtotal < 50 else 0  # Free shipping over $50
        total = subtotal + tax + shipping_cost
        
        # Create order
        order = Order.objects.create(
            user=user,
            subtotal=subtotal,
            tax=tax,
            shipping_cost=shipping_cost,
            total=total,
            shipping_name=shipping_address.get('full_name'),
            shipping_email=shipping_address.get('email'),
            shipping_phone=shipping_address.get('phone'),
            shipping_address_line1=shipping_address.get('address_line1'),
            shipping_address_line2=shipping_address.get('address_line2', ''),
            shipping_city=shipping_address.get('city'),
            shipping_state=shipping_address.get('state'),
            shipping_country=shipping_address.get('country'),
            shipping_postal_code=shipping_address.get('postal_code'),
            customer_notes=validated_data.get('customer_notes', '')
        )
        
        # Create order items
        for item_data in order_items:
            OrderItem.objects.create(order=order, **item_data)
        
        return order


class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_price = serializers.DecimalField(source='product.price', max_digits=10, decimal_places=2, read_only=True)
    product_image = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()
    
    class Meta:
        model = CartItem
        fields = ['id', 'product', 'variant', 'quantity', 'product_name', 
                  'product_price', 'product_image', 'subtotal']
    
    def get_product_image(self, obj):
        primary_image = obj.product.images.filter(is_primary=True).first()
        if primary_image:
            return self.context['request'].build_absolute_uri(primary_image.image.url)
        return None
    
    def get_subtotal(self, obj):
        price = obj.variant.price if obj.variant and obj.variant.price else obj.product.price
        return price * obj.quantity


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()
    
    class Meta:
        model = Cart
        fields = ['id', 'items', 'total', 'updated_at']
    
    def get_total(self, obj):
        total = 0
        for item in obj.items.all():
            price = item.variant.price if item.variant and item.variant.price else item.product.price
            total += price * item.quantity
        return total