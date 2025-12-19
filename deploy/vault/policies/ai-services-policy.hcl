# ==============================================================================
# Vault Policy: AI Services
# ==============================================================================
# This policy grants AI services read access to their secrets
#
# Applied to: recommender, search, pricing, chatbot, fraud, forecasting, vision
# ==============================================================================

# AI services-specific secrets
path "ecommerce/data/ai/*" {
  capabilities = ["read", "list"]
}

# Shared secrets (accessible by all services)
path "ecommerce/data/shared/*" {
  capabilities = ["read", "list"]
}

# Metadata access (for secret discovery)
path "ecommerce/metadata/ai/*" {
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
path "*" {
  capabilities = ["deny"]
}
