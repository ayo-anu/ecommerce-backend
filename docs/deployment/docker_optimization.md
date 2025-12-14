# Docker Build Optimization Guide

## Overview

This document outlines the Docker build optimizations implemented across the e-commerce platform to dramatically reduce build times and image sizes.

## Problems Solved

### Before Optimization

| Issue | Impact |
|-------|--------|
| Shared monolithic `requirements.txt` (190 packages) | All services installed ALL dependencies |
| API Gateway installing ML frameworks | 15-20 min build time for lightweight service |
| Single-stage Dockerfiles | Build tools in production images (~500MB overhead) |
| No dependency isolation | Changing one package rebuilds everything |
| No `.dockerignore` files | Large build contexts slow transfers |

### After Optimization

| Improvement | Benefit |
|-------------|---------|
| Per-service requirements files | Only install what each service needs |
| API Gateway: ~20 packages (was 190) | 2-3 min builds (was 15-20 min) |
| Multi-stage builds across all services | 200-500MB smaller images |
| Isolated dependencies | Change isolation, better caching |
| `.dockerignore` files | Faster context transfers |

## Architecture

### Requirements Structure

```
ai-services/
├── requirements-base.txt          # Shared base (FastAPI, Redis, etc.)
├── requirements.txt               # DEPRECATED - DO NOT USE
├── api_gateway/
│   └── requirements.txt          # ~20 packages (minimal)
└── services/
    ├── recommendation_engine/
    │   └── requirements.txt      # ~60 packages (ML basics)
    ├── visual_recognition/
    │   └── requirements.txt      # ~40 packages (OpenCV, PyTorch)
    ├── chatbot_rag/
    │   └── requirements.txt      # ~50 packages (Transformers, NLP)
    ├── search_engine/
    │   └── requirements.txt      # ~55 packages (Elasticsearch, NLP)
    ├── pricing_engine/
    │   └── requirements.txt      # ~45 packages (ML, optimization)
    ├── fraud_detection/
    │   └── requirements.txt      # ~45 packages (ML, anomaly detection)
    └── demand_forecasting/
        └── requirements.txt      # ~55 packages (Prophet, time series)
```

### Dockerfile Pattern

All AI services now use a standardized multi-stage build:

```dockerfile
# Stage 1: Builder - Install dependencies with build tools
FROM python:3.11-slim AS builder
WORKDIR /build
RUN apt-get update && apt-get install -y gcc g++ python3-dev
RUN python -m venv /opt/venv
COPY services/SERVICE_NAME/requirements.txt ./
RUN pip install -r requirements.txt

# Stage 2: Runtime - Minimal production image
FROM python:3.11-slim AS runtime
COPY --from=builder /opt/venv /opt/venv  # NO build tools
COPY services/SERVICE_NAME/ /app/
USER appuser
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "PORT"]
```

## Build Performance

### Estimated Build Times

| Service | Before | After | Improvement |
|---------|--------|-------|-------------|
| API Gateway | 15-20 min | 2-3 min | **85% faster** |
| Recommendation Engine | 15-20 min | 6-8 min | **60% faster** |
| Visual Recognition | 15-20 min | 4-6 min | **70% faster** |
| Chatbot RAG | 15-20 min | 5-7 min | **65% faster** |
| Search Engine | 15-20 min | 5-7 min | **65% faster** |
| Pricing Engine | 15-20 min | 4-6 min | **70% faster** |
| Fraud Detection | 15-20 min | 4-6 min | **70% faster** |
| Demand Forecasting | 15-20 min | 5-7 min | **65% faster** |

### Image Size Reduction

| Component | Before | After | Savings |
|-----------|--------|-------|---------|
| API Gateway | ~3-4 GB | ~600 MB | **85% smaller** |
| Visual Recognition | ~4-5 GB | ~2 GB | **60% smaller** |
| Other ML Services | ~3-4 GB | ~1.5 GB | **60% smaller** |
| Build tools overhead | ~500 MB | 0 MB | **100% removed** |

## Usage Guide

### Building Services

#### Build Individual Service

```bash
# Build specific service
docker-compose build gateway
docker-compose build recommender
docker-compose build vision
```

#### Build All Services

```bash
# Build all services in parallel (recommended)
docker-compose build --parallel

# Build with no cache (force rebuild)
docker-compose build --no-cache --parallel
```

#### Build with BuildKit (faster, better caching)

```bash
# Enable BuildKit for better performance
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# Build with BuildKit
docker-compose build --parallel
```

### Testing Builds Locally

```bash
# Test API Gateway build
cd ai-services
docker build -f api_gateway/Dockerfile -t test-gateway .

# Test recommendation engine build
docker build -f services/recommendation_engine/Dockerfile -t test-recommender .

# Test visual recognition build
docker build -f services/visual_recognition/Dockerfile -t test-vision .
```

### Verifying Optimizations

#### Check Image Sizes

```bash
# List all images and their sizes
docker images | grep ecommerce

# Expected sizes (approximate):
# ecommerce-gateway:        ~600 MB
# ecommerce-recommender:    ~1.5 GB
# ecommerce-vision:         ~2 GB
# ecommerce-chatbot:        ~1.8 GB
# ecommerce-search:         ~1.8 GB
```

#### Verify No Build Tools in Runtime

```bash
# Check that gcc is NOT in production images
docker run --rm ecommerce-gateway which gcc
# Should output: nothing (gcc not found)

# Check that build tools are removed
docker run --rm ecommerce-vision dpkg -l | grep gcc
# Should output: nothing
```

#### Check Dependency Count

