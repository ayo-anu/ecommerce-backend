# Data Retention Policy

## Overview

This Data Retention Policy establishes guidelines for the retention and disposal of data collected, processed, and stored by the E-Commerce Platform. The policy ensures compliance with legal, regulatory, and business requirements while minimizing data retention to only what is necessary.

**Policy Owner**: Legal & Compliance Team
**Effective Date**: 2025-12-19
**Review Frequency**: Annual
**Compliance**: PCI-DSS, GDPR, CCPA, SOC 2

## Table of Contents

1. [Purpose](#purpose)
2. [Scope](#scope)
3. [Legal and Regulatory Requirements](#legal-and-regulatory-requirements)
4. [Data Classification](#data-classification)
5. [Retention Schedules](#retention-schedules)
6. [Data Disposal](#data-disposal)
7. [Exceptions](#exceptions)
8. [Responsibilities](#responsibilities)
9. [Compliance and Audit](#compliance-and-audit)

---

## Purpose

The purpose of this policy is to:

1. **Ensure compliance** with legal and regulatory requirements
2. **Minimize data storage** to reduce security and privacy risks
3. **Support business operations** by retaining necessary data
4. **Facilitate e-discovery** and legal hold processes
5. **Protect customer privacy** by not retaining data longer than necessary
6. **Reduce storage costs** by systematically disposing of unnecessary data

---

## Scope

This policy applies to:

- **All data** collected, processed, or stored by the platform
- **All data types**: customer data, transaction data, system logs, backups
- **All storage locations**: databases, file systems, backups, archives
- **All employees, contractors, and third-party service providers**

---

## Legal and Regulatory Requirements

###  PCI-DSS Requirements

**PCI-DSS 3.1**: Minimize data retention
- Keep cardholder data only as long as necessary for business, legal, or regulatory purposes
- Implement quarterly data retention and disposal process

**Our Implementation:**
- Stripe tokens: Retained while customer account is active
- Last 4 digits: Retained for order history (7 years)
- Full PAN: **Never stored** (tokenization via Stripe)
- Sensitive authentication data (CVV, PIN): **Never stored** (prohibited)

### GDPR Requirements (EU Customers)

**Article 5(1)(e)**: Storage limitation
- Personal data kept only as long as necessary for stated purposes
- Right to erasure ("right to be forgotten") after purpose fulfilled

**Article 17**: Right to erasure
- Customers can request deletion of their personal data
- Must be completed within 30 days unless legal obligation to retain

### CCPA Requirements (California Customers)

**CCPA Section 1798.105**: Right to deletion
- Customers can request deletion of personal information
- Must respond within 45 days

### Tax and Accounting Requirements

**IRS Requirements** (US):
- Transaction records: 7 years
- Tax returns: 7 years
- Payroll records: 4 years

---

## Data Classification

Data is classified based on sensitivity and regulatory requirements:

| Classification | Description | Retention Driver | Example |
|----------------|-------------|------------------|---------|
| **Cardholder Data** | Payment card information | PCI-DSS, Business | Stripe tokens, last 4 digits |
| **PII** | Personally identifiable information | GDPR, CCPA | Name, email, address, phone |
| **Transaction Data** | Purchase and order history | Tax law, Business | Orders, invoices, receipts |
| **System Logs** | Application and security logs | PCI-DSS, SOC 2 | Access logs, audit logs |
| **Business Data** | Operational business data | Business need | Analytics, reports |

---

## Retention Schedules

### Customer Data

| Data Type | Retention Period | Justification | Disposal Method |
|-----------|------------------|---------------|-----------------|
| **Customer Account** | While account active + 7 years after closure | Tax/legal requirements | Secure deletion |
| **Name, Email, Phone** | While account active + 7 years | Transaction history | Secure deletion |
| **Shipping Address** | While account active + 7 years | Order fulfillment, tax | Secure deletion |
| **Billing Address** | While account active + 7 years | Tax records | Secure deletion |
| **Date of Birth** | While account active + 7 years | Age verification | Secure deletion |
| **IP Address** | 90 days | Fraud prevention | Auto-purge |
| **Browser/Device Info** | 90 days | Analytics, fraud | Auto-purge |

### Payment Data

| Data Type | Retention Period | Justification | Disposal Method |
|-----------|------------------|---------------|-----------------|
| **Stripe Customer ID** | While account active + 7 years | Payment processing | Secure deletion |
| **Stripe Token** | While payment method active | Future charges | Secure deletion |
| **Last 4 Digits** | While account active + 7 years | Order history display | Secure deletion |
| **Card Brand** | While account active + 7 years | Order history | Secure deletion |
| **Expiration Date** | While payment method active | Card validity check | Secure deletion |
| **Full PAN** | **Never stored** | N/A (tokenization) | N/A |
| **CVV/CVC** | **Never stored** | Prohibited by PCI-DSS | N/A |

**Important**: Stripe handles card data retention in compliance with PCI-DSS. We retain only minimal metadata.

### Transaction Data

| Data Type | Retention Period | Justification | Disposal Method |
|-----------|------------------|---------------|-----------------|
| **Orders** | 7 years | Tax/accounting | Secure deletion after anonymization |
| **Invoices** | 7 years | Tax/accounting | Secure deletion |
| **Receipts** | 7 years | Tax/accounting | Secure deletion |
| **Refunds** | 7 years | Tax/accounting | Secure deletion |
| **Stripe Charge Records** | 7 years | Financial records | Secure deletion |
| **Failed Transactions** | 90 days | Fraud analysis | Auto-purge |

### System Logs

| Data Type | Retention Period | Justification | Disposal Method |
|-----------|------------------|---------------|-----------------|
| **Application Logs** | 90 days active + 1 year archive | Troubleshooting, compliance | Auto-purge after archive period |
| **Access Logs** | 90 days active + 1 year archive | PCI-DSS Req 10.7 | Auto-purge |
| **Audit Logs (Vault)** | 1 year active + 6 years archive | Security, compliance | Secure deletion |
| **Security Incident Logs** | 7 years | Legal/regulatory | Secure archival |
| **Nginx Access Logs** | 90 days | Performance analysis | Auto-purge |
| **Error Logs** | 180 days | Debugging | Auto-purge |

### Backup Data

| Data Type | Retention Period | Justification | Disposal Method |
|-----------|------------------|---------------|-----------------|
| **Database Backups** | 90 days | Disaster recovery | Secure deletion |
| **Full System Backups** | 30 days | Disaster recovery | Secure deletion |
| **Incremental Backups** | 7 days | Operational recovery | Auto-purge |
| **Disaster Recovery Archive** | 1 year | Business continuity | Secure deletion |

**Note**: Backups may contain data past its normal retention period. Implement backup data lifecycle management.

### Marketing and Analytics

| Data Type | Retention Period | Justification | Disposal Method |
|-----------|------------------|---------------|-----------------|
| **Email Marketing Consent** | While active + 3 years | Compliance proof | Secure deletion |
| **Marketing Campaign Data** | 3 years | Analysis, ROI | Secure deletion |
| **Website Analytics** | 2 years | Business insights | Auto-purge |
| **A/B Test Results** | 1 year | Optimization | Auto-purge |
| **Customer Surveys** | 3 years | Feedback analysis | Anonymize then archive |

### Employment Data

| Data Type | Retention Period | Justification | Disposal Method |
|-----------|------------------|---------------|-----------------|
| **Employee Records** | 7 years after termination | Legal requirements | Secure deletion |
| **Payroll Records** | 7 years | Tax requirements | Secure deletion |
| **Background Checks** | 7 years | Compliance | Secure deletion |
| **Training Records** | Duration of employment + 3 years | Compliance | Secure deletion |

---

## Data Disposal

### Disposal Methods

#### 1. Secure Deletion (Digital Data)

**For active systems:**
```sql
-- PostgreSQL secure deletion
DELETE FROM customers WHERE account_closed_date < NOW() - INTERVAL '7 years';

-- Vacuum to reclaim space
VACUUM FULL customers;
```

**For backups and archives:**
- Cryptographic erasure (destroy encryption keys)
- Multi-pass overwrite (DoD 5220.22-M standard)
- Degaussing for magnetic media

#### 2. Automated Purging

**Cron job for automated deletion:**
```bash
# /etc/cron.daily/data-retention

# Delete old failed transactions (90 days)
psql -U postgres -d ecommerce -c "DELETE FROM failed_transactions WHERE created_at < NOW() - INTERVAL '90 days';"

# Delete old access logs (90 days, before archiving)
find /var/log/ecommerce/access -name "*.log" -mtime +90 -delete

# Delete old backups (90 days)
find /backup/database -name "*.sql.gz" -mtime +90 -delete
```

#### 3. Third-Party Data Deletion

**Stripe:**
- Customer deletion request via Stripe API
- Verify deletion through Stripe dashboard

**Analytics (Google Analytics):**
- User deletion request via GA API
- Set data retention to minimum required

### Disposal Verification

1. **Log all disposal actions**
   ```json
   {
     "timestamp": "2025-12-19T10:00:00Z",
     "action": "data_disposal",
     "data_type": "customer_accounts",
     "retention_period_expired": "2018-12-19",
     "records_deleted": 1234,
     "performed_by": "automated_job"
   }
   ```

2. **Quarterly disposal reports** to compliance team

3. **Annual audit** of disposal processes

---

## Exceptions

### Legal Hold

When legal proceedings are anticipated or ongoing:

1. **Suspend disposal** of relevant data immediately
2. **Notify Legal team** within 24 hours
3. **Document hold** in Legal Hold register
4. **Preserve data** until hold is lifted
5. **Resume normal disposal** after legal approval

**Legal Hold Process:**
```
Legal Event → Legal Team Notification → Hold Implemented → Data Preserved → Legal Resolution → Hold Lifted → Resume Disposal
```

### Regulatory Investigation

When subject to regulatory investigation:

1. **Preserve all relevant data**
2. **Notify Compliance Officer**
3. **Cooperate with regulators**
4. **Document preservation**

### Business Exception Request

If business requires data retention beyond standard period:

1. **Submit request** to Data Governance Committee
2. **Justify business need**
3. **Assess risk and compliance impact**
4. **Obtain approval** from Legal and Compliance
5. **Document exception** (max 1 year extension)
6. **Review annually**

---

## Responsibilities

### Data Protection Officer (DPO)

- Oversee policy implementation
- Ensure compliance with data protection laws
- Handle data subject requests (erasure, access)
- Report to board on data retention compliance

### IT/DevOps Team

- Implement automated deletion processes
- Maintain secure disposal procedures
- Generate disposal reports
- Archive data per schedule

### Legal Team

- Monitor legal and regulatory changes
- Manage legal holds
- Approve exception requests
- Review policy annually

### Application Developers

- Implement data retention logic in applications
- Design for data minimization
- Ensure deletion propagates through all systems

### All Employees

- Comply with retention policy
- Report policy violations
- Participate in training

---

## Compliance and Audit

### GDPR Compliance

**Right to Erasure (Article 17):**
1. Customer submits deletion request
2. Verify customer identity
3. Delete data within 30 days
4. Notify third-party processors (e.g., Stripe)
5. Provide confirmation to customer

**Implementation:**
```python
# Django management command
def handle_erasure_request(customer_id):
    # Delete customer data
    Customer.objects.filter(id=customer_id).delete()

    # Delete from Stripe
    stripe_customer_id = get_stripe_customer_id(customer_id)
    stripe.Customer.delete(stripe_customer_id)

    # Log deletion
    log_erasure(customer_id, timestamp=now())

    # Notify customer
    send_erasure_confirmation(customer_id)
```

### PCI-DSS Compliance

**Quarterly Process:**
1. Review cardholder data storage
2. Identify data exceeding retention period
3. Securely delete expired data
4. Document deletion
5. Report to QSA (if applicable)

### Audit Trail

All data disposal must be logged:

| Field | Description |
|-------|-------------|
| Timestamp | When disposal occurred |
| Data Type | Type of data deleted |
| Record Count | Number of records deleted |
| Retention Period | Original retention period |
| Method | Disposal method used |
| Performed By | User or system that performed deletion |
| Verification | Disposal verification status |

### Annual Review

**Review Checklist:**
- [ ] Update retention periods based on legal changes
- [ ] Review exception requests
- [ ] Audit disposal logs
- [ ] Test disposal procedures
- [ ] Train staff on policy updates
- [ ] Update documentation
- [ ] Report to board

---

## Data Subject Rights

### Right to Access

Customers can request a copy of their data:
- Respond within 30 days
- Provide data in portable format (JSON/CSV)

### Right to Rectification

Customers can request correction of inaccurate data:
- Verify and correct within 30 days
- Notify third parties if data was shared

### Right to Erasure

Customers can request deletion:
- Complete within 30 days (GDPR)
- Complete within 45 days (CCPA)
- Exceptions: Legal obligation, fraud prevention

### Right to Object

Customers can object to data processing:
- Stop processing for marketing purposes immediately
- Evaluate objection within 30 days

---

## Contact Information

**Data Protection Officer (DPO):**
- Email: dpo@example.com
- Phone: +1-555-0123

**Privacy Requests:**
- Email: privacy@example.com
- Web Form: https://example.com/privacy-request

**Legal Department:**
- Email: legal@example.com

---

## References

- PCI-DSS Requirement 3.1
- GDPR Articles 5, 17, 18
- CCPA Section 1798.105
- IRS Publication 583
- ISO 27001:2013 Annex A.18.1.3

---

## Appendix: Retention Period Quick Reference

| Data Category | Retention Period |
|---------------|------------------|
| Customer Account | Active + 7 years |
| Transaction Records | 7 years |
| System Logs | 90 days + 1 year archive |
| Backups | 90 days |
| Marketing Data | 3 years |
| Employee Records | 7 years after termination |
| IP Addresses | 90 days |
| Failed Transactions | 90 days |

---

**Document Version**: 1.0
**Last Updated**: 2025-12-19
**Next Review**: 2026-12-19
**Approved By**: Legal, Compliance, CISO
