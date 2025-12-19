#!/bin/bash
# ==============================================================================
# Vault Initialization Script
# ==============================================================================
# This script initializes HashiCorp Vault and sets up AppRole authentication
#
# Usage:
#   ./scripts/security/init-vault.sh
#
# What it does:
#   1. Initializes Vault (creates unseal keys and root token)
#   2. Unseals Vault
#   3. Enables KV v2 secrets engine
#   4. Enables audit logging
#   5. Creates policies for services
#   6. Enables AppRole authentication
#   7. Creates AppRoles for backend and AI services
#   8. Generates role IDs and secret IDs
#
# IMPORTANT:
#   - Run this script ONLY ONCE when first setting up Vault
#   - Save the unseal keys and root token in a secure location
#   - The init.json file contains sensitive data - protect it!
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
INIT_FILE="${VAULT_DATA_DIR}/init.json"
POLICIES_DIR="./deploy/vault/policies"

# Create data directory
mkdir -p "$VAULT_DATA_DIR"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       HashiCorp Vault Initialization Script                   ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if Vault is available
echo -e "${BLUE}🔍 Checking Vault status...${NC}"
if ! curl -s "${VAULT_ADDR}/v1/sys/health" > /dev/null; then
    echo -e "${RED}❌ Vault is not accessible at ${VAULT_ADDR}${NC}"
    echo -e "${YELLOW}Make sure Vault is running: docker-compose -f deploy/docker/compose/base.yml -f deploy/docker/compose/vault.yml up -d vault${NC}"
    exit 1
fi

