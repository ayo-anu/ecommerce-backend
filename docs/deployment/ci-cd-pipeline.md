# CI/CD Pipeline Documentation

**Version:** 1.0
**Last Updated:** 2025-12-18
**Owner:** Platform Engineering Team

---

## Table of Contents

1. [Overview](#overview)
2. [Pipeline Architecture](#pipeline-architecture)
3. [Workflows](#workflows)
4. [Deployment Environments](#deployment-environments)
5. [Deployment Process](#deployment-process)
6. [Rollback Procedures](#rollback-procedures)
7. [Monitoring & Notifications](#monitoring--notifications)
8. [Troubleshooting](#troubleshooting)

---

## Overview

The e-commerce platform uses GitHub Actions for continuous integration and deployment. The pipeline supports three environments:

- **Development** - Auto-deploy from feature branches
- **Staging** - Auto-deploy from `develop` and `phase-*` branches
- **Production** - Manual approval required, triggered by version tags

### Key Features

- ✅ Automated testing (unit, integration, smoke tests)
- ✅ Security scanning (Trivy, Snyk, Semgrep)
- ✅ Multi-stage Docker builds with caching
- ✅ Blue-green deployment for zero downtime
- ✅ Automatic rollback on failure
- ✅ Slack/email notifications
- ✅ Post-deployment monitoring

---

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Pull Request                            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
            ┌────────────────────────────────┐
            │     PR Checks Workflow         │
            │  - Linting                     │
            │  - Unit Tests                  │
            │  - Build Validation            │
            │  - Integration Tests           │
            │  - Security Preview            │
            └────────────────┬───────────────┘
                             │
                ┌────────────┴────────────┐
                │                         │
        [Merge to develop]        [Merge to main]
                │                         │
                ▼                         ▼
    ┌───────────────────┐     ┌───────────────────┐
    │ Staging Deploy    │     │  Tag Created      │
    │  - Auto Deploy    │     │  (v*.*.*)         │
    │  - Smoke Tests    │     └─────────┬─────────┘
    └───────────────────┘               │
                                        ▼
                            ┌────────────────────────┐
                            │ Production Pipeline    │
                            │ - Security Scan        │
                            │ - Build & Test         │
                            │ - Integration Tests    │
                            │ - Build & Push Images  │
                            │ - Manual Approval ⚠️   │
                            │ - Deploy Production    │
                            │ - Post-Deploy Monitor  │
                            │ - Notifications        │
                            └────────────────────────┘
```

---

## Workflows

### 1. PR Checks (`pr-checks.yml`)

**Trigger:** Pull requests to `main`, `develop`, or `phase-*` branches

**Jobs:**
1. **lint-backend** - Python linting (flake8, pylint, black, isort)
2. **lint-ai-services** - AI services linting
3. **test-backend** - Backend unit tests with PostgreSQL/Redis
4. **test-ai-services** - AI services unit tests
5. **build-backend** - Build backend Docker image
6. **build-ai-gateway** - Build AI gateway Docker image
7. **integration-tests** - Full integration test suite
8. **security-preview** - Quick Trivy scan (non-blocking)
9. **pr-summary** - Comment results on PR

**Duration:** ~8-12 minutes

**Failure Handling:**
- PRs cannot merge if checks fail
- Failed tests show detailed logs
- Security issues shown but don't block (preview only)

### 2. Staging Deployment (`staging-deploy.yml`)

**Trigger:**
- Push to `develop` branch
- Push to `phase-*/**` branches
- Manual workflow dispatch

**Jobs:**
1. **build-and-push** - Build and push images to container registry
2. **deploy-staging** - Deploy to staging environment
3. **smoke-tests** - Validate deployment

**Duration:** ~5-8 minutes

**Environment:** `staging`
- URL: https://staging-api.example.com
- Auto-deployment (no approval needed)

### 3. Production Deployment (`production-deploy.yml`)

**Trigger:**
- Git tags matching `v*.*.*` (e.g., v1.2.3)
- Manual workflow dispatch

**Jobs:**
1. **security-scan** - Comprehensive security scanning
2. **build-and-test** - Build all service images
3. **integration-tests** - Full integration test suite
4. **build-push-production** - Push production images
5. **deploy-production** - Deploy to production (requires approval)
6. **post-deployment-monitoring** - 5-minute health monitoring
7. **notify** - Send notifications
8. **rollback** - Automatic rollback on failure

**Duration:** ~15-25 minutes

**Environment:** `production`
- URL: https://api.example.com
- **Manual approval required** (minimum 2 approvers)

---

## Deployment Environments

### Development

**Purpose:** Local development and testing

**Infrastructure:**
- Docker Compose on developer machines
- Local PostgreSQL, Redis
- No external services required

**Access:** Developers only

### Staging

**Purpose:** Pre-production testing and validation

**Infrastructure:**
- Dedicated staging server
- Staging database (isolated from production)
- Matches production architecture

**Access:**
- Development team
- QA team
- Product managers

**Deployment:**
- Automatic on `develop` branch merge
- No approval required
- Can be manually triggered

**URL:** https://staging-api.example.com

### Production

**Purpose:** Live customer-facing environment

**Infrastructure:**
- Production servers with high availability
- Production database with backups
- CDN for static assets
- Full monitoring and alerting

**Access:**
- DevOps team only
- Read-only access for developers (logs, monitoring)

**Deployment:**
- Version tags only (v1.2.3)
- **Requires manual approval**
- Minimum 2 approvers from DevOps team
- Blue-green deployment strategy

**URL:** https://api.example.com

---

## Deployment Process

### Standard Production Deployment

**Step 1: Create Release Tag**

```bash
# Ensure you're on main branch
git checkout main
git pull origin main

# Create and push version tag
git tag -a v1.2.3 -m "Release version 1.2.3"
git push origin v1.2.3
```

**Step 2: Pipeline Automatically Triggered**

The production pipeline starts automatically:
1. Security scanning runs
2. All tests execute
3. Images build and push to registry

**Step 3: Manual Approval Required**

- GitHub creates an approval issue
- Notifies DevOps team via Slack
- Displays pre-deployment checklist:
  - [ ] All tests passing
  - [ ] Security scans clear
  - [ ] Staging deployment successful
  - [ ] Database migrations reviewed
  - [ ] Rollback plan ready

**Step 4: Approval & Deployment**

Once approved (minimum 2 approvers):
1. SSH to production server
2. Pull latest images
3. Run database migrations
4. Execute blue-green deployment
5. Health checks verify deployment
6. Traffic switches to new version

**Step 5: Post-Deployment**

- 5-minute monitoring period
- Health checks every 30 seconds
- Error rate monitoring
- Automatic rollback on issues

**Step 6: Notifications**

- Slack notification to #deployments
- Email to devops@example.com
- GitHub release created

### Emergency Production Deployment

For critical hotfixes only:

```bash
# Use workflow dispatch
gh workflow run production-deploy.yml \
  -f version=v1.2.4 \
  -f skip_tests=false  # Keep tests even for emergency
```

**Warning:** Never skip tests unless absolutely critical (P0 outage).

### Staging Deployment

Automatic on every push to `develop`:

```bash
git checkout develop
git pull origin develop

# Make changes
git add .
git commit -m "feat: add new feature"
git push origin develop

# Pipeline automatically deploys to staging
```

---

## Rollback Procedures

### Automatic Rollback

The pipeline automatically rolls back if:
- Health checks fail after deployment
- Smoke tests fail
- Error rate exceeds threshold
- Post-deployment monitoring detects issues

**Process:**
1. Pipeline detects failure
2. Executes `rollback.sh` script
3. Switches traffic back to previous version
4. Sends failure notifications
5. Creates incident issue

### Manual Rollback

If needed, manually rollback:

```bash
# SSH to production server
ssh deployer@production-server

# Execute rollback script
cd /opt/ecommerce
bash deploy/docker/scripts/rollback.sh

# Verify rollback
curl -f https://api.example.com/health/
```

**Rollback Script:**
- Switches traffic to previous version
- Rolls back database migrations (if needed)
- Restores previous configuration
- Completes in < 30 seconds

### Rollback Validation

After rollback:
1. Verify health checks pass
2. Check error rates in Grafana
3. Monitor for 10 minutes
4. Investigate root cause
5. Create post-mortem

---

## Monitoring & Notifications

### Slack Notifications

**Channel:** `#deployments`

**Events:**
- Staging deployment started/completed
- Production approval requested
- Production deployment started/completed
- Deployment failures
- Rollbacks

**Format:**
```
✅ Production Deployment Successful
Version: v1.2.3
Deployed by: @john.doe
Environment: Production
Status: success

[View Production] [View Workflow] [Grafana Dashboard]
```

### Email Notifications

**Recipients:** devops@example.com

**Events:**
- Production deployment failures
- Critical security vulnerabilities detected
- Rollback executed

### GitHub Releases

Automatically created for each production deployment:
- Version tag
- Commit changelog
- Deployment timestamp
- Services updated
- Deployment status

---

## Troubleshooting

### Pipeline Failures

#### Security Scan Failures

**Symptom:** `security-scan` job fails with critical vulnerabilities

**Solution:**
1. Review Trivy report in GitHub Security tab
2. Update vulnerable dependencies
3. Rebuild images
4. Re-run pipeline

```bash
# Update dependencies
cd services/backend
pip-audit --fix
pip install --upgrade <package>

# Commit and push
git add requirements/
git commit -m "fix: update vulnerable dependencies"
git push
```

#### Test Failures

**Symptom:** `test-backend` or `integration-tests` fail

**Solution:**
1. Review test logs in GitHub Actions
2. Run tests locally:

```bash
# Backend tests
cd services/backend
pytest tests/unit/ -v

# Integration tests
docker-compose -f deploy/docker/compose/ci.yml up -d
docker-compose -f deploy/docker/compose/ci.yml exec backend pytest tests/integration/
```

3. Fix failing tests
4. Push fix

#### Build Failures

**Symptom:** Docker build fails

**Solution:**
1. Check build logs
2. Validate Dockerfile syntax
3. Test build locally:

```bash
docker build -t backend:test ./services/backend
```

### Deployment Failures

#### SSH Connection Failed

**Symptom:** Cannot connect to production server

**Solution:**
1. Verify SSH key in GitHub Secrets
2. Check server firewall rules
3. Verify server is accessible:

```bash
ssh -i ~/.ssh/deploy_key deployer@production-server
```

#### Health Checks Failing

**Symptom:** Deployment completes but health checks fail

**Solution:**
1. SSH to server
2. Check logs:

```bash
docker-compose -f deploy/docker/compose/production.yml logs -f backend
```

3. Check database connectivity:

```bash
docker-compose exec backend python manage.py check --database default
```

4. Manual rollback if needed

#### Database Migration Failures

**Symptom:** `run_migrations` fails

**Solution:**
1. Review migration error
2. Check database state:

```bash
docker-compose exec backend python manage.py showmigrations
```

3. Fix migration or create rollback migration
4. Re-run deployment

### Approval Issues

#### Approval Timeout

**Symptom:** No approvers available

**Solution:**
1. Contact DevOps team via Slack
2. Emergency: Use workflow_dispatch with authorized account
3. Document in incident log

#### Approval Issue Not Created

**Symptom:** GitHub issue not created for approval

**Solution:**
1. Check GitHub Actions permissions
2. Manually approve via GitHub UI
3. File bug report

---

## CI/CD Metrics

### Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| PR Check Duration | < 10 min | ~8 min |
| Staging Deploy Duration | < 8 min | ~6 min |
| Production Deploy Duration | < 20 min | ~18 min |
| Deployment Success Rate | > 95% | 97% |
| Rollback Time | < 2 min | ~1 min |
| Test Coverage | > 80% | 85% |

### SLIs

- **Deployment Frequency:** Daily to staging, weekly to production
- **Lead Time for Changes:** < 1 day for hotfixes, < 3 days for features
- **Mean Time to Recovery (MTTR):** < 15 minutes
- **Change Failure Rate:** < 5%

---

## Security

### Secrets Management

**GitHub Secrets Required:**

**Staging:**
- `STAGING_SSH_KEY` - SSH private key
- `STAGING_HOST` - Server hostname
- `STAGING_USER` - SSH username

**Production:**
- `PRODUCTION_SSH_KEY` - SSH private key
- `PRODUCTION_HOST` - Server hostname
- `PRODUCTION_USER` - SSH username
- `SLACK_WEBHOOK_URL` - Slack notifications
- `EMAIL_USERNAME` - Email notifications
- `EMAIL_PASSWORD` - Email password
- `SNYK_TOKEN` - Snyk security scanning

### Permissions

**Required GitHub Permissions:**
- `contents: read` - Read repository
- `packages: write` - Push container images
- `security-events: write` - Upload security scans
- `issues: write` - Create approval issues

### Security Scanning

All deployments scan for:
- Container vulnerabilities (Trivy)
- Dependency vulnerabilities (Snyk, pip-audit)
- Code vulnerabilities (Semgrep)
- Secret leaks (Gitleaks)

**Blocking Criteria:**
- Critical or High severity vulnerabilities
- Secrets detected in code
- Failed security policy checks

---

## Maintenance

### Weekly Tasks

- [ ] Review failed deployments
- [ ] Update pipeline dependencies
- [ ] Check disk space on servers
- [ ] Review security scan results

### Monthly Tasks

- [ ] Audit access permissions
- [ ] Review and update documentation
- [ ] Test rollback procedures
- [ ] Performance optimization review

### Quarterly Tasks

- [ ] Pipeline security audit
- [ ] Disaster recovery drill
- [ ] Update deployment playbooks
- [ ] Review and improve metrics

---

## References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Build Documentation](https://docs.docker.com/build/)
- [Deployment Runbook](./runbook.md)
- [Rollback Procedures](./rollback-procedures.md)
- [Blue-Green Deployment](./blue-green-deployment.md)

---

**Need Help?**
- Slack: #devops-help
- On-call: PagerDuty rotation
- Documentation: https://docs.example.com
