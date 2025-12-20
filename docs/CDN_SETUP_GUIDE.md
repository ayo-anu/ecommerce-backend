# CDN Setup Guide

## Overview

This guide covers the setup and configuration of a Content Delivery Network (CDN) for serving static assets (CSS, JavaScript, images) to reduce latency for global users.

**Benefits:**
- **Performance**: Global edge caching reduces latency (target: <100ms globally)
- **Scalability**: Offload static file serving from application servers
- **Cost**: Reduce bandwidth costs on origin servers
- **Security**: DDoS protection and SSL/TLS termination at the edge

---

## Supported CDN Providers

### 1. AWS CloudFront
- **Best for**: AWS-centric infrastructure, tight S3 integration
- **Free tier**: 1 TB data transfer out, 10M HTTP/HTTPS requests
- **Pricing**: Pay-as-you-go after free tier
- **Setup complexity**: Medium (requires AWS knowledge)

### 2. Cloudflare
- **Best for**: Ease of use, generous free tier
- **Free tier**: Unlimited bandwidth, global CDN
- **Pricing**: Free for most use cases
- **Setup complexity**: Low (user-friendly dashboard)

### 3. Local/Development
- **Best for**: Development, testing, CI/CD environments
- **Uses**: WhiteNoise for serving static files locally
- **Setup complexity**: None (default)

---

## Architecture

```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │ 1. Request static file
       ▼
┌─────────────┐
│     CDN     │ (CloudFront/Cloudflare)
│  Edge Cache │
└──────┬──────┘
       │ 2. Cache miss → Fetch from origin
       ▼
┌─────────────┐
│  S3 Bucket  │ (Origin)
│ Static Files│
└──────┬──────┘
       │ 3. Upload via deployment
       ▼
┌─────────────┐
│   Django    │
│ collectstatic│
└─────────────┘
```

---

## Quick Start

### Option 1: Local/Development (Default)

No setup required. Static files are served by WhiteNoise.

```bash
# .env
USE_S3=false
USE_CDN=false
```

### Option 2: S3 without CDN

```bash
# .env
USE_S3=true
USE_CDN=false
AWS_STORAGE_BUCKET_NAME=your-bucket-name
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_S3_REGION_NAME=us-east-1
```

### Option 3: S3 + CloudFront CDN

```bash
# 1. Create CloudFront distribution
cd services/backend
./scripts/cdn/setup_cloudfront.sh

# 2. Update .env with output
USE_S3=true
USE_CDN=true
AWS_STORAGE_BUCKET_NAME=your-bucket-name
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
CDN_DOMAIN=d1234567890.cloudfront.net
CDN_DISTRIBUTION_ID=E1234567890ABC

# 3. Deploy static files
./scripts/cdn/deploy_static_files.sh production

# 4. Test CDN delivery
./scripts/cdn/test_cdn_delivery.sh d1234567890.cloudfront.net
```

### Option 4: S3 + Cloudflare CDN

```bash
# 1. Setup Cloudflare (follow instructions)
cd services/backend
./scripts/cdn/setup_cloudflare.sh

# 2. Update .env
USE_S3=true
USE_CDN=true
AWS_STORAGE_BUCKET_NAME=your-bucket-name
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
CDN_DOMAIN=cdn.yourdomain.com

# 3. Deploy static files
./scripts/cdn/deploy_static_files.sh production

# 4. Test CDN delivery
./scripts/cdn/test_cdn_delivery.sh cdn.yourdomain.com
```

---

## Detailed Setup: AWS CloudFront

### Prerequisites

1. AWS account with appropriate permissions
2. S3 bucket for static files
3. AWS CLI installed and configured

### Step 1: Create S3 Bucket

```bash
# Create bucket
aws s3 mb s3://your-ecommerce-static --region us-east-1

# Configure bucket for public read (static files only)
aws s3api put-bucket-policy --bucket your-ecommerce-static --policy file://bucket-policy.json
```

