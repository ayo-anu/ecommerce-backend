#!/bin/bash
# Integration Test: Health Endpoints
# Tests that all services expose working health check endpoints

set -e

echo "=== Testing Health Endpoints ==="
echo ""

# Test backend health endpoint
echo "Testing backend health endpoint..."
BACKEND_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://backend:8000/health/)
if [ "$BACKEND_RESPONSE" != "200" ]; then
    echo "❌ Backend health check failed! HTTP $BACKEND_RESPONSE"
    exit 1
fi
echo "✅ Backend health endpoint returned HTTP 200"

# Test API Gateway health endpoint
echo "Testing API Gateway health endpoint..."
GATEWAY_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://api-gateway:8080/health)
if [ "$GATEWAY_RESPONSE" != "200" ]; then
    echo "❌ API Gateway health check failed! HTTP $GATEWAY_RESPONSE"
    exit 1
fi
echo "✅ API Gateway health endpoint returned HTTP 200"

echo ""
echo "🎉 All health endpoints are responding correctly!"
exit 0
