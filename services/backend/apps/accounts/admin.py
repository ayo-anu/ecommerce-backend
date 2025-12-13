from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Address, UserProfile


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'username', 'first_name', 'last_name', 'is_staff', 'email_verified', 'created_at']
    list_filter = ['is_staff', 'is_superuser', 'email_verified', 'created_at']
    search_fields = ['email', 'username', 'first_name', 'last_name']
    ordering = ['-created_at']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('phone', 'date_of_birth', 'avatar', 'bio', 'email_verified')}),
    )


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ['user', 'full_name', 'address_type', 'city', 'country', 'is_default']
    list_filter = ['address_type', 'is_default', 'country']
    search_fields = ['user__email', 'full_name', 'city']


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'newsletter_subscribed', 'total_orders', 'total_spent']
    search_fields = ['user__email']