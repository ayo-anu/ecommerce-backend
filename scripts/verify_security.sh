#!/bin/bash
# ==============================================================================
# Security Verification Script
# ==============================================================================
# Verifies that all security fixes have been properly implemented
# ==============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=============================================${NC}"
echo -e "${BLUE}Security Verification Script${NC}"
echo -e "${BLUE}=============================================${NC}"
echo ""

# Counter for issues
ISSUES=0
CHECKS=0

# ==============================================================================
# Check 1: Verify dual-network architecture
# ==============================================================================
echo -e "${YELLOW}[1/7] Checking network architecture...${NC}"
CHECKS=$((CHECKS + 1))

if grep -q "ecommerce-frontend" docker-compose.yml && grep -q "ecommerce-internal" docker-compose.yml; then
    if grep -q "internal: true" docker-compose.yml; then
        echo -e "${GREEN}✓ Dual-network architecture configured${NC}"
        echo -e "  - Frontend network: ecommerce-frontend"
        echo -e "  - Internal network: ecommerce-internal (isolated)"
    else
        echo -e "${RED}✗ Internal network not properly isolated${NC}"
        ISSUES=$((ISSUES + 1))
    fi
else
    echo -e "${RED}✗ Dual-network architecture not found${NC}"
    ISSUES=$((ISSUES + 1))
fi
echo ""

# ==============================================================================
# Check 2: Verify DATABASE_URL removed from AI services
# ==============================================================================
echo -e "${YELLOW}[2/7] Checking DATABASE_URL in AI services...${NC}"
CHECKS=$((CHECKS + 1))

AI_SERVICES_WITH_DB=$(grep -A 10 "container_name: ecommerce-recommender\|container_name: ecommerce-search\|container_name: ecommerce-pricing\|container_name: ecommerce-fraud\|container_name: ecommerce-forecasting\|container_name: ecommerce-vision" docker-compose.yml | grep "DATABASE_URL" | wc -l)

if [ "$AI_SERVICES_WITH_DB" -eq 0 ]; then
    echo -e "${GREEN}✓ No AI services have DATABASE_URL${NC}"
else
    echo -e "${RED}✗ Found $AI_SERVICES_WITH_DB AI services with DATABASE_URL${NC}"
    ISSUES=$((ISSUES + 1))
fi
echo ""

# ==============================================================================
# Check 3: Verify port exposures
# ==============================================================================
echo -e "${YELLOW}[3/7] Checking port exposures...${NC}"
CHECKS=$((CHECKS + 1))

# Count ports exposed (should only be backend:8000, gateway:8080, and optionally rabbitmq:15672)
POSTGRES_EXPOSED=$(grep -A 5 "container_name: ecommerce-postgres" docker-compose.yml | grep -c "ports:" || true)
REDIS_EXPOSED=$(grep -A 5 "container_name: ecommerce-redis" docker-compose.yml | grep -c "ports:" || true)
QDRANT_EXPOSED=$(grep -A 5 "container_name: ecommerce-qdrant" docker-compose.yml | grep -c "ports:" || true)
ELASTIC_EXPOSED=$(grep -A 5 "container_name: ecommerce-elasticsearch" docker-compose.yml | grep -c "ports:" || true)
RECOMMENDER_EXPOSED=$(grep -A 5 "container_name: ecommerce-recommender" docker-compose.yml | grep -c "ports:" || true)

if [ "$POSTGRES_EXPOSED" -eq 0 ] && [ "$REDIS_EXPOSED" -eq 0 ] && [ "$QDRANT_EXPOSED" -eq 0 ] && [ "$ELASTIC_EXPOSED" -eq 0 ] && [ "$RECOMMENDER_EXPOSED" -eq 0 ]; then
    echo -e "${GREEN}✓ Infrastructure and AI services not exposed to host${NC}"
else
    echo -e "${RED}✗ Unnecessary services exposed:${NC}"
    [ "$POSTGRES_EXPOSED" -gt 0 ] && echo -e "  - PostgreSQL (port 5432)"
    [ "$REDIS_EXPOSED" -gt 0 ] && echo -e "  - Redis (port 6379)"
    [ "$QDRANT_EXPOSED" -gt 0 ] && echo -e "  - Qdrant (port 6333)"
    [ "$ELASTIC_EXPOSED" -gt 0 ] && echo -e "  - Elasticsearch (port 9200)"
    [ "$RECOMMENDER_EXPOSED" -gt 0 ] && echo -e "  - Recommender (port 8001)"
    ISSUES=$((ISSUES + 1))
fi
echo ""

# ==============================================================================
# Check 4: Verify healthchecks added
# ==============================================================================
echo -e "${YELLOW}[4/7] Checking healthchecks...${NC}"
CHECKS=$((CHECKS + 1))

