# Encryption Policy

## Overview

This document defines the encryption standards and requirements for the E-Commerce Platform to ensure the confidentiality and integrity of sensitive data, including cardholder data, personally identifiable information (PII), and other confidential information.

**Policy Owner**: Security Team
**Effective Date**: 2025-12-19
**Review Frequency**: Annual
**Compliance**: PCI-DSS Requirement 3 & 4, SOC 2, GDPR

## Table of Contents

1. [Purpose](#purpose)
2. [Scope](#scope)
3. [Encryption Standards](#encryption-standards)
4. [Data Classification](#data-classification)
5. [Encryption at Rest](#encryption-at-rest)
6. [Encryption in Transit](#encryption-in-transit)
7. [Key Management](#key-management)
8. [Implementation Guidelines](#implementation-guidelines)
9. [Exceptions](#exceptions)
10. [Compliance and Audit](#compliance-and-audit)

---

## Purpose

The purpose of this policy is to:

1. **Protect sensitive data** from unauthorized access, disclosure, or modification
2. **Ensure PCI-DSS compliance** for cardholder data protection
3. **Establish consistent encryption standards** across all systems and applications
4. **Define key management procedures** for secure key lifecycle management
5. **Prevent data breaches** through defense-in-depth encryption

---

## Scope

This policy applies to:

- **All data classified as "Confidential" or "Restricted"**
- **All cardholder data** (even though we use tokenization)
- **Personally Identifiable Information (PII)**
- **Authentication credentials** (passwords, API keys, tokens)
- **Business-critical data** (trade secrets, financial data)
- **Data in all states**: at rest, in transit, and in use
- **All systems**: production, staging, development (where confidential data exists)
- **All personnel**: employees, contractors, third-party vendors

---

## Encryption Standards

### Approved Algorithms

#### Symmetric Encryption (Data at Rest)

| Algorithm | Key Size | Status | Use Case |
|-----------|----------|--------|----------|
| AES-256-GCM | 256-bit | ✅ Recommended | Database encryption, file encryption |
| AES-128-GCM | 128-bit | ✅ Acceptable | Performance-critical applications |
| ChaCha20-Poly1305 | 256-bit | ✅ Acceptable | Mobile/embedded systems |
| AES-256-CBC | 256-bit | ⚠️ Legacy (use GCM instead) | Existing systems only |

**Prohibited:**
- ❌ DES, 3DES
- ❌ RC4
- ❌ AES with ECB mode
- ❌ Any algorithm with key size < 128 bits

#### Asymmetric Encryption (Key Exchange, Digital Signatures)

| Algorithm | Key Size | Status | Use Case |
|-----------|----------|--------|----------|
| RSA | 4096-bit | ✅ Recommended | Certificate signing, key wrapping |
| RSA | 2048-bit | ✅ Acceptable | TLS certificates |
| ECDSA | P-384 | ✅ Recommended | Digital signatures |
| ECDSA | P-256 | ✅ Acceptable | TLS, JWT signing |
| Ed25519 | 256-bit | ✅ Recommended | SSH keys, API signing |

**Prohibited:**
- ❌ RSA < 2048 bits
- ❌ DSA
- ❌ Weak elliptic curves (P-192, secp256k1 for non-cryptocurrency use)

#### Hash Functions

| Algorithm | Output Size | Status | Use Case |
|-----------|-------------|--------|----------|
| SHA-256 | 256-bit | ✅ Recommended | General hashing |
| SHA-384 | 384-bit | ✅ Recommended | High-security hashing |
| SHA-512 | 512-bit | ✅ Recommended | High-security hashing |
| BLAKE2 | 256/512-bit | ✅ Acceptable | Performance-critical |
| Argon2id | Variable | ✅ Recommended | Password hashing |
| bcrypt | 60 bytes | ✅ Acceptable | Password hashing (legacy) |
| PBKDF2-SHA256 | Variable | ✅ Acceptable | Password hashing, key derivation |

**Prohibited:**
- ❌ MD5
- ❌ SHA-1
- ❌ Plain SHA-256 for passwords (use Argon2id/bcrypt/PBKDF2)

---

## Data Classification

Data must be classified to determine appropriate encryption requirements:

| Classification | Description | Encryption at Rest | Encryption in Transit | Examples |
|----------------|-------------|-------------------|----------------------|----------|
| **Restricted** | Highest sensitivity | ✅ Required (AES-256) | ✅ Required (TLS 1.3) | Payment tokens, SSNs, health records |
| **Confidential** | Sensitive business data | ✅ Required (AES-256) | ✅ Required (TLS 1.2+) | Customer PII, financial data, trade secrets |
| **Internal** | Internal use only | ✅ Recommended | ✅ Required (TLS 1.2+) | Internal documents, employee data |
| **Public** | Public information | ❌ Not required | ✅ Recommended | Marketing materials, public website |

### Cardholder Data Classification

Per PCI-DSS, cardholder data includes:

| Data Element | Classification | Our Implementation |
|--------------|----------------|-------------------|
| Primary Account Number (PAN) | Restricted | Not stored (Stripe tokenization) |
| Cardholder Name | Restricted | Stored encrypted (DB encryption) |
| Expiration Date | Restricted | Stored encrypted (DB encryption) |
| Service Code | Restricted | Not stored (Stripe handles) |
| Stripe Token | Restricted | Stored encrypted (DB encryption) |
| Last 4 Digits | Confidential | Stored encrypted (DB encryption) |
| Card Brand | Confidential | Stored encrypted (DB encryption) |

---

## Encryption at Rest

### Database Encryption

**Requirement**: All databases containing confidential or restricted data must use encryption at rest.

#### PostgreSQL - Transparent Data Encryption (TDE)

```yaml
# Implementation
Method: Full-disk encryption + column-level encryption
Algorithm: AES-256-GCM
Key Management: HashiCorp Vault
Key Rotation: Every 90 days
```

**Configuration:**
```sql
-- Enable pgcrypto extension
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Column-level encryption for sensitive fields
CREATE TABLE payment_methods (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER,
    stripe_token BYTEA,  -- Encrypted
    card_last4 VARCHAR(4),
    created_at TIMESTAMP
);

-- Encryption/Decryption functions
-- Handled by application layer using Vault keys
```

**Evidence:**
- Configuration: `deploy/docker/compose/production.yml`
- Encryption verification: `scripts/security/verify-encryption.sh`

#### Redis - Encryption

```yaml
# Implementation
Method: Encrypted volumes
Algorithm: AES-256-XTS (volume encryption)
Key Management: Cloud provider KMS
```

**Note**: Redis stores only session data and cache (no cardholder data).

### File System Encryption

**Requirement**: Encrypted volumes for all persistent storage.

| Storage Type | Encryption Method | Key Management |
|--------------|------------------|----------------|
| Docker Volumes | LUKS encryption | Cloud provider KMS |
| Backup Storage | AES-256-GCM | Vault-managed keys |
| Log Archives | AES-256-GCM | Vault-managed keys |

**Implementation:**
```bash
# Create encrypted volume
cryptsetup luksFormat /dev/sdb --cipher aes-xts-plain64 --key-size 256

# Mount encrypted volume
cryptsetup open /dev/sdb encrypted_data
mount /dev/mapper/encrypted_data /mnt/data
```

### Application-Level Encryption

For sensitive fields requiring additional protection beyond database encryption:

```python
# Example: Encrypting sensitive data in application
from cryptography.fernet import Fernet
from core.vault_client import vault_client

def encrypt_sensitive_data(plaintext: str) -> bytes:
    """Encrypt data using Vault encryption key"""
    encryption_key = vault_client.get_secret('encryption/data-key')
    f = Fernet(encryption_key)
    return f.encrypt(plaintext.encode())

def decrypt_sensitive_data(ciphertext: bytes) -> str:
    """Decrypt data using Vault encryption key"""
    encryption_key = vault_client.get_secret('encryption/data-key')
    f = Fernet(encryption_key)
    return f.decrypt(ciphertext).decode()
```

---

## Encryption in Transit

### TLS Configuration

**Requirement**: All data transmission must use TLS 1.2 or higher.

#### Minimum TLS Version

| Protocol | Status | Notes |
|----------|--------|-------|
| TLS 1.3 | ✅ Preferred | Best performance and security |
| TLS 1.2 | ✅ Acceptable | Minimum acceptable version |
| TLS 1.1 | ❌ Prohibited | Deprecated, insecure |
| TLS 1.0 | ❌ Prohibited | Deprecated, insecure |
| SSL 3.0 and below | ❌ Prohibited | Insecure |

#### Approved Cipher Suites (Priority Order)

```nginx
# Nginx TLS configuration
ssl_protocols TLSv1.3 TLSv1.2;

ssl_ciphers 'ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256';

ssl_prefer_server_ciphers on;

# Diffie-Hellman parameter for DHE ciphersuites
ssl_dhparam /etc/nginx/dhparam.pem;  # 4096-bit

# HSTS (HTTP Strict Transport Security)
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

# OCSP Stapling
ssl_stapling on;
ssl_stapling_verify on;
```

**Cipher Suite Requirements:**
- ✅ Must use ECDHE or DHE for forward secrecy
- ✅ Must use GCM or Poly1305 for AEAD (Authenticated Encryption)
- ✅ Must use SHA-256 or stronger for MAC
- ❌ No NULL ciphers
- ❌ No export-grade ciphers
- ❌ No RC4
- ❌ No 3DES
- ❌ No MD5

#### Certificate Requirements

```yaml
Certificate Authority: Let's Encrypt or commercial CA
Key Algorithm: RSA 2048-bit minimum (4096-bit recommended) or ECDSA P-256
Signature Algorithm: SHA-256 or stronger
Validity Period: Maximum 397 days (per CA/Browser Forum)
Renewal: Automated via Certbot (30 days before expiry)
Certificate Pinning: Not implemented (allows CA rotation)
```

### Internal Communications

**Requirement**: All internal service-to-service communication must be encrypted.

| Communication | Encryption | Authentication |
|--------------|------------|----------------|
| Backend ↔ Database | TLS 1.2+ | Certificate + password |
| Backend ↔ Redis | TLS 1.2+ | Password (from Vault) |
| Backend ↔ Vault | TLS 1.3 | AppRole authentication |
| Services ↔ AI Gateway | TLS 1.2+ | JWT tokens |

**Configuration Example:**
```python
# Django database connection with TLS
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'OPTIONS': {
            'sslmode': 'require',
            'sslcert': '/etc/ssl/certs/client-cert.pem',
            'sslkey': '/etc/ssl/private/client-key.pem',
            'sslrootcert': '/etc/ssl/certs/ca-cert.pem',
        }
    }
}
```

### API Communications

| API Type | Encryption | Authentication |
|----------|------------|----------------|
| Public API (Customer-facing) | TLS 1.3 | OAuth 2.0 / JWT |
| Stripe API | TLS 1.3 | API Key (from Vault) |
| Internal APIs | TLS 1.2+ | Service tokens |
| Admin API | TLS 1.3 | MFA + JWT |

---

## Key Management

### Key Lifecycle

```
┌─────────────┐
│   Generate  │ ← Vault generates key using FIPS 140-2 RNG
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Activate  │ ← Key made available for use
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Use       │ ← Key used for encryption/decryption (audit logged)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Rotate    │ ← Key rotated (every 90 days)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Archive   │ ← Old key archived (decrypt-only)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Destroy   │ ← Key destroyed after retention period (1 year)
└─────────────┘
```

### Key Storage

**Primary Key Storage**: HashiCorp Vault

```bash
# Vault transit engine for encryption keys
vault secrets enable transit
vault write -f transit/keys/database-encryption

# Key rotation
vault write -f transit/keys/database-encryption/rotate
```

**Key Encryption Key (KEK):**
- Stored in Vault
- Protected by Vault's master key
- Master key split using Shamir's Secret Sharing (5 shares, 3 required)

**Data Encryption Keys (DEK):**
- Generated per database/service
- Encrypted by KEK
- Rotated every 90 days

### Key Rotation Schedule

| Key Type | Rotation Frequency | Automated | Notes |
|----------|-------------------|-----------|-------|
| Database Encryption Keys | Every 90 days | ✅ Yes | Automated via Vault |
| TLS Certificates | Every 90 days | ✅ Yes | Let's Encrypt auto-renewal |
| API Keys | Every 180 days | ⚠️ Manual | Coordinated with partners |
| JWT Signing Keys | Every 30 days | ✅ Yes | Invalidates old tokens |
| SSH Keys | Every 365 days | ⚠️ Manual | Personal responsibility |

### Key Access Control

**Principle of Least Privilege**: Only authorized services and personnel can access encryption keys.

| Key Type | Access | Audit Logging |
|----------|--------|---------------|
| Database Encryption Keys | Backend service (AppRole) | ✅ All access logged |
| TLS Private Keys | Nginx service only | ✅ File access logged |
| API Keys | Respective services only | ✅ Vault audit log |
| Master Keys | Security team (3 of 5 required) | ✅ All unseals logged |

**Vault Policy Example:**
```hcl
# Policy for backend service
path "transit/encrypt/database-encryption" {
  capabilities = ["update"]
}

path "transit/decrypt/database-encryption" {
  capabilities = ["update"]
}

path "database/creds/backend-role" {
  capabilities = ["read"]
}
```

### Key Backup and Recovery

**Vault Backup:**
```bash
# Automated daily backup
vault operator raft snapshot save backup-$(date +%Y%m%d).snap

# Encrypt backup
gpg --encrypt --recipient security@example.com backup-*.snap

# Store in secure location
aws s3 cp backup-*.snap.gpg s3://backups/vault/ --sse AES256
```

**Recovery Procedure:**
1. Restore Vault from snapshot
2. Unseal Vault using master key shares (3 of 5)
3. Verify key availability
4. Test encryption/decryption
5. Resume normal operations

---

## Implementation Guidelines

### For Developers

#### 1. Always Use TLS

```python
# ✅ Good: Use TLS for external API calls
import requests

response = requests.get('https://api.example.com/data', verify=True)

# ❌ Bad: Disable certificate verification
response = requests.get('https://api.example.com/data', verify=False)
```

#### 2. Never Hardcode Keys

```python
# ✅ Good: Retrieve from Vault
from core.vault_client import vault_client

api_key = vault_client.get_secret('api-keys/stripe', 'secret_key')

# ❌ Bad: Hardcoded key
api_key = "sk_live_abc123xyz"  # Never do this!
```

#### 3. Use Proper Password Hashing

```python
# ✅ Good: Use Django's password hashers (Argon2)
from django.contrib.auth.hashers import make_password

hashed = make_password(password)  # Uses Argon2 by default

# ❌ Bad: Plain SHA-256
import hashlib
hashed = hashlib.sha256(password.encode()).hexdigest()  # Insecure for passwords!
```

#### 4. Encrypt Sensitive Data in Application

```python
# ✅ Good: Encrypt before storing
encrypted_ssn = encrypt_sensitive_data(ssn)
user.encrypted_ssn = encrypted_ssn

# ❌ Bad: Store plaintext
user.ssn = ssn  # Even with DB encryption, avoid this
```

### For DevOps

#### 1. Configure TLS Properly

```nginx
# ✅ Good: Strong TLS configuration
ssl_protocols TLSv1.3 TLSv1.2;
ssl_ciphers 'ECDHE-ECDSA-AES256-GCM-SHA384:...';
ssl_prefer_server_ciphers on;
add_header Strict-Transport-Security "max-age=31536000" always;

# ❌ Bad: Weak configuration
ssl_protocols TLSv1 TLSv1.1 TLSv1.2;  # TLS 1.0/1.1 are insecure
ssl_ciphers 'ALL';  # Includes weak ciphers
```

#### 2. Use Encrypted Volumes

```bash
# ✅ Good: Encrypted Docker volume
docker volume create --driver local \
  --opt type=none \
  --opt device=/mnt/encrypted_data \
  --opt o=bind \
  encrypted-volume

# ❌ Bad: Unencrypted volume for sensitive data
docker volume create plaintext-volume  # Don't use for sensitive data
```

---

## Exceptions

### Exception Process

Exceptions to this policy require:

1. **Written justification** - Business or technical reason
2. **Risk assessment** - Document security risks
3. **Compensating controls** - Alternative security measures
4. **Approval** - Security team + business owner approval
5. **Time-bound** - Maximum 90 days, renewable
6. **Documentation** - Record in exceptions register

### Approved Exceptions

| System | Exception | Compensating Control | Expiry |
|--------|-----------|---------------------|--------|
| Development DB | No encryption at rest | No production data, network isolated | 2026-03-19 |
| Legacy API | TLS 1.2 only (no 1.3) | Strong cipher suites, monitoring | 2026-06-19 |

**Exception Request Template**: `docs/templates/encryption-exception-request.md`

---

## Compliance and Audit

### Compliance Requirements

| Standard | Requirement | Our Implementation |
|----------|-------------|-------------------|
| PCI-DSS 4.0 Req 3 | Protect stored account data | ✅ Database encryption, tokenization |
| PCI-DSS 4.0 Req 4 | Encrypt transmission of cardholder data | ✅ TLS 1.3, strong ciphers |
| SOC 2 CC6.7 | Encryption for data at rest and in transit | ✅ Full encryption coverage |
| GDPR Art 32 | Encryption of personal data | ✅ PII encrypted |

### Audit Verification

**Monthly:**
- TLS configuration scan (SSL Labs)
- Certificate expiry check
- Key rotation verification

**Quarterly:**
- Encryption coverage audit
- Access control review
- Exception review

**Annually:**
- Full encryption policy review
- Penetration test (encryption)
- Third-party security audit

### Automated Compliance Checks

```bash
# Run encryption compliance check
./scripts/security/encryption-compliance-check.sh

# Checks:
# ✅ TLS version and ciphers
# ✅ Certificate validity
# ✅ Database encryption enabled
# ✅ Vault seal status
# ✅ Key rotation status
```

---

## Policy Enforcement

### Monitoring

- **TLS monitoring**: Continuous monitoring of TLS configuration
- **Key access logging**: All key access logged via Vault
- **Encryption failures**: Alerts on encryption/decryption failures
- **Certificate expiry**: Alerts 30 days before expiry

### Violations

Violations of this policy will result in:

1. **Incident response** - Immediate investigation
2. **Remediation** - Fix within 24 hours (critical) or 7 days (non-critical)
3. **Disciplinary action** - Per HR policy
4. **Reporting** - Report to security team and compliance

---

## References

- PCI-DSS v4.0 Requirements 3 & 4
- NIST SP 800-52 Rev 2: TLS Guidelines
- NIST SP 800-57: Key Management
- OWASP Cryptographic Storage Cheat Sheet
- Mozilla SSL Configuration Generator
- Let's Encrypt Documentation

---

## Appendix A: Encryption Decision Tree

```
Is the data sensitive?
│
├─ Yes → Is it cardholder data?
│        │
│        ├─ Yes → Use Stripe tokenization (PAN never stored)
│        │        Store only tokens (encrypted in DB)
│        │
│        └─ No → Is it PII?
│               │
│               ├─ Yes → Encrypt at rest (AES-256-GCM)
│               │        Encrypt in transit (TLS 1.3)
│               │
│               └─ No → Is it confidential business data?
│                      │
│                      ├─ Yes → Encrypt at rest (AES-256-GCM)
│                      │        Encrypt in transit (TLS 1.2+)
│                      │
│                      └─ No → Apply standard security controls
│
└─ No → Is it transmitted over internet?
       │
       ├─ Yes → Encrypt in transit (TLS 1.2+)
       │
       └─ No → Standard security controls
```

---

**Document Version**: 1.0
**Last Updated**: 2025-12-19
**Next Review**: 2026-12-19
**Document Owner**: Security Team
**Approved By**: CISO, CTO