```bash
# Count installed packages in API Gateway
docker run --rm ecommerce-gateway pip list | wc -l
# Should be ~25-30 (not 200+)

# Count installed packages in Visual Recognition
docker run --rm ecommerce-vision pip list | wc -l
# Should be ~45-55 (not 200+)
```

## Best Practices

### 1. Adding New Dependencies

When adding a new dependency to a service:

```bash
# 1. Add to the service's requirements.txt
echo "new-package==1.0.0" >> ai-services/services/SERVICE_NAME/requirements.txt

# 2. If it's used by multiple services, consider adding to requirements-base.txt
echo "common-package==1.0.0" >> ai-services/requirements-base.txt

# 3. Rebuild only the affected service
docker-compose build SERVICE_NAME
```

### 2. Cache Optimization

```bash
# Docker layer caching works best when:
# 1. requirements.txt changes less frequently than code
# 2. BuildKit is enabled
# 3. Build context is minimal (via .dockerignore)

# Enable BuildKit for optimal caching
export DOCKER_BUILDKIT=1
```

### 3. Parallel Builds

```bash
# Always build in parallel to save time
docker-compose build --parallel

# On systems with limited resources, limit parallelism
docker-compose build --parallel --max-parallel 3
```

### 4. Cleaning Up

```bash
# Remove old images to save disk space
docker image prune -a

# Remove build cache (when troubleshooting)
docker builder prune -a

# Full cleanup (careful!)
docker system prune -a --volumes
```

## Troubleshooting

### Issue: Build fails with "No such file or directory"

**Cause:** Dockerfile is looking for requirements.txt in wrong location

**Solution:**
```bash
# Check that per-service requirements.txt exists
ls ai-services/services/SERVICE_NAME/requirements.txt

# If missing, create it:
cp ai-services/requirements-base.txt ai-services/services/SERVICE_NAME/requirements.txt
# Then add service-specific dependencies
```

### Issue: Module not found at runtime

**Cause:** Dependency not in service's requirements.txt

**Solution:**
```bash
# 1. Check which service needs the dependency
docker-compose logs SERVICE_NAME | grep "ModuleNotFoundError"

# 2. Add missing dependency to service's requirements.txt
echo "missing-package==1.0.0" >> ai-services/services/SERVICE_NAME/requirements.txt

# 3. Rebuild the service
docker-compose build SERVICE_NAME
```

### Issue: Build is still slow

**Possible causes:**
1. BuildKit not enabled
2. Build context too large
3. Cache invalidated

**Solutions:**
```bash
# Enable BuildKit
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# Check build context size
du -sh ai-services/

# Verify .dockerignore is working
docker build -f ai-services/api_gateway/Dockerfile ai-services/ 2>&1 | grep "Sending build context"
# Should be < 50MB, not GBs

# Force rebuild with cache
docker-compose build --pull SERVICE_NAME
```

## Migration Notes

### Deprecated Files

The following files are **DEPRECATED** and should not be used:

- `services/ai/requirements.txt` - Replaced by per-service requirements
- `services/ai/Dockerfile.template` - Replaced by per-service Dockerfiles
- Any references to `SERVICE_NAME` build args in docker-compose.yml

### Backward Compatibility

To revert to the old monolithic approach (not recommended):

```yaml
# docker-compose.yml (OLD WAY - DO NOT USE)
gateway:
  build:
    context: ./ai-services
    dockerfile: api_gateway/Dockerfile
# This will still work but defeats the optimization
```

## Performance Monitoring

### Track Build Times

```bash
# Time a build
time docker-compose build gateway

# Time full stack build
time docker-compose build --parallel

# Track build cache hits
docker build --progress=plain -f ai-services/api_gateway/Dockerfile ai-services/
```

### CI/CD Integration

For CI/CD pipelines (GitHub Actions, GitLab CI, etc.):

```yaml
# Example: GitHub Actions
- name: Build Docker images
  env:
    DOCKER_BUILDKIT: 1
    COMPOSE_DOCKER_CLI_BUILD: 1
  run: |
    docker-compose build --parallel

# Enable layer caching in CI
- name: Cache Docker layers
  uses: actions/cache@v3
  with:
    path: /tmp/.buildx-cache
    key: ${{ runner.os }}-buildx-${{ github.sha }}
    restore-keys: |
      ${{ runner.os }}-buildx-
```

## Summary

### Key Changes

1. ✅ Created `requirements-base.txt` for shared dependencies
2. ✅ Created per-service `requirements.txt` files (8 services)
3. ✅ Standardized all Dockerfiles with multi-stage builds
4. ✅ Updated `docker-compose.yml` with correct build paths
5. ✅ Added `.dockerignore` files to reduce build context
6. ✅ Removed unnecessary dependencies (e.g., nltk from backend)

### Expected Results

- **Build time reduction:** 60-85% faster
- **Image size reduction:** 60-85% smaller
- **Disk space savings:** 15-20 GB for full stack
- **Network transfer savings:** 80% less data to push/pull

### Verification Checklist

- [ ] All services build successfully
- [ ] Image sizes are significantly smaller
- [ ] No build tools (gcc, g++) in production images
- [ ] Services run correctly with isolated dependencies
- [ ] Build cache works effectively (second build is faster)
- [ ] `.dockerignore` reduces build context size

## Support

For questions or issues with Docker optimization:

1. Check this documentation first
2. Verify you're using BuildKit (`export DOCKER_BUILDKIT=1`)
3. Check build logs for specific errors
4. Verify dependency requirements files are correct
5. Test builds individually before building the full stack

---

**Last Updated:** December 2024
**Optimizations By:** DevOps Team
**Estimated Time Savings:** 2-3 hours per day for development team
