from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAdminUser
from django.core.cache import cache
from django.db.models import Prefetch, Q, Count
from django_filters.rest_framework import DjangoFilterBackend
from .models import Product, Category, ProductImage
from .serializers import (
    ProductListSerializer, ProductDetailSerializer,
    ProductCreateUpdateSerializer, CategorySerializer
)
from core.pagination import CursorPagination
from core.permissions import IsAdminOrReadOnly
import logging

logger = logging.getLogger(__name__)


class ProductViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'is_active', 'is_featured']
    search_fields = ['name', 'description', 'sku']
    ordering_fields = ['price', 'created_at', 'name']
    ordering = ['-created_at']
    pagination_class = CursorPagination
    
    def get_queryset(self):
        """Optimized queryset with select_related and prefetch_related"""
        if self.action == 'list':
            # Lightweight queryset for lists
            return Product.objects.filter(is_active=True).select_related(
                'category'
            ).prefetch_related(
                Prefetch('images', queryset=ProductImage.objects.filter(is_primary=True))
            ).only(
                'id', 'name', 'slug', 'price', 'compare_at_price',
                'stock_quantity', 'low_stock_threshold', 'category__name'
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