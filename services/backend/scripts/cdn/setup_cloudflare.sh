#!/bin/bash
set -euo pipefail

##############################################################################
# Setup Cloudflare CDN
#
# This script provides instructions for setting up Cloudflare CDN
# for serving static files from S3.
#
# Note: Cloudflare setup is primarily done through their dashboard.
# This script provides guidance and can configure cache rules via API.
#
# Usage:
#   ./setup_cloudflare.sh
#
# Environment variables required:
#   CLOUDFLARE_API_TOKEN - Cloudflare API token
#   CLOUDFLARE_ZONE_ID - Zone ID for your domain
#   CDN_DOMAIN - Your CDN subdomain (e.g., cdn.example.com)
##############################################################################

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[NOTE]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

echo ""
echo "=========================================="
echo "Cloudflare CDN Setup Guide"
echo "=========================================="
echo ""

log_info "Cloudflare CDN offers excellent performance with a generous free tier."
echo ""

log_step "1. Create a CNAME record for your CDN subdomain"
echo "   - Log in to Cloudflare dashboard"
echo "   - Go to DNS settings for your domain"
echo "   - Add a CNAME record:"
echo "     Name: cdn (or your preferred subdomain)"
echo "     Target: ${AWS_STORAGE_BUCKET_NAME:-your-bucket}.s3.amazonaws.com"
echo "     Proxy status: Proxied (orange cloud)"
echo ""

log_step "2. Configure Page Rules for optimal caching"
echo "   - Go to Rules → Page Rules"
echo "   - Create a new page rule:"
echo "     URL: cdn.yourdomain.com/static/*"
echo "     Settings:"
echo "       - Cache Level: Cache Everything"
echo "       - Edge Cache TTL: 1 year"
echo "       - Browser Cache TTL: 1 year"
echo ""

log_step "3. Enable Performance Features"
echo "   - Speed → Optimization"
echo "     ✓ Auto Minify (CSS, JavaScript)"
echo "     ✓ Brotli compression"
echo "     ✓ HTTP/2"
echo "     ✓ HTTP/3 (QUIC)"
echo ""

log_step "4. Configure Security Settings"
echo "   - SSL/TLS → Overview: Full (strict)"
echo "   - SSL/TLS → Edge Certificates: Always Use HTTPS"
echo ""

# If API token is available, configure via API
if [ -n "${CLOUDFLARE_API_TOKEN:-}" ] && [ -n "${CLOUDFLARE_ZONE_ID:-}" ]; then
    log_info "API credentials detected. Configuring cache rules via API..."

    # Create page rule for static assets
    curl -X POST "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}/pagerules" \
        -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
        -H "Content-Type: application/json" \
        --data '{
            "targets": [
                {
                    "target": "url",
                    "constraint": {
                        "operator": "matches",
                        "value": "'${CDN_DOMAIN:-cdn.example.com}'/static/*"
                    }
                }
            ],
            "actions": [
                {
                    "id": "cache_level",
                    "value": "cache_everything"
                },
                {
                    "id": "edge_cache_ttl",
                    "value": 31536000
                },
                {
                    "id": "browser_cache_ttl",
                    "value": 31536000
                }
            ],
            "status": "active"
        }' | jq '.'

    log_info "Page rule created successfully via API"
else
    log_warn "To configure via API, set:"
    echo "  - CLOUDFLARE_API_TOKEN (from Cloudflare dashboard → My Profile → API Tokens)"
    echo "  - CLOUDFLARE_ZONE_ID (from domain overview page)"
    echo "  - CDN_DOMAIN (your CDN subdomain, e.g., cdn.example.com)"
fi

echo ""
log_step "5. Update your Django settings"
echo "   Add to .env:"
echo "   USE_CDN=true"
echo "   CDN_DOMAIN=cdn.yourdomain.com"
echo ""

log_step "6. Deploy static files"
echo "   Run: ./scripts/cdn/deploy_static_files.sh"
echo ""

log_step "7. Purge Cloudflare cache (when deploying updates)"
echo "   - Cloudflare dashboard → Caching → Purge Cache"
echo "   - Or via API:"
echo '   curl -X POST "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}/purge_cache" \'
echo '     -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \'
echo '     -H "Content-Type: application/json" \'
echo '     --data '"'"'{"purge_everything":true}'"'"
echo ""

log_info "Cloudflare setup guide complete!"
log_info "Visit: https://dash.cloudflare.com/ to configure your CDN"