# Step 1: Initialize Vault
echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 1: Initialize Vault${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"

if [ -f "$INIT_FILE" ]; then
    echo -e "${YELLOW}⚠️  Vault already initialized (init.json exists)${NC}"
    echo -e "${YELLOW}   Using existing unseal keys and root token${NC}"
else
    echo -e "${GREEN}🔐 Initializing Vault with 5 key shares and threshold of 3...${NC}"

    # Initialize Vault
    curl -s \
        --request POST \
        --data '{"secret_shares": 5, "secret_threshold": 3}' \
        "${VAULT_ADDR}/v1/sys/init" > "$INIT_FILE"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Vault initialized successfully!${NC}"
        echo ""
        echo -e "${RED}═══════════════════════════════════════════════════════════════${NC}"
        echo -e "${RED}        IMPORTANT: SAVE THESE CREDENTIALS SECURELY!            ${NC}"
        echo -e "${RED}═══════════════════════════════════════════════════════════════${NC}"
        echo ""
        echo -e "${YELLOW}Unseal Keys:${NC}"
        cat "$INIT_FILE" | jq -r '.keys[]' | awk '{print "  " NR ". " $0}'
        echo ""
        echo -e "${YELLOW}Root Token:${NC}"
        echo "  $(cat "$INIT_FILE" | jq -r '.root_token')"
        echo ""
        echo -e "${RED}Store these credentials in a secure password manager!${NC}"
        echo -e "${RED}You will need them to unseal Vault after restarts.${NC}"
        echo -e "${RED}═══════════════════════════════════════════════════════════════${NC}"
        echo ""
        read -p "Press Enter to continue after saving the credentials..."
    else
        echo -e "${RED}❌ Failed to initialize Vault${NC}"
        exit 1
    fi
fi

# Step 2: Unseal Vault
echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 2: Unseal Vault${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"

# Check if Vault is sealed
SEALED=$(curl -s "${VAULT_ADDR}/v1/sys/seal-status" | jq -r '.sealed')

if [ "$SEALED" = "false" ]; then
    echo -e "${GREEN}✅ Vault is already unsealed${NC}"
else
    echo -e "${YELLOW}🔓 Unsealing Vault (requires 3 of 5 keys)...${NC}"

    # Unseal with first 3 keys
    for i in 0 1 2; do
        UNSEAL_KEY=$(cat "$INIT_FILE" | jq -r ".keys[$i]")
        echo -e "  Using unseal key $((i+1))/3..."

        curl -s \
            --request POST \
            --data "{\"key\": \"${UNSEAL_KEY}\"}" \
            "${VAULT_ADDR}/v1/sys/unseal" > /dev/null
    done

    # Verify unsealed
    SEALED=$(curl -s "${VAULT_ADDR}/v1/sys/seal-status" | jq -r '.sealed')
    if [ "$SEALED" = "false" ]; then
        echo -e "${GREEN}✅ Vault unsealed successfully!${NC}"
    else
        echo -e "${RED}❌ Failed to unseal Vault${NC}"
        exit 1
    fi
fi

# Get root token
ROOT_TOKEN=$(cat "$INIT_FILE" | jq -r '.root_token')
export VAULT_TOKEN="$ROOT_TOKEN"

# Step 3: Enable secrets engine
echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 3: Enable KV v2 Secrets Engine${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"

# Check if secrets engine is already enabled
if curl -s -H "X-Vault-Token: ${ROOT_TOKEN}" "${VAULT_ADDR}/v1/sys/mounts" | jq -e '.["ecommerce/"]' > /dev/null; then
    echo -e "${YELLOW}⚠️  KV v2 secrets engine already enabled at ecommerce/${NC}"
else
    echo -e "${GREEN}📦 Enabling KV v2 secrets engine at ecommerce/...${NC}"

    curl -s \
        -H "X-Vault-Token: ${ROOT_TOKEN}" \
        --request POST \
        --data '{"type": "kv", "options": {"version": "2"}}' \
        "${VAULT_ADDR}/v1/sys/mounts/ecommerce" > /dev/null

    echo -e "${GREEN}✅ KV v2 secrets engine enabled${NC}"
fi

# Step 4: Enable audit logging
echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 4: Enable Audit Logging${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"

# Check if audit is already enabled
if curl -s -H "X-Vault-Token: ${ROOT_TOKEN}" "${VAULT_ADDR}/v1/sys/audit" | jq -e '.["file/"]' > /dev/null; then
    echo -e "${YELLOW}⚠️  Audit logging already enabled${NC}"
else
    echo -e "${GREEN}📝 Enabling file-based audit logging...${NC}"

    curl -s \
        -H "X-Vault-Token: ${ROOT_TOKEN}" \
        --request POST \
        --data '{"type": "file", "options": {"file_path": "/vault/logs/audit.log"}}' \
        "${VAULT_ADDR}/v1/sys/audit/file" > /dev/null

    echo -e "${GREEN}✅ Audit logging enabled${NC}"
fi

# Step 5: Create policies
echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 5: Create Service Policies${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"

echo -e "${GREEN}📋 Creating policy: backend${NC}"
curl -s \
    -H "X-Vault-Token: ${ROOT_TOKEN}" \
    --request PUT \
    --data "{\"policy\": \"$(cat ${POLICIES_DIR}/backend-policy.hcl | sed 's/"/\\"/g' | tr '\n' ' ')\"}" \
    "${VAULT_ADDR}/v1/sys/policies/acl/backend" > /dev/null

echo -e "${GREEN}📋 Creating policy: ai-services${NC}"
curl -s \
    -H "X-Vault-Token: ${ROOT_TOKEN}" \
    --request PUT \
    --data "{\"policy\": \"$(cat ${POLICIES_DIR}/ai-services-policy.hcl | sed 's/"/\\"/g' | tr '\n' ' ')\"}" \
    "${VAULT_ADDR}/v1/sys/policies/acl/ai-services" > /dev/null

echo -e "${GREEN}📋 Creating policy: api-gateway${NC}"
curl -s \
    -H "X-Vault-Token: ${ROOT_TOKEN}" \
    --request PUT \
    --data "{\"policy\": \"$(cat ${POLICIES_DIR}/api-gateway-policy.hcl | sed 's/"/\\"/g' | tr '\n' ' ')\"}" \
    "${VAULT_ADDR}/v1/sys/policies/acl/api-gateway" > /dev/null

echo -e "${GREEN}✅ All policies created${NC}"

# Step 6: Enable AppRole auth
echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 6: Enable AppRole Authentication${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"

# Check if AppRole is already enabled
if curl -s -H "X-Vault-Token: ${ROOT_TOKEN}" "${VAULT_ADDR}/v1/sys/auth" | jq -e '.["approle/"]' > /dev/null; then
    echo -e "${YELLOW}⚠️  AppRole authentication already enabled${NC}"
else
    echo -e "${GREEN}🔑 Enabling AppRole authentication...${NC}"

    curl -s \
        -H "X-Vault-Token: ${ROOT_TOKEN}" \
        --request POST \
        --data '{"type": "approle"}' \
        "${VAULT_ADDR}/v1/sys/auth/approle" > /dev/null

    echo -e "${GREEN}✅ AppRole authentication enabled${NC}"
fi

# Step 7: Create AppRoles
echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 7: Create AppRoles for Services${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"

# Backend AppRole
echo -e "${GREEN}🔐 Creating AppRole: backend${NC}"
curl -s \
    -H "X-Vault-Token: ${ROOT_TOKEN}" \
    --request POST \
    --data '{"policies": ["backend"], "token_ttl": "1h", "token_max_ttl": "4h", "secret_id_ttl": "24h", "bind_secret_id": true}' \
    "${VAULT_ADDR}/v1/auth/approle/role/backend" > /dev/null

# AI Services AppRole
echo -e "${GREEN}🔐 Creating AppRole: ai-services${NC}"
curl -s \
    -H "X-Vault-Token: ${ROOT_TOKEN}" \
    --request POST \
    --data '{"policies": ["ai-services"], "token_ttl": "1h", "token_max_ttl": "4h", "secret_id_ttl": "24h", "bind_secret_id": true}' \
    "${VAULT_ADDR}/v1/auth/approle/role/ai-services" > /dev/null

# API Gateway AppRole
echo -e "${GREEN}🔐 Creating AppRole: api-gateway${NC}"
curl -s \
    -H "X-Vault-Token: ${ROOT_TOKEN}" \
    --request POST \
    --data '{"policies": ["api-gateway"], "token_ttl": "1h", "token_max_ttl": "4h", "secret_id_ttl": "24h", "bind_secret_id": true}' \
    "${VAULT_ADDR}/v1/auth/approle/role/api-gateway" > /dev/null

echo -e "${GREEN}✅ All AppRoles created${NC}"

# Step 8: Generate Role IDs and Secret IDs
echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 8: Generate Role IDs and Secret IDs${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"

# Backend
echo -e "${GREEN}📝 Generating credentials for backend...${NC}"
BACKEND_ROLE_ID=$(curl -s -H "X-Vault-Token: ${ROOT_TOKEN}" \
    "${VAULT_ADDR}/v1/auth/approle/role/backend/role-id" | jq -r '.data.role_id')

BACKEND_SECRET_ID=$(curl -s -H "X-Vault-Token: ${ROOT_TOKEN}" \
    --request POST \
    "${VAULT_ADDR}/v1/auth/approle/role/backend/secret-id" | jq -r '.data.secret_id')

echo "$BACKEND_ROLE_ID" > "${VAULT_DATA_DIR}/backend-role-id"
echo "$BACKEND_SECRET_ID" > "${VAULT_DATA_DIR}/backend-secret-id"

# AI Services
echo -e "${GREEN}📝 Generating credentials for ai-services...${NC}"
AI_ROLE_ID=$(curl -s -H "X-Vault-Token: ${ROOT_TOKEN}" \
    "${VAULT_ADDR}/v1/auth/approle/role/ai-services/role-id" | jq -r '.data.role_id')

AI_SECRET_ID=$(curl -s -H "X-Vault-Token: ${ROOT_TOKEN}" \
    --request POST \
    "${VAULT_ADDR}/v1/auth/approle/role/ai-services/secret-id" | jq -r '.data.secret_id')

echo "$AI_ROLE_ID" > "${VAULT_DATA_DIR}/ai-role-id"
echo "$AI_SECRET_ID" > "${VAULT_DATA_DIR}/ai-secret-id"

# API Gateway
echo -e "${GREEN}📝 Generating credentials for api-gateway...${NC}"
GATEWAY_ROLE_ID=$(curl -s -H "X-Vault-Token: ${ROOT_TOKEN}" \
    "${VAULT_ADDR}/v1/auth/approle/role/api-gateway/role-id" | jq -r '.data.role_id')

GATEWAY_SECRET_ID=$(curl -s -H "X-Vault-Token: ${ROOT_TOKEN}" \
    --request POST \
    "${VAULT_ADDR}/v1/auth/approle/role/api-gateway/secret-id" | jq -r '.data.secret_id')

echo "$GATEWAY_ROLE_ID" > "${VAULT_DATA_DIR}/gateway-role-id"
echo "$GATEWAY_SECRET_ID" > "${VAULT_DATA_DIR}/gateway-secret-id"

echo -e "${GREEN}✅ All credentials generated${NC}"

# Summary
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    Initialization Complete!                    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}✅ Vault has been successfully initialized and configured!${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo ""
echo -e "1. ${BLUE}Migrate secrets to Vault:${NC}"
echo -e "   ./scripts/security/migrate-secrets.sh"
echo ""
echo -e "2. ${BLUE}Update .env file with AppRole credentials:${NC}"
echo -e "   # Backend"
echo -e "   VAULT_ROLE_ID=${BACKEND_ROLE_ID}"
echo -e "   VAULT_SECRET_ID=${BACKEND_SECRET_ID}"
echo -e "   USE_VAULT=true"
echo ""
echo -e "3. ${BLUE}Restart services to use Vault:${NC}"
echo -e "   docker-compose restart backend api_gateway"
echo ""
echo -e "${RED}IMPORTANT:${NC}"
echo -e "  • Root token: ${ROOT_TOKEN}"
echo -e "  • Credentials stored in: ${VAULT_DATA_DIR}/"
echo -e "  • Keep these files secure and backed up!"
echo ""
