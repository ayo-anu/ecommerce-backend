from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, CategoryViewSet, ProductReviewViewSet, WishlistViewSet

# Router for ProductViewSet with empty prefix
# Note: Empty prefix creates catch-all pattern that must come LAST in URL resolution
router = DefaultRouter()
router.register(r'', ProductViewSet, basename='product')

# Manual URL patterns for other viewsets to avoid being caught by product detail route
# These MUST be defined before router.urls to ensure proper matching order
urlpatterns = [
    # Reviews - all actions
    path('reviews/', ProductReviewViewSet.as_view({'get': 'list', 'post': 'create'}), name='product-review-list'),
    path('reviews/<pk>/', ProductReviewViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='product-review-detail'),
    path('reviews/<pk>/mark_helpful/', ProductReviewViewSet.as_view({'post': 'mark_helpful'}), name='product-review-mark-helpful'),

    # Categories - all actions
    path('categories/', CategoryViewSet.as_view({'get': 'list', 'post': 'create'}), name='category-list'),
    path('categories/<slug:slug>/', CategoryViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='category-detail'),
    path('categories/<slug:slug>/products/', CategoryViewSet.as_view({'get': 'products'}), name='category-products'),

    # Wishlist - all actions
    path('wishlist/', WishlistViewSet.as_view({'get': 'list', 'post': 'create'}), name='wishlist-list'),
    path('wishlist/<pk>/', WishlistViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='wishlist-detail'),
    path('wishlist/<pk>/add_item/', WishlistViewSet.as_view({'post': 'add_item'}), name='wishlist-add-item'),
    path('wishlist/<pk>/remove_item/', WishlistViewSet.as_view({'post': 'remove_item'}), name='wishlist-remove-item'),

    # Product routes (catch-all) - MUST come LAST
    path('', include(router.urls)),
]