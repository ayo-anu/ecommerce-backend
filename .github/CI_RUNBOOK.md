# CI/CD Runbook

This document describes the CI/CD workflows for the ecommerce project and provides acceptance tests.

## Overview

The repository uses GitHub Actions for continuous integration and continuous deployment:

- **Backend CI** (`backend-ci.yml`) - Runs on PRs that modify backend code
- **AI Services CI** (`ai-services-ci.yml`) - Runs on PRs that modify AI services code
- **Docker Release** (`docker-release.yml`) - Runs on push to `main` to build and publish images

## Workflows

### Backend CI (`backend-ci.yml`)

**Triggers:**
- Pull requests modifying `backend/**` or workflow file
- Manual dispatch via Actions UI

**Jobs:**
1. **Lint & Tests** - Python 3.11, flake8, pip-audit, Django tests
2. **Dockerfile Lint** - Hadolint validation
3. **Build Sanity** - Docker build test with layer caching

**Requirements:**
- Python 3.11
- Dependencies from `backend/requirements/prod.txt` and `backend/requirements/tests.txt`
- Test environment variables (auto-configured for CI)

### AI Services CI (`ai-services-ci.yml`)

**Triggers:**
- Pull requests modifying `ai-services/**` or workflow file
- Manual dispatch via Actions UI

**Jobs:**
1. **Lint & Tests** - Python 3.11, flake8, pip-audit, pytest (if tests exist)
2. **Dockerfile Lint** - Hadolint validation
3. **Build Sanity** - Docker build test with layer caching

**Requirements:**
- Python 3.11
- Dependencies from `ai-services/api_gateway/requirements.txt`

### Docker Release (`docker-release.yml`)

**Triggers:**
- Push to `main` branch modifying `backend/**` or `ai-services/**`
- Manual dispatch via Actions UI

**Jobs:**
1. **Build & Push Backend** - Multi-arch build, push to GHCR
2. **Build & Push AI Gateway** - Multi-arch build, push to GHCR
3. **Release Summary** - Job summary with image tags

**Image Tags:**
- `ghcr.io/<owner>/<repo>-backend:latest`
- `ghcr.io/<owner>/<repo>-backend:sha-<short-sha>`
- `ghcr.io/<owner>/<repo>-ai-gateway:latest`
- `ghcr.io/<owner>/<repo>-ai-gateway:sha-<short-sha>`

**Authentication:**
- Uses `GITHUB_TOKEN` (auto-provided, no manual secrets needed)
- Pushes to GitHub Container Registry (ghcr.io)

## Developer Workflow

### Running CI Locally

**Backend:**
```bash
# Lint
cd backend
pip install flake8
flake8 apps config core --max-line-length=120 --exclude=migrations

# Security scan
pip install pip-audit
pip-audit --disable-pip

# Tests
export DJANGO_SETTINGS_MODULE=config.settings.development
export SECRET_KEY=test-secret-key-local
export DATABASE_URL=sqlite:///test.db
pytest -v

# Docker build
docker build -t backend-local:test -f backend/Dockerfile backend
```

**AI Services:**
```bash
# Lint
cd ai-services/api_gateway
pip install flake8
flake8 . --max-line-length=120

# Security scan
pip install pip-audit
pip-audit --disable-pip

# Tests (if available)
cd ../
pytest -v

# Docker build
docker build -t ai-gateway-local:test -f ai-services/api_gateway/Dockerfile ai-services
```

### Pull Request Workflow

1. Create feature branch from `main`
2. Make changes to backend or AI services
3. Push branch and open PR
4. CI workflows run automatically
5. Review CI results in PR checks
6. Fix any failing checks
7. Merge PR after approval and green CI

### Release Workflow

1. Merge PR to `main`
2. `docker-release.yml` runs automatically
3. Images built and pushed to GHCR with tags
4. Check Actions summary for image tags
5. Pull images in production:
   ```bash
   docker pull ghcr.io/<owner>/<repo>-backend:latest
   docker pull ghcr.io/<owner>/<repo>-ai-gateway:latest
   ```

## Caching Strategy

All workflows use GitHub Actions cache:
- **Pip cache** - Keyed by requirements file hash
- **Docker layer cache** - GitHub Actions cache backend
- **Concurrent builds** - Same PR branch cancels old runs

## Security

- No Vault tokens or production secrets in workflows
- `GITHUB_TOKEN` used for GHCR authentication (auto-scoped)
- Security scans via `pip-audit` on every PR
- Dockerfile linting via Hadolint
- Non-root user in production images
- Multi-stage builds for minimal attack surface

