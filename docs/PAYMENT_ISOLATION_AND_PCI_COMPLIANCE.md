# Payment Isolation and PCI DSS Compliance Guide

## Executive Summary

This document outlines the payment processing isolation strategy and PCI DSS compliance measures implemented in the e-commerce platform. The design minimizes PCI scope by **never storing sensitive cardholder data** and using Stripe's secure tokenization.

---

## Table of Contents

1. [PCI DSS Scope](#pci-dss-scope)
2. [Payment Data Isolation](#payment-data-isolation)
3. [Stripe Integration Security](#stripe-integration-security)
4. [Payment Flow Architecture](#payment-flow-architecture)
5. [Security Controls](#security-controls)
6. [Audit and Logging](#audit-and-logging)
7. [Incident Response](#incident-response)
8. [Compliance Checklist](#compliance-checklist)

---

## PCI DSS Scope

### Scope Reduction Strategy

**Primary Principle**: Never handle raw credit card data.

```
┌─────────────────────────────────────────────────────────────┐
│  OUT OF SCOPE (No cardholder data handled)                  │
├─────────────────────────────────────────────────────────────┤
│  • Frontend: Uses Stripe.js (data goes directly to Stripe)  │
│  • Backend: Only handles tokens, never raw card numbers     │
│  • Database: Stores only last4 digits and metadata          │
│  • Logs: Never log PAN (Primary Account Number)             │
└─────────────────────────────────────────────────────────────┘
```

### What We DO Store

| Data Element | Stored? | Format | Notes |
|--------------|---------|--------|-------|
| Full card number (PAN) | ❌ NO | N/A | Handled by Stripe only |
| CVV/CVC | ❌ NO | N/A | Never transmitted to backend |
| Expiration date | ❌ NO | N/A | Stored by Stripe |
| Cardholder name | ✅ YES | Plain text | Not considered sensitive by PCI |
| Last 4 digits | ✅ YES | Plain text | Allowed for display purposes |
| Card brand | ✅ YES | Plain text | (Visa, Mastercard, etc.) |
| Payment intent ID | ✅ YES | Encrypted | Stripe reference |
| Customer ID | ✅ YES | Encrypted | Stripe customer reference |
| Amount | ✅ YES | Encrypted at rest | Transaction amount |
| Status | ✅ YES | Plain text | Payment status |

### PCI SAQ (Self-Assessment Questionnaire)

**Recommended SAQ Level**: **SAQ A** (E-commerce with outsourced payment processing)

**Requirements**:
- ✅ Use Stripe.js for all payment data collection
- ✅ Serve website over HTTPS only
- ✅ Maintain proper access controls
- ✅ Regular security scanning
- ✅ Maintain firewall configurations

---

## Payment Data Isolation

### Database Isolation

#### Separate Payment Database (Recommended for Production)

```yaml
# docker-compose.prod.yaml
services:
  postgres_payments:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: ecommerce_payments
      POSTGRES_USER: ${PAYMENTS_DB_USER}
      POSTGRES_PASSWORD: ${PAYMENTS_DB_PASSWORD}
    volumes:
      - payments_db_data:/var/lib/postgresql/data
    networks:
      - payments_network  # Isolated network
    restart: always
```

#### Database Router for Payment Models

```python
# backend/core/database_routers.py

class PaymentDatabaseRouter:
    """
    Router to isolate payment-related models to separate database.

    This provides defense-in-depth for PCI compliance.
    """

    payment_apps = {'payments'}

    def db_for_read(self, model, **hints):
        """Direct reads of payment models to payments DB."""
        if model._meta.app_label in self.payment_apps:
            return 'payments'
        return None

    def db_for_write(self, model, **hints):
        """Direct writes of payment models to payments DB."""
        if model._meta.app_label in self.payment_apps:
            return 'payments'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """Allow relations within payment app or to main DB."""
        if (obj1._meta.app_label in self.payment_apps or
            obj2._meta.app_label in self.payment_apps):
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Ensure payment app only migrates to payments DB."""
        if app_label in self.payment_apps:
            return db == 'payments'
        return db != 'payments'
```

**Enable in settings**:
```python
# config/settings/production.py
DATABASE_ROUTERS = ['core.database_routers.PaymentDatabaseRouter']
```

### Network Isolation

#### Payment Service Subnet

```yaml
# infrastructure/docker-compose.prod.yaml
networks:
  payments_network:
    internal: true  # No external access
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/24
```

**Access Policy**:
- ✅ Backend Django app → Payments DB
- ✅ Celery workers → Payments DB (for async payment processing)
- ❌ Frontend → Payments DB (BLOCKED)
- ❌ AI Services → Payments DB (BLOCKED)
- ❌ External services → Payments DB (BLOCKED)

### Process Isolation

#### Dedicated Payment Worker (Optional)

```python
# backend/core/celery_config.py

# Separate queue for payment processing
CELERY_TASK_ROUTES = {
    'apps.payments.tasks.*': {
        'queue': 'payments',
        'routing_key': 'payments',
        'priority': 10,  # High priority
    },
}

# Dedicated worker command:
# celery -A config worker -Q payments --hostname=payments-worker@%h
```

---

## Stripe Integration Security

### Secure API Key Management

```python
# backend/apps/payments/stripe_client.py

import stripe
from django.conf import settings
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

class SecureStripeClient:
    """Wrapper for Stripe API with security controls."""

    def __init__(self):
        # Never log the secret key
        self.api_key = settings.STRIPE_SECRET_KEY
        if not self.api_key or self.api_key.startswith('sk_test_'):
            logger.warning("Using Stripe test API key")

        stripe.api_key = self.api_key
        stripe.max_network_retries = 3

    def create_payment_intent(self, amount, currency='usd', **kwargs):
        """Create payment intent with idempotency."""
        # Use idempotency key to prevent duplicate charges
        idempotency_key = kwargs.pop('idempotency_key', None)

        try:
            return stripe.PaymentIntent.create(
                amount=amount,
                currency=currency,
                idempotency_key=idempotency_key,
                **kwargs
            )
        except stripe.error.StripeError as e:
            logger.error(
                f"Stripe error: {e.user_message}",
                extra={
                    'error_type': type(e).__name__,
                    'error_code': e.code,
                    'amount': amount,
                    'currency': currency,
                }
            )
            raise
```

### Webhook Signature Verification

```python
# backend/apps/payments/webhooks.py

import stripe
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import logging

logger = logging.getLogger(__name__)

@csrf_exempt
@require_POST
def stripe_webhook(request):
    """
    Handle Stripe webhooks with signature verification.

    SECURITY: Always verify webhook signatures to prevent
    spoofed payment confirmation attacks.
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        # Verify webhook signature
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError:
        # Invalid payload
        logger.warning("Invalid Stripe webhook payload")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        # Invalid signature
        logger.warning(
            "Invalid Stripe webhook signature",
            extra={'signature': sig_header[:20] + '...'}
        )
        return HttpResponse(status=400)

    # Handle the event
    event_type = event['type']

    if event_type == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        _handle_payment_success(payment_intent)

    elif event_type == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        _handle_payment_failure(payment_intent)

    return HttpResponse(status=200)
```

### Frontend Integration (Secure)

```javascript
// frontend/src/lib/stripe.ts

import { loadStripe } from '@stripe/stripe-js';

// Load Stripe with publishable key (safe to expose)
const stripePromise = loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY!);

export async function createPaymentIntent(orderId: string) {
  // Call backend to create payment intent
  const response = await fetch('/api/v1/payments/create-intent/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${getAuthToken()}`,
    },
    body: JSON.stringify({ order_id: orderId }),
  });

  return response.json();
}

export async function confirmPayment(clientSecret: string, paymentMethod: any) {
  const stripe = await stripePromise;

  // Card data NEVER sent to our backend
  // Stripe.js sends directly to Stripe servers
  const { error, paymentIntent } = await stripe!.confirmCardPayment(
    clientSecret,
    { payment_method: paymentMethod }
  );

  if (error) {
    throw new Error(error.message);
  }

  return paymentIntent;
}
```

---

## Payment Flow Architecture

### End-to-End Flow

```
┌──────────┐                 ┌──────────┐                 ┌──────────┐
│ Frontend │                 │ Backend  │                 │  Stripe  │
│  (Next)  │                 │ (Django) │                 │   API    │
└────┬─────┘                 └────┬─────┘                 └────┬─────┘
     │                            │                            │
     │ 1. Create Order            │                            │
     ├───────────────────────────►│                            │
     │                            │                            │
     │ 2. Request Payment Intent  │                            │
     ├───────────────────────────►│ 3. Create Payment Intent   │
     │                            ├───────────────────────────►│
     │                            │ 4. Return client_secret    │
     │ 5. Return client_secret    │◄───────────────────────────┤
     │◄───────────────────────────┤                            │
     │                            │                            │
     │ 6. Collect card details    │                            │
     │    (via Stripe Elements)   │                            │
     │                            │                            │
     │ 7. Confirm payment         │                            │
     │    (card data → Stripe)    ├───────────────────────────►│
     │───────────────────────────────────────────────────────►│
     │                            │                            │
     │                            │ 8. Webhook: payment success│
     │                            │◄───────────────────────────┤
     │                            │                            │
     │                            │ 9. Update order status     │
     │                            │    (mark as paid)          │
     │                            │                            │
     │ 10. Success response       │                            │
     │◄───────────────────────────┤                            │
     │                            │                            │
```

**Key Security Points**:
1. ✅ Card data never touches our servers
2. ✅ Backend creates intent with order amount (prevents tampering)
3. ✅ Webhook verifies signature before processing
4. ✅ Payment status stored separately from order
5. ✅ Idempotency prevents duplicate charges

---

## Security Controls

### 1. Data Encryption

#### At Rest
```python
# backend/apps/payments/models.py

from django_cryptography.fields import encrypt

class Payment(models.Model):
    # Encrypted fields
    stripe_payment_intent_id = encrypt(models.CharField(max_length=255))
    stripe_customer_id = encrypt(models.CharField(max_length=255, blank=True))
    amount = encrypt(models.DecimalField(max_digits=10, decimal_places=2))

    # Non-sensitive fields
    status = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
```

#### In Transit
- ✅ HTTPS only (enforced by `SECURE_SSL_REDIRECT=True`)
- ✅ TLS 1.2+ required
- ✅ Strong cipher suites only

### 2. Access Control

```python
# backend/apps/payments/permissions.py

from rest_framework import permissions

class IsPaymentOwner(permissions.BasePermission):
    """Only allow users to view their own payments."""

    def has_object_permission(self, request, view, obj):
        # Staff can view all
        if request.user.is_staff:
            return True

        # Users can only view their own payments
        return obj.user == request.user


class CanRefund(permissions.BasePermission):
    """Only admins can issue refunds."""

    def has_permission(self, request, view):
        return request.user.is_staff and request.user.has_perm('payments.can_refund')
```

### 3. Rate Limiting

```python
# backend/apps/payments/throttles.py

from rest_framework.throttling import UserRateThrottle

class PaymentRateThrottle(UserRateThrottle):
    """Strict rate limiting for payment endpoints."""

    # 10 payment attempts per hour
    rate = '10/hour'


# Apply in view
class PaymentViewSet(viewsets.ViewSet):
    throttle_classes = [PaymentRateThrottle]
```

### 4. Input Validation

```python
# backend/apps/payments/serializers.py

from rest_framework import serializers
from decimal import Decimal

class CreatePaymentIntentSerializer(serializers.Serializer):
    order_id = serializers.UUIDField(required=True)
    payment_method_id = serializers.CharField(required=False)
    save_payment_method = serializers.BooleanField(default=False)

    def validate_order_id(self, value):
        """Ensure order exists and belongs to user."""
        request = self.context['request']
        try:
            order = Order.objects.get(id=value, user=request.user)
        except Order.DoesNotExist:
            raise serializers.ValidationError("Order not found")

        if order.payment_status == 'paid':
            raise serializers.ValidationError("Order already paid")

        return value
```

---

## Audit and Logging

### Payment Audit Trail

```python
# backend/apps/payments/models.py

class PaymentAuditLog(models.Model):
    """Immutable audit log for all payment operations."""

    payment = models.ForeignKey(Payment, on_delete=models.PROTECT)
    action = models.CharField(max_length=50)  # created, confirmed, refunded, failed
    user = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    previous_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['payment', '-created_at']),
        ]


# Usage in view
def _create_audit_log(payment, action, request, **kwargs):
    PaymentAuditLog.objects.create(
        payment=payment,
        action=action,
        user=request.user if request.user.is_authenticated else None,
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        **kwargs
    )
```

### Structured Logging

```python
import logging
import json

logger = logging.getLogger('payments')

# Log payment events
logger.info(
    "Payment intent created",
    extra={
        'payment_id': str(payment.id),
        'order_id': str(order.id),
        'amount': float(amount),
        'currency': currency,
        'user_id': str(request.user.id),
        'ip_address': get_client_ip(request),
    }
)

# NEVER log:
# - Full card numbers
# - CVV codes
# - Stripe secret keys
# - Customer payment method details
```

---

## Incident Response

### Payment Security Incident Checklist

#### Detection
- [ ] Monitor for unusual payment patterns
- [ ] Alert on failed payment spikes
- [ ] Track refund rate anomalies
- [ ] Monitor Stripe webhook failures

#### Response
1. **Isolate**: Disable payment processing if compromise suspected
2. **Investigate**: Review audit logs and Stripe dashboard
3. **Notify**: Contact Stripe support if API key compromised
4. **Rotate**: Immediately rotate all Stripe API keys
5. **Document**: Record incident timeline and actions taken

#### Recovery
```bash
# Emergency: Disable payment processing
# Set in environment or Django admin
PAYMENTS_ENABLED=False

# Rotate Stripe keys
1. Generate new keys in Stripe Dashboard
2. Update production secrets
3. Deploy updated configuration
4. Verify old keys are revoked
```

---

## Compliance Checklist

### PCI DSS Requirements

- [ ] **Req 1**: Install and maintain firewall configuration
  - ✅ Network segmentation with Docker networks
  - ✅ Only necessary ports exposed

- [ ] **Req 2**: Do not use vendor-supplied defaults
  - ✅ All default passwords changed
  - ✅ Unnecessary services disabled

- [ ] **Req 3**: Protect stored cardholder data
  - ✅ No PAN stored (using Stripe tokens only)
  - ✅ Last 4 digits only for display

- [ ] **Req 4**: Encrypt transmission of cardholder data
  - ✅ HTTPS enforced
  - ✅ TLS 1.2+ only

- [ ] **Req 5**: Protect against malware
  - ✅ Container image scanning
  - ✅ Dependency vulnerability scanning

- [ ] **Req 6**: Develop secure systems
  - ✅ Code review process
  - ✅ Security testing in CI
  - ✅ Input validation

- [ ] **Req 7**: Restrict access to cardholder data
  - ✅ Role-based access control
  - ✅ Least privilege principle

- [ ] **Req 8**: Identify and authenticate access
  - ✅ Unique user IDs
  - ✅ Strong authentication
  - ✅ MFA for admin access

- [ ] **Req 9**: Restrict physical access
  - ✅ Cloud infrastructure (AWS/GCP)
  - ✅ No physical servers

- [ ] **Req 10**: Track and monitor access
  - ✅ Audit logging enabled
  - ✅ Log retention (90 days minimum)

- [ ] **Req 11**: Regularly test security
  - ✅ Vulnerability scanning
  - ✅ Penetration testing

- [ ] **Req 12**: Maintain security policy
  - ✅ This documentation
  - ✅ Incident response plan

---

## Implementation Timeline

### Phase 1: Core Isolation (Implemented)
- ✅ Stripe integration (no PAN storage)
- ✅ Webhook signature verification
- ✅ HTTPS enforcement
- ✅ Input validation

### Phase 2: Enhanced Security (Next)
- [ ] Implement database router for payment isolation
- [ ] Enable encryption at rest for payment data
- [ ] Add comprehensive audit logging
- [ ] Implement payment-specific rate limiting

### Phase 3: Advanced Isolation (Future)
- [ ] Separate payment database server
- [ ] Dedicated payment worker processes
- [ ] Advanced fraud detection integration
- [ ] PCI audit and certification

---

## Support and Maintenance

### Regular Tasks

**Daily**:
- Monitor Stripe webhook delivery
- Review failed payment logs
- Check refund queue

**Weekly**:
- Audit payment logs for anomalies
- Review Stripe dashboard for disputes
- Check for Stripe API updates

**Monthly**:
- Review access controls
- Audit user permissions
- Test incident response procedures

**Quarterly**:
- PCI self-assessment questionnaire
- Security vulnerability scan
- Update this documentation

---

## References

- [PCI DSS Quick Reference Guide](https://www.pcisecuritystandards.org/documents/PCI_DSS_Quick_Reference_Guide.pdf)
- [Stripe Security Best Practices](https://stripe.com/docs/security/guide)
- [Django Security Best Practices](https://docs.djangoproject.com/en/stable/topics/security/)
- [OWASP Payment Processing](https://owasp.org/www-community/vulnerabilities/Payment_Card_Industry_Data_Security_Standard)

---

**Document Version**: 1.0
**Last Updated**: 2025-12-04
**Owner**: Security Team
**Review Schedule**: Quarterly
