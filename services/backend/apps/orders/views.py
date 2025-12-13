from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.db import transaction
from django.db.models import Prefetch
from .models import Order, Cart, CartItem
from apps.products.models import ProductImage
from .serializers import (
    OrderListSerializer, OrderDetailSerializer,
    OrderCreateSerializer, CartSerializer, CartItemSerializer
)
from apps.products.models import Product, ProductVariant


class OrderViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Order.objects.all().select_related('user').prefetch_related(
                'items__product', 
                'items__variant'  
            )
        return Order.objects.filter(user=user).prefetch_related(
            'items__product', 
            'items__variant'   
        )
    
    def get_serializer_class(self):
        if self.action == 'list':
            return OrderListSerializer
        elif self.action == 'create':
            return OrderCreateSerializer
        return OrderDetailSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        
        # Trigger async tasks
        from .tasks import send_order_confirmation_email, update_analytics
        send_order_confirmation_email.delay(order.id)
        update_analytics.delay(order.id)
        
        return Response(
            OrderDetailSerializer(order).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel an order"""
        order = self.get_object()
        
        if order.status not in ['pending', 'processing']:
            return Response(
                {'error': 'Order cannot be cancelled'},
                status=status.HTTP_400_BAD_REQUEST
                )
        
        with transaction.atomic():
            # Restore inventory
            for item in order.items.select_related('product', 'variant'):
                if item.variant:
                    item.variant.stock_quantity += item.quantity
                    item.variant.save()
                else:
                    item.product.stock_quantity += item.quantity
                    item.product.save()
            
            order.status = 'cancelled'
            order.save()
        
        # Send cancellation email
        from .tasks import send_order_cancellation_email
        send_order_cancellation_email.delay(order.id)
        
        return Response({'status': 'Order cancelled successfully'})
    
    @action(detail=False, methods=['get'])
    def history(self, request):
        """Get user's order history"""
        orders = self.get_queryset().filter(user=request.user)
        page = self.paginate_queryset(orders)
        serializer = OrderListSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)


class CartViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CartSerializer
    
    #Cart Queryset
    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user).prefetch_related(
            Prefetch(
                'items',
                queryset=CartItem.objects.select_related('product', 'variant')
            ),
            Prefetch(
                'items__product__images',
                queryset=ProductImage.objects.filter(is_primary=True)
            )
        )
    
    def get_object(self):
        """Get or create cart for user"""
        cart, created = Cart.objects.get_or_create(user=self.request.user)
        return cart
    
    @action(detail=False, methods=['post'])
    def add_item(self, request):
        """Add item to cart"""
        cart = self.get_object()
        product_id = request.data.get('product_id')
        variant_id = request.data.get('variant_id')
        quantity = int(request.data.get('quantity', 1))
        
        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            return Response(
                {'error': 'Product not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        variant = None
        if variant_id:
            try:
                variant = ProductVariant.objects.get(id=variant_id, product=product, is_active=True)
            except ProductVariant.DoesNotExist:
                return Response(
                    {'error': 'Variant not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Check stock
        stock_source = variant if variant else product
        if product.track_inventory and stock_source.stock_quantity < quantity:
            return Response(
                {'error': f'Only {stock_source.stock_quantity} items available'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Add or update cart item
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            variant=variant,
            defaults={'quantity': quantity}
        )
        
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
        
        serializer = CartSerializer(cart, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['patch'])
    def update_item(self, request):
        """Update cart item quantity"""
        cart = self.get_object()
        item_id = request.data.get('item_id')
        quantity = int(request.data.get('quantity', 1))
        
        try:
            cart_item = CartItem.objects.get(id=item_id, cart=cart)
        except CartItem.DoesNotExist:
            return Response(
                {'error': 'Item not found in cart'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if quantity < 1:
            cart_item.delete()
        else:
            # Check stock
            stock_source = cart_item.variant if cart_item.variant else cart_item.product
            if cart_item.product.track_inventory and stock_source.stock_quantity < quantity:
                return Response(
                    {'error': f'Only {stock_source.stock_quantity} items available'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            cart_item.quantity = quantity
            cart_item.save()
        
        serializer = CartSerializer(cart, context={'request': request})
        return Response(serializer.data)


    @extend_schema(
    parameters=[
        OpenApiParameter(
            name='item_id',
            description='ID of the cart item to remove',
            required=True,
            type=str,
        ),
    ],
    responses={200: CartSerializer},
)
    @action(detail=False, methods=['delete'])
    def remove_item(self, request):
        """Remove a specific item from the user’s cart"""
        cart = self.get_object()
        item_id = request.query_params.get('item_id')

        if not item_id:
            return Response({'error': 'item_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cart_item = CartItem.objects.get(id=item_id, cart=cart)
            cart_item.delete()
        except CartItem.DoesNotExist:
            return Response({'error': 'Item not found in cart'}, status=status.HTTP_404_NOT_FOUND)

        serializer = CartSerializer(cart, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def clear(self, request):
        """Clear all items from cart"""
        cart = self.get_object()
        cart.items.all().delete()
        
        serializer = CartSerializer(cart, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def checkout(self, request):
        """Convert cart to order"""
        cart = self.get_object()
        
        if not cart.items.exists():
            return Response(
                {'error': 'Cart is empty'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Prepare order data from cart
        items = []
        for item in cart.items.all():
            items.append({
                'product_id': str(item.product.id),
                'variant_id': str(item.variant.id) if item.variant else None,
                'quantity': item.quantity
            })
        
        order_data = {
            'items': items,
            'shipping_address': request.data.get('shipping_address'),
            'billing_address': request.data.get('billing_address'),
            'customer_notes': request.data.get('customer_notes', '')
        }
        
        # Create order
        serializer = OrderCreateSerializer(data=order_data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        
        # Clear cart
        cart.items.all().delete()
        
        return Response(
            OrderDetailSerializer(order).data,
            status=status.HTTP_201_CREATED
        )