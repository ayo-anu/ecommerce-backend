from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, CategoryViewSet, ProductReviewViewSet, WishlistViewSet

router = DefaultRouter()
router.register(r'', ProductViewSet, basename='product')

urlpatterns = [
    path('reviews/', ProductReviewViewSet.as_view({'get': 'list', 'post': 'create'}), name='product-review-list'),
    path('reviews/<pk>/', ProductReviewViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='product-review-detail'),
    path('reviews/<pk>/mark_helpful/', ProductReviewViewSet.as_view({'post': 'mark_helpful'}), name='product-review-mark-helpful'),

    path('categories/', CategoryViewSet.as_view({'get': 'list', 'post': 'create'}), name='category-list'),
    path('categories/<slug:slug>/', CategoryViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='category-detail'),
    path('categories/<slug:slug>/products/', CategoryViewSet.as_view({'get': 'products'}), name='category-products'),

    path('wishlist/', WishlistViewSet.as_view({'get': 'list', 'post': 'create'}), name='wishlist-list'),
    path('wishlist/<pk>/', WishlistViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='wishlist-detail'),
    path('wishlist/<pk>/add_item/', WishlistViewSet.as_view({'post': 'add_item'}), name='wishlist-add-item'),
    path('wishlist/<pk>/remove_item/', WishlistViewSet.as_view({'post': 'remove_item'}), name='wishlist-remove-item'),

    path('', include(router.urls)),
]
