# Container Security Policies

## Overview

This document describes the OPA (Open Policy Agent) security policies enforced on our container infrastructure to ensure best practices and compliance with security standards.

## Policy Enforcement

Security policies are automatically enforced through:

1. **CI/CD Pipeline**: GitHub Actions workflow validates all Dockerfiles and Docker Compose files
2. **Pre-deployment**: Local testing with `scripts/security/test-policies.sh`
3. **Continuous Monitoring**: Regular audits of deployed containers

## Policy Categories

### 1. Dockerfile Security Policies

Location: `config/policies/docker.rego`

#### Deny Rules (Blocking)

| Policy | Description | Rationale |
|--------|-------------|-----------|
| No Privileged Mode | Blocks `--privileged` flag | Prevents container escape and host compromise |
| Non-Root User Required | Requires `USER` directive | Principle of least privilege |
| Health Check Required | Requires `HEALTHCHECK` instruction | Enables container monitoring and auto-recovery |
| No Latest Tags | Blocks `:latest` tags | Ensures reproducible builds |
| No Untagged Images | Requires explicit version tags | Supply chain security |
| Approved Base Images Only | Restricts to approved image list | Reduces attack surface |

#### Warning Rules (Advisory)

| Policy | Description | Best Practice |
|--------|-------------|---------------|
| Unpinned Pip Packages | Warns about unpinned versions | Use `package==version` for reproducibility |
| COPY without chown | Suggests `--chown` flag | Proper file ownership |
| Unclean Downloads | Warns about uncleaned curl/wget | Remove temporary files |
| Missing EXPOSE | Suggests documenting ports | Documentation and discovery |

#### Approved Base Images

```
✅ python:3.11-slim*
✅ python:3.11-alpine*
✅ nginx:*-alpine*
✅ postgres:*-alpine*
✅ redis:*-alpine*
✅ hashicorp/vault:*
✅ scratch
```

### 2. Docker Compose Security Policies

Location: `config/policies/compose.rego`

#### Deny Rules (Blocking)

| Policy | Description | Rationale |
|--------|-------------|-----------|
| Resource Limits Required | Requires memory and CPU limits | Prevents resource exhaustion |
| Health Checks Required | Requires healthcheck configuration | High availability |
| Restart Policy Required | Requires restart policy | Automatic recovery |
| No Privileged Mode | Blocks `privileged: true` | Security isolation |
| Security Options Required | Requires `security_opt` | Security hardening |
| Logging Required | Requires logging configuration | Audit trail |
| No Host Network | Blocks `network_mode: host` | Network isolation |
| No Latest Tags | Blocks `:latest` in images | Version control |
| No Sensitive Mounts | Blocks mounts to `/`, `/etc`, etc. | Host protection |

#### Warning Rules (Advisory)

| Policy | Description | Best Practice |
|--------|-------------|---------------|
| Read-Only Filesystem | Suggests `read_only: true` | Immutable infrastructure |
| User Specification | Suggests non-root user | Least privilege |
| Capability Warnings | Warns about `cap_add` | Minimal capabilities |
| Port Exposure | Warns about exposed ports | Internal-only services |
| Environment Secrets | Warns about passwords/secrets | Use Vault or Docker secrets |

#### Service Exclusions

Some services are excluded from certain policies due to their nature:

**Resource Limits Exclusions:**
- `localstack` (development only)
- `mailhog` (development only)

**Health Check Exclusions:**
- Database services (`postgres`, `postgres_ai`, `redis`, etc.)
- Monitoring services (`prometheus`, `grafana`)
- Infrastructure services (`pgbouncer`)

**Security Options Exclusions:**
- `vault` (requires `IPC_LOCK` capability)

**Read-Only Filesystem Exclusions:**
- Databases that need to write data (`postgres`, `redis`, `vault`)

## Usage

### Local Testing

Test all files:
```bash
./scripts/security/test-policies.sh --all
```

Test specific Dockerfile:
```bash
./scripts/security/test-policies.sh --dockerfile deploy/docker/images/backend/Dockerfile.production
```

Test specific compose file:
```bash
./scripts/security/test-policies.sh --compose deploy/docker/compose/production.yml
```

Show fix suggestions:
```bash
./scripts/security/test-policies.sh --all --fix
```

Verbose output:
```bash
./scripts/security/test-policies.sh --all --verbose
```

### CI/CD Integration

Policies are automatically checked on:
- Pull requests modifying Dockerfiles or compose files
- Pushes to main and phase branches
- Manual workflow triggers