**bucket-policy.json:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::your-ecommerce-static/static/*"
    }
  ]
}
```

### Step 2: Create CloudFront Distribution

```bash
cd services/backend
./scripts/cdn/setup_cloudfront.sh
```

This script creates a CloudFront distribution with:
- HTTPS enforcement
- HTTP/2 and HTTP/3 support
- Brotli/Gzip compression
- Optimized cache settings
- Global edge locations

**Expected output:**
```
Distribution ID: E1234567890ABC
Distribution Domain: d1234567890.cloudfront.net
```

### Step 3: Configure Django Settings

Add to `.env.production`:
```bash
USE_S3=true
USE_CDN=true
AWS_STORAGE_BUCKET_NAME=your-ecommerce-static
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_S3_REGION_NAME=us-east-1
CDN_DOMAIN=d1234567890.cloudfront.net
CDN_DISTRIBUTION_ID=E1234567890ABC
```

### Step 4: Deploy Static Files

```bash
# First time: collect and upload all static files
python manage.py collectstatic --noinput
./scripts/cdn/deploy_static_files.sh production

# Subsequent deployments
./scripts/cdn/deploy_static_files.sh production
```

### Step 5: Verify Setup

```bash
# Test CDN delivery and cache headers
./scripts/cdn/test_cdn_delivery.sh d1234567890.cloudfront.net

# Check specific file
curl -I https://d1234567890.cloudfront.net/static/admin/css/base.css
```

**Expected headers:**
```
HTTP/2 200
cache-control: max-age=31536000, public, immutable
content-encoding: gzip
x-cache: Hit from cloudfront
```

---

## Detailed Setup: Cloudflare

### Prerequisites

1. Domain registered and added to Cloudflare
2. S3 bucket for static files
3. Cloudflare account (free tier sufficient)

### Step 1: Create S3 Bucket

Same as CloudFront setup (see above).

### Step 2: Configure DNS in Cloudflare

1. Log in to Cloudflare dashboard
2. Select your domain
3. Go to **DNS** tab
4. Add CNAME record:
   - **Name**: `cdn`
   - **Target**: `your-ecommerce-static.s3.amazonaws.com`
   - **Proxy status**: Proxied (orange cloud) ✓
   - **TTL**: Auto

### Step 3: Configure Page Rules

1. Go to **Rules** → **Page Rules**
2. Create page rule for static assets:
   - **URL**: `cdn.yourdomain.com/static/*`
   - **Cache Level**: Cache Everything
   - **Edge Cache TTL**: 1 year
   - **Browser Cache TTL**: 1 year

### Step 4: Enable Performance Features

1. Go to **Speed** → **Optimization**
2. Enable:
   - ✓ Auto Minify (CSS, JavaScript)
   - ✓ Brotli compression
   - ✓ HTTP/2
   - ✓ HTTP/3 (QUIC)

### Step 5: Configure SSL/TLS

1. Go to **SSL/TLS** → **Overview**
2. Set to **Full (strict)**
3. Go to **Edge Certificates**
4. Enable **Always Use HTTPS**

### Step 6: Configure Django Settings

Add to `.env.production`:
```bash
USE_S3=true
USE_CDN=true
AWS_STORAGE_BUCKET_NAME=your-ecommerce-static
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
CDN_DOMAIN=cdn.yourdomain.com
```

### Step 7: Deploy and Test

```bash
# Deploy static files
./scripts/cdn/deploy_static_files.sh production

# Test CDN delivery
./scripts/cdn/test_cdn_delivery.sh cdn.yourdomain.com
```

---

## Cache Strategy

### Static Files (CSS, JS, Fonts)

**Cache Duration**: 1 year (31,536,000 seconds)

```
Cache-Control: max-age=31536000, public, immutable
```

**Rationale**:
- Static files have versioned/hashed filenames (e.g., `main.a3f5b8c2.css`)
- Changes result in new filenames → automatic cache busting
- Safe to cache indefinitely

### Media Files (User Uploads)

**Cache Duration**: 24 hours (86,400 seconds)

```
Cache-Control: max-age=86400, public
```

**Rationale**:
- Media files can be updated
- Balance between performance and freshness
- Shorter cache for frequently changing content

### Private Files

**Cache Duration**: No cache

```
Cache-Control: no-cache, no-store, must-revalidate
```

**Rationale**:
- Sensitive content
- Served via signed URLs
- Should not be cached

---

## Cache Invalidation

### CloudFront

**Automatic** (via deployment script):
```bash
./scripts/cdn/deploy_static_files.sh production
```

**Manual**:
```bash
aws cloudfront create-invalidation \
  --distribution-id E1234567890ABC \
  --paths "/static/*"
```

**Cost**: First 1,000 invalidations per month are free, $0.005 per path after.

### Cloudflare

**Via Dashboard**:
1. Go to **Caching** → **Purge Cache**
2. Select **Purge Everything** or **Custom Purge**

**Via API**:
```bash
curl -X POST "https://api.cloudflare.com/client/v4/zones/${ZONE_ID}/purge_cache" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  --data '{"purge_everything":true}'
```

**Cost**: Free (unlimited purges)

---

## Monitoring

### Key Metrics

1. **Cache Hit Rate**: >90% target
2. **Response Time**: <100ms globally
3. **Bandwidth Usage**: Track data transfer costs
4. **Error Rate**: 4xx/5xx errors

### CloudFront Metrics

```bash
# Get distribution statistics
aws cloudfront get-distribution --id E1234567890ABC

# CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/CloudFront \
  --metric-name Requests \
  --dimensions Name=DistributionId,Value=E1234567890ABC \
  --start-time 2025-01-01T00:00:00Z \
  --end-time 2025-01-02T00:00:00Z \
  --period 3600 \
  --statistics Sum
```

### Cloudflare Analytics

1. Go to **Analytics & Logs** → **Traffic**
2. View:
   - Requests over time
   - Bandwidth usage
   - Cache ratio
   - Top content

---

## Troubleshooting

### Issue: Static files not loading

**Symptoms**: 404 errors for static files

**Solutions**:
1. Verify files uploaded to S3:
   ```bash
   aws s3 ls s3://your-bucket/static/ --recursive
   ```
2. Check bucket policy allows public read
3. Verify CDN_DOMAIN in .env matches actual domain
4. Test direct S3 access first (without CDN)

### Issue: Old cached files served

**Symptoms**: Changes not reflecting after deployment

**Solutions**:
1. Invalidate CDN cache:
   ```bash
   # CloudFront
   aws cloudfront create-invalidation --distribution-id E123 --paths "/*"

   # Cloudflare (purge all)
   curl -X POST "https://api.cloudflare.com/client/v4/zones/${ZONE_ID}/purge_cache" \
     -H "Authorization: Bearer ${TOKEN}" \
     --data '{"purge_everything":true}'
   ```
2. Verify cache headers are correct
3. Check browser cache (hard refresh: Ctrl+Shift+R)

### Issue: Slow performance

**Symptoms**: Static files load slowly

**Solutions**:
1. Test CDN response time:
   ```bash
   ./scripts/cdn/test_cdn_delivery.sh your-cdn-domain
   ```
2. Verify compression is enabled (gzip/brotli)
3. Check CDN coverage (are edge locations near users?)
4. Enable HTTP/2 and HTTP/3

### Issue: High costs

**Symptoms**: Unexpected CDN bills

**Solutions**:
1. Review cache hit rate (should be >90%)
2. Optimize image sizes (use WebP, lazy loading)
3. Enable compression
4. Consider switching to Cloudflare (free tier)
5. Set up AWS billing alerts

---

## Security Considerations

### 1. HTTPS Enforcement

**CloudFront**:
- Set `ViewerProtocolPolicy: redirect-to-https`
- Minimum TLS version: TLSv1.2

**Cloudflare**:
- Enable "Always Use HTTPS"
- Set SSL/TLS to "Full (strict)"

### 2. Access Control

**Public static assets**:
- CSS, JavaScript, fonts: Public read
- CDN caching enabled

**Private media files**:
- Use `PrivateMediaStorage` backend
- Serve via signed URLs
- No CDN caching

### 3. CORS Configuration

If serving assets to external domains, configure CORS:

```python
# settings/production.py
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=31536000, public, immutable',
}

# S3 bucket CORS configuration
[{
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET", "HEAD"],
    "AllowedOrigins": ["https://yourdomain.com"],
    "ExposeHeaders": [],
    "MaxAgeSeconds": 3000
}]
```

### 4. Content Security Policy (CSP)

Update CSP headers to allow CDN domain:

```python
# settings/production.py
CSP_DEFAULT_SRC = ["'self'", "https://cdn.yourdomain.com"]
CSP_STYLE_SRC = ["'self'", "'unsafe-inline'", "https://cdn.yourdomain.com"]
CSP_SCRIPT_SRC = ["'self'", "https://cdn.yourdomain.com"]
CSP_IMG_SRC = ["'self'", "data:", "https://cdn.yourdomain.com"]
```

---

## Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Cache Hit Rate | >90% | CDN analytics |
| Global Load Time | <100ms | CDN edge metrics |
| Compression Ratio | >70% | Response headers |
| HTTPS | 100% | Force HTTPS redirect |
| HTTP/2 or higher | 100% | Protocol usage |

---

## Cost Estimates

### AWS CloudFront

**Free Tier** (first 12 months):
- 1 TB data transfer out
- 10M HTTP/HTTPS requests
- 2M CloudFront Function invocations

**After free tier** (approximate):
- $0.085/GB data transfer (first 10 TB/month)
- $0.0075 per 10,000 HTTP requests
- $0.01 per 10,000 HTTPS requests

**Example**: 100GB/month + 1M requests = ~$9/month

### Cloudflare

**Free Tier**:
- Unlimited bandwidth
- Unlimited requests
- Global CDN
- DDoS protection

**Pro Plan** ($20/month):
- All free features
- Image optimization
- Mobile optimization
- Advanced cache rules

**Recommendation**: Start with free tier

---

## Integration with CI/CD

### GitHub Actions

Add CDN deployment to your workflow:

```yaml
# .github/workflows/deploy.yml
- name: Deploy static files to CDN
  env:
    AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
    AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
    AWS_STORAGE_BUCKET_NAME: ${{ secrets.AWS_STORAGE_BUCKET_NAME }}
    CDN_DISTRIBUTION_ID: ${{ secrets.CDN_DISTRIBUTION_ID }}
  run: |
    ./services/backend/scripts/cdn/deploy_static_files.sh production
```

### Docker Deployment

Include in your deployment process:

```bash
# deploy.sh
docker-compose exec backend python manage.py collectstatic --noinput
docker-compose exec backend ./scripts/cdn/deploy_static_files.sh production
```

---

## Maintenance

### Regular Tasks

1. **Monitor cache hit rate** (weekly)
   - Target: >90%
   - If lower, investigate cache configuration

2. **Review costs** (monthly)
   - Check data transfer usage
   - Optimize if needed

3. **Test CDN performance** (monthly)
   ```bash
   ./scripts/cdn/test_cdn_delivery.sh your-cdn-domain
   ```

4. **Update SSL certificates** (automatic for CloudFront/Cloudflare)

### Updating CDN Configuration

When changing cache settings:

1. Update settings (CloudFront distribution or Cloudflare page rules)
2. Deploy changes
3. Invalidate cache
4. Test with `test_cdn_delivery.sh`
5. Monitor metrics for 24 hours

---

## Additional Resources

### Documentation

- [AWS CloudFront Documentation](https://docs.aws.amazon.com/cloudfront/)
- [Cloudflare CDN Documentation](https://developers.cloudflare.com/cache/)
- [Django Storages Documentation](https://django-storages.readthedocs.io/)

### Tools

- [WebPageTest](https://www.webpagetest.org/) - Test global performance
- [GTmetrix](https://gtmetrix.com/) - Performance analysis
- [KeyCDN Tools](https://tools.keycdn.com/) - CDN testing utilities

### Support

- AWS Support: Via AWS Console
- Cloudflare Community: https://community.cloudflare.com/
- Django Storages: GitHub Issues

---

**Document Owner**: DevOps Team
**Last Updated**: 2025-12-20
**Status**: Ready for Use
