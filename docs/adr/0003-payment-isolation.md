# 3. Payment Data Isolation Strategy

Date: 2025-12-04

## Status

Accepted

## Context

We handle payment processing and need to comply with PCI DSS (Payment Card Industry Data Security Standard). The key question: How should we isolate payment data to minimize PCI compliance scope?

Regulatory requirements:
- PCI DSS SAQ (Self-Assessment Questionnaire) compliance
- Minimize cardholder data exposure
- Isolate payment processing from other systems

## Decision

Implement **multi-layer payment isolation**:

1. **Never Store Card Data**: Use Stripe tokenization (card data never touches our servers)
2. **Database Isolation**: Separate payment models to dedicated database (optional router)
3. **Network Isolation**: Payment services on isolated network segment
4. **Code Isolation**: Payment logic in dedicated modules with restricted imports

### Architecture

```
┌──────────────┐
│   Frontend   │
│  (Stripe.js) │  ← Card data goes directly to Stripe
└──────┬───────┘
       │ (only tokens pass through)
       ▼
┌──────────────┐
│   Backend    │  ← Only receives/stores tokens
│   (Django)   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Payments DB  │  ← Isolated database (optional)
│  (tokenized) │
└──────────────┘
```

## Consequences

### Positive

- **Reduced PCI Scope**: SAQ-A (lowest compliance level)
- **Security**: Payment data isolated from application data
- **Blast Radius**: Compromise of main DB doesn't expose payment data
- **Compliance**: Easier audits and compliance verification
- **Separate Backups**: Different retention policies for payment data

### Negative

- **Database Cost**: Optional separate database adds infrastructure cost
- **Query Complexity**: Cross-database joins require application-level logic
- **Development Overhead**: Developers must understand payment boundaries

### Neutral

- **Documentation Required**: Clear guidelines for payment data handling
- **Code Review Focus**: Payment code requires extra scrutiny

## Implementation

### Phase 1: Never Store PAN (Completed)

- ✅ Stripe integration using tokenization
- ✅ Only store: `last4`, `brand`, `exp_month`, `exp_year`
- ✅ Webhook signature verification
- ✅ No card data in logs

### Phase 2: Code Isolation (Completed)

- ✅ Payment models in `backend/apps/payments/`
- ✅ Clear API boundaries
- ✅ Database router created (`backend/core/database_routers.py`)

### Phase 3: Documentation (Completed)

- ✅ PCI compliance guide (`docs/PAYMENT_ISOLATION_AND_PCI_COMPLIANCE.md`)
- ✅ Payment security tests
- ✅ Incident response procedures

### Phase 4: Database Isolation (Optional - Future)

- [ ] Deploy separate PostgreSQL instance for payments
- [ ] Configure database router in production
- [ ] Test cross-database operations

## Design Decisions

### Why Stripe vs Building In-House?

**Stripe chosen** because:
- PCI compliance handled by Stripe
- Battle-tested security
- Reduces our liability
- Lower development cost

### Why Optional Database Isolation?

- **Required for**: Large enterprises, high security requirements
- **Optional for**: Startups, MVP phase
- **Our approach**: Implement router, activate when needed

### Why Not Separate Microservice?

Considered but **rejected** for now because:
- Additional operational complexity
- Current scale doesn't warrant it
- Can extract later if needed

## Alternatives Considered

### Store Encrypted Card Data

**Rejected** because:
- Still in PCI scope
- Key management complexity
- Higher compliance requirements
- Stripe tokenization is better

### Separate Payment Microservice

**Deferred** because:
- Overkill for current scale
- Would complicate development
- Can extract later if needed

### No Isolation (Status Quo)

**Rejected** because:
- Security risk
- Compliance risk
- Larger blast radius

## Migration Path

Current state → Goal state:

1. ✅ Stripe integration with tokenization
2. ✅ Payment models grouped in single app
3. ✅ Database router implemented (not yet activated)
4. [ ] Optional: Deploy separate payment database in production
5. [ ] Optional: Extract to microservice if scale requires

## Compliance Checklist

- [x] No PAN stored
- [x] No CVV stored
- [x] Webhook signatures verified
- [x] TLS/HTTPS enforced
- [x] Access controls on payment data
- [x] Audit logging
- [ ] Annual PCI SAQ completion
- [ ] Quarterly vulnerability scans

## References

- [PCI DSS Quick Reference Guide](https://www.pcisecuritystandards.org/)
- [Stripe Security Best Practices](https://stripe.com/docs/security/guide)
- [SAQ A Requirements](https://www.pcisecuritystandards.org/documents/SAQ_A_v4.pdf)
