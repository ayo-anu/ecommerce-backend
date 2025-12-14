from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class Payment(models.Model):
    """Payment records"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('card', 'Credit/Debit Card'),
        ('paypal', 'PayPal'),
        ('bank_transfer', 'Bank Transfer'),
        ('wallet', 'Digital Wallet'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey('orders.Order', on_delete=models.PROTECT, related_name='payments')
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='payments')
    
    # Payment details
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Stripe details
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, unique=True, null=True)
    stripe_charge_id = models.CharField(max_length=255, blank=True)
    stripe_customer_id = models.CharField(max_length=255, blank=True)
    
    # Additional info
    failure_reason = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['stripe_payment_intent_id']),
        ]
    
    def __str__(self):
        return f"Payment {self.id} - {self.order.order_number}"


class Refund(models.Model):
    """Refund records"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    REASON_CHOICES = [
        ('duplicate', 'Duplicate'),
        ('fraudulent', 'Fraudulent'),
        ('requested_by_customer', 'Requested by Customer'),
        ('product_issue', 'Product Issue'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name='refunds')
    order = models.ForeignKey('orders.Order', on_delete=models.PROTECT, related_name='refunds')
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=50, choices=REASON_CHOICES)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Stripe
    stripe_refund_id = models.CharField(max_length=255, blank=True)
    
    # Admin
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='processed_refunds')
    
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['payment']),
            models.Index(fields=['order']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Refund {self.id} - {self.amount}"


class PaymentMethod(models.Model):
    """Saved payment methods for users"""
    METHOD_TYPES = [
        ('card', 'Card'),
        ('bank_account', 'Bank Account'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_methods')
    
    method_type = models.CharField(max_length=20, choices=METHOD_TYPES)
    is_default = models.BooleanField(default=False)
    
    # Card details (last 4 digits only)
    card_brand = models.CharField(max_length=20, blank=True)
    card_last4 = models.CharField(max_length=4, blank=True)
    card_exp_month = models.IntegerField(null=True, blank=True)
    card_exp_year = models.IntegerField(null=True, blank=True)
    
    # Stripe
    stripe_payment_method_id = models.CharField(max_length=255)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'is_default']),
        ]
    
    def save(self, *args, **kwargs):
        # Ensure only one default payment method per user
        if self.is_default:
            PaymentMethod.objects.filter(user=self.user, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)
    
    def __str__(self):
        if self.card_last4:
            return f"{self.card_brand} ending in {self.card_last4}"
        return f"{self.method_type} - {self.user.email}"


class Transaction(models.Model):
    """Transaction log for all payment activities"""
    TRANSACTION_TYPES = [
        ('charge', 'Charge'),
        ('refund', 'Refund'),
        ('capture', 'Capture'),
        ('void', 'Void'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name='transactions')
    
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    
    # External reference
    external_transaction_id = models.CharField(max_length=255, blank=True)
    
    # Details
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['payment', '-created_at']),
            models.Index(fields=['transaction_type', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.transaction_type.title()} - {self.amount}"