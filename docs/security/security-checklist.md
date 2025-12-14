# Production Security Checklist

## Table of Contents
- [Pre-Deployment Security](#pre-deployment-security)
- [Network Security](#network-security)
- [Application Security](#application-security)
- [Database Security](#database-security)
- [Authentication & Authorization](#authentication--authorization)
- [SSL/TLS Configuration](#ssltls-configuration)
- [Secrets Management](#secrets-management)
- [Monitoring & Logging](#monitoring--logging)
- [Compliance](#compliance)
- [Incident Response](#incident-response)

---

## Pre-Deployment Security

### Infrastructure

- [ ] **Server Hardening**
  - [ ] Operating system fully updated
  - [ ] Unnecessary services disabled
  - [ ] SSH key-based authentication only
  - [ ] SSH password authentication disabled
  - [ ] Root login disabled
  - [ ] Fail2ban installed and configured
  - [ ] Regular security updates scheduled

- [ ] **Firewall Configuration**
  - [ ] Only ports 80, 443, and 22 (SSH) open
  - [ ] SSH restricted to specific IP addresses
  - [ ] Rate limiting enabled
  - [ ] DDoS protection configured

- [ ] **User Management**
  - [ ] Separate user accounts for admins
  - [ ] Sudo access properly configured
  - [ ] No default passwords
  - [ ] Regular user access reviews

### Docker Security

- [ ] **Docker Daemon**
  - [ ] Docker rootless mode (if possible)
  - [ ] Docker daemon only accessible via socket
  - [ ] Regular Docker version updates
  - [ ] Docker Content Trust enabled

- [ ] **Image Security**
  - [ ] All images from official sources
  - [ ] Images scanned for vulnerabilities (Trivy, Snyk)
  - [ ] No images with known CVEs
  - [ ] Multi-stage builds for smaller attack surface
  - [ ] Non-root users in containers

```bash
# Scan images for vulnerabilities
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image ecommerce_backend:latest
```

---

## Network Security

### Network Segmentation

- [ ] **Isolated Networks**
  - [ ] `public_network` only contains Nginx and API Gateway
  - [ ] `backend_network` set to internal in production
  - [ ] `ai_network` set to internal in production
  - [ ] No direct access to internal services from internet

- [ ] **Port Exposure**
  - [ ] **Production:** Only Nginx exposes ports 80, 443
  - [ ] All internal services have `ports: []`
  - [ ] No debug ports (5005, 9229, etc.) exposed
  - [ ] Database ports NOT exposed

```yaml
# Verify in docker-compose.prod.yaml
services:
  backend:
    ports: []  # ✓ Correct

  postgres:
    ports: []  # ✓ Correct

  nginx:
    ports:
      - "80:80"
      - "443:443"  # ✓ Only Nginx exposes ports
```

### API Gateway as Control Plane

- [ ] **Single Entry Point**
  - [ ] All traffic flows through Nginx → API Gateway
  - [ ] No direct backend access
  - [ ] No direct AI service access
  - [ ] Frontend only calls API Gateway

- [ ] **Gateway Security**
  - [ ] Rate limiting configured
  - [ ] Circuit breakers enabled
  - [ ] Request size limits set
  - [ ] Timeout values configured

---

## Application Security

### Django Backend

- [ ] **Settings Security**
  ```python
  # config/settings/production.py
  DEBUG = False
  SECRET_KEY = env('SECRET_KEY')  # Strong random key
  ALLOWED_HOSTS = ['yourdomain.com', 'api.yourdomain.com']

  # Security headers
  SECURE_SSL_REDIRECT = True
  SESSION_COOKIE_SECURE = True
  CSRF_COOKIE_SECURE = True
  SECURE_BROWSER_XSS_FILTER = True
  SECURE_CONTENT_TYPE_NOSNIFF = True
  SECURE_HSTS_SECONDS = 31536000
  SECURE_HSTS_INCLUDE_SUBDOMAINS = True
  SECURE_HSTS_PRELOAD = True
  X_FRAME_OPTIONS = 'DENY'
  ```

- [ ] **Django Security Checks**
  ```bash
  # Run Django security check
  docker compose run --rm backend python manage.py check --deploy

  # Expected: No warnings or errors
  ```

- [ ] **CSRF Protection**
  - [ ] CSRF tokens enabled
  - [ ] CSRF cookie secure flag set
  - [ ] CSRF trusted origins configured

- [ ] **XSS Protection**
  - [ ] Template auto-escaping enabled
  - [ ] User input sanitized
  - [ ] Content Security Policy configured

- [ ] **SQL Injection Protection**
  - [ ] ORM used for all queries
  - [ ] No raw SQL with user input
  - [ ] Parameterized queries where needed

- [ ] **File Upload Security**
  - [ ] File type validation
  - [ ] File size limits
  - [ ] Files stored in S3, not local
  - [ ] Virus scanning enabled

### API Gateway

- [ ] **Input Validation**
  - [ ] Request schema validation
  - [ ] Size limits enforced
  - [ ] Content-Type validation
  - [ ] JSON parsing limits

- [ ] **Rate Limiting**
  ```python
  # Per-IP rate limiting
  @limiter.limit("100/hour")
  async def endpoint():
      pass
  ```

- [ ] **Circuit Breakers**
  - [ ] Failure thresholds set
  - [ ] Timeout values configured
  - [ ] Fallback mechanisms implemented

### AI Services

- [ ] **Model Security**
  - [ ] Models from trusted sources only
  - [ ] Model versioning tracked
  - [ ] Input/output validation
  - [ ] Resource limits set

- [ ] **API Key Protection**
  - [ ] OpenAI keys in environment variables
  - [ ] Keys rotated regularly
  - [ ] Usage monitoring enabled
  - [ ] Spending limits set

---

## Database Security

### PostgreSQL

- [ ] **Access Control**
  - [ ] Strong database passwords
  - [ ] Database users per service
  - [ ] Least privilege principle
  - [ ] No default passwords

- [ ] **Network Access**
  - [ ] Database not exposed to internet
  - [ ] Only backend services can connect
  - [ ] SSL/TLS for connections (if needed)

- [ ] **Configuration**
  ```bash
  # Check PostgreSQL config
  docker exec ecommerce_postgres cat /var/lib/postgresql/data/postgresql.conf

  # Verify:
  # - listen_addresses = '*' (internal network only)
  # - ssl = on (if using SSL)
  # - max_connections appropriate
  ```

- [ ] **Backups**
  - [ ] Automated daily backups
  - [ ] Backup encryption enabled
  - [ ] Backup restoration tested
  - [ ] Off-site backup storage

### Redis

- [ ] **Authentication**
  - [ ] Redis password set (`requirepass`)
  - [ ] Strong password (32+ characters)
  - [ ] Password in environment variables

- [ ] **Network Access**
  - [ ] Not exposed to internet
  - [ ] Bind to internal networks only
  - [ ] No default configuration

- [ ] **Configuration**
  ```bash
  # Verify Redis security
  docker exec ecommerce_redis redis-cli CONFIG GET requirepass
  # Should return: password set
  ```

### Elasticsearch

- [ ] **Security**
  - [ ] X-Pack security enabled (paid) or alternatives
  - [ ] Not exposed to internet
  - [ ] Regular updates applied

### Qdrant Vector DB

- [ ] **Access Control**
  - [ ] API key authentication enabled
  - [ ] Not exposed to internet
  - [ ] Only AI services can access

---

## Authentication & Authorization

### JWT Tokens

- [ ] **Token Configuration**
  - [ ] Strong signing algorithm (RS256 or HS256)
  - [ ] Secret key 256+ bits
  - [ ] Short expiration times (15-30 min for access tokens)
  - [ ] Refresh token rotation

- [ ] **Token Validation**
  - [ ] Signature verification
  - [ ] Expiration check
  - [ ] Issuer validation
  - [ ] Audience validation

### API Gateway Auth

- [ ] **Authentication Middleware**
  ```python
  # All routes require authentication
  @app.middleware("http")
  async def authenticate_request(request: Request, call_next):
      # Verify JWT token
      token = request.headers.get("Authorization")
      if not verify_token(token):
          return JSONResponse(status_code=401, content={"error": "Unauthorized"})
      return await call_next(request)
  ```

- [ ] **Permission Checks**
  - [ ] Role-based access control (RBAC)
  - [ ] Scope validation
  - [ ] Resource ownership checks

### User Management

- [ ] **Password Policy**
  - [ ] Minimum 12 characters
  - [ ] Complexity requirements
  - [ ] Password hashing (bcrypt/Argon2)
  - [ ] No password reuse

- [ ] **Account Security**
  - [ ] Account lockout after failed attempts
  - [ ] Email verification required
  - [ ] Password reset flow secure
  - [ ] Two-factor authentication (optional)

---

## SSL/TLS Configuration

### Certificate Management

- [ ] **Certificate Validity**
  - [ ] Valid SSL certificate installed
  - [ ] Certificate not expired
  - [ ] Certificate chain complete
  - [ ] Auto-renewal configured

```bash
# Check certificate expiration
openssl x509 -in /etc/nginx/ssl/fullchain.pem -noout -dates

# Test SSL configuration
curl -I https://api.yourdomain.com
```

### Nginx SSL Configuration

- [ ] **TLS Version**
  ```nginx
  # Only TLS 1.2 and 1.3
  ssl_protocols TLSv1.2 TLSv1.3;
  ```

- [ ] **Cipher Suites**
  ```nginx
  # Strong ciphers only
  ssl_ciphers HIGH:!aNULL:!MD5:!3DES;
  ssl_prefer_server_ciphers on;
  ```

- [ ] **HSTS Enabled**
  ```nginx
  add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
  ```

- [ ] **SSL Grade**
  - [ ] Test on SSL Labs: https://www.ssllabs.com/ssltest/
  - [ ] Target: A or A+ rating

### Security Headers

- [ ] **Required Headers**
  ```nginx
  # Nginx configuration
  add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
  add_header X-Frame-Options "SAMEORIGIN" always;
  add_header X-Content-Type-Options "nosniff" always;
  add_header X-XSS-Protection "1; mode=block" always;
  add_header Referrer-Policy "strict-origin-when-cross-origin" always;
  add_header Content-Security-Policy "default-src 'self'" always;
  ```

- [ ] **Verify Headers**
  ```bash
  # Check security headers
  curl -I https://api.yourdomain.com | grep -i "x-\|strict\|content-security"
  ```

---

## Secrets Management

### Environment Variables

- [ ] **Secret Storage**
  - [ ] All secrets in `.env.prod` file
  - [ ] `.env.prod` in `.gitignore`
  - [ ] `.env.prod` file permissions: 600
  - [ ] No secrets in code or docker-compose files

- [ ] **Secret Rotation**
  - [ ] Database passwords rotated quarterly
  - [ ] API keys rotated regularly
  - [ ] SSL certificates renewed before expiry
  - [ ] Rotation documented

### Sensitive Data

- [ ] **Credit Card Data**
  - [ ] Never stored locally
  - [ ] Stripe handles all card data
  - [ ] PCI DSS compliance maintained

- [ ] **Personal Data (GDPR)**
  - [ ] User consent obtained
  - [ ] Data encryption at rest
  - [ ] Data deletion mechanism
  - [ ] Privacy policy published

### Docker Secrets (Alternative)

```bash
# For enhanced security, use Docker secrets
echo "my-db-password" | docker secret create db_password -

# Reference in docker-compose:
services:
  backend:
    secrets:
      - db_password
secrets:
  db_password:
    external: true
```

---

## Monitoring & Logging

### Application Monitoring

- [ ] **Error Tracking**
  - [ ] Sentry configured
  - [ ] Error notifications enabled
  - [ ] Error rate alerts set
  - [ ] Regular error review

- [ ] **Performance Monitoring**
  - [ ] Response time tracking
  - [ ] Database query monitoring
  - [ ] Resource usage alerts
  - [ ] Uptime monitoring

### Security Logging

- [ ] **Audit Logs**
  - [ ] Authentication attempts logged
  - [ ] Failed login attempts tracked
  - [ ] Admin actions logged
  - [ ] API calls logged

- [ ] **Log Management**
  - [ ] Centralized logging (ELK stack, CloudWatch)
  - [ ] Log retention policy (90 days minimum)
  - [ ] Log encryption
  - [ ] Log access control

### Intrusion Detection

- [ ] **Security Tools**
  - [ ] Fail2ban installed
  - [ ] OSSEC or Wazuh (optional)
  - [ ] Regular vulnerability scans
  - [ ] Penetration testing scheduled

---

## Compliance

### OWASP Top 10

- [ ] **A01:2021 - Broken Access Control**
  - [ ] Authorization checks on all endpoints
  - [ ] User can only access their own data
  - [ ] Admin routes protected

- [ ] **A02:2021 - Cryptographic Failures**
  - [ ] All data in transit encrypted (HTTPS)
  - [ ] Sensitive data encrypted at rest
  - [ ] Strong encryption algorithms used

- [ ] **A03:2021 - Injection**
  - [ ] ORM used for database queries
  - [ ] Input validation on all inputs
  - [ ] No eval() or exec() with user input

- [ ] **A04:2021 - Insecure Design**
  - [ ] Threat modeling completed
  - [ ] Security requirements defined
  - [ ] Secure architecture review

- [ ] **A05:2021 - Security Misconfiguration**
  - [ ] Default credentials changed
  - [ ] Debug mode disabled in production
  - [ ] Error messages don't leak info
  - [ ] Security headers configured

- [ ] **A06:2021 - Vulnerable Components**
  - [ ] All dependencies up to date
  - [ ] Regular dependency audits
  - [ ] Deprecated packages removed

```bash
# Check for vulnerable dependencies
docker compose run --rm backend pip-audit
docker compose run --rm backend python manage.py check
```

- [ ] **A07:2021 - Authentication Failures**
  - [ ] Strong password policy
  - [ ] Account lockout enabled
  - [ ] Session timeout configured
  - [ ] Secure password reset

- [ ] **A08:2021 - Software/Data Integrity**
  - [ ] Code signing enabled
  - [ ] CI/CD pipeline secured
  - [ ] Dependencies verified

- [ ] **A09:2021 - Logging Failures**
  - [ ] Security events logged
  - [ ] Logs protected from tampering
  - [ ] Log monitoring active

- [ ] **A10:2021 - SSRF**
  - [ ] URL validation on all external requests
  - [ ] Whitelist of allowed domains
  - [ ] Network segmentation

### GDPR Compliance (if applicable)

- [ ] **Data Protection**
  - [ ] Data encryption
  - [ ] Right to access implemented
  - [ ] Right to deletion implemented
  - [ ] Data portability supported

- [ ] **Documentation**
  - [ ] Privacy policy published
  - [ ] Data processing agreements signed
  - [ ] Data breach response plan

---

## Incident Response

### Incident Response Plan

- [ ] **Preparation**
  - [ ] Incident response team identified
  - [ ] Contact information documented
  - [ ] Response procedures documented
  - [ ] Communication plan ready

- [ ] **Detection & Analysis**
  - [ ] Monitoring alerts configured
  - [ ] Log analysis tools ready
  - [ ] Forensics tools available

- [ ] **Containment & Recovery**
  - [ ] Rollback procedures documented
  - [ ] Backup restoration tested
  - [ ] Disaster recovery plan

### Security Contacts

```
Security Team: security@yourdomain.com
On-Call: +1-XXX-XXX-XXXX
Incident Reporting: incidents@yourdomain.com
```

---

## Regular Security Tasks

### Daily
- [ ] Review error logs
- [ ] Check failed login attempts
- [ ] Monitor resource usage
- [ ] Check backup status

### Weekly
- [ ] Review security alerts
- [ ] Check SSL certificate expiry
- [ ] Review user access logs
- [ ] Update dependency packages

### Monthly
- [ ] Security patch updates
- [ ] Access control review
- [ ] Penetration testing
- [ ] Disaster recovery drill

### Quarterly
- [ ] Full security audit
- [ ] Password rotation
- [ ] Update security documentation
- [ ] Team security training

---

## Security Testing

### Before Deployment

```bash
# 1. Run Django security check
docker compose run --rm backend python manage.py check --deploy

# 2. Scan for secrets in code
pip install detect-secrets
detect-secrets scan

# 3. Scan Docker images
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image ecommerce_backend:latest

# 4. Check dependencies
docker compose run --rm backend pip-audit

# 5. Test SSL configuration
nmap --script ssl-enum-ciphers -p 443 api.yourdomain.com
```

### After Deployment

```bash
# 1. Port scan
nmap -sV api.yourdomain.com

# 2. Test for common vulnerabilities
nikto -h https://api.yourdomain.com

# 3. Check security headers
curl -I https://api.yourdomain.com

# 4. Test authentication
# Try accessing protected endpoints without token
curl https://api.yourdomain.com/api/backend/api/products/
# Should return 401 Unauthorized
```

---

## Emergency Procedures

### If Breach Detected

1. **Isolate**: Take affected services offline immediately
2. **Analyze**: Review logs to understand scope
3. **Notify**: Inform security team and stakeholders
4. **Remediate**: Fix vulnerability, rotate credentials
5. **Monitor**: Watch for further suspicious activity
6. **Document**: Record incident details and response

### Emergency Contacts

- **Security Team**: security@yourdomain.com
- **DevOps**: devops@yourdomain.com
- **Legal**: legal@yourdomain.com
- **External Security Firm**: [Contact Info]

---

## Security Audit Report

Use this checklist to generate a security audit report:

```markdown
# Security Audit Report
Date: YYYY-MM-DD
Auditor: [Name]

## Summary
- Total Checks: X
- Passed: Y
- Failed: Z
- Critical Issues: N

## Critical Issues
1. [Issue description]
   - Severity: Critical
   - Remediation: [Steps]
   - Deadline: [Date]

## Recommendations
1. [Recommendation]
2. [Recommendation]

## Sign-off
Security Lead: ___________  Date: _______
Tech Lead: ___________      Date: _______
```

---

## Resources

### Tools
- **Trivy**: Container vulnerability scanner
- **OWASP ZAP**: Web app security scanner
- **Nmap**: Network port scanner
- **SSL Labs**: SSL configuration tester
- **Fail2ban**: Intrusion prevention

### Documentation
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Django Security](https://docs.djangoproject.com/en/stable/topics/security/)
- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)

---

**Last Updated**: 2025-01-01
**Review Frequency**: Monthly
**Owner**: Security Team