**Workflow**: `.github/workflows/policy-check.yml`

## Common Violations and Fixes

### Dockerfile Violations

#### 1. Missing Non-Root User

**Violation:**
```dockerfile
FROM python:3.11-slim
# ... no USER directive
```

**Fix:**
```dockerfile
FROM python:3.11-slim

# Create and use non-root user
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser
USER appuser
```

#### 2. Missing Health Check

**Violation:**
```dockerfile
FROM python:3.11-slim
# ... no HEALTHCHECK
```

**Fix:**
```dockerfile
FROM python:3.11-slim

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1
```

#### 3. Using Latest Tag

**Violation:**
```dockerfile
FROM python:latest
```

**Fix:**
```dockerfile
FROM python:3.11-slim-bookworm
```

#### 4. Unpinned Dependencies

**Violation:**
```dockerfile
RUN pip install django flask requests
```

**Fix:**
```dockerfile
# Use requirements file with pinned versions
COPY requirements.txt .
RUN pip install -r requirements.txt

# Or pin inline
RUN pip install django==4.2.0 flask==2.3.0 requests==2.31.0
```

### Docker Compose Violations

#### 1. Missing Resource Limits

**Violation:**
```yaml
services:
  backend:
    image: backend:latest
    # ... no resource limits
```

**Fix:**
```yaml
services:
  backend:
    image: backend:1.0.0
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

#### 2. Missing Health Check

**Violation:**
```yaml
services:
  backend:
    image: backend:1.0.0
    # ... no healthcheck
```

**Fix:**
```yaml
services:
  backend:
    image: backend:1.0.0
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

#### 3. Missing Security Options

**Violation:**
```yaml
services:
  backend:
    image: backend:1.0.0
    # ... no security_opt
```

**Fix:**
```yaml
services:
  backend:
    image: backend:1.0.0
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
```

#### 4. Missing Logging Configuration

**Violation:**
```yaml
services:
  backend:
    image: backend:1.0.0
    # ... no logging
```

**Fix:**
```yaml
services:
  backend:
    image: backend:1.0.0
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
        labels: "service=backend"
```

## Policy Maintenance

### Adding New Policies

1. Edit the relevant policy file:
   - `config/policies/docker.rego` for Dockerfile policies
   - `config/policies/compose.rego` for Docker Compose policies

2. Add new rule:
```rego
# Deny rule example
deny[msg] {
    input[i].Cmd == "run"
    contains(input[i].Value[_], "dangerous-command")
    msg := sprintf("Line %d: Dangerous command not allowed", [i])
}

# Warn rule example
warn[msg] {
    input[i].Cmd == "env"
    msg := sprintf("Line %d: Consider using build args instead of ENV", [i])
}
```

3. Test the policy:
```bash
./scripts/security/test-policies.sh --all --verbose
```

4. Document the policy in this file

### Updating Exclusions

To exclude a service from a specific policy, add it to the exclusion functions in `config/policies/compose.rego`:

```rego
excluded_from_resource_limits(name) {
    name == "new-service"
}
```

## Integration with Security Audit

The security policies integrate with our comprehensive security audit system:

```bash
# Run full security audit (includes policy checks)
./scripts/security/security-audit.sh

# Run just policy checks
./scripts/security/test-policies.sh --all
```

## Compliance Mapping

These policies support our compliance requirements:

| Policy | PCI-DSS | SOC 2 | OWASP |
|--------|---------|-------|-------|
| Non-root containers | Req 2.2 | CC6.1 | A05 |
| Resource limits | Req 6.6 | A1.2 | A04 |
| Health checks | Req 10.1 | A1.1 | - |
| No privileged mode | Req 2.2 | CC6.1 | A05 |
| Security options | Req 2.2 | CC6.6 | A05 |
| Logging required | Req 10.2 | CC7.2 | A09 |
| No host network | Req 1.2 | CC6.1 | A05 |
| Approved images | Req 6.2 | CC9.1 | A06 |

## References

- [OPA Documentation](https://www.openpolicyagent.org/docs/latest/)
- [Conftest](https://www.conftest.dev/)
- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
- [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)
- [NIST Container Security Guide](https://csrc.nist.gov/publications/detail/sp/800-190/final)

## Support

For questions or issues with security policies:

1. Check this documentation
2. Review policy files in `config/policies/`
3. Run `./scripts/security/test-policies.sh --fix` for suggestions
4. Contact the security team

---

**Last Updated**: 2024-12-19
**Version**: 1.0
**Owner**: Security & Platform Team
