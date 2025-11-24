from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import stripe
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY

@csrf_exempt
@require_POST
def stripe_webhook(request):
    """Handle Stripe webhooks"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Invalid payload
        logger.error(f"Invalid webhook payload: {e}")
        return JsonResponse({'error': 'Invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        logger.error(f"Invalid webhook signature: {e}")
        return JsonResponse({'error': 'Invalid signature'}, status=400)
    
    # Handle the event
    event_type = event.get('type')
    
    if event_type == 'payment_intent.succeeded':
        payment_intent = event.data.object
        handle_payment_intent_succeeded(payment_intent)
    
    elif event_type == 'payment_intent.payment_failed':
        payment_intent = event.data.object
        handle_payment_intent_failed(payment_intent)
    
    elif event_type == 'charge.refunded':
        charge = event.data.object
        handle_charge_refunded(charge)
    
    else:
        logger.info(f"Unhandled webhook event type: {event_type}")
    
    return JsonResponse({'status': 'success'})


def handle_payment_intent_succeeded(payment_intent):
    """Handle successful payment intent"""
    from apps.payments.models import Payment
    from django.utils import timezone
    from django.db import transaction
    
    try:
        payment = Payment.objects.get(stripe_payment_intent_id=payment_intent.id)
        
        with transaction.atomic():
            payment.status = 'succeeded'
            payment.paid_at = timezone.now()
            payment.stripe_charge_id = payment_intent.charges.data[0].id if payment_intent.charges.data else ''
            payment.save()
            
            # Update order
            order = payment.order
            order.payment_status = 'paid'
            order.status = 'processing'
            order.paid_at = timezone.now()
            order.save()
            
            # Create transaction log
            from apps.payments.models import Transaction
            Transaction.objects.create(
                payment=payment,
                transaction_type='charge',
                amount=payment.amount,
                external_transaction_id=payment_intent.id,
                description='Payment succeeded'
            )
            
            # Send confirmation email
            from apps.notifications.tasks import send_order_confirmation_email
            send_order_confirmation_email.delay(str(order.id))
            
        logger.info(f"Payment succeeded for order {order.order_number}")
        
    except Payment.DoesNotExist:
        logger.warning(f"Payment not found for payment_intent {payment_intent.id}")


def handle_payment_intent_failed(payment_intent):
    """Handle failed payment intent"""
    from apps.payments.models import Payment, Transaction
    
    try:
        payment = Payment.objects.get(stripe_payment_intent_id=payment_intent.id)
        
        failure_reason = 'Unknown error'
        if payment_intent.last_payment_error:
            failure_reason = payment_intent.last_payment_error.message
        
        payment.status = 'failed'
        payment.failure_reason = failure_reason
        payment.save()
        
        payment.order.payment_status = 'failed'
        payment.order.save()
        
        Transaction.objects.create(
            payment=payment,
            transaction_type='charge',
            amount=payment.amount,
            external_transaction_id=payment_intent.id,
            description=f'Payment failed: {failure_reason}'
        )
        
        logger.error(f"Payment failed for order {payment.order.order_number}: {failure_reason}")
        
    except Payment.DoesNotExist:
        logger.warning(f"Payment not found for payment_intent {payment_intent.id}")


def handle_charge_refunded(charge):
    """Handle refunded charge"""
    from apps.payments.models import Payment, Transaction
    
    try:
        payment = Payment.objects.get(stripe_charge_id=charge.id)
        payment.status = 'refunded'
        payment.save()
        
        Transaction.objects.create(
            payment=payment,
            transaction_type='refund',
            amount=payment.amount,
            external_transaction_id=charge.refunds.data[0].id if charge.refunds.data else charge.id,
            description='Payment refunded'
        )
        
        logger.info(f"Payment refunded for order {payment.order.order_number}")
        
    except Payment.DoesNotExist:
        logger.warning(f"Payment not found for charge {charge.id}")