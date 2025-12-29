from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, CategoryViewSet, ProductReviewViewSet, WishlistViewSet

router = DefaultRouter()
# Register at root level since 'api/products/' is already in main urls.py
# This avoids /api/products/products/ duplication
router.register(r'', ProductViewSet, basename='product')  # -> /api/products/
router.register(r'categories', CategoryViewSet, basename='category')  # -> /api/products/categories/
router.register(r'reviews', ProductReviewViewSet, basename='product-review')  # -> /api/products/reviews/
router.register(r'wishlist', WishlistViewSet, basename='wishlist')  # -> /api/products/wishlist/

urlpatterns = [
    path('', include(router.urls)),
]