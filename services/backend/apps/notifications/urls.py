from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet, EmailTemplateViewSet

router = DefaultRouter()
# Register at root level since 'api/notifications/' is already in main urls.py
# This avoids /api/notifications/notifications/ duplication
router.register(r'', NotificationViewSet, basename='notification')  # -> /api/notifications/
router.register(r'email-templates', EmailTemplateViewSet, basename='email-template')  # -> /api/notifications/email-templates/

urlpatterns = [
    path('', include(router.urls)),
]