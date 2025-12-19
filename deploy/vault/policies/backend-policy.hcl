# ==============================================================================
# Vault Policy: Backend Services
# ==============================================================================
# This policy grants backend services read access to their secrets
#
# Applied to: backend, celery_worker, celery_beat
# ==============================================================================

# Backend-specific secrets
path "ecommerce/data/backend/*" {
  capabilities = ["read", "list"]
}

# Shared secrets (accessible by all services)
path "ecommerce/data/shared/*" {
  capabilities = ["read", "list"]
}

# Metadata access (for secret discovery)
path "ecommerce/metadata/backend/*" {
  capabilities = ["read", "list"]
}

path "ecommerce/metadata/shared/*" {
  capabilities = ["read", "list"]
}

# Allow reading own token information
path "auth/token/lookup-self" {
  capabilities = ["read"]
}

# Allow renewing own token
path "auth/token/renew-self" {
  capabilities = ["update"]
}

# Deny access to other paths (principle of least privilege)
# This is implicit, but can be made explicit for clarity
path "*" {
  capabilities = ["deny"]
}
