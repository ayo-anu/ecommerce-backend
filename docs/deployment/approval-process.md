# Production Deployment Approval Process

## Overview

This document outlines the approval process for production deployments in the E-Commerce Platform. The approval workflow ensures that all production deployments are reviewed and authorized by qualified team members before execution, maintaining the stability and security of the production environment.

## Table of Contents

1. [Approval Workflow](#approval-workflow)
2. [Approval Requirements](#approval-requirements)
3. [Eligible Approvers](#eligible-approvers)
4. [Pre-deployment Checklist](#pre-deployment-checklist)
5. [Approval Process](#approval-process)
6. [Emergency Deployments](#emergency-deployments)
7. [Audit Trail](#audit-trail)
8. [Troubleshooting](#troubleshooting)

---

## Approval Workflow

### Deployment Trigger

Production deployments can be triggered in two ways:

1. **Tag-based deployment**: Push a semantic version tag (e.g., `v1.2.3`)
   ```bash
   git tag v1.2.3
   git push origin v1.2.3
   ```

2. **Manual dispatch**: Trigger workflow manually via GitHub Actions UI
   - Go to Actions → Production Deployment Pipeline
   - Click "Run workflow"
   - Specify version and options

### Pipeline Flow

```
┌─────────────────────┐
│ Security Scanning   │ ← Automated
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Build & Test        │ ← Automated
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Integration Tests   │ ← Automated
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Build Production    │ ← Automated
│ Images              │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ ⏸️  APPROVAL GATE   │ ← MANUAL (Requires 2 approvals)
│                     │
│ Creates GitHub      │
│ Issue for approval  │
│                     │
│ Timeout: 60 min     │
└──────────┬──────────┘
           │
           │ Approved
           ▼
┌─────────────────────┐
│ Deploy to           │ ← Automated
│ Production          │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Post-Deployment     │ ← Automated
│ Monitoring          │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Notifications       │ ← Automated
└─────────────────────┘
```

---

## Approval Requirements

### Minimum Approvals

- **Standard Deployments**: 2 approvals required
- **Emergency Deployments**: 1 approval required (from senior team member)
- **Hotfix Deployments**: 2 approvals required (expedited review process)

### Approval Timeout

- Approval requests timeout after **60 minutes**
- If no approval within timeout, deployment is automatically cancelled
- A new deployment workflow must be triggered to retry

### GitHub Environment Protection

In addition to the manual approval workflow, production deployments use GitHub's environment protection rules:

- **Environment**: `production`
- **Required reviewers**: Configured in repository settings
- **Branch restrictions**: Only `main` branch and version tags

---

## Eligible Approvers

### Primary Approvers

The following teams and individuals are authorized to approve production deployments:

1. **@devops-team** - DevOps engineers responsible for infrastructure
2. **@platform-leads** - Platform engineering leadership
3. **@ayo-anu** - Platform owner (can approve individually)

### Team Composition

Configure these teams in your GitHub organization settings:

- **devops-team**: DevOps engineers with production access
- **platform-leads**: Senior engineers and tech leads
- **sre-team**: Site reliability engineers (backup approvers)

### Approval Authority Matrix

| Role | Can Approve Standard | Can Approve Emergency | Can Approve Alone |
|------|---------------------|----------------------|-------------------|
| Platform Owner (@ayo-anu) | ✅ | ✅ | ✅ |
| DevOps Team Member | ✅ | ✅ | ❌ |
| Platform Lead | ✅ | ✅ | ❌ |
| SRE Team Member | ✅ | ⚠️ (with justification) | ❌ |

---

## Pre-deployment Checklist

Before approving a production deployment, reviewers must verify the following:

### ✅ Technical Checks

- [ ] **All tests passing** - Unit, integration, and E2E tests successful
- [ ] **Security scans passed** - No CRITICAL or HIGH vulnerabilities
- [ ] **Code review completed** - All PRs reviewed and approved
- [ ] **Database migrations reviewed** - Migrations tested and backward compatible
- [ ] **Rollback plan ready** - Clear rollback procedure documented

### ✅ Operational Checks

- [ ] **Monitoring dashboards ready** - Grafana dashboards configured
- [ ] **Team notified** - Relevant teams informed of deployment
- [ ] **No active incidents** - No ongoing P0/P1 incidents
- [ ] **Change management ticket** - Ticket created (if required by org policy)
- [ ] **Documentation updated** - CHANGELOG, API docs, runbooks updated

### ✅ Compliance Checks

- [ ] **PCI-DSS compliance** - No impact to cardholder data handling
- [ ] **Data retention** - Follows data retention policies
- [ ] **Audit requirements** - Meets audit and compliance requirements
- [ ] **Customer communication** - Customer-facing changes communicated

### ✅ Business Checks

- [ ] **Business hours** - Deployment scheduled appropriately
- [ ] **Peak traffic** - Not during peak business hours (unless necessary)
- [ ] **Stakeholder approval** - Business stakeholders notified
- [ ] **Feature flags** - New features properly flagged

---

## Approval Process

### Step 1: Automated Issue Creation

When the approval gate is reached, an automated GitHub issue is created:

- **Title**: "Production Deployment Approval: v1.2.3"
- **Labels**: `deployment`, `production`, `approval-required`
- **Assignees**: All eligible approvers are mentioned
- **Content**: Includes deployment details and checklist

### Step 2: Review the Deployment

Approvers should:

1. **Click the workflow link** in the issue to view the pipeline run
2. **Review test results** - Check all tests passed
3. **Review security scans** - Verify no critical vulnerabilities
4. **Check the diff** - Review changes being deployed
5. **Verify checklist items** - Ensure all pre-deployment checks complete

### Step 3: Provide Approval

To approve the deployment, comment on the issue:

```
approve
```

or

```
/approve
```

**Optional**: Include justification or notes:
```
approve - All checks passed, migrations tested in staging
```

### Step 4: Deny if Necessary

To deny the deployment, comment:

```
deny
```

or

```
/deny
```

**Required**: Include reason for denial:
```
deny - Database migration needs more testing. Found issue in staging.
```

### Step 5: Minimum Approvals Met

Once 2 approvals are received:

- The approval gate passes automatically
- The deployment proceeds to production
- Notifications are sent to the team
- The approval issue is closed with deployment results

---

## Emergency Deployments

### When to Use

Emergency deployments are for critical issues:

- **Production outages** - System down or degraded
- **Security vulnerabilities** - Critical security fixes
- **Data integrity issues** - Data corruption or loss prevention
- **Revenue-impacting bugs** - Issues affecting business operations

### Emergency Approval Process

1. **Trigger with emergency flag**:
   ```bash
   # Manual workflow dispatch with skip_tests: true
   # Only use in true emergencies
   ```

2. **Reduced approval requirement**:
   - Only 1 approval required (instead of 2)
   - Must be from @platform-leads or @ayo-anu
   - Approval timeout extended to 30 minutes

3. **Required documentation**:
   - Incident ticket number
   - Root cause summary
   - Justification for emergency process
   - Post-mortem scheduled

4. **Post-deployment**:
   - Full test suite run after deployment
   - Post-mortem conducted within 48 hours
   - Process improvements identified

### Emergency Deployment Template

When requesting emergency approval, include:

```markdown
🚨 EMERGENCY DEPLOYMENT

**Incident**: #INC-12345
**Severity**: P0 - Production Outage
**Root Cause**: Database connection pool exhaustion
**Impact**: 100% of users unable to checkout
**Downtime**: 15 minutes so far

**Fix**: Increase connection pool size and add circuit breaker

**Rollback Plan**: Revert to previous version (v1.2.2)
**Estimated Fix Time**: 5 minutes
**Post-Mortem**: Scheduled for tomorrow 10am

**Approver**: @platform-lead-name
```

---

## Audit Trail

### What is Logged

All production deployments maintain a complete audit trail:

1. **Approval Issue**:
   - Who requested deployment
   - Who approved
   - Timestamp of approvals
   - Comments and justifications

2. **Workflow Run**:
   - All pipeline stages and results
   - Test results and security scans
   - Deployment logs
   - Rollback logs (if applicable)

3. **GitHub Release**:
   - Version deployed
   - Changes included
   - Deployment timestamp
   - Deployment status

### Audit Requirements

For compliance (PCI-DSS, SOC 2), we maintain:

- **90-day audit trail** - All deployments and approvals
- **Change management records** - Link to change tickets
- **Access logs** - Who accessed production systems
- **Rollback records** - All rollback events

### Accessing Audit Trail

View deployment history:

```bash
# List recent deployments
gh api repos/:owner/:repo/deployments | jq '.[] | {id, ref, environment, created_at}'

# View specific deployment
gh api repos/:owner/:repo/deployments/:deployment_id

# View approval issues
gh issue list --label "deployment,production" --state closed
```

---

## Troubleshooting

### Issue: Approval Not Recognized

**Symptoms**: Commented "approve" but workflow still waiting

**Solutions**:
1. Ensure you're an eligible approver (check CODEOWNERS)
2. Use exact syntax: `approve` or `/approve`
3. Comment on the approval issue, not the PR
4. Check you have write access to the repository

### Issue: Approval Timeout

**Symptoms**: Workflow cancelled due to timeout

**Solutions**:
1. Re-trigger the workflow
2. For emergencies, use emergency deployment process
3. Extend timeout in workflow (requires code change)
4. Ensure approvers are available and notified

### Issue: Cannot Find Approval Issue

**Symptoms**: Approval gate reached but no issue created

**Solutions**:
1. Check repository issues with label `approval-required`
2. Verify GitHub token has `issues:write` permission
3. Check workflow logs for errors
4. Manually review workflow and approve via environment

### Issue: Wrong Approvers Listed

**Symptoms**: Approval issue mentions wrong team/people

**Solutions**:
1. Update `.github/CODEOWNERS` file
2. Update `approvers` in `production-deploy.yml`
3. Configure GitHub teams properly
4. Re-trigger workflow after changes

### Issue: Deployment Failed After Approval

**Symptoms**: Approved but deployment failed

**Solutions**:
1. Check deployment logs in workflow run
2. Verify production environment accessibility
3. Check rollback triggered successfully
4. Review post-deployment monitoring results
5. Follow incident response process

---

## Configuration Files

### GitHub Workflow

File: `.github/workflows/production-deploy.yml`

Key configuration:
```yaml
approval-gate:
  name: Production Approval Gate
  runs-on: ubuntu-latest
  needs: [build-push-production]
  steps:
    - name: Wait for manual approval
      uses: trstringer/manual-approval@v1
      timeout-minutes: 60
      with:
        approvers: devops-team,platform-leads,ayo-anu
        minimum-approvals: 2
```

### Code Owners

File: `.github/CODEOWNERS`

Defines who can approve different parts of the codebase:
```
/deploy/ @ayo-anu @devops-team
/.github/workflows/ @ayo-anu @devops-team
/services/backend/ @ayo-anu @backend-team
```

### Environment Protection

Configure in: Repository Settings → Environments → production

- Required reviewers: Add teams/individuals
- Wait timer: 0 minutes (approval handles timing)
- Deployment branches: Only `main` and tags matching `v*`

---

## Best Practices

### For Deployment Requesters

1. **Prepare in advance**: Ensure all tests pass before triggering
2. **Clear change notes**: Provide detailed commit messages
3. **Notify approvers**: Give heads-up via Slack before triggering
4. **Schedule appropriately**: Avoid peak hours unless necessary
5. **Be available**: Stay online during deployment for questions

### For Approvers

1. **Review thoroughly**: Don't rubber-stamp approvals
2. **Check all items**: Verify the complete checklist
3. **Ask questions**: If anything unclear, ask before approving
4. **Timely response**: Respond within 30 minutes if possible
5. **Document concerns**: If denying, provide clear reasons

### For Teams

1. **Establish on-call**: Ensure approvers available 24/7
2. **Document incidents**: Learn from failed deployments
3. **Update process**: Improve based on feedback
4. **Training**: Train all approvers on the process
5. **Automation**: Automate as many checks as possible

---

## Related Documentation

- [CI/CD Pipeline Overview](./ci-cd-pipeline.md)
- [Blue-Green Deployment Guide](./blue-green-deployment.md)
- [Production Deployment Guide](./production-guide.md)
- [Rollback Procedures](./runbook.md#rollback-procedures)
- [Incident Response](../operations/runbooks/incident-response.md)

---

## References

- GitHub Actions Environments: https://docs.github.com/en/actions/deployment/targeting-different-environments
- CODEOWNERS Documentation: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners
- Manual Approval Action: https://github.com/trstringer/manual-approval

---

**Document Version**: 1.0
**Last Updated**: 2025-12-19
**Owner**: Platform Engineering Team
**Review Cycle**: Quarterly
