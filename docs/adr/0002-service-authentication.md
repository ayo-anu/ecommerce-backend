# 2. Per-Service Authentication Keys

Date: 2025-12-04

## Status

Accepted

## Context

Our microservices need to authenticate with each other. The initial implementation used Django's `SECRET_KEY` for signing JWT tokens across all services, creating a security vulnerability: if one service is compromised, an attacker could forge tokens for all services.

We need a more secure service-to-service authentication mechanism.

## Decision

Implement **unique cryptographic signing keys for each service**:

- Each service has its own `SERVICE_AUTH_SECRET_<SERVICE_NAME>` environment variable
- Keys are 64+ characters of cryptographic-quality randomness
- No fallback to Django `SECRET_KEY` (fail fast if keys missing)
- Support for key rotation via JWKS (JSON Web Key Sets)
- RS256 (asymmetric) support for production environments

## Consequences

### Positive

- **Blast Radius Reduction**: Compromised service cannot forge tokens for others
- **Independent Security**: Each service's security is isolated
- **Key Rotation**: Can rotate keys per service without affecting others
- **Compliance**: Meets security requirements for service isolation
- **Auditability**: Can track which service issued each token

### Negative

- **More Configuration**: Need to generate and manage multiple keys
- **Deployment Complexity**: Must ensure all keys are set before startup
- **Key Management**: Need secure storage (environment vars, secrets managers)

### Neutral

- **Development Overhead**: One-time cost to generate keys via script
- **Documentation Required**: Team needs to understand new auth flow

## Implementation

1. ✅ Created `backend/core/service_tokens.py` with isolated key management
2. ✅ Added startup validation to fail if keys missing
3. ✅ Generated key creation script (`scripts/generate_service_keys.py`)
4. ✅ Updated `.env.example` with key templates
5. ✅ Implemented JWKS endpoint for key rotation (`backend/core/jwks.py`)
6. ✅ Documented in `docs/SECRETS_MANAGEMENT.md`

## Key Design Decisions

### Why HS256 for Development, RS256 for Production?

- **HS256** (symmetric): Simpler for development, single secret
- **RS256** (asymmetric): More secure, public key can be shared

### Why Not mTLS?

mTLS considered but **rejected** because:
- Requires complex certificate infrastructure
- Higher operational overhead
- JWT tokens provide sufficient security with simpler implementation
- Can add mTLS later if needed

## Alternatives Considered

### Continue Using Single SECRET_KEY

**Rejected** because:
- Significant security risk
- Fails principle of least privilege
- Not suitable for production

### OAuth 2.0 Client Credentials Flow

**Rejected** because:
- Overkill for internal services
- Requires additional OAuth server
- More complex for small team

### API Keys

**Rejected** because:
- Less secure than JWT (no expiration)
- No standard format
- Difficult to rotate

## Migration Path

1. ✅ Phase 1: Add new auth system alongside old
2. ✅ Phase 2: Generate and deploy service keys
3. Phase 3: Switch all services to new system
4. Phase 4: Remove old auth code

## References

- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [Service-to-Service Auth Patterns](https://cloud.google.com/architecture/microservices-architecture-service-to-service-authentication)
- [JWKS Specification](https://tools.ietf.org/html/rfc7517)
