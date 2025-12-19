# Cardholder Data Flow Documentation

## Overview

This document describes how cardholder data flows through our e-commerce platform. Understanding data flow is critical for PCI-DSS compliance (Requirement 1.1.3) and ensures we maintain proper security controls at each step.

**Key Principle**: We use **Stripe tokenization** to minimize our PCI scope. Cardholder data flows directly from the customer's browser to Stripe, never touching our servers.

## Table of Contents

1. [Data Classification](#data-classification)
2. [Payment Processing Flow](#payment-processing-flow)
3. [Data Storage](#data-storage)
4. [Network Segmentation](#network-segmentation)
5. [Security Controls by Flow](#security-controls-by-flow)
6. [PCI Scope](#pci-scope)

---

## Data Classification

### Cardholder Data Elements

| Data Element | PCI Classification | Storage | Transmission | Display |
|--------------|-------------------|---------|--------------|---------|
| Primary Account Number (PAN) | Cardholder Data | ❌ Never | ✅ Direct to Stripe | ❌ Never (masked only) |
| Cardholder Name | Cardholder Data | ❌ Never | ✅ Direct to Stripe | ✅ Yes (needed for orders) |
| Expiration Date | Cardholder Data | ❌ Never | ✅ Direct to Stripe | ❌ Never |
| Service Code | Cardholder Data | ❌ Never | ✅ Direct to Stripe | ❌ Never |

### Sensitive Authentication Data

| Data Element | PCI Classification | Storage | Transmission | Display |
|--------------|-------------------|---------|--------------|---------|
| CVV/CVC | Sensitive Auth Data | ❌ Never (prohibited) | ✅ Direct to Stripe | ❌ Never (prohibited) |
| PIN | Sensitive Auth Data | ❌ Never (prohibited) | ❌ N/A (not used) | ❌ Never (prohibited) |
| Magnetic Stripe Data | Sensitive Auth Data | ❌ Never (prohibited) | ❌ N/A (not used) | ❌ Never (prohibited) |
| Chip Data | Sensitive Auth Data | ❌ Never (prohibited) | ❌ N/A (not used) | ❌ Never (prohibited) |

**Important**: Sensitive authentication data must NEVER be stored after authorization, even if encrypted. This is a PCI-DSS absolute requirement.

### What We Store

| Data Element | Storage | Purpose | Encryption |
|--------------|---------|---------|------------|
| Stripe Token | ✅ Database | Future charges, subscriptions | ✅ Database encryption |
| Last 4 digits | ✅ Database | Order history display | ✅ Database encryption |
| Card Brand | ✅ Database | Display (Visa, MC, etc.) | ✅ Database encryption |
| Expiration Month | ✅ Database | Card expiry checking | ✅ Database encryption |
| Billing Address | ✅ Database | Fraud prevention | ✅ Database encryption |
| Customer Name | ✅ Database | Order fulfillment | ✅ Database encryption |

---

## Payment Processing Flow

### Flow 1: New Card Payment

```
┌─────────────────────────────────────────────────────────────────┐
│                    CUSTOMER BROWSER                              │
│                                                                   │
│  1. Customer enters card details in checkout form                │
│     - PAN (16 digits)                                            │
│     - Expiration (MM/YY)                                         │
│     - CVV (3-4 digits)                                           │
│     - Cardholder name                                            │
│     - Billing address                                            │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   │ 2. Stripe.js intercepts form submission
                   │    (Cardholder data NEVER sent to our server)
                   │
                   ▼
         ┌─────────────────────┐
         │   STRIPE API        │ ◄─── 3. HTTPS/TLS 1.3
         │   (PCI Level 1)     │      Encrypted connection
         │                     │
         │  - Validates card   │
         │  - Performs 3DS     │
         │  - Creates token    │
         └──────────┬──────────┘
                    │
                    │ 4. Returns token (tok_xxxxxxxxxxxx)
                    │    and card metadata (last4, brand, exp)
                    │
                    ▼
         ┌─────────────────────┐
         │  CUSTOMER BROWSER   │
         └──────────┬──────────┘
                    │
                    │ 5. HTTPS POST to /api/orders/
                    │    Body: {
                    │      "stripe_token": "tok_xxx",
                    │      "amount": 99.99,
                    │      "items": [...]
                    │    }
                    │
                    ▼
         ┌─────────────────────────────┐
         │   OUR BACKEND API           │
         │   (Django REST Framework)   │
         │                             │
         │  6. Receives:                │
         │     - Stripe token           │
         │     - Order details          │
         │     - Customer ID            │
         │                             │
         │  7. Calls Stripe API:       │
         │     stripe.Charge.create(   │
         │       token=tok_xxx,        │
         │       amount=9999,          │
         │       currency='usd'        │
         │     )                       │
         └──────────┬─────────────────┘
                    │
                    │ 8. HTTPS API call to Stripe
                    │    (Server-to-Server, API key)
                    │
                    ▼
         ┌─────────────────────┐
         │   STRIPE API        │
         │                     │
         │  9. Processes charge │
         │  10. Returns result  │
         │      - Charge ID     │
         │      - Status        │
         │      - Card metadata │
         └──────────┬──────────┘
                    │
                    │ 11. Success response
                    │
                    ▼
         ┌─────────────────────────────┐
         │   OUR BACKEND API           │
         │                             │
         │  12. Stores in database:     │
         │      - Order ID             │
         │      - Stripe Charge ID     │
         │      - Last 4 digits        │
         │      - Card brand           │
         │      - Customer ID          │
         │                             │
         │  13. Returns order confirmation │
         └──────────┬─────────────────┘
                    │
                    │ 14. HTTPS response
                    │
                    ▼
         ┌─────────────────────┐
         │  CUSTOMER BROWSER   │
         │                     │
         │  Displays:          │
         │  "Order confirmed!" │
         │  "Card ending 1234" │
         └─────────────────────┘
```

### Key Security Points

1. **Direct Submission**: Cardholder data goes directly from browser to Stripe (never to our server)
2. **TLS Encryption**: All transmission uses TLS 1.3
3. **Tokenization**: We receive only a token, not the actual PAN
4. **Minimal Storage**: We store only what's needed (last 4, brand, token)
5. **PCI Scope Reduction**: Since PAN never touches our systems, our PCI scope is minimal

---

### Flow 2: Saved Card Payment (Returning Customer)

```
┌─────────────────────────────────────────────────────────────────┐
│                    CUSTOMER BROWSER                              │
│                                                                   │
│  1. Customer selects saved card:                                 │
│     "Visa ending in 1234"                                        │
│                                                                   │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   │ 2. HTTPS POST to /api/orders/
                   │    Body: {
                   │      "payment_method_id": "pm_xxx",
                   │      "amount": 149.99,
                   │      "items": [...]
                   │    }
                   │
                   ▼
         ┌─────────────────────────────┐
         │   OUR BACKEND API           │
         │                             │
         │  3. Retrieves from database: │
         │     - Stripe Customer ID    │
         │     - Payment Method ID     │
         │                             │
         │  4. Calls Stripe API:       │
         │     stripe.PaymentIntent.create( │
         │       customer='cus_xxx',   │
         │       payment_method='pm_xxx', │
         │       amount=14999          │
         │     )                       │
         └──────────┬─────────────────┘
                    │
                    │ 5. HTTPS to Stripe API
                    │
                    ▼
         ┌─────────────────────┐
         │   STRIPE API        │
         │                     │
         │  6. Charges saved card │
         │  7. Returns result   │
         └──────────┬──────────┘
                    │
                    │ 8. Success response
                    │
                    ▼
         ┌─────────────────────────────┐
         │   OUR BACKEND API           │
         │                             │
         │  9. Creates order record     │
         │  10. Returns confirmation    │
         └──────────┬─────────────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │  CUSTOMER BROWSER   │
         │  "Order confirmed!" │
         └─────────────────────┘
```

**Note**: Even with saved cards, the actual PAN is stored only by Stripe. We store only the Stripe Payment Method ID.

---

### Flow 3: 3D Secure Authentication

```
┌──────────────┐                  ┌──────────┐
│   Customer   │                  │  Stripe  │
│   Browser    │◄────────────────►│   API    │
└──────┬───────┘                  └────┬─────┘
       │                               │
       │ 1. Submit card details        │
       ├──────────────────────────────►│
       │                               │
       │ 2. 3DS required               │
       │◄──────────────────────────────┤
       │                               │
       │ 3. Redirect to bank           │
       ├───────────────────────────────┼────────►┌──────────┐
       │                               │         │  Issuing │
       │ 4. Authenticate               │         │   Bank   │
       │◄────────────────────────────────────────┤  (3DS)   │
       │   (SMS code, biometric, etc.) │         └──────────┘
       │                               │
       │ 5. Authentication complete    │
       ├───────────────────────────────┼────────►│
       │                               │
       │ 6. Redirect back to Stripe    │
       │◄──────────────────────────────┤
       │                               │
       │ 7. Payment confirmed          │
       │◄──────────────────────────────┤
       │                               │
       │ 8. Return to merchant         │
       ├──────────────────────────────►│
       │                               │
       ▼                               ▼
```

**Security Note**: 3D Secure adds strong customer authentication (SCA) without requiring us to handle any additional sensitive data.

---

## Data Storage

### Database Schema (Simplified)

```sql
-- Table: payments
CREATE TABLE payments (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id),
    stripe_charge_id VARCHAR(255) NOT NULL,  -- ch_xxxxxx
    stripe_customer_id VARCHAR(255),         -- cus_xxxxx
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    card_last4 VARCHAR(4),                   -- Last 4 digits only
    card_brand VARCHAR(20),                  -- Visa, Mastercard, etc.
    card_exp_month INTEGER,                  -- Expiry month
    card_exp_year INTEGER,                   -- Expiry year
    status VARCHAR(20),                      -- succeeded, failed, etc.
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Table: payment_methods (for saved cards)
CREATE TABLE payment_methods (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id),
    stripe_payment_method_id VARCHAR(255),   -- pm_xxxxx (Stripe token)
    card_last4 VARCHAR(4),
    card_brand VARCHAR(20),
    card_exp_month INTEGER,
    card_exp_year INTEGER,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**What's NOT in our database:**
- ❌ Full PAN (16-digit card number)
- ❌ CVV/CVC
- ❌ Magnetic stripe data
- ❌ Chip data
- ❌ PIN

**Encryption:**
- ✅ Database-level encryption enabled (PostgreSQL TDE)
- ✅ Encrypted backups
- ✅ Encrypted connections (TLS)
- ✅ Vault for database credentials

---

## Network Segmentation

### Network Zones

```
                    INTERNET
                       │
                       │ TLS 1.3
                       │
                  ┌────▼────┐
                  │  CDN    │
                  │ (Public)│
                  └────┬────┘
                       │
              ┌────────┴────────┐
              │                 │
         ┌────▼────┐       ┌───▼────┐
         │  Nginx  │       │ Stripe │
         │ (DMZ)   │       │  API   │
         └────┬────┘       └────────┘
              │
              │ Internal Network
              │ (No direct internet access)
              │
    ┌─────────┼─────────┐
    │         │         │
┌───▼───┐ ┌──▼───┐ ┌──▼──────┐
│Backend│ │ AI   │ │ Redis   │
│ API   │ │Gateway│ │(Session)│
└───┬───┘ └──┬───┘ └─────────┘
    │        │
    │    ┌───▼────────┐
    │    │ AI Services│
    │    │ (Internal) │
    │    └────────────┘
    │
┌───▼──────────┐
│  PostgreSQL  │ ◄─── Encrypted at rest
│  (Database)  │      No external access
│              │      Vault credentials
└──────────────┘
```

### Network Rules

| Source | Destination | Port | Protocol | Purpose |
|--------|-------------|------|----------|---------|
| Internet | Nginx | 443 | HTTPS | Public web traffic |
| Internet | Nginx | 80 | HTTP | Redirect to HTTPS |
| Nginx | Backend | 8000 | HTTP | Internal API calls |
| Nginx | AI Gateway | 8080 | HTTP | AI service proxy |
| Backend | PostgreSQL | 5432 | PostgreSQL | Database queries |
| Backend | Redis | 6379 | Redis | Session/cache |
| Backend | Stripe API | 443 | HTTPS | Payment processing |
| Backend | Vault | 8200 | HTTPS | Secret retrieval |

**Blocked:**
- ❌ Direct internet access to Backend
- ❌ Direct internet access to Database
- ❌ Direct internet access to Redis
- ❌ Database connections from DMZ

---

## Security Controls by Flow

### Browser → Stripe (Cardholder Data)

| Control | Implementation | PCI Requirement |
|---------|----------------|-----------------|
| Encryption in Transit | TLS 1.3 | Requirement 4 |
| Secure Transmission | HTTPS only, HSTS | Requirement 4.1 |
| Certificate Validation | Let's Encrypt, auto-renewal | Requirement 4.2 |
| No PAN Storage | Stripe.js direct submission | Requirement 3.2 |
| Input Validation | Client-side + Stripe validation | Requirement 6.4 |

### Backend → Stripe API

| Control | Implementation | PCI Requirement |
|---------|----------------|-----------------|
| API Authentication | Secret API keys in Vault | Requirement 7 |
| Encryption in Transit | TLS 1.3 | Requirement 4 |
| Logging | All API calls logged | Requirement 10 |
| Error Handling | No sensitive data in errors | Requirement 6.4 |
| Rate Limiting | 100 requests/min | Requirement 1 |

### Database Storage

| Control | Implementation | PCI Requirement |
|---------|----------------|-----------------|
| Data Minimization | Tokens only, no PAN | Requirement 3.1 |
| Encryption at Rest | PostgreSQL TDE | Requirement 3.4 |
| Access Control | Vault-managed credentials | Requirement 7 |
| Backup Encryption | Encrypted backups | Requirement 3.4 |
| Audit Logging | All access logged | Requirement 10 |

---

## PCI Scope

### In Scope

**Systems that handle cardholder data or connect to systems that do:**

1. **Frontend (Partial)**
   - Checkout page (collects data but sends to Stripe)
   - Uses Stripe.js (reduces scope)

2. **Backend API**
   - Receives Stripe tokens
   - Calls Stripe API
   - Stores payment metadata

3. **Database**
   - Stores Stripe tokens
   - Stores card metadata (last 4, brand, exp)

4. **Network Infrastructure**
   - Nginx reverse proxy
   - Load balancers
   - Firewalls

### Out of Scope

**Systems that do not handle or connect to cardholder data:**

1. **AI Services**
   - Recommendation engine
   - Search engine
   - Chatbot
   - Fraud detection (uses metadata only)

2. **Internal Tools**
   - Admin dashboards (no payment processing)
   - Analytics systems
   - Monitoring systems

3. **Third-Party Services**
   - Email service (SendGrid)
   - SMS service (Twilio)
   - Analytics (Google Analytics)

### Scope Reduction Strategy

Our primary scope reduction strategies:

1. **Tokenization via Stripe**
   - Eliminates PAN from our environment
   - Reduces SAQ complexity

2. **Network Segmentation**
   - Payment processing isolated
   - Limits scope to specific systems

3. **Stripe.js Direct Submission**
   - Cardholder data never touches our servers
   - Qualifies for SAQ A or SAQ A-EP

### SAQ Classification

Based on our implementation, we likely qualify for:

**SAQ A-EP** (E-commerce with Partial Outsourcing)

**Requirements:**
- All cardholder data functions outsourced to PCI-DSS validated third party (Stripe ✅)
- Merchant does not receive cardholder data (✅)
- Merchant has website that directly impacts security of payment transaction (✅)
- Website does not receive cardholder data but controls how consumers are redirected to third party (✅)

**Number of requirements**: ~170 (vs. 329 for SAQ D)

---

## Data Flow Audit Trail

Every transaction creates an audit trail:

### 1. Frontend Event Logs
```json
{
  "event": "payment_initiated",
  "timestamp": "2025-12-19T10:30:00Z",
  "session_id": "sess_xxxxx",
  "user_id": "user_12345",
  "amount": 99.99,
  "currency": "USD"
}
```

### 2. Stripe API Logs
```json
{
  "event": "charge.succeeded",
  "charge_id": "ch_xxxxx",
  "amount": 9999,
  "currency": "usd",
  "card": {
    "last4": "1234",
    "brand": "visa",
    "exp_month": 12,
    "exp_year": 2026
  }
}
```

### 3. Backend Application Logs
```json
{
  "timestamp": "2025-12-19T10:30:05Z",
  "level": "INFO",
  "event": "payment_processed",
  "user_id": "user_12345",
  "order_id": "ord_67890",
  "stripe_charge_id": "ch_xxxxx",
  "amount": 99.99,
  "card_last4": "1234"
}
```

### 4. Database Audit Log (Vault)
```json
{
  "timestamp": "2025-12-19T10:30:03Z",
  "path": "database/credentials",
  "operation": "read",
  "user": "backend-service",
  "result": "success"
}
```

---

## Incident Response for Data Breach

In the unlikely event of a potential cardholder data breach:

### Immediate Response (0-1 hour)

1. **Isolate affected systems**
   - Disconnect from network
   - Preserve evidence

2. **Notify security team**
   - Page on-call security engineer
   - Start incident response plan

3. **Initial assessment**
   - Scope of potential exposure
   - Systems affected
   - Data potentially compromised

### Short-term Response (1-24 hours)

4. **Notify Stripe**
   - Contact Stripe security team
   - Provide incident details

5. **Forensic investigation**
   - Preserve logs
   - Analyze attack vectors
   - Determine data accessed

6. **Containment**
   - Patch vulnerabilities
   - Strengthen controls
   - Monitor for further activity

### Long-term Response (1-30 days)

7. **Notification obligations**
   - Notify payment brands (if required)
   - Notify affected customers (if required)
   - Notify regulators (if required)

8. **Remediation**
   - Implement fixes
   - Enhance monitoring
   - Update security controls

9. **Post-incident review**
   - Root cause analysis
   - Lessons learned
   - Process improvements

**Note**: Given our tokenization approach, a breach would likely expose only:
- Stripe tokens (which can be invalidated)
- Last 4 digits
- Card metadata

Full PANs would NOT be exposed as we don't store them.

---

## References

- PCI-DSS Requirement 1.1.3 - Data Flow Diagrams
- Stripe Security Guide: https://stripe.com/docs/security/guide
- PCI-DSS Tokenization Guidelines: https://www.pcisecuritystandards.org/documents/Tokenization_Guidelines_Info_Supplement.pdf
- Network Segmentation Guide: https://www.pcisecuritystandards.org/documents/Guidance-PCI-DSS-Scoping-and-Segmentation_v1.pdf

---

**Document Version**: 1.0
**Last Updated**: 2025-12-19
**Document Owner**: Security Team
**Review Frequency**: Quarterly or after any payment flow changes