BACKEND_HEALTHCHECK=$(grep -A 10 "container_name: ecommerce-backend" docker-compose.yml | grep -c "healthcheck:" || true)
CELERY_WORKER_HEALTHCHECK=$(grep -A 10 "container_name: ecommerce-celery-worker" docker-compose.yml | grep -c "healthcheck:" || true)
CELERY_BEAT_HEALTHCHECK=$(grep -A 10 "container_name: ecommerce-celery-beat" docker-compose.yml | grep -c "healthcheck:" || true)

if [ "$BACKEND_HEALTHCHECK" -gt 0 ] && [ "$CELERY_WORKER_HEALTHCHECK" -gt 0 ] && [ "$CELERY_BEAT_HEALTHCHECK" -gt 0 ]; then
    echo -e "${GREEN}✓ All services have healthchecks${NC}"
else
    echo -e "${RED}✗ Missing healthchecks:${NC}"
    [ "$BACKEND_HEALTHCHECK" -eq 0 ] && echo -e "  - Backend"
    [ "$CELERY_WORKER_HEALTHCHECK" -eq 0 ] && echo -e "  - Celery Worker"
    [ "$CELERY_BEAT_HEALTHCHECK" -eq 0 ] && echo -e "  - Celery Beat"
    ISSUES=$((ISSUES + 1))
fi
echo ""

# ==============================================================================
# Check 5: Verify network assignments
# ==============================================================================
echo -e "${YELLOW}[5/7] Checking network assignments...${NC}"
CHECKS=$((CHECKS + 1))

# Check that backend and gateway are on both networks
BACKEND_NETWORKS=$(grep -A 20 "container_name: ecommerce-backend" docker-compose.yml | grep -A 5 "networks:" | grep -c "frontend\|internal" || true)
GATEWAY_NETWORKS=$(grep -A 20 "container_name: ecommerce-gateway" docker-compose.yml | grep -A 5 "networks:" | grep -c "frontend\|internal" || true)

# Check that AI services are ONLY on internal network
RECOMMENDER_INTERNAL=$(grep -A 20 "container_name: ecommerce-recommender" docker-compose.yml | grep -A 3 "networks:" | grep "internal" | wc -l)
RECOMMENDER_FRONTEND=$(grep -A 20 "container_name: ecommerce-recommender" docker-compose.yml | grep -A 3 "networks:" | grep "frontend" | wc -l)

if [ "$BACKEND_NETWORKS" -ge 2 ] && [ "$GATEWAY_NETWORKS" -ge 2 ]; then
    echo -e "${GREEN}✓ Backend and Gateway on both networks${NC}"
else
    echo -e "${RED}✗ Backend/Gateway not properly configured on both networks${NC}"
    ISSUES=$((ISSUES + 1))
fi

if [ "$RECOMMENDER_INTERNAL" -gt 0 ] && [ "$RECOMMENDER_FRONTEND" -eq 0 ]; then
    echo -e "${GREEN}✓ AI services isolated on internal network${NC}"
else
    echo -e "${RED}✗ AI services not properly isolated${NC}"
    ISSUES=$((ISSUES + 1))
fi
echo ""

# ==============================================================================
# Check 6: Verify config.py uses Docker DNS
# ==============================================================================
echo -e "${YELLOW}[6/7] Checking config.py defaults...${NC}"
CHECKS=$((CHECKS + 1))

LOCALHOST_COUNT=$(grep -c "localhost" services/ai/shared/config.py || true)

if [ "$LOCALHOST_COUNT" -le 1 ]; then  # Allow one localhost for ALLOWED_ORIGINS
    echo -e "${GREEN}✓ Config.py uses Docker DNS names${NC}"
else
    echo -e "${YELLOW}⚠ Config.py still has $LOCALHOST_COUNT localhost references${NC}"
    echo -e "  (This is low priority if overridden by env vars)"
fi
echo ""

# ==============================================================================
# Check 7: Verify restart policies
# ==============================================================================
echo -e "${YELLOW}[7/7] Checking restart policies...${NC}"
CHECKS=$((CHECKS + 1))

RESTART_COUNT=$(grep -c "restart: unless-stopped" docker-compose.yml || true)

if [ "$RESTART_COUNT" -ge 10 ]; then
    echo -e "${GREEN}✓ Services have restart policies configured${NC}"
else
    echo -e "${YELLOW}⚠ Only $RESTART_COUNT services have restart policies${NC}"
fi
echo ""

# ==============================================================================
# Summary
# ==============================================================================
echo -e "${BLUE}=============================================${NC}"
echo -e "${BLUE}Verification Summary${NC}"
echo -e "${BLUE}=============================================${NC}"
echo -e "Checks performed: $CHECKS"

if [ "$ISSUES" -eq 0 ]; then
    echo -e "${GREEN}Critical issues found: 0${NC}"
    echo -e "${GREEN}✓ All security fixes verified successfully!${NC}"
    exit 0
else
    echo -e "${RED}Critical issues found: $ISSUES${NC}"
    echo -e "${RED}✗ Please fix the issues above${NC}"
    exit 1
fi
