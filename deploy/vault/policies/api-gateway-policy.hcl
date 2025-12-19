# ==============================================================================
# Vault Policy: API Gateway
# ==============================================================================
# This policy grants API Gateway read access to its secrets
#
# Applied to: api_gateway
# ==============================================================================

# API Gateway-specific secrets
path "ecommerce/data/gateway/*" {
  capabilities = ["read", "list"]
}

# Shared secrets (accessible by all services)
path "ecommerce/data/shared/*" {
  capabilities = ["read", "list"]
}

# Metadata access (for secret discovery)
path "ecommerce/metadata/gateway/*" {
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

# Deny access to other paths
path "*" {
  capabilities = ["deny"]
}
