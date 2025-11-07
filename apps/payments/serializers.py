from rest_framework import serializers
from .models import Payment, Refund, PaymentMethod, Transaction


class PaymentSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    
    class Meta:
        model = Payment
        fields = ['id', 'order', 'order_number', 'payment_method', 'amount', 
                  'currency', 'status', 'stripe_payment_intent_id', 'created_at', 
                  'paid_at']
        read_only_fields = ['id', 'status', 'stripe_payment_intent_id', 'created_at', 'paid_at']


class RefundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Refund
        fields = ['id', 'payment', 'order', 'amount', 'reason', 'description', 
                  'status', 'created_at', 'processed_at']
        read_only_fields = ['id', 'status', 'created_at', 'processed_at']


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ['id', 'method_type', 'is_default', 'card_brand', 'card_last4', 
                  'card_exp_month', 'card_exp_year', 'created_at']
        read_only_fields = ['id', 'created_at']


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['id', 'transaction_type', 'amount', 'currency', 'description', 
                  'created_at']
        read_only_fields = ['id', 'created_at']


class CreatePaymentIntentSerializer(serializers.Serializer):
    order_id = serializers.UUIDField(required=True)
    payment_method_id = serializers.CharField(required=False)
    save_payment_method = serializers.BooleanField(default=False)


class ConfirmPaymentSerializer(serializers.Serializer):
    payment_intent_id = serializers.CharField(required=True)


class RefundRequestSerializer(serializers.Serializer):
    payment_id = serializers.UUIDField(required=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    reason = serializers.ChoiceField(choices=Refund.REASON_CHOICES)
    description = serializers.CharField(required=False, allow_blank=True)