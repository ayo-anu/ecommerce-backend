# Dependency Management Guide

**Version**: 1.0
**Last Updated**: 2025-12-24
**Owner**: Platform Team

---

## Overview

This document outlines the automated dependency management system using Dependabot for the E-Commerce platform. The system ensures dependencies are kept up-to-date with security patches while maintaining system stability.

## Dependabot Configuration

### Update Schedule

| Ecosystem | Frequency | Day/Time | Coverage |
|-----------|-----------|----------|----------|
| **Backend Python** | Daily | 02:00 UTC | `/services/backend` |
| **AI Gateway Python** | Daily | 03:00 UTC | `/services/ai/api_gateway` |
| **AI Services Python** | Weekly | Mon-Tue 04:00-06:00 UTC | All AI microservices |
| **GitHub Actions** | Weekly | Wed 02:00 UTC | Workflow files |
| **Docker Images** | Weekly | Wed-Fri 03:00-05:00 UTC | All Dockerfiles |
| **Docker Compose** | Weekly | Fri 05:00 UTC | Infrastructure compose files |

### Monitored Dependencies

**Python Packages** (16 locations):
- Backend Django application
- AI API Gateway (FastAPI)
- 7 AI microservices (recommendation, fraud detection, search, chatbot, pricing, forecasting, vision)

**Docker Images** (10 locations):
- All service Dockerfiles
- Infrastructure compose files

**GitHub Actions**:
- All workflow files in `.github/workflows/`

## Security Update Workflow

### Priority Levels

#### 🔴 CRITICAL (CVSS >= 9.0)

**Response Time**: Immediate (< 4 hours)

**Actions**:
1. Dependabot creates PR automatically
2. GitHub Security Advisory alert sent
3. Platform team notified via Slack/Email
4. Review PR immediately
5. Run automated security tests
6. Merge after CI passes
7. Deploy to production within 24 hours

**Example**:
```bash
# Review critical security update
gh pr view 123
gh pr checks 123
gh pr review 123 --approve
gh pr merge 123 --squash
```

#### 🟠 HIGH (CVSS >= 7.0)

**Response Time**: 24 hours review, 48 hours merge

**Actions**:
1. Review within 1 business day
2. Test in staging environment
3. Check for breaking changes in changelog
4. Merge within 48 hours
5. Deploy with next release (within 1 week)

#### 🟡 MEDIUM (CVSS >= 4.0)

**Response Time**: 1 week review, 2 weeks merge

**Actions**:
1. Review during weekly dependency review meeting
2. Group with other updates if possible
3. Test in staging
4. Include in next sprint release

#### 🟢 LOW (CVSS < 4.0)

**Response Time**: Monthly

**Actions**:
1. Batch with regular updates
2. Include in quarterly dependency upgrade cycle

### Update Type Handling

#### Patch Updates (x.y.Z)

**Auto-Merge**: ✅ Enabled (after CI passes)

**Process**:
1. Dependabot creates PR with `automerge-candidate` label
2. CI pipeline runs all tests
3. Auto-merge workflow approves PR
4. PR auto-merges when CI passes
5. Automatic deployment to staging
6. Manual promotion to production

**Manual Override**:
```bash
# Prevent auto-merge
gh pr edit 123 --add-label "do-not-merge"

# Remove from auto-merge queue
gh pr edit 123 --remove-label "automerge-candidate"
```

#### Minor Updates (x.Y.0)

**Auto-Merge**: ❌ Disabled (requires manual review)

**Process**:
1. Review changelog for new features
2. Check for deprecation warnings
3. Test in staging environment
4. Update integration tests if needed
5. Manual code review required
6. Merge after approval

**Review Checklist**:
- [ ] Changelog reviewed
- [ ] No breaking changes
- [ ] Tests pass in staging
- [ ] Performance impact assessed
- [ ] Documentation updated if needed

#### Major Updates (X.0.0)

**Auto-Merge**: ❌ Blocked by Dependabot config

**Process**:
Major version updates are **intentionally ignored** by Dependabot and require:

1. **Planning Phase** (Quarterly)
   - Identify major updates needed
   - Create migration epic
   - Assess breaking changes
   - Plan rollout strategy

2. **Development Phase**
   - Create feature branch
   - Update dependencies incrementally
   - Fix breaking changes
   - Update tests and documentation

