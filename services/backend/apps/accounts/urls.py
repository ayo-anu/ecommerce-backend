from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView
from .views import (
    UserRegistrationView, UserViewSet, AddressViewSet, 
    PasswordResetViewSet, LoginView
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'addresses', AddressViewSet, basename='address')
router.register(r'password-reset', PasswordResetViewSet, basename='password-reset')

urlpatterns = [
    # Authentication - Using custom LoginView that returns user data
    path('login/', LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    
    # Registration
    path('register/', UserRegistrationView.as_view(), name='register'),
    
    # Router URLs
    path('', include(router.urls)),
]