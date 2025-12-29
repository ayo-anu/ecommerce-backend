from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PaymentViewSet, RefundViewSet, PaymentMethodViewSet
from .webhooks import stripe_webhook


router = DefaultRouter()
# Register at root level since 'api/payments/' is already in main urls.py
# This avoids /api/payments/payments/ duplication
router.register(r'', PaymentViewSet, basename='payment')  # -> /api/payments/
router.register(r'refunds', RefundViewSet, basename='refund')  # -> /api/payments/refunds/
router.register(r'payment-methods', PaymentMethodViewSet, basename='payment-method')  # -> /api/payments/payment-methods/

urlpatterns = [
    path('webhook/', stripe_webhook, name='stripe-webhook'),  # -> /api/payments/webhook/
    path('', include(router.urls)),
]