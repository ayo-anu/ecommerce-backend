# CDN Deployment Scripts

This directory contains scripts for deploying and managing static assets via CDN (CloudFront or Cloudflare).

## Scripts Overview

### 1. `deploy_static_files.sh`

Deploys static files to S3 and invalidates CDN cache.

**Usage:**
```bash
./deploy_static_files.sh [environment]
```

**What it does:**
1. Collects Django static files
2. Uploads to S3 with optimized cache headers
3. Invalidates CloudFront distribution (if configured)
4. Verifies deployment

**Required environment variables:**
- `AWS_STORAGE_BUCKET_NAME`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `CDN_DISTRIBUTION_ID` (optional, for CloudFront invalidation)

**Example:**
```bash
# Deploy to production
./deploy_static_files.sh production

# Deploy with custom env file
AWS_STORAGE_BUCKET_NAME=my-bucket ./deploy_static_files.sh
```

---

### 2. `setup_cloudfront.sh`

Creates an AWS CloudFront distribution for your S3 bucket.

**Usage:**
```bash
./setup_cloudfront.sh
```

**What it does:**
1. Creates CloudFront distribution with optimal settings
2. Configures HTTPS, HTTP/2, compression
3. Sets up caching rules
4. Returns distribution ID and domain

**Required environment variables:**
- `AWS_STORAGE_BUCKET_NAME`
- `AWS_S3_REGION_NAME` (default: us-east-1)

**Output:**
```
Distribution ID: E1234567890ABC
Distribution Domain: d1234567890.cloudfront.net
```

Add these to your `.env`:
```bash
CDN_DOMAIN=d1234567890.cloudfront.net
CDN_DISTRIBUTION_ID=E1234567890ABC
```

---

### 3. `setup_cloudflare.sh`

Provides instructions and optionally configures Cloudflare CDN via API.

**Usage:**
```bash
./setup_cloudflare.sh
```

**What it does:**
1. Displays step-by-step setup instructions
2. Configures page rules via API (if credentials provided)
3. Guides through Cloudflare dashboard setup

**Optional environment variables** (for API configuration):
- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ZONE_ID`
- `CDN_DOMAIN`

**Manual setup:**
Follow the on-screen instructions to configure via Cloudflare dashboard.

---

### 4. `test_cdn_delivery.sh`

Tests CDN configuration and verifies proper caching.

**Usage:**
```bash
./test_cdn_delivery.sh <cdn_domain>
```

**What it tests:**
1. HTTP status codes
2. Cache headers (max-age, cache-control)
3. Compression (gzip/brotli)
4. HTTPS enforcement
5. CDN-specific headers
6. Response time

**Example:**
```bash
# Test CloudFront
./test_cdn_delivery.sh d1234567890.cloudfront.net

# Test Cloudflare
./test_cdn_delivery.sh cdn.yourdomain.com
```

**Expected output:**
```
========================================
CDN Delivery Test Suite
========================================
✓ HTTP Status: 200 OK
✓ Cache-Control: max-age=31536000, public, immutable
✓ Compression: gzip
✓ HTTPS: Enabled
✓ CDN Header detected
✓ Average response time: 0.089s
========================================
Test Summary
========================================
Tests Passed: 15
Tests Failed: 0
```

---

## Quick Start

### For CloudFront:

```bash
# 1. Setup CloudFront distribution
./setup_cloudfront.sh

# 2. Update .env with output from step 1
# USE_CDN=true
# CDN_DOMAIN=d1234567890.cloudfront.net
# CDN_DISTRIBUTION_ID=E1234567890ABC

# 3. Deploy static files
./deploy_static_files.sh production

# 4. Test
./test_cdn_delivery.sh d1234567890.cloudfront.net
```

### For Cloudflare:

```bash
# 1. Setup Cloudflare (follow instructions)
./setup_cloudflare.sh

# 2. Update .env
# USE_CDN=true
# CDN_DOMAIN=cdn.yourdomain.com

# 3. Deploy static files
./deploy_static_files.sh production

