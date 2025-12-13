from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AnalyticsDashboardViewSet, UserActivityViewSet, SalesReportViewSet

router = DefaultRouter()
router.register(r'dashboard', AnalyticsDashboardViewSet, basename='analytics-dashboard')
router.register(r'activity', UserActivityViewSet, basename='user-activity')
router.register(r'reports', SalesReportViewSet, basename='sales-report')

urlpatterns = [
    path('', include(router.urls)),
]