3. **Testing Phase**
   - Full regression testing
   - Performance testing
   - Security scanning
   - Staging environment validation

4. **Deployment Phase**
   - Blue-green deployment
   - Gradual rollout
   - Monitor for issues
   - Rollback plan ready

**Example - Django Major Upgrade**:
```bash
# Create migration branch
git checkout -b upgrade/django-5.0

# Update requirements
vim services/backend/requirements.txt
# django==5.0.1  # was 4.2.x

# Test locally
docker-compose -f docker-compose.dev.yml up --build

# Run migration scripts
python manage.py check --deploy
python manage.py test

# Create detailed PR with migration notes
gh pr create --title "Upgrade Django to 5.0" \
  --body-file docs/migrations/django-5.0-migration.md
```

## Dependency Grouping

Dependabot groups related dependencies to reduce PR volume:

### Django Ecosystem
- `django`
- `djangorestframework`
- `django-cors-headers`
- `django-extensions`

### FastAPI Ecosystem
- `fastapi`
- `uvicorn`
- `pydantic`
- `starlette`

### Database Drivers
- `psycopg2-binary`
- `sqlalchemy`
- `asyncpg`

### ML Libraries
- `scikit-learn`
- `numpy`
- `pandas`
- `tensorflow`
- `torch`
- `scipy`

### Testing Tools
- `pytest`
- `pytest-cov`
- `pytest-django`
- `coverage`
- `factory-boy`

### Security Libraries
- `cryptography`
- `pyjwt`
- `authlib`

## Managing Dependabot PRs

### Weekly Dependency Review

**Schedule**: Every Monday 10:00 AM

**Agenda**:
1. Review all open Dependabot PRs
2. Prioritize security updates
3. Group related updates
4. Schedule merges
5. Plan testing for larger updates

**Commands**:
```bash
# List all open Dependabot PRs
gh pr list --author "app/dependabot" --state open

# Filter by label
gh pr list --label "dependencies" --label "security"

# View PR with details
gh pr view 123 --web

# Check CI status
gh pr checks 123

# Review and approve
gh pr review 123 --approve --body "LGTM - CI passed"

# Merge PR
gh pr merge 123 --squash --delete-branch
```

### Auto-Merge Configuration

#### Prerequisites

1. **Enable Auto-Merge** in repository settings:
   ```
   Settings → General → Pull Requests
   ☑ Allow auto-merge
   ```

2. **Branch Protection** for `main`:
   ```
   Settings → Branches → Branch protection rules
   ☑ Require status checks to pass before merging
   ☑ Require branches to be up to date before merging
   Status checks required:
     - test
     - lint
     - security-scan
   ```

3. **GitHub Action** workflow:
   - `.github/workflows/dependabot-auto-merge.yml` (already configured)

#### How Auto-Merge Works

1. Dependabot creates PR with `automerge-candidate` label
2. CI pipeline runs all tests
3. `dependabot-auto-merge` workflow:
   - Checks if PR is from Dependabot
   - Verifies it's a patch update
   - Confirms `automerge-candidate` label present
   - Confirms NO `do-not-merge` label
4. If eligible:
   - Auto-approves PR
   - Enables auto-merge
   - Waits for CI to pass
   - Auto-merges when all checks pass
5. If not eligible:
   - Adds comment explaining why
   - Requires manual review

#### Manual Controls

**Prevent Auto-Merge**:
```bash
# Add do-not-merge label
gh pr edit 123 --add-label "do-not-merge"

# Remove automerge-candidate label
gh pr edit 123 --remove-label "automerge-candidate"
```

**Force Manual Review**:
```bash
# Request changes to block merge
gh pr review 123 --request-changes --body "Requires manual testing"
```

**Re-enable Auto-Merge**:
```bash
# Remove blocking labels
gh pr edit 123 --remove-label "do-not-merge"
gh pr edit 123 --add-label "automerge-candidate"

# Re-approve if previously rejected
gh pr review 123 --approve
```

## Monitoring and Metrics

### Weekly Metrics

Track the following metrics in team dashboard:

| Metric | Target | Current |
|--------|--------|---------|
| Open Dependabot PRs | < 10 | [TBD] |
| Average PR Age | < 7 days | [TBD] |
| Security Updates Merged (24h) | 100% | [TBD] |
| Auto-Merge Success Rate | > 90% | [TBD] |
| Outdated Dependencies | < 5% | [TBD] |

