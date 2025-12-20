#!/bin/bash
set -euo pipefail

##############################################################################
# Deploy Static Files to CDN
#
# This script:
# 1. Collects all static files
# 2. Uploads them to S3
# 3. Invalidates CDN cache (if CloudFront is configured)
#
# Usage:
#   ./deploy_static_files.sh [environment]
#
# Environment variables required:
#   AWS_ACCESS_KEY_ID
#   AWS_SECRET_ACCESS_KEY
#   AWS_STORAGE_BUCKET_NAME
#   CDN_DISTRIBUTION_ID (optional, for CloudFront invalidation)
##############################################################################

ENVIRONMENT="${1:-production}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Load environment variables
if [ -f "${PROJECT_ROOT}/.env.${ENVIRONMENT}" ]; then
    log_info "Loading environment from .env.${ENVIRONMENT}"
    export $(cat "${PROJECT_ROOT}/.env.${ENVIRONMENT}" | grep -v '^#' | xargs)
elif [ -f "${PROJECT_ROOT}/.env" ]; then
    log_info "Loading environment from .env"
    export $(cat "${PROJECT_ROOT}/.env" | grep -v '^#' | xargs)
else
    log_warn "No .env file found, using existing environment variables"
fi

# Validate required variables
if [ -z "${AWS_STORAGE_BUCKET_NAME:-}" ]; then
    log_error "AWS_STORAGE_BUCKET_NAME is not set"
    exit 1
fi

# Step 1: Collect static files
log_info "Collecting static files..."
cd "${PROJECT_ROOT}"
python manage.py collectstatic --noinput --clear

# Step 2: Upload to S3
log_info "Uploading static files to S3 bucket: ${AWS_STORAGE_BUCKET_NAME}"

# Upload with optimized cache headers
aws s3 sync staticfiles/ "s3://${AWS_STORAGE_BUCKET_NAME}/static/" \
    --delete \
    --cache-control "max-age=31536000, public, immutable" \
    --metadata-directive REPLACE \
    --exclude "*.html" \
    --exclude "admin/*"

# Upload HTML files with shorter cache (they might change)
aws s3 sync staticfiles/ "s3://${AWS_STORAGE_BUCKET_NAME}/static/" \
    --cache-control "max-age=3600, public" \
    --metadata-directive REPLACE \
    --exclude "*" \
    --include "*.html"

# Upload admin files separately (different cache strategy)
if [ -d "staticfiles/admin" ]; then
    aws s3 sync staticfiles/admin/ "s3://${AWS_STORAGE_BUCKET_NAME}/static/admin/" \
        --cache-control "max-age=86400, public" \
        --metadata-directive REPLACE
fi

log_info "Static files uploaded successfully"

# Step 3: Invalidate CDN cache (if CloudFront is configured)
if [ -n "${CDN_DISTRIBUTION_ID:-}" ]; then
    log_info "Invalidating CloudFront distribution: ${CDN_DISTRIBUTION_ID}"

    INVALIDATION_ID=$(aws cloudfront create-invalidation \
        --distribution-id "${CDN_DISTRIBUTION_ID}" \
        --paths "/static/*" \
        --query 'Invalidation.Id' \
        --output text)

    log_info "CloudFront invalidation created: ${INVALIDATION_ID}"
    log_info "Waiting for invalidation to complete..."

    aws cloudfront wait invalidation-completed \
        --distribution-id "${CDN_DISTRIBUTION_ID}" \
        --id "${INVALIDATION_ID}"

    log_info "CloudFront invalidation completed"
else
    log_warn "CDN_DISTRIBUTION_ID not set, skipping CloudFront invalidation"
    log_info "If using Cloudflare, purge cache manually or via API"
fi

# Step 4: Verify deployment
log_info "Verifying deployment..."
SAMPLE_FILE=$(find staticfiles -type f -name "*.css" | head -1)
if [ -n "${SAMPLE_FILE}" ]; then
    FILE_KEY="static/${SAMPLE_FILE#staticfiles/}"
    S3_URL="https://${AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/${FILE_KEY}"

    if curl -sI "${S3_URL}" | grep -q "200 OK"; then
        log_info "✓ Sample file accessible: ${S3_URL}"
    else
        log_warn "✗ Sample file not accessible: ${S3_URL}"
    fi
fi

log_info "Static file deployment completed successfully!"
log_info ""
log_info "Next steps:"
log_info "1. Verify static files are loading on your site"
log_info "2. Check browser DevTools Network tab for cache headers"
log_info "3. Test from multiple geographic locations"
