# Non-Root Container Implementation

## Overview

All containers in the e-commerce platform run as non-root users following the **principle of least privilege**. This security hardening measure reduces the attack surface and limits potential damage if a container is compromised.

## Implementation Status

### ✅ Completed Services

| Service | User | UID:GID | Dockerfile |
|---------|------|---------|------------|
| Backend | appuser | 1000:1000 | `deploy/docker/images/backend/Dockerfile.production` |
| Celery Worker | appuser | 1000:1000 | (inherits from backend) |
| Celery Beat | appuser | 1000:1000 | (inherits from backend) |
| API Gateway | appuser | 1000:1000 | (FastAPI service) |
| Recommendation Engine | aiuser | 1001:1001 | `deploy/docker/images/ai-services/Dockerfile.template` |
| Search Engine | aiuser | 1001:1001 | (AI service template) |
| Pricing Engine | aiuser | 1001:1001 | (AI service template) |
| Chatbot RAG | aiuser | 1001:1001 | (AI service template) |
| Fraud Detection | aiuser | 1001:1001 | (AI service template) |
| Demand Forecasting | aiuser | 1001:1001 | (AI service template) |
| Visual Recognition | aiuser | 1001:1001 | (AI service template) |
| Nginx | nginx | 101:101 | `deploy/docker/images/nginx/Dockerfile` |

### ⚠️ Infrastructure Services (Non-Root by Default)

These services use their official images which already run as non-root:

| Service | User | Notes |
|---------|------|-------|
| PostgreSQL | postgres | Official image runs as postgres user |
| PostgreSQL AI | postgres | Official image runs as postgres user |
| Redis | redis | Official image runs as redis user |
| Elasticsearch | elasticsearch | Official image runs as elasticsearch user |
| Qdrant | qdrant | Official image runs as qdrant user |
| Prometheus | nobody | Official image runs as nobody user |
| Grafana | grafana | Official image runs as grafana user |

## Security Benefits

### 1. Reduced Attack Surface
- Compromised containers cannot modify system files
- Limited access to host resources
- Prevents privilege escalation attacks

### 2. Compliance
- Meets PCI-DSS Requirement 2.2 (secure configuration)
- Satisfies SOC 2 CC6.1 (logical access controls)
- Aligns with CIS Docker Benchmark 4.1

### 3. Defense in Depth
- Additional security layer even with other protections
- Limits blast radius of security incidents
- Complements network segmentation and resource limits

## Implementation Details

### Dockerfile Configuration

#### Application Services (Backend)

```dockerfile
FROM python:3.11-slim-bookworm AS base

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser

# ... build stages ...

# Set ownership during copy
COPY --from=builder --chown=appuser:appuser /opt/venv /opt/venv
COPY --chown=appuser:appuser services/backend/ /app/

# Create directories with proper permissions
RUN mkdir -p /app/logs /app/staticfiles /app/media && \
    chown -R appuser:appuser /app && \
    chmod 750 /app

# Switch to non-root user
USER appuser
```

#### AI Services

```dockerfile
FROM python:3.11-slim-bookworm AS base

# Create non-root user with different UID
RUN groupadd -r aiuser && useradd -r -g aiuser -u 1001 aiuser

# ... build stages ...

# Set ownership
COPY --from=builder --chown=aiuser:aiuser /opt/venv /opt/venv
COPY --chown=aiuser:aiuser services/ai/services/${SERVICE_NAME}/ /app/

# Create directories
RUN mkdir -p /app/logs /app/models /app/tmp && \
    chown -R aiuser:aiuser /app && \
    chmod 750 /app

# Switch to non-root
USER aiuser
```

### Docker Compose Configuration

#### User Enforcement

All application services in `deploy/docker/compose/production.yml` include explicit user directives:

```yaml
services:
  backend:
    user: "1000:1000"  # Enforce non-root
    # ... other config ...

  recommender:
    user: "1001:1001"  # AI service user
    # ... other config ...
```

#### Security Options

Combined with other security measures:

```yaml
services:
  backend:
    user: "1000:1000"
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    read_only: false  # Applications need to write logs
```

## File Permissions

### Directory Structure

```
/app/
├── logs/          # 755, owned by appuser:appuser (writable)
├── staticfiles/   # 755, owned by appuser:appuser (writable)
├── media/         # 755, owned by appuser:appuser (writable)
├── tmp/           # 755, owned by appuser:appuser (writable)
└── *.py           # 444, owned by appuser:appuser (read-only)
```

### Permission Patterns

| Directory/File | Permissions | Owner | Purpose |
|---------------|-------------|-------|---------|
| Application code | 444 | appuser | Read-only for security |
| Log directories | 755 | appuser | Writable for application logs |
| Static files | 755 | appuser | Writable for collectstatic |
| Temporary files | 755 | appuser | Writable for uploads/temp |
| Virtual environment | 755 | appuser | Read/execute for dependencies |

## Verification

### Automated Verification Script

Use the verification script to check all containers:

```bash
# Check all running containers
./scripts/security/verify-nonroot.sh --all

# Check specific service
./scripts/security/verify-nonroot.sh --service backend

# Show fix suggestions
./scripts/security/verify-nonroot.sh --all --fix

# Strict mode (exit with error if root found)
./scripts/security/verify-nonroot.sh --all --strict
```

### Manual Verification

Check a specific container:

```bash
# Get container ID or name
docker ps

# Check user inside container
docker exec <container_name> id

# Expected output (non-root):
# uid=1000(appuser) gid=1000(appuser) groups=1000(appuser)

# Bad output (root):
# uid=0(root) gid=0(root) groups=0(root)
```

### OPA Policy Enforcement

