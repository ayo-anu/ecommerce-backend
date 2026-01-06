from rest_framework import serializers
from django.db import transaction
from .models import Order, OrderItem, Cart, CartItem
from apps.products.models import Product, ProductVariant
from apps.accounts.models import Address
from decimal import Decimal
import bleach


class ProductSnapshotSerializer(serializers.Serializer):
    """Product snapshot data stored in OrderItem"""
    name = serializers.CharField(source='product_name')
    sku = serializers.CharField(source='product_sku')
    id = serializers.UUIDField(source='product.id', read_only=True)


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSnapshotSerializer(source='*', read_only=True)
    price = serializers.DecimalField(source='unit_price', max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'variant', 'variant_name',
                  'quantity', 'price', 'unit_price', 'total_price']
        read_only_fields = ['product', 'variant_name', 'price', 'unit_price', 'total_price']


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


class OrderFromCartSerializer(serializers.Serializer):
    """
    Create order from user's cart with address ID.
    Used for POST /api/orders/ - the main checkout endpoint.
    """
    shipping_address_id = serializers.UUIDField()
    billing_address_id = serializers.UUIDField(required=False, allow_null=True)
    billing_same_as_shipping = serializers.BooleanField(default=True)
    payment_method = serializers.CharField(required=False, allow_blank=True, default='card')
    customer_notes = serializers.CharField(required=False, allow_blank=True, default='')

    def validate_customer_notes(self, value):
        """Sanitize customer notes to prevent XSS"""
        if value:
            return bleach.clean(value, strip=True)
        return value

    def validate(self, attrs):
        """
        Validate cart exists and has items BEFORE validating addresses.
        This ensures empty cart error takes precedence over invalid address error.
        """
        user = self.context['request'].user

        # Check cart exists and has items FIRST
        try:
            cart = Cart.objects.get(user=user)
            if not cart.items.exists():
                raise serializers.ValidationError({"error": "Cart is empty"})
        except Cart.DoesNotExist:
            raise serializers.ValidationError({"error": "Cart is empty"})

        # Now validate addresses
        shipping_address_id = attrs.get('shipping_address_id')
        if shipping_address_id:
            try:
                address = Address.objects.get(id=shipping_address_id, user=user)
                self._shipping_address = address
            except Address.DoesNotExist:
                raise serializers.ValidationError({"shipping_address_id": "Shipping address not found or does not belong to you"})

        billing_address_id = attrs.get('billing_address_id')
        if billing_address_id:
            try:
                address = Address.objects.get(id=billing_address_id, user=user)
                self._billing_address = address
            except Address.DoesNotExist:
                raise serializers.ValidationError({"billing_address_id": "Billing address not found or does not belong to you"})

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        """
        Create order from user's cart.

        Steps:
        1. Get user's cart
        2. Validate cart has items
        3. Build items list from cart
        4. Fetch and validate addresses
        5. Create order with inventory deduction
        6. Clear cart
        7. Return order
        """
        user = self.context['request'].user

        # Step 1 & 2: Get cart and validate it has items
        try:
            cart = Cart.objects.prefetch_related(
                'items__product',
                'items__variant'
            ).get(user=user)
        except Cart.DoesNotExist:
            raise serializers.ValidationError({"error": "Cart is empty"})

        if not cart.items.exists():
            raise serializers.ValidationError({"error": "Cart is empty"})

        # Step 3: Build items list from cart
        items_data = []
        for cart_item in cart.items.all():
            item_data = {
                'product_id': str(cart_item.product.id),
                'quantity': cart_item.quantity
            }
            if cart_item.variant:
                item_data['variant_id'] = str(cart_item.variant.id)
            items_data.append(item_data)

        # Step 4: Get addresses (already validated and stored in validate_* methods)
        shipping_address = self._shipping_address
        billing_address = getattr(self, '_billing_address', None)

        # If billing same as shipping, use shipping address
        if validated_data.get('billing_same_as_shipping', True):
            billing_address = shipping_address

        # Step 5: Fetch products and variants with locks
        product_ids = [item['product_id'] for item in items_data]
        variant_ids = [item.get('variant_id') for item in items_data if 'variant_id' in item]

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

        # Calculate totals and validate stock
        subtotal = Decimal('0')
        order_items = []

        for item_data in items_data:
            product = products.get(item_data['product_id'])
            if not product:
                raise serializers.ValidationError(f"Product {item_data['product_id']} not found")

            variant = None
            if 'variant_id' in item_data:
                variant = variants.get(item_data['variant_id'])
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

            # Deduct inventory
            old_stock = stock_source.stock_quantity
            stock_source.stock_quantity -= quantity
            stock_source.save()

            # Invalidate product detail cache (product details are cached for 15 min)
            from django.core.cache import cache
            cache.delete(f'product_detail_{product.id}')
            cache.delete(f'product_list_{product.id}')  # Also invalidate list cache if exists

            # Debug logging
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"INVENTORY DEDUCTION: {product.name} (ID: {product.id}): {old_stock} -> {stock_source.stock_quantity} (deducted {quantity}), cache invalidated")

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

        # Calculate tax and total
        tax = subtotal * Decimal('0.1')  # 10% tax
        shipping_cost = Decimal('10.00') if subtotal < Decimal('50') else Decimal('0')  # Free shipping over $50
        total = subtotal + tax + shipping_cost

        # Step 6: Create order
        order = Order.objects.create(
            user=user,
            subtotal=subtotal,
            tax=tax,
            shipping_cost=shipping_cost,
            total=total,
            shipping_name=shipping_address.full_name,
            shipping_email=user.email,  # Use user's email
            shipping_phone=shipping_address.phone,
            shipping_address_line1=shipping_address.address_line1,
            shipping_address_line2=shipping_address.address_line2,
            shipping_city=shipping_address.city,
            shipping_state=shipping_address.state,
            shipping_country=shipping_address.country,
            shipping_postal_code=shipping_address.postal_code,
            billing_same_as_shipping=validated_data.get('billing_same_as_shipping', True),
            billing_address_line1=billing_address.address_line1 if billing_address else '',
            billing_city=billing_address.city if billing_address else '',
            billing_postal_code=billing_address.postal_code if billing_address else '',
            customer_notes=validated_data.get('customer_notes', '')
        )

        # Create order items
        for item_data in order_items:
            OrderItem.objects.create(order=order, **item_data)

        # Step 7: Clear cart
        cart.items.all().delete()

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
        """
        Get primary product image.
        Uses prefetched 'primary_images' if available (from optimized query),
        otherwise falls back to standard query.
        """
        # Try to use prefetched data first (avoids N+1 query)
        if hasattr(obj.product, 'primary_images') and obj.product.primary_images:
            primary_image = obj.product.primary_images[0]
            return self.context['request'].build_absolute_uri(primary_image.image.url)

        # Fallback to standard query (for backward compatibility)
        primary_image = obj.product.images.filter(is_primary=True).first()
        if primary_image:
            return self.context['request'].build_absolute_uri(primary_image.image.url)
        return None

    def get_subtotal(self, obj):
        """
        Calculate item subtotal.
        Accesses product/variant price (should be prefetched with select_related).
        """
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