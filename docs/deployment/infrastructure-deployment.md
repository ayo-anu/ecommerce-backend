# Production Deployment Guide

## Table of Contents
- [Prerequisites](#prerequisites)
- [Pre-Deployment Checklist](#pre-deployment-checklist)
- [Environment Configuration](#environment-configuration)
- [SSL Certificate Setup](#ssl-certificate-setup)
- [Deployment Steps](#deployment-steps)
- [Post-Deployment Verification](#post-deployment-verification)
- [Monitoring Setup](#monitoring-setup)
- [Backup Configuration](#backup-configuration)
- [Rollback Procedures](#rollback-procedures)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

**Minimum Production Server Specs:**
- **CPU**: 16 cores
- **RAM**: 32 GB
- **Disk**: 500 GB SSD
- **OS**: Ubuntu 22.04 LTS or similar
- **Network**: Static IP address, open ports 80, 443

**Software Requirements:**
```bash
# Docker
Docker Engine: 24.0+
Docker Compose: 2.20+

# System tools
git
curl
openssl
```

### Install Docker

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt install docker-compose-plugin -y

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Verify installation
docker --version
docker compose version
```

---

## Pre-Deployment Checklist

### 1. **Domain & DNS Configuration**

- [ ] Domain purchased and active
- [ ] DNS A record pointing to server IP:
  ```
  api.yourdomain.com → YOUR_SERVER_IP
  yourdomain.com → YOUR_SERVER_IP
  ```
- [ ] DNS propagation verified (use `nslookup api.yourdomain.com`)

### 2. **Firewall Configuration**

```bash
# Ubuntu UFW
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS
sudo ufw enable

# Verify
sudo ufw status
```

**AWS Security Groups:**
```
Inbound Rules:
- Type: SSH,   Protocol: TCP, Port: 22,  Source: Your IP
- Type: HTTP,  Protocol: TCP, Port: 80,  Source: 0.0.0.0/0
- Type: HTTPS, Protocol: TCP, Port: 443, Source: 0.0.0.0/0
```

### 3. **Required Accounts & Keys**

- [ ] Stripe account (for payments)
- [ ] AWS account (for S3 storage)
- [ ] Sentry account (for error tracking)
- [ ] OpenAI API key (for chatbot)
- [ ] Email service (SendGrid, Mailgun, etc.)

---

## Environment Configuration

### 1. **Clone Repository**

```bash
# SSH to your server
ssh user@YOUR_SERVER_IP

# Clone repository
git clone https://github.com/yourusername/ecommerce-project.git
cd ecommerce-project/infrastructure
```

### 2. **Create Production Environment File**

Create `.env.prod` file:

```bash
# Navigate to infrastructure directory
cd infrastructure

# Create production environment file
nano .env.prod
```

Add the following variables:

```bash
# ==============================================================================
# PRODUCTION ENVIRONMENT VARIABLES
# ==============================================================================

# Django Settings
SECRET_KEY=your-super-secret-key-here-min-50-chars-random-string
DEBUG=False
ENVIRONMENT=production
ALLOWED_HOSTS=yourdomain.com,api.yourdomain.com

# Domain
DOMAIN=yourdomain.com

# Database
POSTGRES_DB=ecommerce
POSTGRES_USER=ecommerce_user
POSTGRES_PASSWORD=super-strong-db-password-here
POSTGRES_AI_DB=ecommerce_ai

# Redis
REDIS_PASSWORD=super-strong-redis-password-here

# Stripe Payment
STRIPE_SECRET_KEY=sk_live_xxxxxxxxxxxxxxxxxxxxx
STRIPE_PUBLISHABLE_KEY=pk_live_xxxxxxxxxxxxxxxxxxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxxxxxxxxxx

# AWS S3
AWS_ACCESS_KEY_ID=AKIAXXXXXXXXXXXXXXXX
AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AWS_STORAGE_BUCKET_NAME=your-bucket-name
AWS_S3_REGION_NAME=us-east-1

# Email (SendGrid example)
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=SG.xxxxxxxxxxxxxxxxxxxxx
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

# Sentry Error Tracking
SENTRY_DSN=https://xxxxxxxxxxxxxxxx@sentry.io/xxxxxxx

# OpenAI (for chatbot)
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Monitoring
GRAFANA_USER=admin
GRAFANA_PASSWORD=super-strong-grafana-password-here

# Log Level
LOG_LEVEL=WARNING
```

**Generate Strong Secrets:**

```bash
# Generate Django SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(50))"

# Generate database password
openssl rand -base64 32

# Generate Redis password
openssl rand -base64 32
```

### 3. **Validate Environment File**

```bash
# Check file exists and has correct permissions
ls -la .env.prod

# Secure the file (only owner can read)
chmod 600 .env.prod

# Verify no syntax errors
cat .env.prod | grep "="
```

---

## SSL Certificate Setup

### Option 1: Let's Encrypt (Recommended - Free)

```bash
# Install Certbot
sudo apt install certbot -y

# Stop any running services on port 80
docker compose down

# Generate certificate
sudo certbot certonly --standalone \
  -d yourdomain.com \
  -d api.yourdomain.com \
  --agree-tos \
  --email your-email@example.com \
  --non-interactive

# Certificates will be in:
# /etc/letsencrypt/live/yourdomain.com/fullchain.pem
# /etc/letsencrypt/live/yourdomain.com/privkey.pem
```

**Copy Certificates to Project:**

```bash
# Create SSL directory
mkdir -p infrastructure/nginx/ssl

# Copy certificates
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem infrastructure/nginx/ssl/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem infrastructure/nginx/ssl/

# Set permissions
sudo chown $USER:$USER infrastructure/nginx/ssl/*
chmod 644 infrastructure/nginx/ssl/fullchain.pem
chmod 600 infrastructure/nginx/ssl/privkey.pem
```

**Auto-Renewal Setup:**

```bash
# Test renewal
sudo certbot renew --dry-run

# Add cron job for auto-renewal
sudo crontab -e

# Add this line:
0 0 * * * certbot renew --quiet && docker compose -f /path/to/docker-compose.yaml -f /path/to/docker-compose.prod.yaml restart nginx
```

### Option 2: Custom SSL Certificate

```bash
# If you have your own certificates
mkdir -p infrastructure/nginx/ssl

# Copy your certificates
cp /path/to/your/fullchain.pem infrastructure/nginx/ssl/
cp /path/to/your/privkey.pem infrastructure/nginx/ssl/

# Set permissions
chmod 644 infrastructure/nginx/ssl/fullchain.pem
chmod 600 infrastructure/nginx/ssl/privkey.pem
```

### Update Nginx Configuration

Verify SSL paths in `nginx/conf.d/api.conf`:

```nginx
ssl_certificate /etc/nginx/ssl/fullchain.pem;
ssl_certificate_key /etc/nginx/ssl/privkey.pem;
```

---

## Deployment Steps

### 1. **Build Images**

```bash
# Navigate to infrastructure directory
cd infrastructure

# Load environment variables
export $(cat .env.prod | xargs)

# Pull base images
docker compose -f docker-compose.yaml pull

# Build application images
docker compose -f docker-compose.yaml build --no-cache
```

### 2. **Initialize Databases**

```bash
# Start only databases first
docker compose -f docker-compose.yaml up -d postgres postgres_ai redis

# Wait for databases to be ready
sleep 30

# Run Django migrations
docker compose -f docker-compose.yaml run --rm backend python manage.py migrate

# Create superuser
docker compose -f docker-compose.yaml run --rm backend python manage.py createsuperuser

# Collect static files
docker compose -f docker-compose.yaml run --rm backend python manage.py collectstatic --noinput

# Load initial data (if you have fixtures)
# docker compose -f docker-compose.yaml run --rm backend python manage.py loaddata initial_data.json
```

### 3. **Start All Services (Production Mode)**

```bash
# Start with production overrides
docker compose \
  -f docker-compose.yaml \
  -f docker-compose.prod.yaml \
  --env-file .env.prod \
  up -d

# View logs
docker compose logs -f

# Check all services are running
docker compose ps
```

### 4. **Verify Services**

```bash
# Check service health
docker compose ps

# All services should show "healthy" status
# Example output:
# ecommerce_nginx       Up (healthy)
# ecommerce_backend     Up (healthy)
# ecommerce_api_gateway Up (healthy)
# etc.

# Check logs for errors
docker compose logs nginx
docker compose logs api_gateway
docker compose logs backend
```

---

## Post-Deployment Verification

### 1. **Health Check Endpoints**

```bash
# Test Nginx
curl -I https://api.yourdomain.com/health
# Expected: 200 OK

# Test API Gateway
docker exec ecommerce_api_gateway curl -f http://localhost:8080/health
# Expected: {"status": "healthy", ...}

# Test Backend
docker exec ecommerce_backend curl -f http://localhost:8000/api/health/
# Expected: {"status": "ok", ...}
```

### 2. **Test API Endpoints**

```bash
# Test backend through gateway
curl https://api.yourdomain.com/api/backend/api/products/

# Test AI service through gateway
curl https://api.yourdomain.com/api/ai/recommender/health

# Test authentication
curl -X POST https://api.yourdomain.com/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your-password"}'
```

### 3. **Check SSL Certificate**

```bash
# Verify SSL certificate
echo | openssl s_client -servername api.yourdomain.com -connect api.yourdomain.com:443 2>/dev/null | openssl x509 -noout -dates

# Check SSL grade (optional)
# Visit: https://www.ssllabs.com/ssltest/analyze.html?d=api.yourdomain.com
```

### 4. **Monitor Resource Usage**

```bash
# Check container resource usage
docker stats

# Check disk usage
df -h

# Check Docker disk usage
docker system df
```

---

## Monitoring Setup

### 1. **Access Monitoring Dashboards**

**Prometheus** (Internal Only):
```bash
# Port forward for access (temporary)
ssh -L 9090:localhost:9090 user@YOUR_SERVER_IP

# Then access: http://localhost:9090
```

**Grafana** (Internal Only):
```bash
# Port forward for access
ssh -L 3001:localhost:3001 user@YOUR_SERVER_IP

# Access: http://localhost:3001
# Login: admin / <GRAFANA_PASSWORD from .env.prod>
```

**Jaeger** (Internal Only):
```bash
# Port forward for access
ssh -L 16686:localhost:16686 user@YOUR_SERVER_IP

# Access: http://localhost:16686
```

### 2. **Configure Alerts**

Edit `monitoring/prometheus/alerts/*.yml` to configure alerts.

Example alert for high error rate:

```yaml
# monitoring/prometheus/alerts/api_alerts.yml
- alert: HighErrorRate
  expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "High error rate detected"
    description: "Error rate is {{ $value }} requests/second"
```

---

## Backup Configuration

### 1. **Database Backups**

Create backup script:

```bash
# Create backups directory
mkdir -p /backups

# Create backup script
nano /usr/local/bin/backup-databases.sh
```

**Backup Script:**

```bash
#!/bin/bash

# Backup script for production databases

BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
PROJECT_DIR="/path/to/ecommerce-project/infrastructure"

# Backup PostgreSQL (Backend)
docker exec ecommerce_postgres pg_dump -U ecommerce_user ecommerce | gzip > \
  $BACKUP_DIR/backend_db_$DATE.sql.gz

# Backup PostgreSQL (AI)
docker exec ecommerce_postgres_ai pg_dump -U ecommerce_user ecommerce_ai | gzip > \
  $BACKUP_DIR/ai_db_$DATE.sql.gz

# Backup Redis
docker exec ecommerce_redis redis-cli --rdb /data/dump.rdb
docker cp ecommerce_redis:/data/dump.rdb $BACKUP_DIR/redis_$DATE.rdb

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.gz" -mtime +7 -delete
find $BACKUP_DIR -name "*.rdb" -mtime +7 -delete

# Upload to S3 (optional)
# aws s3 sync $BACKUP_DIR s3://your-backup-bucket/db-backups/

echo "Backup completed: $DATE"
```

**Schedule Backups:**

```bash
# Make script executable
chmod +x /usr/local/bin/backup-databases.sh

# Add to crontab (daily at 2 AM)
crontab -e

# Add line:
0 2 * * * /usr/local/bin/backup-databases.sh >> /var/log/backup.log 2>&1
```

### 2. **Docker Volume Backups**

```bash
# Backup all Docker volumes
docker run --rm \
  -v ecommerce_postgres_data:/data \
  -v /backups:/backup \
  ubuntu tar czf /backup/postgres_data_$(date +%Y%m%d).tar.gz -C /data .
```

---

## Rollback Procedures

### 1. **Rollback to Previous Version**

```bash
# Stop current deployment
docker compose -f docker-compose.yaml -f docker-compose.prod.yaml down

# Checkout previous version
git log --oneline -10  # Find commit to rollback to
git checkout <commit-hash>

# Rebuild and restart
docker compose -f docker-compose.yaml -f docker-compose.prod.yaml build
docker compose -f docker-compose.yaml -f docker-compose.prod.yaml up -d
```

### 2. **Database Rollback**

```bash
# Restore database from backup
cat /backups/backend_db_20240101_020000.sql.gz | \
  gunzip | \
  docker exec -i ecommerce_postgres psql -U ecommerce_user ecommerce
```

---

## Troubleshooting

### Common Issues

#### 1. **Services Not Starting**

```bash
# Check logs
docker compose logs <service-name>

# Check service health
docker compose ps

# Restart specific service
docker compose restart <service-name>
```

#### 2. **Nginx 502 Bad Gateway**

```bash
# Check if API Gateway is running
docker ps | grep api_gateway

# Check Gateway logs
docker compose logs api_gateway

# Check network connectivity
docker exec ecommerce_nginx ping api_gateway

# Restart Nginx
docker compose restart nginx
```

#### 3. **Database Connection Errors**

```bash
# Check database is running
docker ps | grep postgres

# Check database logs
docker compose logs postgres

# Test connection
docker exec ecommerce_backend python manage.py dbshell
```

#### 4. **Out of Disk Space**

```bash
# Check disk usage
df -h

# Clean Docker
docker system prune -a --volumes

# Clean old logs
journalctl --vacuum-time=7d
```

#### 5. **SSL Certificate Issues**

```bash
# Check certificate validity
openssl x509 -in /etc/nginx/ssl/fullchain.pem -text -noout

# Renew certificate
sudo certbot renew

# Restart Nginx
docker compose restart nginx
```

### Logs Location

```bash
# Application logs
docker compose logs -f [service-name]

# Nginx access logs
docker exec ecommerce_nginx cat /var/log/nginx/access.log

# Nginx error logs
docker exec ecommerce_nginx cat /var/log/nginx/error.log

# System logs
journalctl -u docker -f
```

---

## Maintenance Tasks

### Regular Maintenance Checklist

**Daily:**
- [ ] Check service health
- [ ] Review error logs
- [ ] Check disk space

**Weekly:**
- [ ] Review monitoring dashboards
- [ ] Check backup integrity
- [ ] Update dependencies (security patches)

**Monthly:**
- [ ] Review and optimize database
- [ ] Clean old logs and backups
- [ ] Update SSL certificates (if needed)
- [ ] Security audit

### Useful Commands

```bash
# View resource usage
docker stats

# Clean up
docker system prune -a

# View all containers
docker ps -a

# Restart all services
docker compose -f docker-compose.yaml -f docker-compose.prod.yaml restart

# Update services
docker compose -f docker-compose.yaml -f docker-compose.prod.yaml pull
docker compose -f docker-compose.yaml -f docker-compose.prod.yaml up -d

# View logs from last hour
docker compose logs --since 1h

# Export logs
docker compose logs > logs_$(date +%Y%m%d).txt
```

---

## Emergency Contacts

**Development Team:**
- Tech Lead: techleads@yourdomain.com
- DevOps: devops@yourdomain.com
- Security: security@yourdomain.com

**External Services:**
- AWS Support: https://console.aws.amazon.com/support/
- Stripe Support: https://support.stripe.com/
- Sentry: https://sentry.io/support/

---

## Next Steps

1. Set up external monitoring (Datadog, New Relic, etc.)
2. Configure automated alerts
3. Set up CI/CD pipeline
4. Implement blue-green deployment
5. Set up staging environment

**Related Documentation:**
- [Architecture Overview](./ARCHITECTURE.md)
- [Security Checklist](./SECURITY_CHECKLIST.md)
- [API Documentation](../docs/API.md)
