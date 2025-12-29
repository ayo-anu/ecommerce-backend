from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAdminUser
from django.core.cache import cache
from django.db.models import Prefetch, Q, Count
from django_filters.rest_framework import DjangoFilterBackend
from .models import Product, Category, ProductImage, ProductReview, ReviewHelpful, Wishlist, WishlistItem
from .serializers import (
    ProductListSerializer, ProductDetailSerializer,
    ProductCreateUpdateSerializer, CategorySerializer,
    ProductReviewSerializer, CreateReviewSerializer,
    WishlistSerializer, WishlistItemSerializer
)
from .filters import ProductFilter
from core.pagination import StandardResultsSetPagination
from core.permissions import IsAdminOrReadOnly
import logging

logger = logging.getLogger(__name__)


class ProductViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProductFilter  # Use custom filter class
    search_fields = ['name', 'description', 'sku']
    ordering_fields = ['price', 'created_at', 'name']
    ordering = ['-created_at']
    pagination_class = StandardResultsSetPagination  # Changed from CursorPagination to include count
    
    def get_queryset(self):
        """Optimized queryset with select_related and prefetch_related"""
        if self.action == 'list':
            # Lightweight queryset for lists
            # Note: Removed .only() to avoid field access issues with filters
            return Product.objects.filter(is_active=True).select_related(
                'category'
            ).prefetch_related(
                Prefetch('images', queryset=ProductImage.objects.filter(is_primary=True))
            )
        else:
            # Full queryset for detail views
            return Product.objects.select_related(
                'category'
            ).prefetch_related(
                'images', 'variants', 'tags'
            )
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ProductListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ProductCreateUpdateSerializer
        return ProductDetailSerializer
    
    def list(self, request, *args, **kwargs):
        # Try cache for common list requests
        cache_key = f'product_list_{request.GET.urlencode()}'
        cached_response = cache.get(cache_key)
        
        if cached_response:
            return Response(cached_response)
        
        response = super().list(request, *args, **kwargs)
        cache.set(cache_key, response.data, 60 * 5)  # Cache for 5 minutes
        return response
    
    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Get featured products"""
        products = self.get_queryset().filter(is_featured=True)[:10]
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Full-text search using Elasticsearch"""
        query = request.query_params.get('q', '')
        if not query:
            return Response({'results': []})
        
        try:
            # Use Elasticsearch for search
            from .documents import ProductDocument
            search = ProductDocument.search().query("multi_match", query=query, fields=['name', 'description'])
            results = search[0:20].execute()
            
            product_ids = [hit.meta.id for hit in results]
            
            # ✅ OPTIMIZED: Add select_related and prefetch_related to search results
            products = Product.objects.filter(id__in=product_ids).select_related(
                'category'
            ).prefetch_related(
                Prefetch('images', queryset=ProductImage.objects.filter(is_primary=True))
            )
            
        except Exception as e:
            # ✅ FALLBACK: Use database search if Elasticsearch fails
            logger.warning(f"Elasticsearch search failed: {e}, falling back to DB search")
            products = Product.objects.filter(
                Q(name__icontains=query) | Q(description__icontains=query),
                is_active=True
            ).select_related('category').prefetch_related(
                Prefetch('images', queryset=ProductImage.objects.filter(is_primary=True))
            )[:20]
        
        serializer = ProductListSerializer(products, many=True, context={'request': request})
        return Response({'results': serializer.data})
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def upload_image(self, request, pk=None):
        """Upload product image"""
        product = self.get_object()
        image_file = request.FILES.get('image')
        
        if not image_file:
            return Response({'error': 'No image provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        image = ProductImage.objects.create(
            product=product,
            image=image_file,
            alt_text=request.data.get('alt_text', ''),
            is_primary=request.data.get('is_primary', False)
        )
        
        # Invalidate cache
        cache.delete(f'product_detail_{product.id}')
        
        return Response({'id': image.id, 'url': image.image.url}, status=status.HTTP_201_CREATED)


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.filter(is_active=True).prefetch_related('children')
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = 'slug'
    
    @action(detail=True, methods=['get'])
    def products(self, request, slug=None):
        """Get products in category"""
        category = self.get_object()
        products = Product.objects.filter(
            category=category, is_active=True
        ).select_related('category').prefetch_related(
            Prefetch('images', queryset=ProductImage.objects.filter(is_primary=True))
        )
        
        serializer = ProductListSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)