The OPA policies (`config/policies/compose.rego`) warn about missing user specifications:

```rego
warn[msg] {
    service := input.services[name]
    not service.user
    not excluded_from_user_spec(name)
    msg := sprintf("Service '%s' should specify a non-root user", [name])
}
```

## Special Cases

### Nginx

Nginx requires special handling:
- **Master process**: Runs as root (required to bind to ports 80/443)
- **Worker processes**: Run as nginx user (defined in nginx.conf)
- This is standard practice and secure

Nginx configuration:
```nginx
user nginx;
worker_processes auto;
```

### Database Services

PostgreSQL, Redis, and other databases:
- Official images already run as non-root
- Use dedicated system users (postgres, redis, etc.)
- No additional configuration needed

### Vault

HashiCorp Vault:
- Requires `IPC_LOCK` capability
- Runs as vault user in official image
- Security options configured appropriately

## Troubleshooting

### Permission Denied Errors

**Problem**: Container fails to start with permission errors

**Solution**:
1. Check file ownership:
   ```bash
   docker exec <container> ls -la /app
   ```

2. Fix ownership in Dockerfile:
   ```dockerfile
   RUN chown -R appuser:appuser /app
   ```

3. Use `--chown` flag in COPY:
   ```dockerfile
   COPY --chown=appuser:appuser . /app/
   ```

### Cannot Write to Directories

**Problem**: Application cannot write logs or upload files

**Solution**:
1. Create writable directories:
   ```dockerfile
   RUN mkdir -p /app/logs /app/media && \
       chown -R appuser:appuser /app/logs /app/media && \
       chmod 755 /app/logs /app/media
   ```

2. Ensure compose doesn't override:
   ```yaml
   services:
     backend:
       user: "1000:1000"
       # Don't use root for volume mounts
   ```

### Volume Mount Permissions

**Problem**: Mounted volumes have wrong permissions

**Solution**:
1. Pre-create directories on host with correct ownership:
   ```bash
   sudo mkdir -p /var/lib/ecommerce/logs
   sudo chown 1000:1000 /var/lib/ecommerce/logs
   ```

2. Or use named volumes (Docker manages permissions):
   ```yaml
   volumes:
     logs:
       driver: local
   ```

## Testing

### Unit Tests

Test that services start correctly:

```bash
# Start services
docker-compose up -d

# Verify non-root
./scripts/security/verify-nonroot.sh --all

# Check health
docker-compose ps
```

### Integration Tests

Test application functionality:

```bash
# Backend health check
curl http://localhost:8000/health/

# API Gateway health check
curl http://localhost:8080/health

# Check logs (should be writable)
docker-compose logs backend --tail=10
```

### Security Tests

Verify security boundaries:

```bash
# Try to become root (should fail)
docker exec ecommerce_backend sudo -i
# Expected: sudo: command not found OR permission denied

# Try to write to read-only files (should fail)
docker exec ecommerce_backend touch /app/manage.py
# Expected: Permission denied

# Try to access host (should fail)
docker exec ecommerce_backend ls /host
# Expected: Permission denied
```

## Compliance Mapping

### PCI-DSS

| Requirement | Implementation | Evidence |
|-------------|---------------|----------|
| 2.2 - Secure configuration | All containers non-root | Verification script |
| 2.2.4 - Configure system security | User directives in compose | compose files |
| 7.1 - Limit access | Principle of least privilege | Dockerfile USER directives |

### SOC 2

| Control | Implementation | Evidence |
|---------|---------------|----------|
| CC6.1 - Logical access | Non-root execution | Dockerfile + compose config |
| CC6.6 - Logical access restrictions | File permissions | Permission audit |
| CC7.2 - System monitoring | Verification script | Automated checks |

### CIS Docker Benchmark

| Section | Requirement | Status |
|---------|------------|--------|
| 4.1 | Create user for container | ✅ Implemented |
| 4.2 | Use trusted base images | ✅ Implemented |
| 5.1 | Do not disable AppArmor | ✅ Not disabled |
| 5.3 | Restrict Linux capabilities | ✅ cap_drop: ALL |

## Best Practices

### 1. Always Create Dedicated User

```dockerfile
# Good
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser
USER appuser

# Bad
# No USER directive (runs as root)
```

### 2. Set Ownership During Build

```dockerfile
# Good
COPY --chown=appuser:appuser . /app/

# Acceptable (but less efficient)
COPY . /app/
RUN chown -R appuser:appuser /app
```

### 3. Use Specific UID/GID

```yaml
# Good - specific UID
user: "1000:1000"

# Acceptable - username (if user exists in image)
user: appuser

# Bad - root
user: "0:0"
```

### 4. Combine with Other Security Measures

```yaml
services:
  app:
    user: "1000:1000"              # Non-root
    read_only: true                # Read-only filesystem
    security_opt:
      - no-new-privileges:true     # No privilege escalation
    cap_drop:
      - ALL                        # Drop all capabilities
```

### 5. Test Thoroughly

- Verify services start and run correctly
- Check application functionality
- Ensure logs are written successfully
- Validate file uploads work
- Test database connections

## References

- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
- [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)
- [NIST SP 800-190: Container Security](https://csrc.nist.gov/publications/detail/sp/800-190/final)
- [OWASP Docker Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)

## Support

For issues with non-root containers:

1. Run verification script: `./scripts/security/verify-nonroot.sh --all --fix`
2. Check logs: `docker-compose logs <service>`
3. Verify permissions: `docker exec <container> ls -la /app`
4. Review Dockerfile USER directives
5. Check compose user specifications

---

**Last Updated**: 2024-12-19
**Version**: 1.0
**Owner**: Security & Platform Team
