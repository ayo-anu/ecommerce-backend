#!/bin/bash

# Sentry Setup Script
# This script helps you configure Sentry for all services

set -e

echo "========================================="
echo "Sentry Configuration Setup"
echo "========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env files exist
check_env_file() {
    local file=$1
    if [ ! -f "$file" ]; then
        echo -e "${RED}Error: $file not found${NC}"
        echo "Please create it from .env.example first"
        exit 1
    fi
}

# Update environment variable in file
update_env_var() {
    local file=$1
    local var=$2
    local value=$3

    if grep -q "^${var}=" "$file"; then
        # Variable exists, update it
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s|^${var}=.*|${var}=${value}|" "$file"
        else
            sed -i "s|^${var}=.*|${var}=${value}|" "$file"
        fi
        echo -e "${GREEN}✓${NC} Updated $var in $file"
    else
        # Variable doesn't exist, add it
        echo "${var}=${value}" >> "$file"
        echo -e "${GREEN}✓${NC} Added $var to $file"
    fi
}

echo "This script will help you configure Sentry DSN for all services."
echo ""
echo -e "${YELLOW}Before starting, make sure you have:${NC}"
echo "1. Created a Sentry account at https://sentry.io"
echo "2. Created projects for each service"
echo "3. Copied the DSN from each project"
echo ""

read -p "Do you want to continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

# Backend
echo ""
echo "========================================="
echo "1. Backend (Django)"
echo "========================================="
read -p "Enter Sentry DSN for Backend: " BACKEND_DSN
if [ ! -z "$BACKEND_DSN" ]; then
    check_env_file "services/backend/.env"
    update_env_var "services/backend/.env" "SENTRY_DSN" "$BACKEND_DSN"

    read -p "Enter environment (development/staging/production) [production]: " BACKEND_ENV
    BACKEND_ENV=${BACKEND_ENV:-production}
    update_env_var "services/backend/.env" "SENTRY_ENVIRONMENT" "$BACKEND_ENV"

    read -p "Enter traces sample rate (0.0-1.0) [0.1]: " BACKEND_SAMPLE
    BACKEND_SAMPLE=${BACKEND_SAMPLE:-0.1}
    update_env_var "services/backend/.env" "SENTRY_TRACES_SAMPLE_RATE" "$BACKEND_SAMPLE"
fi

# Gateway
echo ""
echo "========================================="
echo "2. API Gateway"
echo "========================================="
read -p "Enter Sentry DSN for Gateway: " GATEWAY_DSN
if [ ! -z "$GATEWAY_DSN" ]; then
    check_env_file "services/gateway/.env"
    update_env_var "services/gateway/.env" "SENTRY_DSN" "$GATEWAY_DSN"
fi

# AI Services
echo ""
echo "========================================="
echo "3. AI Services"
echo "========================================="
echo "You can use the same DSN for all AI services or different ones."
read -p "Use same DSN for all AI services? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    read -p "Enter Sentry DSN for all AI services: " AI_DSN
    if [ ! -z "$AI_DSN" ]; then
        for service in recommendation_engine search_engine pricing_engine chatbot_rag fraud_detection demand_forecasting visual_recognition; do
            env_file="services/ai/services/$service/.env"
            if [ -f "$env_file" ]; then
                update_env_var "$env_file" "SENTRY_DSN" "$AI_DSN"
            fi
        done
    fi
else
    # Individual DSNs
    for service in recommendation_engine search_engine pricing_engine chatbot_rag fraud_detection demand_forecasting visual_recognition; do
        echo ""
        echo "Service: $service"
        read -p "Enter Sentry DSN (or press Enter to skip): " SERVICE_DSN
        if [ ! -z "$SERVICE_DSN" ]; then
            env_file="services/ai/services/$service/.env"
            if [ -f "$env_file" ]; then
                update_env_var "$env_file" "SENTRY_DSN" "$SERVICE_DSN"
            fi
        fi
    done
fi

echo ""
echo "========================================="
echo "Configuration Complete!"
echo "========================================="
echo ""
echo -e "${GREEN}Next steps:${NC}"
echo "1. Restart your services:"
echo "   cd deploy/docker/compose"
echo "   docker-compose restart backend gateway"
echo ""
echo "2. Test Sentry integration:"
echo "   docker-compose exec backend python manage.py shell"
echo "   >>> from sentry_sdk import capture_message"
echo "   >>> capture_message('Test from backend')"
echo ""
echo "3. Check Sentry dashboard for test message"
echo ""
echo -e "${YELLOW}Note:${NC} Make sure to never commit .env files with real DSNs!"
echo ""