class ProductReviewViewSet(viewsets.ModelViewSet):
    """Product review management"""
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['product', 'rating', 'is_approved']
    ordering_fields = ['created_at', 'helpful_count', 'rating']
    ordering = ['-created_at']

    def get_queryset(self):
        """Return approved reviews, or all reviews if admin"""
        queryset = ProductReview.objects.select_related('user', 'product')

        # Filter by product if specified
        product_id = self.request.query_params.get('product_id')
        if product_id:
            queryset = queryset.filter(product_id=product_id)

        # Show only approved reviews to non-staff users
        if not self.request.user.is_staff:
            queryset = queryset.filter(is_approved=True)

        return queryset

    def get_serializer_class(self):
        if self.action == 'create':
            return CreateReviewSerializer
        return ProductReviewSerializer

    def perform_create(self, serializer):
        """Create review and check if verified purchase"""
        from apps.orders.models import Order

        product = serializer.validated_data['product']

        # Check if user purchased this product
        has_purchased = Order.objects.filter(
            user=self.request.user,
            items__product=product,
            status='delivered'
        ).exists()

        serializer.save(
            user=self.request.user,
            is_verified_purchase=has_purchased
        )

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticatedOrReadOnly])
    def mark_helpful(self, request, pk=None):
        """Mark review as helpful"""
        review = self.get_object()

        # Check if user already marked as helpful
        helpful, created = ReviewHelpful.objects.get_or_create(
            review=review,
            user=request.user
        )

        if not created:
            return Response(
                {'detail': 'You already marked this review as helpful'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update helpful count
        review.helpful_count = review.helpful_votes.count()
        review.save()

        return Response({
            'helpful_count': review.helpful_count,
            'message': 'Review marked as helpful'
        })


class WishlistViewSet(viewsets.ModelViewSet):
    """User wishlist management"""
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = WishlistSerializer

    def get_queryset(self):
        """Return current user's wishlist"""
        return Wishlist.objects.filter(user=self.request.user).prefetch_related(
            'items__product__images',
            'items__product__category'
        )

    def get_object(self):
        """Get or create wishlist for current user"""
        wishlist, created = Wishlist.objects.get_or_create(user=self.request.user)
        return wishlist

    @action(detail=False, methods=['get'])
    def my_wishlist(self, request):
        """Get current user's wishlist"""
        wishlist = self.get_object()
        serializer = self.get_serializer(wishlist)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def add_item(self, request):
        """Add item to wishlist"""
        wishlist = self.get_object()
        product_id = request.data.get('product_id')
        variant_id = request.data.get('variant_id')
        notes = request.data.get('notes', '')

        if not product_id:
            return Response(
                {'error': 'product_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if product exists
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response(
                {'error': 'Product not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if already in wishlist
        if WishlistItem.objects.filter(wishlist=wishlist, product=product, variant_id=variant_id).exists():
            return Response(
                {'error': 'Product already in wishlist'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create wishlist item
        item = WishlistItem.objects.create(
            wishlist=wishlist,
            product=product,
            variant_id=variant_id,
            notes=notes
        )

        serializer = WishlistItemSerializer(item)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['delete'])
    def remove_item(self, request):
        """Remove item from wishlist"""
        wishlist = self.get_object()
        item_id = request.query_params.get('item_id')

        if not item_id:
            return Response(
                {'error': 'item_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            item = WishlistItem.objects.get(id=item_id, wishlist=wishlist)
            item.delete()
            return Response({'message': 'Item removed from wishlist'})
        except WishlistItem.DoesNotExist:
            return Response(
                {'error': 'Item not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['post'])
    def clear(self, request):
        """Clear all items from wishlist"""
        wishlist = self.get_object()
        WishlistItem.objects.filter(wishlist=wishlist).delete()
        return Response({'message': 'Wishlist cleared'})