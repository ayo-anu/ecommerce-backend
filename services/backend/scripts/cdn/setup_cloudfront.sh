#!/bin/bash
set -euo pipefail

##############################################################################
# Setup AWS CloudFront Distribution for CDN
#
# This script creates a CloudFront distribution for serving static files
# from an S3 bucket with optimal caching and security settings.
#
# Usage:
#   ./setup_cloudfront.sh
#
# Environment variables required:
#   AWS_STORAGE_BUCKET_NAME - S3 bucket name
#   AWS_S3_REGION_NAME - S3 region (default: us-east-1)
##############################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

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
if [ -f "${PROJECT_ROOT}/.env" ]; then
    export $(cat "${PROJECT_ROOT}/.env" | grep -v '^#' | xargs)
fi

# Validate required variables
if [ -z "${AWS_STORAGE_BUCKET_NAME:-}" ]; then
    log_error "AWS_STORAGE_BUCKET_NAME is not set"
    exit 1
fi

AWS_S3_REGION_NAME="${AWS_S3_REGION_NAME:-us-east-1}"
S3_DOMAIN="${AWS_STORAGE_BUCKET_NAME}.s3.${AWS_S3_REGION_NAME}.amazonaws.com"

log_info "Creating CloudFront distribution for bucket: ${AWS_STORAGE_BUCKET_NAME}"

# Create CloudFront distribution configuration
DISTRIBUTION_CONFIG=$(cat <<EOF
{
  "CallerReference": "ecommerce-cdn-$(date +%s)",
  "Comment": "CDN for ecommerce static assets",
  "Enabled": true,
  "Origins": {
    "Quantity": 1,
    "Items": [
      {
        "Id": "S3-${AWS_STORAGE_BUCKET_NAME}",
        "DomainName": "${S3_DOMAIN}",
        "CustomOriginConfig": {
          "HTTPPort": 80,
          "HTTPSPort": 443,
          "OriginProtocolPolicy": "https-only",
          "OriginSslProtocols": {
            "Quantity": 1,
            "Items": ["TLSv1.2"]
          }
        },
        "ConnectionAttempts": 3,
        "ConnectionTimeout": 10
      }
    ]
  },
  "DefaultCacheBehavior": {
    "TargetOriginId": "S3-${AWS_STORAGE_BUCKET_NAME}",
    "ViewerProtocolPolicy": "redirect-to-https",
    "AllowedMethods": {
      "Quantity": 2,
      "Items": ["GET", "HEAD"],
      "CachedMethods": {
        "Quantity": 2,
        "Items": ["GET", "HEAD"]
      }
    },
    "Compress": true,
    "CachePolicyId": "658327ea-f89d-4fab-a63d-7e88639e58f6",
    "MinTTL": 0,
    "DefaultTTL": 86400,
    "MaxTTL": 31536000,
    "ForwardedValues": {
      "QueryString": false,
      "Cookies": {
        "Forward": "none"
      }
    }
  },
  "PriceClass": "PriceClass_100",
  "ViewerCertificate": {
    "CloudFrontDefaultCertificate": true,
    "MinimumProtocolVersion": "TLSv1.2_2021"
  },
  "HttpVersion": "http2and3"
}
EOF
)

# Create the distribution
log_info "Creating CloudFront distribution..."
DISTRIBUTION_OUTPUT=$(aws cloudfront create-distribution \
    --distribution-config "${DISTRIBUTION_CONFIG}" \
    --output json)

DISTRIBUTION_ID=$(echo "${DISTRIBUTION_OUTPUT}" | jq -r '.Distribution.Id')
DISTRIBUTION_DOMAIN=$(echo "${DISTRIBUTION_OUTPUT}" | jq -r '.Distribution.DomainName')

log_info "CloudFront distribution created successfully!"
log_info ""
log_info "Distribution ID: ${DISTRIBUTION_ID}"
log_info "Distribution Domain: ${DISTRIBUTION_DOMAIN}"
log_info ""
log_info "Add these to your .env file:"
log_info "CDN_DOMAIN=${DISTRIBUTION_DOMAIN}"
log_info "CDN_DISTRIBUTION_ID=${DISTRIBUTION_ID}"
log_info ""
log_info "Note: CloudFront distribution deployment takes 15-20 minutes."
log_info "Status: https://console.aws.amazon.com/cloudfront/home#distribution-settings:${DISTRIBUTION_ID}"