**Check Outdated Dependencies**:
```bash
# Backend
cd services/backend
pip list --outdated

# AI Services
cd services/ai/api_gateway
pip list --outdated
```

### Alerts and Notifications

**GitHub Security Advisories**:
- Automatic alerts for vulnerable dependencies
- Email notifications to security team
- Slack integration via GitHub app

**Dependabot Alerts Dashboard**:
```
Repository → Security → Dependabot alerts
```

**Weekly Summary**:
- Automated email every Monday
- Lists all open PRs
- Highlights security updates
- Shows merge statistics

## Troubleshooting

### Dependabot PR Failed to Create

**Issue**: Dependabot couldn't create PR due to conflicts

**Solution**:
```bash
# Manual update required
cd services/backend
pip install --upgrade package-name
pip freeze > requirements.txt

# Create PR manually
git checkout -b deps/update-package-name
git add requirements.txt
git commit -m "chore(deps): update package-name to X.Y.Z"
gh pr create
```

### Auto-Merge Not Working

**Common Causes**:

1. **CI Checks Failing**
   ```bash
   # View check details
   gh pr checks 123

   # Re-run failed checks
   gh pr checks 123 --watch
   ```

2. **Missing Label**
   ```bash
   # Add automerge-candidate label
   gh pr edit 123 --add-label "automerge-candidate"
   ```

3. **Branch Protection Not Configured**
   - Verify branch protection rules in Settings
   - Ensure required checks are configured

### Merge Conflicts

**Issue**: Dependabot PR has merge conflicts

**Solution**:
```bash
# Rebase via comment (Dependabot will rebase automatically)
gh pr comment 123 --body "@dependabot rebase"

# Or manually resolve
git checkout dependabot/pip/services/backend/django-5.0.1
git rebase main
git push --force
```

### Security Advisory Not Auto-Fixed

**Issue**: Security advisory exists but no Dependabot PR

**Possible Reasons**:
- No patch available yet
- Dependency is not direct (transitive)
- Update requires major version change (blocked)

**Manual Fix**:
```bash
# Check dependency tree
pip-audit

# Update specific package
pip install --upgrade vulnerable-package==safe-version
pip freeze > requirements.txt
```

## Best Practices

### ✅ DO

- Review Dependabot PRs weekly
- Merge security updates immediately
- Test in staging before production
- Keep PR count low (< 10 open)
- Monitor dependency health metrics
- Update documentation when dependencies change
- Run full test suite before merging

### ❌ DON'T

- Ignore security updates
- Auto-merge minor/major updates
- Skip testing in staging
- Let PRs accumulate
- Disable Dependabot completely
- Merge without CI passing
- Ignore breaking changes in changelog

## Quarterly Maintenance

### Dependency Audit (Every 3 Months)

**Tasks**:
1. **Review Outdated Dependencies**
   ```bash
   ./scripts/maintenance/audit-dependencies.sh
   ```

2. **Plan Major Version Upgrades**
   - Identify dependencies >1 major version behind
   - Create upgrade epics
   - Schedule in next quarter

3. **Remove Unused Dependencies**
   - Review `requirements.txt`
   - Remove packages not imported
   - Clean up development dependencies

4. **Security Audit**
   ```bash
   pip-audit
   safety check
   ```

5. **Performance Review**
   - Check for lighter alternatives
   - Review bundle sizes
   - Optimize dependency tree

### Compliance Review

**SOC 2 Requirements**:
- [ ] All security updates applied within SLA
- [ ] Dependency update process documented
- [ ] Access controls for merging PRs
- [ ] Audit trail of all updates

**PCI-DSS Requirements**:
- [ ] Security patches applied promptly
- [ ] Vulnerable dependencies identified and fixed
- [ ] Regular security scanning enabled

## Related Documentation

- [Dependabot Configuration](../../.github/dependabot.yml)
- [Auto-Merge Workflow](../../.github/workflows/dependabot-auto-merge.yml)
- [Security Review Process](./security-review-process.md)
- [Deployment Procedures](../operations/deployment-procedures.md)

## Support

**Questions**: #platform-team on Slack
**Issues**: Create ticket in platform-team board
**Escalation**: Platform Lead
