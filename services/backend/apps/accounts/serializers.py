from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils.html import strip_tags
from .models import Address, UserProfile

User = get_user_model()


def _sanitize_text(value):
    if value:
        return strip_tags(value).strip()
    return value


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'password', 'password2', 'first_name', 'last_name', 'phone']
        read_only_fields = ['id']

    def validate_first_name(self, value):
        return _sanitize_text(value)

    def validate_last_name(self, value):
        return _sanitize_text(value)

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        UserProfile.objects.create(user=user)
        from apps.notifications.tasks import send_verification_email
        send_verification_email.delay(user.id)
        
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['newsletter_subscribed', 'sms_notifications', 'preferred_language', 
                  'preferred_currency', 'total_orders', 'total_spent']
        read_only_fields = ['total_orders', 'total_spent']


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'first_name', 'last_name', 'phone', 
                  'date_of_birth', 'avatar', 'bio', 'email_verified', 'profile', 
                  'created_at', 'last_login']
        read_only_fields = ['id', 'email', 'email_verified', 'created_at', 'last_login']


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone', 'date_of_birth', 'bio']

    def validate_first_name(self, value):
        return _sanitize_text(value)

    def validate_last_name(self, value):
        return _sanitize_text(value)

    def validate_bio(self, value):
        return _sanitize_text(value)


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, validators=[validate_password])
    new_password2 = serializers.CharField(required=True, write_only=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({"new_password": "Password fields didn't match."})
        return attrs
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect")
        return value


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ['id', 'address_type', 'full_name', 'phone', 'address_line1',
                  'address_line2', 'city', 'state', 'country', 'postal_code',
                  'is_default', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_full_name(self, value):
        return _sanitize_text(value)

    def validate_address_line1(self, value):
        return _sanitize_text(value)

    def validate_address_line2(self, value):
        return _sanitize_text(value)

    def validate_city(self, value):
        return _sanitize_text(value)

    def validate_state(self, value):
        return _sanitize_text(value)

    def validate_country(self, value):
        return _sanitize_text(value)

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    
    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email does not exist")
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    new_password2 = serializers.CharField(required=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({"new_password": "Password fields didn't match."})
        return attrs
