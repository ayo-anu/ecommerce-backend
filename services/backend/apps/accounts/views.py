from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string
from django.core.cache import cache
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from .models import Address, UserProfile
from PIL import Image
from django.core.files.uploadedfile import InMemoryUploadedFile
import io
from .serializers import (
    UserRegistrationSerializer, UserSerializer, UserUpdateSerializer,
    ChangePasswordSerializer, AddressSerializer, UserProfileSerializer,
    PasswordResetRequestSerializer, PasswordResetConfirmSerializer
)

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    
    def validate(self, attrs):
        data = super().validate(attrs)
        
        data['user'] = UserSerializer(self.user).data
        
        return data


class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [AllowAny]
    throttle_scope = "login"


class UserRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = UserRegistrationSerializer


class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return User.objects.filter(id=self.request.user.id).select_related('profile')
    
    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserSerializer
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def change_password(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
        
        return Response({'message': 'Password changed successfully'})


    
    @action(detail=False, methods=['post'])
    def upload_avatar(self, request):
        if 'avatar' not in request.FILES:
            return Response({'error': 'No image provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        avatar_file = request.FILES['avatar']
        
        if avatar_file.size > 5 * 1024 * 1024:
            return Response(
                {'error': 'File too large. Maximum size is 5MB'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        if avatar_file.content_type not in allowed_types:
            return Response(
                {'error': 'Invalid file type. Allowed: JPEG, PNG, GIF, WebP'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            img = Image.open(avatar_file)
            img.verify()
            avatar_file.seek(0)
        except Exception as e:
            return Response(
                {'error': 'Invalid or corrupted image file'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = request.user
        user.avatar = avatar_file
        user.save()
        
        return Response({
            'message': 'Avatar uploaded successfully',
            'avatar_url': user.avatar.url
        })


    
    @action(detail=False, methods=['patch'])
    def update_preferences(self, request):
        profile = request.user.profile
        serializer = UserProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def verify_email(self, request):
        token = request.data.get('token')
        
        try:
            user = User.objects.get(email_verification_token=token)
            user.email_verified = True
            user.email_verification_token = ''
            user.save()
            
            return Response({'message': 'Email verified successfully'})
        except User.DoesNotExist:
            return Response(
                {'error': 'Invalid verification token'},
                status=status.HTTP_400_BAD_REQUEST
            )


class AddressViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = AddressSerializer
    
    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        address = self.get_object()
        
        Address.objects.filter(
            user=request.user,
            address_type=address.address_type,
            is_default=True
        ).update(is_default=False)
        
        address.is_default = True
        address.save()
        
        return Response({'message': 'Address set as default'})


class PasswordResetViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    
    @method_decorator(ratelimit(key='ip', rate='5/h', method='POST'))
    @action(detail=False, methods=['post'])
    def request_reset(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'message': 'If that email exists, a reset link has been sent'})
        
        token = get_random_string(64)
        cache.set(f'password_reset_{token}', user.id, 3600)
        
        from apps.notifications.tasks import send_password_reset_email
        send_password_reset_email.delay(user.id, token)
        
        return Response({'message': 'Password reset email sent'})
    
    @action(detail=False, methods=['post'])
    def confirm_reset(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        token = serializer.validated_data['token']
        user_id = cache.get(f'password_reset_{token}')
        
        if not user_id:
            return Response(
                {'error': 'Invalid or expired token'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(id=user_id)
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            
            cache.delete(f'password_reset_{token}')
            
            return Response({'message': 'Password reset successful'})
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_400_BAD_REQUEST
            )
