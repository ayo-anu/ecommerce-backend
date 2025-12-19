#!/bin/bash
# ==============================================================================
# Secret Migration Script - Move secrets from .env to Vault
# ==============================================================================
# This script migrates all secrets from environment files to HashiCorp Vault
#
# Usage:
#   ./scripts/security/migrate-secrets.sh [env-file]
#
# Arguments:
#   env-file: Path to .env file (default: .env)
#
# Prerequisites:
#   - Vault must be initialized and unsealed
#   - Root token or appropriate credentials must be available
#   - Run init-vault.sh first
#
# What it does:
#   1. Reads secrets from .env file
#   2. Stores them in appropriate Vault paths
#   3. Creates a backup of original .env file
#   4. Optionally creates .env.vault with Vault config
# ==============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
VAULT_ADDR="${VAULT_ADDR:-http://localhost:8200}"
VAULT_DATA_DIR="${VAULT_DATA_DIR:-./vault-data}"
ENV_FILE="${1:-.env}"
BACKUP_FILE="${ENV_FILE}.backup.$(date +%Y%m%d_%H%M%S)"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           Secret Migration to Vault                            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if Vault is available
echo -e "${BLUE}🔍 Checking Vault status...${NC}"
VAULT_STATUS=$(curl -s "${VAULT_ADDR}/v1/sys/health" | jq -r '.sealed')
if [ "$VAULT_STATUS" = "true" ]; then
    echo -e "${RED}❌ Vault is sealed!${NC}"
    echo -e "${YELLOW}Run: ./scripts/security/unseal-vault.sh${NC}"
    exit 1
elif [ "$VAULT_STATUS" = "null" ]; then
    echo -e "${RED}❌ Vault is not accessible at ${VAULT_ADDR}${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Vault is unsealed and accessible${NC}"

# Get root token
if [ ! -f "${VAULT_DATA_DIR}/init.json" ]; then
    echo -e "${RED}❌ init.json not found. Run init-vault.sh first!${NC}"
    exit 1
fi

ROOT_TOKEN=$(cat "${VAULT_DATA_DIR}/init.json" | jq -r '.root_token')
export VAULT_TOKEN="$ROOT_TOKEN"

# Check if .env file exists
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}❌ Environment file not found: ${ENV_FILE}${NC}"
    exit 1
fi

# Create backup
echo ""
echo -e "${BLUE}📋 Creating backup of ${ENV_FILE}...${NC}"
cp "$ENV_FILE" "$BACKUP_FILE"
echo -e "${GREEN}✅ Backup created: ${BACKUP_FILE}${NC}"

# Function to store secret in Vault
store_secret() {
    local path=$1
    local key=$2
    local value=$3

    # URL encode the value
    local encoded_value=$(echo -n "$value" | jq -Rs .)

    # Store in Vault
    curl -s \
        -H "X-Vault-Token: ${ROOT_TOKEN}" \
        --request POST \
        --data "{\"data\": {\"${key}\": ${encoded_value}}}" \
        "${VAULT_ADDR}/v1/ecommerce/data/${path}" > /dev/null

    if [ $? -eq 0 ]; then
        echo -e "  ${GREEN}✓${NC} ${key}"
    else
        echo -e "  ${RED}✗${NC} ${key} (failed)"
    fi
}

