from django.contrib import admin
from .models import Payment, Refund, PaymentMethod, Transaction


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'user', 'amount', 'payment_method', 'status', 'created_at', 'paid_at']
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['order__order_number', 'user__email', 'stripe_payment_intent_id']
    readonly_fields = ['created_at', 'updated_at', 'paid_at']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('order', 'user', 'payment_method', 'amount', 'currency', 'status')
        }),
        ('Stripe Details', {
            'fields': ('stripe_payment_intent_id', 'stripe_charge_id', 'stripe_customer_id')
        }),
        ('Additional Info', {
            'fields': ('failure_reason', 'metadata', 'created_at', 'updated_at', 'paid_at')
        }),
    )


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ['id', 'payment', 'order', 'amount', 'reason', 'status', 'created_at', 'processed_at']
    list_filter = ['status', 'reason', 'created_at']
    search_fields = ['payment__id', 'order__order_number']
    readonly_fields = ['created_at', 'processed_at']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('payment', 'order', 'amount', 'reason', 'description', 'status')
        }),
        ('Processing', {
            'fields': ('stripe_refund_id', 'processed_by', 'processed_at')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'method_type', 'card_brand', 'card_last4', 'is_default', 'created_at']
    list_filter = ['method_type', 'card_brand', 'is_default']
    search_fields = ['user__email', 'card_last4']
    readonly_fields = ['created_at']


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'payment', 'transaction_type', 'amount', 'currency', 'created_at']
    list_filter = ['transaction_type', 'created_at']
    search_fields = ['payment__id', 'external_transaction_id']
    readonly_fields = ['created_at']