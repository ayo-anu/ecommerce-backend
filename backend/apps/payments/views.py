import stripe
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.db import transaction as db_transaction
from .models import Payment, Refund, PaymentMethod, Transaction
from .serializers import (
    PaymentSerializer, RefundSerializer, PaymentMethodSerializer,
    TransactionSerializer, CreatePaymentIntentSerializer,
    ConfirmPaymentSerializer, RefundRequestSerializer
)
from apps.orders.models import Order

stripe.api_key = settings.STRIPE_SECRET_KEY


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """Payment management"""
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentSerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Payment.objects.all().select_related('order', 'user')
        return Payment.objects.filter(user=user).select_related('order')
    
    @action(detail=False, methods=['post'])
    def create_intent(self, request):
        """Create Stripe payment intent"""
        serializer = CreatePaymentIntentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        order_id = serializer.validated_data['order_id']
        payment_method_id = serializer.validated_data.get('payment_method_id')
        save_payment_method = serializer.validated_data.get('save_payment_method', False)
        
        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response(
                {'error': 'Order not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if order.payment_status == 'paid':
            return Response(
                {'error': 'Order already paid'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get or create Stripe customer
            customer_id = self._get_or_create_stripe_customer(request.user)
            
            # Create payment intent
            intent_params = {
                'amount': int(order.total * 100),  # cents
                'currency': 'usd',
                'metadata': {
                    'order_id': str(order.id),
                    'order_number': order.order_number,
                    'user_id': str(request.user.id) if request.user.is_authenticated else "guest",
                },
                'automatic_payment_methods': {'enabled': True,'allow_redirects': 'never'},
            }

            # Only attach Stripe customer if user has one
            if customer_id:
                intent_params['customer'] = customer_id

            # Optional features your logic already supports
            if payment_method_id:
                intent_params['payment_method'] = payment_method_id

            if save_payment_method:
                intent_params['setup_future_usage'] = 'off_session'

            intent = stripe.PaymentIntent.create(**intent_params)

            
            # Create payment record
            payment = Payment.objects.create(
                order=order,
                user=request.user,
                payment_method='card',
                amount=order.total,
                stripe_payment_intent_id=intent.id,
                stripe_customer_id=customer_id,
                status='pending'
            )
            
            # Create transaction log
            Transaction.objects.create(
                payment=payment,
                transaction_type='charge',
                amount=order.total,
                external_transaction_id=intent.id,
                description='Payment intent created'
            )
            
            return Response({
                'payment_id': payment.id,
                'client_secret': intent.client_secret,
                'payment_intent_id': intent.id
            })
        
        except stripe.error.StripeError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'])
    def confirm(self, request):
        """Confirm payment after client-side confirmation"""
        serializer = ConfirmPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        payment_intent_id = serializer.validated_data['payment_intent_id']
        
        try:
            payment = Payment.objects.get(stripe_payment_intent_id=payment_intent_id)
            
            # Retrieve payment intent from Stripe
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            if intent.status == 'succeeded':
                self._handle_successful_payment(payment, intent)
                return Response({'message': 'Payment confirmed successfully'})
            else:
                return Response(
                    {'error': f'Payment status: {intent.status}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        except Payment.DoesNotExist:
            return Response(
                {'error': 'Payment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except stripe.error.StripeError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def _get_or_create_stripe_customer(self, user):
        """Get or create Stripe customer for user"""
        # Check if user already has a Stripe customer ID
        existing_payment = Payment.objects.filter(
            user=user,
            stripe_customer_id__isnull=False
        ).first()
        
        if existing_payment:
            return existing_payment.stripe_customer_id
        
        # Create new Stripe customer
        customer = stripe.Customer.create(
            email=user.email,
            name=f"{user.first_name} {user.last_name}",
            metadata={'user_id': str(user.id)}
        )
        
        return customer.id

    def _handle_successful_payment(self, payment, intent):
        """Handle successful payment"""
        from django.utils import timezone
        
        with db_transaction.atomic():
            payment.status = 'succeeded'
            payment.paid_at = timezone.now()
            payment.stripe_charge_id = intent.charges.data[0].id if intent.charges.data else ''
            payment.save()
            
            # Update order
            order = payment.order
            order.payment_status = 'paid'
            order.status = 'processing'
            order.paid_at = timezone.now()
            order.save()

            from apps.orders.models import Cart, CartItem
            cart = Cart.objects.filter(user=order.user).first()
            if cart:
                CartItem.objects.filter(cart=cart).delete()

            
            # Create transaction log
            Transaction.objects.create(
                payment=payment,
                transaction_type='charge',
                amount=payment.amount,
                external_transaction_id=intent.id,
                description='Payment succeeded'
            )
            
            # Send confirmation email
            from apps.notifications.tasks import send_order_confirmation_email
            send_order_confirmation_email.delay(str(order.id))
    
    def _handle_payment_intent_succeeded(self, payment_intent):
        """Webhook: Handle successful payment intent"""
        try:
            payment = Payment.objects.get(stripe_payment_intent_id=payment_intent.id)
            self._handle_successful_payment(payment, payment_intent)
        except Payment.DoesNotExist:
            pass


    def _handle_payment_intent_failed(self, payment_intent):
        """Webhook: Handle failed payment intent"""
        try:
            payment = Payment.objects.get(stripe_payment_intent_id=payment_intent.id)
            payment.status = 'failed'
            payment.failure_reason = payment_intent.last_payment_error.message if payment_intent.last_payment_error else 'Unknown error'
            payment.save()
            
            payment.order.payment_status = 'failed'
            payment.order.save()
            
            Transaction.objects.create(
                payment=payment,
                transaction_type='charge',
                amount=payment.amount,
                external_transaction_id=payment_intent.id,
                description=f'Payment failed: {payment.failure_reason}'
            )
        except Payment.DoesNotExist:
            pass
    
    def _handle_charge_refunded(self, charge):
        """Webhook: Handle refunded charge"""
        try:
            payment = Payment.objects.get(stripe_charge_id=charge.id)
            payment.status = 'refunded'
            payment.save()
            
            Transaction.objects.create(
                payment=payment,
                transaction_type='refund',
                amount=payment.amount,
                external_transaction_id=charge.refunds.data[0].id,
                description='Payment refunded'
            )
        except Payment.DoesNotExist:
            pass


class RefundViewSet(viewsets.ModelViewSet):
    """Refund management"""
    permission_classes = [IsAuthenticated]
    serializer_class = RefundSerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Refund.objects.all().select_related('payment', 'order')
        return Refund.objects.filter(order__user=user).select_related('payment', 'order')
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return super().get_permissions()
    
    @action(detail=False, methods=['post'])
    def request_refund(self, request):
        """Customer request for refund"""
        serializer = RefundRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        payment_id = serializer.validated_data['payment_id']
        
        try:
            payment = Payment.objects.get(id=payment_id, user=request.user)
        except Payment.DoesNotExist:
            return Response(
                {'error': 'Payment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if payment.status != 'succeeded':
            return Response(
                {'error': 'Payment not eligible for refund'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create refund request
        refund = Refund.objects.create(
            payment=payment,
            order=payment.order,
            amount=serializer.validated_data.get('amount', payment.amount),
            reason=serializer.validated_data['reason'],
            description=serializer.validated_data.get('description', ''),
            status='pending'
        )
        
        # Notify admin
        from apps.notifications.tasks import send_email_task
        send_email_task.delay(
            recipient_email=settings.ADMIN_EMAIL,
            subject=f'Refund Request - Order #{payment.order.order_number}',
            html_content=f'<p>Customer requested refund for order #{payment.order.order_number}</p>',
            template_type='system'
        )
        
        return Response(
            RefundSerializer(refund).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def process(self, request, pk=None):
        """Admin: Process refund"""
        refund = self.get_object()
        
        if refund.status != 'pending':
            return Response(
                {'error': 'Refund already processed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Process refund with Stripe
            stripe_refund = stripe.Refund.create(
                payment_intent=refund.payment.stripe_payment_intent_id,
                amount=int(refund.amount * 100)
            )
            
            with db_transaction.atomic():
                refund.status = 'succeeded'
                refund.stripe_refund_id = stripe_refund.id
                refund.processed_by = request.user
                refund.processed_at = timezone.now()
                refund.save()
                
                # Update payment
                refund.payment.status = 'refunded'
                refund.payment.save()
                
                # Update order
                refund.order.status = 'refunded'
                refund.order.payment_status = 'refunded'
                refund.order.save()
                
                # Create transaction
                Transaction.objects.create(
                    payment=refund.payment,
                    transaction_type='refund',
                    amount=refund.amount,
                    external_transaction_id=stripe_refund.id,
                    description=f'Refund processed: {refund.reason}'
                )
            
            # Send notification
            from apps.notifications.tasks import send_email_task
            send_email_task.delay(
                recipient_email=refund.order.shipping_email,
                subject=f'Refund Processed - Order #{refund.order.order_number}',
                html_content=f'<p>Your refund of ${refund.amount} has been processed.</p>',
                template_type='system'
            )
            
            return Response({'message': 'Refund processed successfully'})
        
        except stripe.error.StripeError as e:
            refund.status = 'failed'
            refund.save()
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class PaymentMethodViewSet(viewsets.ModelViewSet):
    """Saved payment methods"""
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentMethodSerializer
    
    def get_queryset(self):
        return PaymentMethod.objects.filter(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """Set payment method as default"""
        payment_method = self.get_object()
        
        PaymentMethod.objects.filter(user=request.user, is_default=True).update(is_default=False)
        payment_method.is_default = True
        payment_method.save()
        
        return Response({'message': 'Payment method set as default'})