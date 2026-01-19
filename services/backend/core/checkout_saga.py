"""Checkout saga flow and compensation steps."""

import logging
from typing import Dict, Any
from decimal import Decimal
from django.db import transaction as db_transaction
from django.utils import timezone

from .saga import SagaOrchestrator, SagaContext, saga_registry
from .ai_clients import fraud_client
from .tracing import get_tracer, add_span_attributes, record_exception

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


class CheckoutSaga:
    """Checkout saga orchestrator."""

    @staticmethod
    def execute(checkout_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run the checkout saga."""
        saga = SagaOrchestrator()
        saga_registry.register(saga)

        if tracer:
            with tracer.start_as_current_span("checkout_saga") as span:
                add_span_attributes(
                    user_id=checkout_data.get('user_id'),
                    cart_id=checkout_data.get('cart_id'),
                    payment_method=checkout_data.get('payment_method'),
                    saga_id=str(saga.saga_id)
                )
                return CheckoutSaga._execute_with_tracing(saga, checkout_data, span)
        else:
            return CheckoutSaga._execute_with_tracing(saga, checkout_data, None)

    @staticmethod
    def _execute_with_tracing(saga, checkout_data, parent_span):
        """Execute saga with optional tracing."""
        saga.add_step(
            name="create_order",
            action=CheckoutSteps.create_order,
            compensate=CheckoutCompensations.delete_order,
            timeout=10.0,
            max_retries=1,
            idempotent=False,
        )

        saga.add_step(
            name="reserve_inventory",
            action=CheckoutSteps.reserve_inventory,
            compensate=CheckoutCompensations.release_inventory,
            timeout=15.0,
            max_retries=3,
            idempotent=True,
        )

        saga.add_step(
            name="check_fraud",
            action=CheckoutSteps.check_fraud,
            compensate=None,
            timeout=10.0,
            max_retries=2,
            idempotent=True,
        )

        saga.add_step(
            name="process_payment",
            action=CheckoutSteps.process_payment,
            compensate=CheckoutCompensations.refund_payment,
            timeout=30.0,
            max_retries=2,
            idempotent=True,
        )

        saga.add_step(
            name="confirm_order",
            action=CheckoutSteps.confirm_order,
            compensate=CheckoutCompensations.cancel_order,
            timeout=10.0,
            max_retries=3,
            idempotent=True,
        )

        return saga.execute(initial_data=checkout_data)


class CheckoutSteps:
    """Saga steps."""

    @staticmethod
    @db_transaction.atomic
    def create_order(context: SagaContext) -> Dict[str, Any]:
        """Create a pending order."""
        from apps.orders.models import Order, OrderItem, Cart

        logger.info(f"[Saga {context.saga_id}] Creating order")

        cart = Cart.objects.select_for_update().get(
            id=context.data['cart_id']
        )

        if not cart.items.exists():
            raise ValueError("Cart is empty")

        subtotal = sum(
            item.product.price * item.quantity
            for item in cart.items.select_related('product')
        )

        tax = subtotal * Decimal('0.10')

        shipping_cost = Decimal('10.00') if subtotal < 100 else Decimal('0.00')

        total = subtotal + tax + shipping_cost

        shipping_addr = context.data['shipping_address']

        order = Order.objects.create(
            user_id=context.data['user_id'],
            status='pending',
            payment_status='pending',
            subtotal=subtotal,
            tax=tax,
            shipping_cost=shipping_cost,
            total=total,
            shipping_name=shipping_addr.get('name', ''),
            shipping_email=shipping_addr.get('email', ''),
            shipping_phone=shipping_addr.get('phone', ''),
            shipping_address_line1=shipping_addr.get('address_line1', ''),
            shipping_address_line2=shipping_addr.get('address_line2', ''),
            shipping_city=shipping_addr.get('city', ''),
            shipping_state=shipping_addr.get('state', ''),
            shipping_country=shipping_addr.get('country', 'US'),
            shipping_postal_code=shipping_addr.get('postal_code', ''),
            customer_notes=context.data.get('customer_notes', ''),
        )

        # Create order items
        for cart_item in cart.items.select_related('product', 'variant'):
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                variant=cart_item.variant,
                product_name=cart_item.product.name,
                product_sku=cart_item.product.sku,
                variant_name=cart_item.variant.name if cart_item.variant else '',
                quantity=cart_item.quantity,
                price=cart_item.product.price,
                total=cart_item.product.price * cart_item.quantity,
            )

        logger.info(
            f"[Saga {context.saga_id}] Order {order.order_number} created",
            extra={'order_id': str(order.id), 'total': float(total)}
        )

        return {
            'order_id': str(order.id),
            'order_number': order.order_number,
            'total': float(total),
            'items_count': cart.items.count(),
        }

    @staticmethod
    @db_transaction.atomic
    def reserve_inventory(context: SagaContext) -> Dict[str, Any]:
        """Reserve inventory for the order."""
        from apps.orders.models import Order
        from apps.products.models import Product

        logger.info(f"[Saga {context.saga_id}] Reserving inventory")

        order_id = context.get_result('create_order')['order_id']
        order = Order.objects.select_for_update().get(id=order_id)

        reservations = []

        for item in order.items.select_related('product'):
            product = Product.objects.select_for_update().get(id=item.product.id)

            if product.track_inventory:
                if product.stock_quantity < item.quantity:
                    raise ValueError(
                        f"Insufficient stock for {product.name}. "
                        f"Available: {product.stock_quantity}, Required: {item.quantity}"
                    )

                product.stock_quantity -= item.quantity
                product.save(update_fields=['stock_quantity'])

                reservations.append({
                    'product_id': str(product.id),
                    'product_name': product.name,
                    'quantity_reserved': item.quantity,
                    'remaining_stock': product.stock_quantity,
                })

                logger.info(
                    f"[Saga {context.saga_id}] Reserved {item.quantity} units of {product.name}",
                    extra={'product_id': str(product.id), 'quantity': item.quantity}
                )

        return {
            'reservations': reservations,
            'total_items_reserved': len(reservations),
        }

    @staticmethod
    def check_fraud(context: SagaContext) -> Dict[str, Any]:
        """Check fraud risk for the order."""
        logger.info(f"[Saga {context.saga_id}] Checking fraud")

        order_result = context.get_result('create_order')

        transaction_data = {
            'user_id': context.data['user_id'],
            'amount': order_result['total'],
            'payment_method': context.data['payment_method'],
            'order_id': order_result['order_id'],
        }

        fraud_result = fraud_client.analyze_transaction(transaction_data)

        if fraud_result:
            risk_score = fraud_result.get('risk_score', 0)
            action = fraud_result.get('action', 'approve')

            logger.info(
                f"[Saga {context.saga_id}] Fraud check result: {action}, risk_score: {risk_score}",
                extra={'risk_score': risk_score, 'action': action}
            )

            if action == 'reject' or risk_score >= 0.9:
                raise ValueError(
                    f"Transaction rejected due to high fraud risk (score: {risk_score})"
                )

            return {
                'risk_score': risk_score,
                'action': action,
                'risk_factors': fraud_result.get('risk_factors', []),
            }

        logger.warning(f"[Saga {context.saga_id}] Fraud check unavailable, proceeding with caution")
        return {
            'risk_score': 0.5,
            'action': 'review',
            'note': 'Fraud service unavailable',
        }

    @staticmethod
    @db_transaction.atomic
    def process_payment(context: SagaContext) -> Dict[str, Any]:
        """Process payment via Stripe."""
        from apps.payments.models import Payment
        from apps.orders.models import Order
        import stripe
        from django.conf import settings

        logger.info(f"[Saga {context.saga_id}] Processing payment")

        order_result = context.get_result('create_order')
        order = Order.objects.get(id=order_result['order_id'])

        payment = Payment.objects.create(
            order=order,
            user_id=context.data['user_id'],
            payment_method=context.data['payment_method'],
            amount=order.total,
            status='processing',
        )

        try:
            stripe.api_key = settings.STRIPE_SECRET_KEY

            intent = stripe.PaymentIntent.create(
                amount=int(order.total * 100),  # Convert to cents
                currency='usd',
                payment_method=context.data.get('payment_method_id'),
                confirm=True,
                metadata={
                    'order_id': str(order.id),
                    'order_number': order.order_number,
                    'saga_id': context.saga_id,
                },
            )

            payment.stripe_payment_intent_id = intent.id
            payment.status = 'succeeded'
            payment.paid_at = timezone.now()
            payment.save()

            order.payment_status = 'paid'
            order.paid_at = timezone.now()
            order.save(update_fields=['payment_status', 'paid_at'])

            logger.info(
                f"[Saga {context.saga_id}] Payment processed successfully",
                extra={'payment_id': str(payment.id), 'stripe_intent': intent.id}
            )

            return {
                'payment_id': str(payment.id),
                'stripe_payment_intent_id': intent.id,
                'amount': float(payment.amount),
                'status': 'succeeded',
            }

        except stripe.error.CardError as e:
            payment.status = 'failed'
            payment.failure_reason = str(e)
            payment.save()

            logger.error(
                f"[Saga {context.saga_id}] Payment failed: {e}",
                extra={'payment_id': str(payment.id)}
            )

            raise ValueError(f"Payment failed: {e.user_message}")

        except Exception as e:
            payment.status = 'failed'
            payment.failure_reason = str(e)
            payment.save()

            logger.error(
                f"[Saga {context.saga_id}] Payment processing error: {e}",
                extra={'payment_id': str(payment.id)},
                exc_info=True
            )

            raise

    @staticmethod
    @db_transaction.atomic
    def confirm_order(context: SagaContext) -> Dict[str, Any]:
        """Mark the order as processing and clear the cart."""
        from apps.orders.models import Order, Cart

        logger.info(f"[Saga {context.saga_id}] Confirming order")

        order_result = context.get_result('create_order')
        order = Order.objects.get(id=order_result['order_id'])

        order.status = 'processing'
        order.save(update_fields=['status'])

        cart = Cart.objects.get(id=context.data['cart_id'])
        cart.items.all().delete()

        logger.info(
            f"[Saga {context.saga_id}] Order {order.order_number} confirmed",
            extra={'order_id': str(order.id), 'order_number': order.order_number}
        )

        return {
            'order_id': str(order.id),
            'order_number': order.order_number,
            'status': order.status,
        }


class CheckoutCompensations:
    """Compensation steps."""

    @staticmethod
    @db_transaction.atomic
    def delete_order(context: SagaContext):
        """Delete the order."""
        from apps.orders.models import Order

        logger.warning(f"[Saga {context.saga_id}] COMPENSATING: Deleting order")

        order_result = context.get_result('create_order')
        if order_result:
            order_id = order_result['order_id']
            try:
                order = Order.objects.get(id=order_id)
                order.status = 'cancelled'
                order.admin_notes = f"Cancelled by saga compensation (saga_id: {context.saga_id})"
                order.save()

                logger.info(f"[Saga {context.saga_id}] Order cancelled")
            except Order.DoesNotExist:
                logger.warning(f"[Saga {context.saga_id}] Order not found for deletion")

    @staticmethod
    @db_transaction.atomic
    def release_inventory(context: SagaContext):
        """Release reserved inventory."""
        from apps.orders.models import Order
        from apps.products.models import Product

        logger.warning(f"[Saga {context.saga_id}] COMPENSATING: Releasing inventory")

        order_result = context.get_result('create_order')
        if order_result:
            order_id = order_result['order_id']
            try:
                order = Order.objects.get(id=order_id)

                for item in order.items.select_related('product'):
                    product = Product.objects.select_for_update().get(id=item.product.id)

                    if product.track_inventory:
                        product.stock_quantity += item.quantity
                        product.save(update_fields=['stock_quantity'])

                        logger.info(
                            f"[Saga {context.saga_id}] Released {item.quantity} units of {product.name}"
                        )

            except Order.DoesNotExist:
                logger.warning(f"[Saga {context.saga_id}] Order not found for inventory release")

    @staticmethod
    @db_transaction.atomic
    def refund_payment(context: SagaContext):
        """Refund the payment."""
        from apps.payments.models import Payment, Refund
        import stripe
        from django.conf import settings

        logger.warning(f"[Saga {context.saga_id}] COMPENSATING: Refunding payment")

        payment_result = context.get_result('process_payment')
        if payment_result:
            payment_id = payment_result['payment_id']
            try:
                payment = Payment.objects.get(id=payment_id)

                if payment.status == 'succeeded' and payment.stripe_payment_intent_id:
                    stripe.api_key = settings.STRIPE_SECRET_KEY

                    refund = stripe.Refund.create(
                        payment_intent=payment.stripe_payment_intent_id,
                        reason='requested_by_customer',
                    )

                    Refund.objects.create(
                        payment=payment,
                        order=payment.order,
                        amount=payment.amount,
                        reason='other',
                        description=f'Saga compensation (saga_id: {context.saga_id})',
                        status='succeeded',
                        stripe_refund_id=refund.id,
                        processed_at=timezone.now(),
                    )

                    payment.status = 'refunded'
                    payment.save()

                    logger.info(f"[Saga {context.saga_id}] Payment refunded")

            except Payment.DoesNotExist:
                logger.warning(f"[Saga {context.saga_id}] Payment not found for refund")
            except Exception as e:
                logger.error(
                    f"[Saga {context.saga_id}] Refund failed: {e}",
                    exc_info=True
                )

    @staticmethod
    @db_transaction.atomic
    def cancel_order(context: SagaContext):
        """Cancel the order."""
        from apps.orders.models import Order

        logger.warning(f"[Saga {context.saga_id}] COMPENSATING: Cancelling order")

        order_result = context.get_result('create_order')
        if order_result:
            order_id = order_result['order_id']
            try:
                order = Order.objects.get(id=order_id)
                order.status = 'cancelled'
                order.admin_notes = f"Cancelled by saga compensation (saga_id: {context.saga_id})"
                order.save()

                logger.info(f"[Saga {context.saga_id}] Order cancelled")
            except Order.DoesNotExist:
                logger.warning(f"[Saga {context.saga_id}] Order not found for cancellation")
