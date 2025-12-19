#!/bin/bash
# ==============================================================================
# Vault Unseal Script
# ==============================================================================
# This script unseals HashiCorp Vault using the stored unseal keys
#
# Usage:
#   ./scripts/security/unseal-vault.sh
#
# Prerequisites:
#   - Vault must be initialized (init.json must exist)
#   - Vault must be running
#
# What it does:
#   1. Checks if Vault is sealed
#   2. Uses 3 of 5 unseal keys to unseal Vault
#   3. Verifies Vault is unsealed
#
# Note:
#   - Vault must be unsealed after every restart
#   - Consider implementing auto-unseal for production
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

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                  Vault Unseal Script                           ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if init file exists
if [ ! -f "$INIT_FILE" ]; then
    echo -e "${RED}❌ init.json not found at ${INIT_FILE}${NC}"
    echo -e "${YELLOW}Run init-vault.sh first to initialize Vault${NC}"
    exit 1
fi

# Check if Vault is accessible
echo -e "${BLUE}🔍 Checking Vault status...${NC}"
if ! curl -s "${VAULT_ADDR}/v1/sys/health" > /dev/null; then
    echo -e "${RED}❌ Vault is not accessible at ${VAULT_ADDR}${NC}"
    echo -e "${YELLOW}Make sure Vault is running:${NC}"
    echo -e "${YELLOW}  docker-compose -f deploy/docker/compose/base.yml -f deploy/docker/compose/vault.yml up -d vault${NC}"
    exit 1
fi

# Check seal status
SEAL_STATUS=$(curl -s "${VAULT_ADDR}/v1/sys/seal-status")
SEALED=$(echo "$SEAL_STATUS" | jq -r '.sealed')
PROGRESS=$(echo "$SEAL_STATUS" | jq -r '.progress')
THRESHOLD=$(echo "$SEAL_STATUS" | jq -r '.t')

if [ "$SEALED" = "false" ]; then
    echo -e "${GREEN}✅ Vault is already unsealed!${NC}"
    echo ""
    echo -e "${BLUE}Vault Status:${NC}"
    echo "$SEAL_STATUS" | jq '{sealed, initialized, cluster_name}'
    exit 0
fi

echo -e "${YELLOW}🔒 Vault is sealed${NC}"
echo -e "${BLUE}   Progress: ${PROGRESS}/${THRESHOLD} unseal keys provided${NC}"
echo ""

# Unseal Vault
echo -e "${BLUE}🔓 Unsealing Vault...${NC}"
echo -e "${YELLOW}   Using first ${THRESHOLD} of 5 unseal keys${NC}"
echo ""

for i in $(seq 0 $((THRESHOLD - 1))); do
    UNSEAL_KEY=$(cat "$INIT_FILE" | jq -r ".keys[$i]")

    echo -e "  ${BLUE}[$((i+1))/${THRESHOLD}]${NC} Providing unseal key..."

    RESULT=$(curl -s \
        --request POST \
        --data "{\"key\": \"${UNSEAL_KEY}\"}" \
        "${VAULT_ADDR}/v1/sys/unseal")

    SEALED=$(echo "$RESULT" | jq -r '.sealed')
    PROGRESS=$(echo "$RESULT" | jq -r '.progress')

    if [ "$SEALED" = "false" ]; then
        echo -e "  ${GREEN}✓${NC} Vault unsealed!"
        break
    else
        echo -e "  ${YELLOW}◌${NC} Progress: ${PROGRESS}/${THRESHOLD}"
    fi
done

# Verify unsealed
echo ""
SEAL_STATUS=$(curl -s "${VAULT_ADDR}/v1/sys/seal-status")
SEALED=$(echo "$SEAL_STATUS" | jq -r '.sealed')

if [ "$SEALED" = "false" ]; then
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                 Vault Unsealed Successfully!                   ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}Vault Status:${NC}"
    echo "$SEAL_STATUS" | jq '{sealed, initialized, cluster_name, version}'
    echo ""
    echo -e "${GREEN}✅ Vault is ready to use!${NC}"
else
    echo -e "${RED}❌ Failed to unseal Vault${NC}"
    echo "$SEAL_STATUS" | jq '.'
    exit 1
fi