## Troubleshooting

### CI Failing on Lint

**Problem:** flake8 errors in PR checks

**Solution:**
```bash
# Run locally and fix
flake8 backend/apps backend/config backend/core --max-line-length=120
# Common fixes: remove unused imports, fix line length, add blank lines
```

### CI Failing on Tests

**Problem:** Django tests fail in CI but pass locally

**Solution:**
- Check environment variables are set correctly
- Use SQLite for CI tests (no Postgres required)
- Run with same settings: `DJANGO_SETTINGS_MODULE=config.settings.development`

### Docker Build Failing

**Problem:** Docker build fails in CI

**Solution:**
- Test locally: `docker build -f backend/Dockerfile backend`
- Check Dockerfile uses correct requirements path
- Verify multi-stage build copies files correctly
- Check hadolint output for Dockerfile issues

### Image Push Permission Denied

**Problem:** Cannot push to GHCR

**Solution:**
- Ensure repository has Packages write permission in workflow
- Check `GITHUB_TOKEN` has correct scopes (auto-configured)
- Verify image name uses correct repository owner

## Acceptance Tests

### Backend CI

**Test 1: Lint Check**
```bash
# Create a PR with Python linting issues
# Expected: CI fails on flake8 step
# Fix issues and push
# Expected: CI passes
```

**Test 2: Security Scan**
```bash
# CI runs pip-audit automatically
# Expected: Audit runs but doesn't fail build (info only)
```

**Test 3: Tests**
```bash
# Create PR with failing test
# Expected: CI fails on test step
# Fix test and push
# Expected: CI passes
```

**Test 4: Docker Build**
```bash
# Create PR that modifies backend code
# Expected: Docker build completes successfully
# Check build uses cache (faster on subsequent runs)
```

### AI Services CI

**Test 1: Lint Check**
```bash
# Create PR modifying ai-services with lint issues
# Expected: CI fails on flake8 step
```

**Test 2: Docker Build**
```bash
# Create PR modifying ai-services
# Expected: Docker build completes for AI Gateway
```

### Docker Release

**Test 1: Manual Release**
```bash
# Go to Actions tab → Docker Release (CD) → Run workflow
# Select branch: main
# Expected: Images built and pushed to GHCR with both tags (latest + sha)
```

**Test 2: Automatic Release on Merge**
```bash
# Merge a PR that modifies backend or ai-services to main
# Expected: Docker Release workflow triggers automatically
# Expected: Images pushed to GHCR
```

**Test 3: Image Pull**
```bash
# After successful release:
docker pull ghcr.io/<owner>/<repo>-backend:latest
docker pull ghcr.io/<owner>/<repo>-ai-gateway:latest
# Expected: Images download successfully
```

**Test 4: Image Tags**
```bash
# Check both tags exist:
docker pull ghcr.io/<owner>/<repo>-backend:latest
docker pull ghcr.io/<owner>/<repo>-backend:sha-abc1234
# Expected: Both tags work and point to same image SHA
```

### Workflow Integration

**Test 1: PR Changes Only Backend**
```bash
# Create PR changing only backend/
# Expected: Only backend-ci.yml runs
# Expected: ai-services-ci.yml does NOT run
```

**Test 2: PR Changes Only AI Services**
```bash
# Create PR changing only ai-services/
# Expected: Only ai-services-ci.yml runs
# Expected: backend-ci.yml does NOT run
```

**Test 3: PR Changes Both**
```bash
# Create PR changing both backend/ and ai-services/
# Expected: Both CI workflows run in parallel
```

**Test 4: Merge to Main Triggers Release**
```bash
# Merge PR to main
# Expected: docker-release.yml runs
# Expected: Both images built and pushed
```

## Monitoring

- Check workflow status: Repository → Actions tab
- View workflow runs: Click on workflow name
- Check job logs: Click on job name → View logs
- Review artifacts: Available in workflow run summary (if configured)

## Maintenance

### Update Python Version

Edit all three workflow files and change:
```yaml
python-version: '3.11'
```

### Update Docker Base Image

Edit Dockerfiles in:
- `backend/Dockerfile`
- `ai-services/api_gateway/Dockerfile`

### Add New Service

1. Create new Dockerfile in service directory
2. Copy and adapt `ai-services-ci.yml`
3. Add build job to `docker-release.yml`

## Support

- Workflow issues: Check Actions logs
- Docker issues: Check Dockerfile linting with hadolint
- Security issues: Review pip-audit output
- Permission issues: Check repository settings → Actions → General

---

**Last Updated:** 2025-12-11
**Maintained By:** DevOps/SRE Team
