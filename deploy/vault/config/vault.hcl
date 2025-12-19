# ==============================================================================
# HashiCorp Vault Configuration
# ==============================================================================
# This configuration file defines how Vault operates
#
# Key Features:
#   - File storage backend for development/small deployments
#   - HTTP listener on port 8200
#   - Audit logging enabled
#   - API address configuration
# ==============================================================================

# Storage backend - File storage for development
# For production, consider using Consul, etcd, or integrated storage (Raft)
storage "file" {
  path = "/vault/data"
}

# HTTP listener
listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = 1  # Disable TLS for development (ENABLE in production!)

  # Uncomment for production with TLS:
  # tls_disable = 0
  # tls_cert_file = "/vault/config/tls/vault.crt"
  # tls_key_file  = "/vault/config/tls/vault.key"
}

# API address
api_addr = "http://0.0.0.0:8200"

# Cluster address (for HA deployments)
# cluster_addr = "https://vault:8201"

# UI configuration
ui = true

# Disable mlock for containers (mlock requires IPC_LOCK capability)
disable_mlock = false

# Default lease TTL and max lease TTL
default_lease_ttl = "168h"  # 7 days
max_lease_ttl = "720h"      # 30 days

# Log level
log_level = "info"

# Plugin directory
plugin_directory = "/vault/plugins"

# ==============================================================================
# PRODUCTION RECOMMENDATIONS
# ==============================================================================
#
# 1. Enable TLS:
#    - Set tls_disable = 0
#    - Provide valid TLS certificates
#    - Update VAULT_ADDR to use https://
#
# 2. Use a robust storage backend:
#    - Consul (recommended for HA)
#    - Integrated Storage/Raft (built-in HA)
#    - etcd, DynamoDB, or other supported backends
#
# 3. Enable audit logging:
#    - Configure file audit device
#    - Or use syslog for centralized logging
#    - Ensure log rotation is configured
#
# 4. Configure auto-unseal:
#    - AWS KMS: seal "awskms" { ... }
#    - Azure Key Vault: seal "azurekeyvault" { ... }
#    - GCP Cloud KMS: seal "gcpckms" { ... }
#
# 5. Set appropriate lease durations:
#    - Shorter leases = more secure, more rotation
#    - Balance security with operational overhead
#
# 6. Enable telemetry:
#    - Configure Prometheus metrics
#    - Monitor seal status, authentication attempts, secret access
#
# ==============================================================================
# EXAMPLE: Production Configuration with Consul and TLS
# ==============================================================================
#
# storage "consul" {
#   address = "consul:8500"
#   path    = "vault/"
# }
#
# listener "tcp" {
#   address       = "0.0.0.0:8200"
#   tls_disable   = 0
#   tls_cert_file = "/vault/config/tls/vault.crt"
#   tls_key_file  = "/vault/config/tls/vault.key"
# }
#
# seal "awskms" {
#   region     = "us-east-1"
#   kms_key_id = "your-kms-key-id"
# }
#
# telemetry {
#   prometheus_retention_time = "30s"
#   disable_hostname = true
# }
#
# ==============================================================================