# 4. Test
./test_cdn_delivery.sh cdn.yourdomain.com
```

---

## Environment Variables

### Required for S3:
```bash
AWS_STORAGE_BUCKET_NAME=your-bucket-name
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_S3_REGION_NAME=us-east-1  # optional, default: us-east-1
```

### Required for CDN:
```bash
USE_CDN=true
CDN_DOMAIN=d1234567890.cloudfront.net  # or cdn.yourdomain.com
```

### Optional for CloudFront:
```bash
CDN_DISTRIBUTION_ID=E1234567890ABC  # for automatic cache invalidation
```

### Optional for Cloudflare API:
```bash
CLOUDFLARE_API_TOKEN=your-api-token
CLOUDFLARE_ZONE_ID=your-zone-id
```

---

## Deployment Workflow

### Initial Setup (One-time)

1. **Choose CDN provider** (CloudFront or Cloudflare)
2. **Run setup script** (`setup_cloudfront.sh` or `setup_cloudflare.sh`)
3. **Configure environment variables** in `.env`
4. **Deploy static files** for the first time

### Regular Deployments

Whenever you update static files (CSS, JS, etc.):

```bash
# 1. Deploy (collects, uploads, invalidates cache)
./deploy_static_files.sh production

# 2. Verify
./test_cdn_delivery.sh your-cdn-domain
```

### CI/CD Integration

Add to your deployment pipeline:

```yaml
# .github/workflows/deploy.yml
- name: Deploy static files to CDN
  run: |
    cd services/backend
    ./scripts/cdn/deploy_static_files.sh production
```

---

## Troubleshooting

### Files not uploading

**Check:**
1. AWS credentials are valid
2. Bucket exists and you have write permissions
3. Bucket name in `.env` is correct

**Test:**
```bash
aws s3 ls s3://your-bucket/
```

### Cache not invalidating

**CloudFront:**
- Ensure `CDN_DISTRIBUTION_ID` is set
- Check AWS permissions for CloudFront invalidation
- Manual invalidation: AWS Console → CloudFront → Invalidations

**Cloudflare:**
- Go to Cloudflare dashboard → Caching → Purge Cache
- Or use API (see `setup_cloudflare.sh` for command)

### Old files still served

**Solutions:**
1. Hard refresh browser (Ctrl+Shift+R)
2. Invalidate CDN cache
3. Check file actually uploaded to S3:
   ```bash
   aws s3 ls s3://your-bucket/static/ --recursive
   ```

### Test script fails

**Common issues:**
1. CDN domain incorrect
2. Files not yet uploaded
3. CDN still deploying (wait 15-20 min for CloudFront)

---

## Performance Tips

### 1. Optimize cache hit rate

- Use versioned filenames (Django does this automatically)
- Set long cache expiry (we use 1 year)
- Don't invalidate unless necessary

### 2. Enable compression

- CloudFront: Automatic with our setup
- Cloudflare: Enable in dashboard (Speed → Optimization)

### 3. Use HTTP/2 or HTTP/3

- CloudFront: Enabled in our setup
- Cloudflare: Enable in dashboard (Network settings)

### 4. Monitor performance

```bash
# Regular testing
./test_cdn_delivery.sh your-cdn-domain

# Check cache hit rate
# CloudFront: CloudWatch metrics
# Cloudflare: Analytics dashboard
```

---

## Security Best Practices

1. **Never commit credentials** to git
   - Use `.env` files (gitignored)
   - Or use environment variables in CI/CD

2. **Use IAM roles** when possible
   - EC2 instances, ECS tasks, Lambda
   - Avoid hardcoded AWS keys

3. **Limit S3 bucket permissions**
   - Public read for `static/*` only
   - Private for `media/private/*`

4. **Enable HTTPS only**
   - Redirect HTTP to HTTPS
   - TLS 1.2+ only

5. **Monitor access logs**
   - CloudFront access logs
   - S3 access logs
   - Cloudflare analytics

---

## Cost Optimization

### CloudFront

1. **Use price class wisely**
   - Price Class 100: NA, Europe (cheapest)
   - Price Class All: Global coverage (most expensive)
   - We use Price Class 100 by default

2. **Optimize invalidations**
   - First 1,000/month are free
   - Use wildcard paths: `/static/*` vs individual files
   - Consider versioned URLs instead of invalidations

3. **Monitor data transfer**
   - Set up billing alerts
   - Review CloudWatch metrics monthly

### Cloudflare

1. **Use free tier** (usually sufficient)
   - Unlimited bandwidth
   - Global CDN
   - Basic DDoS protection

2. **Upgrade only if needed**
   - Pro: $20/month (image optimization, mobile optimization)
   - Business: $200/month (advanced features)

---

## Additional Resources

- [Full CDN Setup Guide](../../../docs/CDN_SETUP_GUIDE.md)
- [AWS CloudFront Docs](https://docs.aws.amazon.com/cloudfront/)
- [Cloudflare CDN Docs](https://developers.cloudflare.com/cache/)

---

**Questions or issues?**
- Check the [CDN Setup Guide](../../../docs/CDN_SETUP_GUIDE.md)
- Review Django logs: `logs/django.log`
- Test with: `./test_cdn_delivery.sh`
