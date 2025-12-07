# Production Deployment Guide - Complete Edition

## Overview

This guide covers all production deployment features including SSL/TLS setup, automated backups, load testing, and database connection pooling.

---

## Table of Contents

1. [SSL/TLS Configuration](#ssltls-configuration)
2. [Database Backups](#database-backups)
3. [Load Testing](#load-testing)
4. [Connection Pooling with PgBouncer](#connection-pooling)
5. [Production Checklist](#production-checklist)

---

## SSL/TLS Configuration

### Prerequisites

- Domain name configured and pointing to your server
- Ports 80 and 443 open on your firewall
- Docker and docker-compose installed

### Setup SSL Certificates

We use Let's Encrypt for free, automated SSL certificates:

```bash
# Basic setup
make setup-ssl DOMAIN=yourdomain.com EMAIL=admin@yourdomain.com

# Or use the script directly
./scripts/setup_ssl.sh yourdomain.com admin@yourdomain.com
```

This script will:
1. Start Nginx in HTTP-only mode
2. Obtain SSL certificates from Let's Encrypt
3. Configure Nginx with SSL
4. Restart services with HTTPS enabled
5. Setup automatic renewal

### Verify SSL Configuration

```bash
# Test HTTPS connectivity
curl -I https://yourdomain.com

# Check SSL certificate
openssl s_client -connect yourdomain.com:443 -servername yourdomain.com

# Test SSL configuration (online)
# Visit: https://www.ssllabs.com/ssltest/analyze.html?d=yourdomain.com
```

### Automatic Certificate Renewal

Certificates are automatically renewed before expiration:

```bash
# Setup automatic renewal (adds cron job)
make setup-auto-backup

# Manual renewal
make renew-ssl

# Or directly
./scripts/renew_ssl.sh
```

**Cron Configuration:**

Add to your crontab (`sudo crontab -e`):

```bash
# Renew SSL certificates daily at 3 AM
0 3 * * * cd /path/to/project && ./scripts/renew_ssl.sh >> /var/log/ssl_renewal.log 2>&1
```

### Nginx Configuration Details

Our Nginx setup includes:

✅ **SSL/TLS Best Practices:**
- TLS 1.2 and 1.3 only
- Modern cipher suites
- OCSP stapling
- HTTP/2 support

✅ **Security Headers:**
- Strict-Transport-Security (HSTS)
- X-Frame-Options
- X-Content-Type-Options
- Content-Security-Policy

✅ **Performance:**
- Gzip compression
- Static file caching
- Connection keepalive

✅ **Protection:**
- Rate limiting (10 req/s general, 30 req/s API)
- Request size limits
- DDoS mitigation

### Domain Configuration

The SSL setup configures these subdomains:

- `yourdomain.com` - Frontend (Next.js)
- `www.yourdomain.com` - Frontend redirect
- `api.yourdomain.com` - Backend API + AI Gateway
- `monitoring.yourdomain.com` - Grafana dashboards

Update your DNS records:

```
A     yourdomain.com            -> YOUR_SERVER_IP
A     www.yourdomain.com        -> YOUR_SERVER_IP
A     api.yourdomain.com        -> YOUR_SERVER_IP
A     monitoring.yourdomain.com -> YOUR_SERVER_IP
```

---

## Database Backups

### Manual Backups

```bash
# Backup all databases
make backup-all

# Backup main database only
make backup-main

# Backup AI database only
make backup-ai

# Backup with S3 upload
make backup-to-s3

# Or use the script directly
./scripts/backup_databases.sh --all --verify --s3
```

**Script Options:**

```bash
./scripts/backup_databases.sh [OPTIONS]

Options:
  --all           Backup all databases (default)
  --main          Backup only main database
  --ai            Backup only AI database
  --retain DAYS   Number of days to retain backups (default: 30)
  --s3            Upload to S3 bucket
  --verify        Verify backup integrity after creation
```

### Automated Backups

Setup automated daily backups:

```bash
# Setup daily backups at 2 AM
make setup-auto-backup

# Or with custom schedule
./scripts/setup_backup_cron.sh --daily
./scripts/setup_backup_cron.sh --hourly
./scripts/setup_backup_cron.sh --custom "0 */6 * * *"  # Every 6 hours
```

This creates a cron job that:
- Runs backups daily at 2 AM (or your schedule)
- Logs to `/var/log/ecommerce_backup.log`
- Retains backups for 30 days
- Optionally uploads to S3

### Restore from Backup

```bash
# List available backups
make list-backups

# Restore specific backup
make restore BACKUP_FILE=backups/databases/main_db_20250128_120000.sql.gz

# Or use the script
./scripts/restore_database.sh backups/databases/main_db_20250128_120000.sql.gz

# Restore to AI database
./scripts/restore_database.sh backups/databases/ai_db_20250128_120000.sql.gz --ai
```

**Safety Features:**
- Creates safety backup before restore
- Confirms before destructive operations
- Verifies database connectivity
- Can rollback on failure

### S3 Backup Configuration

To enable S3 uploads, configure AWS credentials:

```bash
# Install AWS CLI
pip install awscli

# Configure AWS
aws configure

# Set backup bucket in environment
export AWS_BACKUP_BUCKET=your-bucket-name

# Or add to .env.production
echo "AWS_BACKUP_BUCKET=your-bucket-name" >> infrastructure/env/.env.production
```

### Backup Storage

Backups are stored in:
- Local: `./backups/databases/`
- S3: `s3://your-bucket/databases/`

**Naming Convention:**
```
main_db_20250128_120000.sql.gz    # Main database
ai_db_20250128_120000.sql.gz      # AI database
```

### Backup Monitoring

```bash
# View backup logs
tail -f /var/log/ecommerce_backup.log

# Check backup size
du -sh backups/databases/

# Verify latest backup
ls -lh backups/databases/ | head
```

---

## Load Testing

### Overview

We use Locust for realistic load testing with multiple scenarios:

- **Smoke Test**: 10 users, 2 minutes (quick sanity check)
- **Baseline Test**: 50 users, 10 minutes (performance baseline)
- **Stress Test**: 200 users, 15 minutes (find breaking points)
- **Spike Test**: 500 users, 5 minutes (sudden traffic spikes)
- **Endurance Test**: 100 users, 60 minutes (memory leaks, stability)

### Installation

```bash
# Install Locust
pip install -r tests/load/requirements.txt

# Or install globally
pip install locust==2.20.0
```

### Running Load Tests

```bash
# Smoke test (quick check)
make load-test-smoke

# Baseline performance test with report
make load-test-baseline

# Stress test to find limits
make load-test-stress

# Spike test for flash sales
make load-test-spike

# Endurance test for stability
make load-test-endurance

# Launch web UI for custom testing
make load-test-web
```

### Custom Load Tests

```bash
# Test against production
./scripts/run_load_tests.sh baseline --host https://api.yourdomain.com --report

# Custom parameters
locust -f tests/load/locustfile.py \
       --host http://localhost:8000 \
       --users 100 \
       --spawn-rate 10 \
       --run-time 5m \
       --headless \
       --html reports/custom_test.html
```

### Load Test Scenarios

Our test simulates realistic user behavior:

1. **User Registration/Login**
2. **Product Browsing** (homepage, categories)
3. **Product Search**
4. **Product Detail Views**
5. **AI Recommendations**
6. **Add to Cart**
7. **Cart Management**
8. **Fraud Detection Check**
9. **Checkout Initiation**

### Analyzing Results

Reports are saved to `tests/load/reports/`:

```bash
# View HTML report
open tests/load/reports/baseline_20250128_143000.html

# View CSV stats
cat tests/load/reports/baseline_20250128_143000_stats.csv

# Quick summary
head tests/load/reports/baseline_20250128_143000_stats.csv | column -t -s ','
```

### Performance Thresholds

Default acceptable thresholds:

| Metric | Threshold |
|--------|-----------|
| P95 Response Time | < 1000ms |
| P99 Response Time | < 2000ms |
| Error Rate | < 1% |
| Throughput | > 100 req/s |

AI Services have relaxed thresholds:
- P95: < 3000ms
- P99: < 5000ms

### Traffic Patterns

**Daily Traffic Shape:**
```python
# Simulates realistic daily traffic
stages = [
    (60s, 10 users),    # Morning ramp-up
    (120s, 50 users),   # Increasing traffic
    (180s, 100 users),  # Peak hours
    (240s, 100 users),  # Sustained peak
    (300s, 50 users),   # Evening decline
    (360s, 10 users),   # Night time
]
```

**Spike Traffic Shape:**
```python
# Simulates flash sale
stages = [
    (60s, 10 users),    # Normal traffic
    (120s, 200 users),  # Sudden spike
    (240s, 200 users),  # Sustained spike
    (300s, 10 users),   # Back to normal
]
```

### Monitoring During Load Tests

```bash
# Watch resource usage
watch -n 2 'docker stats --no-stream'

# Monitor response times
watch -n 1 'curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/health'

# Check error logs
docker-compose -f infrastructure/docker-compose.yaml logs -f backend | grep ERROR
```

---

## Connection Pooling

### PgBouncer Overview

PgBouncer is configured to:
- Reduce database connection overhead
- Pool connections efficiently
- Support up to 1,000 concurrent clients
- Maintain 25 connections per database
- Use transaction-level pooling

### Configuration

PgBouncer is automatically started with Docker Compose:

```yaml
services:
  pgbouncer:
    build: ./docker/pgbouncer
    ports:
      - "6432:6432"
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
```

### Using PgBouncer

Update your application to connect through PgBouncer:

**Before (Direct Connection):**
```python
DATABASE_URL = "postgresql://postgres:password@postgres:5432/ecommerce"
```

**After (Through PgBouncer):**
```python
DATABASE_URL = "postgresql://postgres:password@pgbouncer:6432/ecommerce"
```

### PgBouncer Configuration

Key settings in `infrastructure/docker/pgbouncer/pgbouncer.ini`:

```ini
# Connection Limits
max_client_conn = 1000           # Total client connections
default_pool_size = 25           # Connections per database
reserve_pool_size = 10           # Extra connections when full
max_db_connections = 100         # Max per database

# Pooling Mode
pool_mode = transaction          # Release after transaction (recommended for web apps)

# Timeouts
server_idle_timeout = 600        # Close idle server connections after 10 min
client_idle_timeout = 0          # Don't close idle clients
server_connect_timeout = 15      # Connection timeout
```

### Monitoring PgBouncer

```bash
# Check PgBouncer stats
docker exec -it ecommerce_pgbouncer psql -h localhost -p 6432 -U postgres -d pgbouncer -c "SHOW STATS"

# View pool status
docker exec -it ecommerce_pgbouncer psql -h localhost -p 6432 -U postgres -d pgbouncer -c "SHOW POOLS"

# Check active connections
docker exec -it ecommerce_pgbouncer psql -h localhost -p 6432 -U postgres -d pgbouncer -c "SHOW CLIENTS"

# View configuration
docker exec -it ecommerce_pgbouncer psql -h localhost -p 6432 -U postgres -d pgbouncer -c "SHOW CONFIG"
```

### Performance Benefits

With PgBouncer:
- **Reduced Latency**: Reuse existing connections
- **Higher Throughput**: Support more concurrent users
- **Lower Memory**: Fewer PostgreSQL processes
- **Better Stability**: Connection pooling prevents exhaustion

Typical improvements:
- 30-50% reduction in connection overhead
- 2-3x more concurrent connections supported
- Consistent performance under load

---

## Production Checklist

### Pre-Deployment

- [ ] Configure environment variables in `.env.production`
- [ ] Set strong passwords for all services
- [ ] Configure domain names in DNS
- [ ] Setup SSL certificates
- [ ] Configure backup schedule
- [ ] Run load tests to establish baseline
- [ ] Review security headers in Nginx
- [ ] Setup monitoring alerts
- [ ] Configure log rotation
- [ ] Test disaster recovery procedures

### Security

- [ ] Change default passwords
- [ ] Enable firewall (UFW/iptables)
- [ ] Configure fail2ban
- [ ] Enable HTTPS only
- [ ] Set up WAF rules
- [ ] Configure rate limiting
- [ ] Review CORS settings
- [ ] Enable database encryption at rest
- [ ] Setup VPN for admin access
- [ ] Audit user permissions

### Monitoring

- [ ] Configure Prometheus scraping
- [ ] Import Grafana dashboards
- [ ] Setup alert rules
- [ ] Configure notification channels (email, Slack)
- [ ] Enable APM (Application Performance Monitoring)
- [ ] Setup log aggregation
- [ ] Configure uptime monitoring
- [ ] Setup error tracking (Sentry)

### Performance

- [ ] Enable PgBouncer connection pooling
- [ ] Configure Redis caching
- [ ] Setup CDN for static files
- [ ] Enable Gzip compression
- [ ] Optimize database indexes
- [ ] Configure Celery workers
- [ ] Setup read replicas (if needed)
- [ ] Enable query caching

### Backups

- [ ] Test backup script
- [ ] Configure automated backups
- [ ] Setup S3 backup storage
- [ ] Test restore procedure
- [ ] Configure backup retention
- [ ] Setup backup monitoring
- [ ] Document recovery procedures

### Testing

- [ ] Run smoke tests
- [ ] Run baseline load tests
- [ ] Run stress tests
- [ ] Perform security audit
- [ ] Test SSL configuration
- [ ] Verify backup/restore
- [ ] Test failover scenarios
- [ ] Validate monitoring alerts

---

## Quick Commands Reference

```bash
# SSL/TLS
make setup-ssl DOMAIN=yourdomain.com EMAIL=admin@yourdomain.com
make renew-ssl

# Backups
make backup-all
make backup-to-s3
make restore BACKUP_FILE=path/to/backup.sql.gz
make setup-auto-backup
make list-backups

# Load Testing
make load-test-smoke
make load-test-baseline
make load-test-stress
make load-test-web

# Monitoring
make health
make monitoring
docker stats

# Database
make migrate
make dbshell
make createsuperuser

# Services
make prod
make restart
make logs-f
```

---

## Support & Troubleshooting

### SSL Issues

**Problem**: Certificate generation fails

```bash
# Check DNS resolution
nslookup yourdomain.com

# Verify ports are open
sudo netstat -tulpn | grep :80
sudo netstat -tulpn | grep :443

# Test with staging certificates first
./scripts/setup_ssl.sh yourdomain.com admin@yourdomain.com 1
```

### Backup Issues

**Problem**: Backup fails

```bash
# Check database connectivity
docker exec -it ecommerce_postgres psql -U postgres -d ecommerce -c "SELECT version();"

# Check disk space
df -h

# Verify permissions
ls -la backups/databases/
```

### Load Testing Issues

**Problem**: High error rate during tests

```bash
# Check service health
make health

# Monitor resources
docker stats

# Check logs for errors
make logs-f | grep ERROR

# Reduce concurrent users
./scripts/run_load_tests.sh smoke  # Start with small test
```

### PgBouncer Issues

**Problem**: Connection errors

```bash
# Check PgBouncer logs
docker logs ecommerce_pgbouncer

# Verify PostgreSQL is running
docker exec -it ecommerce_postgres pg_isready

# Test direct connection
psql -h localhost -p 6432 -U postgres -d ecommerce
```

---

## Additional Resources

- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [Locust Documentation](https://docs.locust.io/)
- [PgBouncer Documentation](https://www.pgbouncer.org/usage.html)
- [Nginx Security Best Practices](https://nginx.org/en/docs/http/configuring_https_servers.html)
- [PostgreSQL Backup Best Practices](https://www.postgresql.org/docs/current/backup.html)

---

**Last Updated**: 2025-01-28
**Version**: 1.0.0