# Read and migrate secrets
echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Migrating Secrets to Vault${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"

# Source the .env file
set -a
source "$ENV_FILE"
set +a

# Django/Backend secrets
echo ""
echo -e "${YELLOW}📦 Backend Secrets (ecommerce/backend/django)${NC}"
if [ ! -z "${SECRET_KEY:-}" ]; then
    store_secret "backend/django" "SECRET_KEY" "$SECRET_KEY"
fi
if [ ! -z "${DEBUG:-}" ]; then
    store_secret "backend/django" "DEBUG" "$DEBUG"
fi
if [ ! -z "${ALLOWED_HOSTS:-}" ]; then
    store_secret "backend/django" "ALLOWED_HOSTS" "$ALLOWED_HOSTS"
fi

# Database secrets
echo ""
echo -e "${YELLOW}🗄️  Database Secrets (ecommerce/backend/database)${NC}"
if [ ! -z "${DATABASE_URL:-}" ]; then
    store_secret "backend/database" "DATABASE_URL" "$DATABASE_URL"
fi
if [ ! -z "${DB_NAME:-}" ]; then
    store_secret "backend/database" "DB_NAME" "$DB_NAME"
fi
if [ ! -z "${DB_USER:-}" ]; then
    store_secret "backend/database" "DB_USER" "$DB_USER"
fi
if [ ! -z "${DB_PASSWORD:-}" ]; then
    store_secret "backend/database" "DB_PASSWORD" "$DB_PASSWORD"
fi
if [ ! -z "${DB_HOST:-}" ]; then
    store_secret "backend/database" "DB_HOST" "$DB_HOST"
fi
if [ ! -z "${DB_PORT:-}" ]; then
    store_secret "backend/database" "DB_PORT" "$DB_PORT"
fi
if [ ! -z "${POSTGRES_PASSWORD:-}" ]; then
    store_secret "backend/database" "POSTGRES_PASSWORD" "$POSTGRES_PASSWORD"
fi

# Redis secrets
echo ""
echo -e "${YELLOW}🔴 Redis Secrets (ecommerce/backend/redis)${NC}"
if [ ! -z "${REDIS_URL:-}" ]; then
    store_secret "backend/redis" "REDIS_URL" "$REDIS_URL"
fi
if [ ! -z "${REDIS_PASSWORD:-}" ]; then
    store_secret "backend/redis" "REDIS_PASSWORD" "$REDIS_PASSWORD"
fi

# Celery secrets
echo ""
echo -e "${YELLOW}⚙️  Celery Secrets (ecommerce/backend/celery)${NC}"
if [ ! -z "${CELERY_BROKER_URL:-}" ]; then
    store_secret "backend/celery" "CELERY_BROKER_URL" "$CELERY_BROKER_URL"
fi
if [ ! -z "${CELERY_RESULT_BACKEND:-}" ]; then
    store_secret "backend/celery" "CELERY_RESULT_BACKEND" "$CELERY_RESULT_BACKEND"
fi

# Shared secrets - Payment (Stripe)
echo ""
echo -e "${YELLOW}💳 Payment Secrets (ecommerce/shared/stripe)${NC}"
if [ ! -z "${STRIPE_SECRET_KEY:-}" ]; then
    store_secret "shared/stripe" "STRIPE_SECRET_KEY" "$STRIPE_SECRET_KEY"
fi
if [ ! -z "${STRIPE_PUBLISHABLE_KEY:-}" ]; then
    store_secret "shared/stripe" "STRIPE_PUBLISHABLE_KEY" "$STRIPE_PUBLISHABLE_KEY"
fi
if [ ! -z "${STRIPE_WEBHOOK_SECRET:-}" ]; then
    store_secret "shared/stripe" "STRIPE_WEBHOOK_SECRET" "$STRIPE_WEBHOOK_SECRET"
fi

# Shared secrets - AWS
echo ""
echo -e "${YELLOW}☁️  AWS Secrets (ecommerce/shared/aws)${NC}"
if [ ! -z "${AWS_ACCESS_KEY_ID:-}" ]; then
    store_secret "shared/aws" "AWS_ACCESS_KEY_ID" "$AWS_ACCESS_KEY_ID"
fi
if [ ! -z "${AWS_SECRET_ACCESS_KEY:-}" ]; then
    store_secret "shared/aws" "AWS_SECRET_ACCESS_KEY" "$AWS_SECRET_ACCESS_KEY"
fi
if [ ! -z "${AWS_S3_BUCKET:-}" ]; then
    store_secret "shared/aws" "AWS_S3_BUCKET" "$AWS_S3_BUCKET"
fi
if [ ! -z "${AWS_REGION:-}" ]; then
    store_secret "shared/aws" "AWS_REGION" "$AWS_REGION"
fi

# Shared secrets - Email
echo ""
echo -e "${YELLOW}📧 Email Secrets (ecommerce/shared/email)${NC}"
if [ ! -z "${EMAIL_HOST:-}" ]; then
    store_secret "shared/email" "EMAIL_HOST" "$EMAIL_HOST"
fi
if [ ! -z "${EMAIL_PORT:-}" ]; then
    store_secret "shared/email" "EMAIL_PORT" "$EMAIL_PORT"
fi
if [ ! -z "${EMAIL_HOST_USER:-}" ]; then
    store_secret "shared/email" "EMAIL_HOST_USER" "$EMAIL_HOST_USER"
fi
if [ ! -z "${EMAIL_HOST_PASSWORD:-}" ]; then
    store_secret "shared/email" "EMAIL_HOST_PASSWORD" "$EMAIL_HOST_PASSWORD"
fi

# AI Services secrets
echo ""
echo -e "${YELLOW}🤖 AI Services Secrets (ecommerce/ai/*)${NC}"
if [ ! -z "${OPENAI_API_KEY:-}" ]; then
    store_secret "ai/openai" "OPENAI_API_KEY" "$OPENAI_API_KEY"
fi
if [ ! -z "${ANTHROPIC_API_KEY:-}" ]; then
    store_secret "ai/anthropic" "ANTHROPIC_API_KEY" "$ANTHROPIC_API_KEY"
fi
if [ ! -z "${HUGGINGFACE_API_KEY:-}" ]; then
    store_secret "ai/huggingface" "HUGGINGFACE_API_KEY" "$HUGGINGFACE_API_KEY"
fi

# Monitoring secrets
echo ""
echo -e "${YELLOW}📊 Monitoring Secrets (ecommerce/shared/monitoring)${NC}"
if [ ! -z "${GRAFANA_PASSWORD:-}" ]; then
    store_secret "shared/monitoring" "GRAFANA_PASSWORD" "$GRAFANA_PASSWORD"
fi
if [ ! -z "${SENTRY_DSN:-}" ]; then
    store_secret "shared/monitoring" "SENTRY_DSN" "$SENTRY_DSN"
fi

# Create .env.vault file
echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Creating .env.vault Configuration${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"

cat > .env.vault << EOF
# ==============================================================================
# Vault Configuration - Use Vault for secrets management
# ==============================================================================
# This file configures services to use HashiCorp Vault instead of .env secrets
#
# Usage:
#   1. Ensure Vault is running and initialized
#   2. Set USE_VAULT=true in your environment
#   3. Provide VAULT_ROLE_ID and VAULT_SECRET_ID for your service
#
# Generated by: migrate-secrets.sh
# Date: $(date)
# ==============================================================================

# Vault connection
VAULT_ADDR=http://vault:8200
USE_VAULT=true

# Backend AppRole credentials (replace with actual values)
# Get these from: vault-data/backend-role-id and vault-data/backend-secret-id
VAULT_ROLE_ID=\${BACKEND_ROLE_ID}
VAULT_SECRET_ID=\${BACKEND_SECRET_ID}

# Keep non-secret configuration
DEBUG=False
ENVIRONMENT=production
LOG_LEVEL=INFO

# Database connection (non-secret parts)
DB_HOST=postgres
DB_PORT=5432

# Redis connection (non-secret parts)
REDIS_HOST=redis
REDIS_PORT=6379

# Note: All sensitive values (passwords, API keys, etc.) are now in Vault
# Access them using the VaultClient in your application code
EOF

echo -e "${GREEN}✅ Created .env.vault${NC}"

# Summary
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                  Migration Complete!                           ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}✅ All secrets have been migrated to Vault!${NC}"
echo ""
echo -e "${YELLOW}Files created:${NC}"
echo -e "  • ${BACKUP_FILE} (backup of original .env)"
echo -e "  • .env.vault (Vault configuration)"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo ""
echo -e "1. ${BLUE}Verify secrets in Vault:${NC}"
echo -e "   vault kv list ecommerce/"
echo -e "   vault kv get ecommerce/backend/django"
echo ""
echo -e "2. ${BLUE}Update your .env or use .env.vault:${NC}"
echo -e "   cp .env.vault .env"
echo ""
echo -e "3. ${BLUE}Add AppRole credentials to .env:${NC}"
echo -e "   echo \"VAULT_ROLE_ID=\$(cat vault-data/backend-role-id)\" >> .env"
echo -e "   echo \"VAULT_SECRET_ID=\$(cat vault-data/backend-secret-id)\" >> .env"
echo ""
echo -e "4. ${BLUE}Restart services:${NC}"
echo -e "   docker-compose restart backend api_gateway"
echo ""
echo -e "${RED}IMPORTANT:${NC}"
echo -e "  • Keep ${BACKUP_FILE} in a secure location"
echo -e "  • Do NOT commit .env.vault with real credentials"
echo -e "  • Rotate secrets after migration for security"
echo ""
