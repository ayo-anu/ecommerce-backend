from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrderViewSet, CartViewSet

router = DefaultRouter()
# Register at root level since 'api/orders/' is already in main urls.py
# This avoids /api/orders/orders/ duplication
# IMPORTANT: Register more specific patterns (cart) BEFORE generic patterns (root)
# to avoid routing conflicts where /api/orders/cart/ matches OrderViewSet's /{pk}/ pattern
router.register(r'cart', CartViewSet, basename='cart')  # -> /api/orders/cart/ (FIRST)
router.register(r'', OrderViewSet, basename='order')  # -> /api/orders/ (SECOND - catches remaining)

urlpatterns = [
    path('', include(router.urls)),
]