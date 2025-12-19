# Security Audit Process

## Overview

This document describes the comprehensive security audit process for the E-Commerce Platform, including vulnerability scanning, compliance validation, and security posture assessment.

## Table of Contents

1. [Audit Components](#audit-components)
2. [Running Security Audits](#running-security-audits)
3. [Understanding Reports](#understanding-reports)
4. [Remediation Process](#remediation-process)
5. [Compliance Validation](#compliance-validation)
6. [Automated Scanning](#automated-scanning)
7. [Best Practices](#best-practices)

---

## Audit Components

### 1. Container Vulnerability Scanning

Scans Docker images for known vulnerabilities in:
- OS packages (base image vulnerabilities)
- Application dependencies
- Security misconfigurations

**Tool:** Trivy (https://github.com/aquasecurity/trivy)

### 2. Dependency Scanning

Scans application dependencies for security vulnerabilities:
- Python packages (pip-audit, safety)
- Node.js packages (npm audit)
- Outdated dependencies with known CVEs

### 3. Secret Scanning

Scans git history and codebase for exposed secrets:
- API keys
- Passwords and tokens
- Private keys
- Database credentials

**Tool:** Gitleaks (https://github.com/gitleaks/gitleaks)

### 4. File Permission Checks

Validates file system security:
- Sensitive file permissions
- World-writable files
- SUID/SGID files

### 5. Network Security Validation

Checks Docker network configuration:
- Network segmentation
- Internal vs external networks
- Exposed ports
- Service isolation

### 6. Configuration Security Review

Reviews security configurations:
- Docker security options
- Resource limits
- Environment variables
- Security headers

### 7. Compliance Validation

Validates compliance with security standards:
- PCI-DSS requirements
- SOC 2 trust service criteria
- OWASP Top 10 controls

---

## Running Security Audits

### Complete Security Audit

Run a full security audit covering all components:

```bash
./scripts/security/security-audit.sh
```

This generates a comprehensive report in `security-reports/[timestamp]/`

### Partial Audits

Skip specific scan types:

```bash
# Skip container scanning
./scripts/security/security-audit.sh --skip-containers

# Skip dependency scanning
./scripts/security/security-audit.sh --skip-dependencies

# Skip secret scanning
./scripts/security/security-audit.sh --skip-secrets

# Skip network checks
./scripts/security/security-audit.sh --skip-network
```

### Container Scanning Only

Scan specific services for vulnerabilities:

```bash
# Scan all containers
./scripts/security/scan-containers.sh

# Scan specific service
./scripts/security/scan-containers.sh backend
./scripts/security/scan-containers.sh api_gateway
```

### Compliance Checks Only

Validate compliance with specific standards:

```bash
# Check all standards
./scripts/security/compliance-check.sh --standard all

# Check PCI-DSS only
./scripts/security/compliance-check.sh --standard pci

# Check SOC 2 only
./scripts/security/compliance-check.sh --standard soc2

# Generate detailed report
./scripts/security/compliance-check.sh --standard all --report
```

---

## Understanding Reports

### Report Directory Structure

```
security-reports/20251218_143022/
├── SUMMARY.txt                    # High-level summary
├── trivy-backend.json            # Container scan results (JSON)
├── trivy-backend.txt             # Container scan results (human-readable)
├── trivy-api_gateway.json
├── trivy-api_gateway.txt
├── pip-audit.json                # Python dependency scan
├── safety-dependencies.json      # Python security scan
├── npm-audit.json                # Node.js dependency scan
├── gitleaks-report.json          # Secret scan results
├── file-permissions.txt          # File permission issues
├── network-security.txt          # Network configuration
├── config-security.txt           # Docker configuration
└── compliance-checks.txt         # Compliance validation
```

### Summary Report

The `SUMMARY.txt` file provides:
- Total vulnerabilities by severity
- Secrets found in git history
- Network security issues
- Overall pass/fail status

Example:

```
SECURITY AUDIT SUMMARY REPORT
Generated: 2025-12-18 14:30:22

1. CONTAINER VULNERABILITY SCAN
  backend              CRITICAL:   0  HIGH:   2  MEDIUM:   5
  api_gateway          CRITICAL:   0  HIGH:   1  MEDIUM:   3
  Total CRITICAL: 0
  Total HIGH: 3

2. DEPENDENCY VULNERABILITIES
  pip-audit: 2 vulnerabilities found
  safety: 1 vulnerabilities found

3. SECRET SCANNING
  Secrets found in git history: 0

4. NETWORK SECURITY
  Internal networks: 3
  Services with exposed ports: 1

OVERALL STATUS
  ✓ No critical vulnerabilities found
  ✓ Security audit PASSED
```

### Vulnerability Details

Container scan reports (JSON format) include:
- CVE identifier
- Severity level (CRITICAL, HIGH, MEDIUM, LOW)
- Affected package and version
- Fixed version (if available)
- Description and references

### Exit Codes

- `0` - All checks passed, no critical issues
- `1` - Critical vulnerabilities found
- `2` - Scan errors occurred

---

## Remediation Process

### Priority Levels

1. **CRITICAL** - Fix immediately (within 24 hours)
2. **HIGH** - Fix within 7 days
3. **MEDIUM** - Fix within 30 days
4. **LOW** - Fix in next release cycle

### Remediation Steps

#### 1. Container Vulnerabilities

```bash
# Identify vulnerable package
cat security-reports/latest/trivy-backend.json | jq '.Results[].Vulnerabilities[] | select(.Severity=="CRITICAL")'

# Update base image
# In Dockerfile:
FROM python:3.11-slim-bookworm  # Update to latest patch version

# Rebuild image
docker-compose build backend

# Rescan
./scripts/security/scan-containers.sh backend
```

#### 2. Dependency Vulnerabilities

```bash
# Python dependencies
pip install --upgrade package-name

# Update requirements.txt
pip freeze > requirements.txt

# Rebuild and test
docker-compose build backend
docker-compose up -d backend
```

#### 3. Exposed Secrets

```bash
# Remove from git history
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch path/to/secret-file" \
  --prune-empty --tag-name-filter cat -- --all

# Rotate compromised secrets
./scripts/security/rotate-secrets.sh [service]

# Add to .gitignore
echo "path/to/secret-file" >> .gitignore
```

#### 4. Configuration Issues

```bash
# Fix Docker security options
# In docker-compose.yml:
services:
  backend:
    security_opt:
      - no-new-privileges:true
    read_only: true  # If possible

# Apply changes
docker-compose up -d
```

---

## Compliance Validation

### PCI-DSS Compliance

Requirements validation:
- Req 1: Firewall configuration and network segmentation
- Req 2: No default credentials
- Req 3: Protect stored cardholder data
- Req 4: Encrypt data in transit
- Req 6: Secure systems and applications
- Req 7: Restrict access by need-to-know
- Req 8: Unique IDs for access
- Req 10: Track and monitor access
- Req 11: Test security systems regularly

Run compliance check:

```bash
./scripts/security/compliance-check.sh --standard pci --report
```

### SOC 2 Compliance

Trust Service Criteria:
- CC1-CC9: Common Criteria (Security)
- A1: Availability
- PI1: Processing Integrity
- C1: Confidentiality
- P1: Privacy

Run compliance check:

```bash
./scripts/security/compliance-check.sh --standard soc2 --report
```

---

## Automated Scanning

### CI/CD Integration

Add to GitHub Actions workflow:

```yaml
name: Security Scan

on:
  push:
    branches: [main, develop]
  pull_request:
  schedule:
    - cron: '0 2 * * 1'  # Weekly on Monday 2 AM

jobs:
  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run security audit
        run: ./scripts/security/security-audit.sh

      - name: Upload reports
        uses: actions/upload-artifact@v3
        with:
          name: security-reports
          path: security-reports/

      - name: Fail on critical
        if: failure()
        run: echo "Critical vulnerabilities found!"
```

### Scheduled Audits

Set up cron job for regular audits:

```bash
# Add to crontab
crontab -e

# Run weekly audit on Sunday at 2 AM
0 2 * * 0 /path/to/scripts/security/security-audit.sh

# Run monthly compliance check
0 3 1 * * /path/to/scripts/security/compliance-check.sh --standard all --report
```

---

## Best Practices

### Before Deployment

1. **Run Full Audit**
   ```bash
   ./scripts/security/security-audit.sh
   ```

2. **Fix Critical Issues**
   - Address all CRITICAL vulnerabilities
   - Resolve HIGH severity issues if possible

3. **Validate Compliance**
   ```bash
   ./scripts/security/compliance-check.sh --standard all
   ```

4. **Test Remediation**
   - Rescan after fixes
   - Verify no new issues introduced

### Regular Audits

1. **Weekly:** Container vulnerability scans
2. **Monthly:** Full security audit
3. **Quarterly:** Compliance validation
4. **After Updates:** Scan after dependency updates

### Continuous Monitoring

1. **Enable CI/CD scanning** - Block PRs with critical vulnerabilities
2. **Monitor audit logs** - Review Vault audit logs regularly
3. **Track metrics** - Monitor vulnerability trends over time
4. **Stay updated** - Subscribe to security advisories

### Security Metrics to Track

- **Vulnerability Count:** Total and by severity
- **Mean Time to Remediate (MTTR):** Average time to fix vulnerabilities
- **Compliance Score:** Percentage of requirements met
- **Scan Coverage:** Percentage of services scanned
- **False Positive Rate:** Accuracy of vulnerability detection

### Vulnerability Management

1. **Triage:** Assess severity and exploitability
2. **Prioritize:** Based on risk and business impact
3. **Remediate:** Apply fixes and patches
4. **Verify:** Rescan to confirm resolution
5. **Document:** Record findings and actions taken

---

## Tool Installation

### Trivy

```bash
# Install Trivy
curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin

# Verify installation
trivy version

# Update vulnerability database
trivy image --download-db-only
```

### Gitleaks

```bash
# Install Gitleaks
brew install gitleaks  # macOS
# Or
wget https://github.com/gitleaks/gitleaks/releases/download/v8.18.0/gitleaks_8.18.0_linux_x64.tar.gz
tar -xzf gitleaks_8.18.0_linux_x64.tar.gz
sudo mv gitleaks /usr/local/bin/

# Verify installation
gitleaks version
```

### pip-audit

```bash
# Install pip-audit
pip install pip-audit

# Verify installation
pip-audit --version
```

### Safety

```bash
# Install safety
pip install safety

# Verify installation
safety --version
```

---

## Troubleshooting

### Issue: Trivy Database Update Fails

```bash
# Manually update database
trivy image --download-db-only

# Clear cache and retry
trivy image --clear-cache
trivy image --download-db-only
```

### Issue: False Positives

Create `.trivyignore` file to ignore specific CVEs:

```bash
# .trivyignore
# Ignore false positive CVE-2021-12345
CVE-2021-12345

# Ignore CVE in test dependencies
CVE-2021-67890
```

### Issue: Scan Takes Too Long

```bash
# Skip OS package scanning
trivy image --scanners vuln --skip-update your-image

# Scan specific severity only
trivy image --severity CRITICAL,HIGH your-image

# Use cache
trivy image --cache-dir /tmp/trivy-cache your-image
```

---

## Reference

### Quick Commands

```bash
# Full security audit
./scripts/security/security-audit.sh

# Container scan only
./scripts/security/scan-containers.sh

# Compliance check
./scripts/security/compliance-check.sh --standard all

# Scan specific service
./scripts/security/scan-containers.sh backend

# Skip specific scans
./scripts/security/security-audit.sh --skip-secrets --skip-network
```

### Configuration Files

- `.trivy.yaml` - Trivy configuration
- `.trivyignore` - Ignored CVEs
- `scripts/security/security-audit.sh` - Main audit script
- `scripts/security/scan-containers.sh` - Container scanner
- `scripts/security/compliance-check.sh` - Compliance validator

### Related Documentation

- [Vault Integration](vault-integration.md)
- [Secret Rotation](secret-rotation.md)
- [Phase 3 Execution Plan](../PHASE_3_EXECUTION_PLAN.md)

---

**Document Version:** 1.0
**Last Updated:** 2025-12-18
**Maintained By:** Platform Engineering Team
