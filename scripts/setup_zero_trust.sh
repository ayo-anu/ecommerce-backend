#!/bin/bash

# ==============================================================================
# Zero-Trust Service Authentication Setup Script
# ==============================================================================
# This script helps set up the zero-trust architecture
# ==============================================================================

set -e

echo "=========================================="
echo "Zero-Trust Setup Script"
echo "=========================================="
echo ""

# Check if we're in the project root
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    exit 1
fi

# Step 1: Generate service keys
echo "Step 1: Generating service authentication keys..."
echo ""

if [ ! -f "scripts/generate_service_keys.py" ]; then
    echo "❌ Error: scripts/generate_service_keys.py not found"
    exit 1
fi

python scripts/generate_service_keys.py > /tmp/service_keys.txt

echo "✅ Service keys generated!"
echo ""
echo "📋 Generated keys (saved to /tmp/service_keys.txt):"
echo "======================================================"
cat /tmp/service_keys.txt
echo ""
echo "======================================================"
echo ""

# Step 2: Prompt user to update .env file
echo "Step 2: Update environment file"
echo ""
echo "Please copy the generated keys into your environment file:"
echo "  - Development: infrastructure/env/.env.development"
echo "  - Production: infrastructure/env/.env.production"
echo ""
echo "The keys are also saved in: /tmp/service_keys.txt"
echo ""

read -p "Press Enter when you have updated the environment file..."
echo ""

# Step 3: Verify env directory exists
echo "Step 3: Verifying environment setup..."
echo ""

if [ ! -d "env" ]; then
    echo "❌ Error: env/ directory not found"
    echo "Creating env/ directory..."
    mkdir -p env
fi

# Check if per-service env files exist
ENV_FILES=(
    "env/recommender.env"
    "env/search.env"
    "env/pricing.env"
    "env/chatbot.env"
    "env/fraud.env"
    "env/forecasting.env"
    "env/vision.env"
    "env/gateway.env"
)

MISSING_FILES=()
for file in "${ENV_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        MISSING_FILES+=("$file")
    fi
done

if [ ${#MISSING_FILES[@]} -ne 0 ]; then
    echo "❌ Missing environment files:"
    for file in "${MISSING_FILES[@]}"; do
        echo "  - $file"
    done
    echo ""
    echo "Please ensure all per-service environment files exist."
    exit 1
fi

echo "✅ All per-service environment files exist"
echo ""

# Step 4: Verify main environment file
echo "Step 4: Checking main environment file..."
echo ""

ENV_FILE="${ENV_FILE:-infrastructure/env/.env.development}"

if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Error: Environment file not found: $ENV_FILE"
    exit 1
fi

echo "✅ Environment file found: $ENV_FILE"
echo ""

# Step 5: Check if secrets are configured
echo "Step 5: Verifying SERVICE_AUTH_SECRET configuration..."
echo ""

REQUIRED_SECRETS=(
    "SERVICE_AUTH_SECRET_API_GATEWAY"
    "SERVICE_AUTH_SECRET_RECOMMENDATION_ENGINE"
    "SERVICE_AUTH_SECRET_SEARCH_ENGINE"
    "SERVICE_AUTH_SECRET_PRICING_ENGINE"
    "SERVICE_AUTH_SECRET_CHATBOT_RAG"
    "SERVICE_AUTH_SECRET_FRAUD_DETECTION"
    "SERVICE_AUTH_SECRET_FORECASTING"
    "SERVICE_AUTH_SECRET_VISUAL_RECOGNITION"
)

MISSING_SECRETS=()
for secret in "${REQUIRED_SECRETS[@]}"; do
    if ! grep -q "^${secret}=" "$ENV_FILE"; then
        MISSING_SECRETS+=("$secret")
    elif grep -q "^${secret}=REPLACE_WITH_GENERATED_KEY_FROM_SCRIPT" "$ENV_FILE"; then
        MISSING_SECRETS+=("$secret (placeholder not replaced)")
    fi
done

if [ ${#MISSING_SECRETS[@]} -ne 0 ]; then
    echo "⚠️  Warning: Some secrets are not configured in $ENV_FILE:"
    for secret in "${MISSING_SECRETS[@]}"; do
        echo "  - $secret"
    done
    echo ""
    echo "Please update these secrets with values from /tmp/service_keys.txt"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "✅ All SERVICE_AUTH_SECRET variables configured"
fi

echo ""

# Step 6: Start services
echo "Step 6: Starting services..."
echo ""

read -p "Start services with docker-compose? (y/N) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Starting services..."
    ENV_FILE=$ENV_FILE docker-compose up -d
    echo ""
    echo "✅ Services started!"
    echo ""

    # Wait for services to be ready
    echo "Waiting for services to be ready (30 seconds)..."
    sleep 30

    # Step 7: Verify services
    echo "Step 7: Verifying service health..."
    echo ""

    SERVICES=(
        "gateway:8080"
        "recommender:8001"
        "search:8002"
        "pricing:8003"
        "chatbot:8004"
        "fraud:8005"
        "forecasting:8006"
        "vision:8007"
    )

    for service in "${SERVICES[@]}"; do
        name="${service%%:*}"
        port="${service##*:}"

        if curl -s -f "http://localhost:$port/health" > /dev/null; then
            echo "✅ $name (port $port) - healthy"
        else
            echo "❌ $name (port $port) - unhealthy or not started"
        fi
    done

    echo ""
    echo "=========================================="
    echo "Setup Complete!"
    echo "=========================================="
    echo ""
    echo "Your zero-trust architecture is now configured."
    echo ""
    echo "Next steps:"
    echo "  1. Run verification tests (see ZERO_TRUST_IMPLEMENTATION.md)"
    echo "  2. Test service authentication"
    echo "  3. Review logs: docker-compose logs -f"
    echo ""
    echo "For more information, see:"
    echo "  - ZERO_TRUST_IMPLEMENTATION.md"
    echo ""
else
    echo "Skipping service startup."
    echo ""
    echo "To start services manually, run:"
    echo "  ENV_FILE=$ENV_FILE docker-compose up -d"
    echo ""
fi

echo "Done!"
