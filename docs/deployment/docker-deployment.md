# Deployment Guide

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Docker Deployment](#docker-deployment)
4. [Kubernetes Deployment](#kubernetes-deployment)
5. [Environment Configuration](#environment-configuration)
6. [Database Setup](#database-setup)
7. [Monitoring Setup](#monitoring-setup)
8. [Troubleshooting](#troubleshooting)
9. [Production Checklist](#production-checklist)

---

## Prerequisites

### Required Software

| Software | Minimum Version | Purpose |
|----------|----------------|---------|
| Docker | 20.10+ | Containerization |
| Docker Compose | 2.0+ | Local orchestration |
| Python | 3.11+ | Backend runtime |
| Node.js | 18+ | Frontend runtime |
| kubectl | 1.25+ | Kubernetes CLI |
| Helm | 3.10+ | K8s package manager |
| Git | 2.30+ | Version control |

### Cloud Account Requirements (Production)
- **AWS** / **GCP** / **Azure** account with billing enabled
- **Domain name** for your platform
- **SSL certificates** (Let's Encrypt or purchased)
- **Stripe account** for payments
- **SendGrid account** for emails

### System Requirements

**Development**:
- CPU: 4+ cores
- RAM: 16 GB minimum, 32 GB recommended
- Disk: 50 GB free space
- OS: Linux, macOS, or Windows with WSL2

**Production (per node)**:
- CPU: 8+ cores
- RAM: 32 GB+
- Disk: 200 GB SSD
- Network: 1 Gbps

---

## Local Development Setup

### Quick Start (5 minutes)

```bash
# 1. Clone the repository
git clone https://github.com/your-org/ecommerce-platform.git
cd ecommerce-platform

# 2. Copy environment files
cp infrastructure/env/.env.example infrastructure/env/.env.development

# 3. Start all services
make dev

# 4. Wait for services to be healthy
./scripts/health_check.py --wait

# 5. Access the platform
# - Frontend: http://localhost:3000
# - Backend API: http://localhost:8000
# - API Gateway: http://localhost:8080
# - Admin: http://localhost:8000/admin
```

### Step-by-Step Setup

#### 1. Clone and Navigate

```bash
git clone https://github.com/your-org/ecommerce-platform.git
cd ecommerce-platform
```

#### 2. Environment Configuration

```bash
# Copy the example environment file
cp infrastructure/env/.env.example infrastructure/env/.env.development

# Edit the file with your configuration
nano infrastructure/env/.env.development
```

**Required Environment Variables**:

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/ecommerce
REDIS_URL=redis://redis:6379/0

# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# AI Services
OPENAI_API_KEY=sk-your-openai-key
QDRANT_URL=http://qdrant:6333

# Stripe (test keys)
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...

# Email (optional for local dev)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

#### 3. Build Docker Images

```bash
# Build all services
docker-compose -f infrastructure/docker-compose.yaml build

# Or use the Makefile
make build
```

#### 4. Initialize Databases

```bash
# Run migrations
docker-compose exec backend python manage.py migrate

# Create superuser
docker-compose exec backend python manage.py createsuperuser

# Load sample data
docker-compose exec backend python manage.py loaddata fixtures/sample_data.json
```

#### 5. Start Services

```bash
# Start all services in detached mode
docker-compose -f infrastructure/docker-compose.yaml \
               -f infrastructure/docker-compose.dev.yaml up -d

# Or use the Makefile
make dev

# View logs
docker-compose logs -f

# Check service health
./scripts/health_check.py
```

#### 6. Access Services

| Service | URL | Credentials |
|---------|-----|-------------|
| Frontend | http://localhost:3000 | - |
| Backend API | http://localhost:8000/api/docs/ | - |
| Django Admin | http://localhost:8000/admin/ | (created in step 4) |
| API Gateway | http://localhost:8080/docs | - |
| Prometheus | http://localhost:9090 | - |
| Grafana | http://localhost:3000 | admin/admin |
| RabbitMQ | http://localhost:15672 | guest/guest |

### Development Workflow

#### Hot Reload Configuration

**Backend (Django)**:
- Code changes are automatically detected
- No restart needed for most changes
- Restart required for: new dependencies, settings changes

**Frontend (Next.js)**:
- Fast refresh enabled
- Changes reflect immediately in browser
- Hard refresh (Ctrl+R) if needed

**AI Services (FastAPI)**:
- Auto-reload enabled with `--reload` flag
- Model changes require service restart

#### Running Tests

```bash
# Run all tests
make test

# Run specific test suites
make test-backend
make test-ai-services
make test-frontend

# Run with coverage
make test-coverage
```

#### Database Management

```bash
# Create migration
docker-compose exec backend python manage.py makemigrations

# Apply migrations
docker-compose exec backend python manage.py migrate

# Database shell
docker-compose exec backend python manage.py dbshell

# Django shell
docker-compose exec backend python manage.py shell
```

#### Debugging

**Backend**:
```bash
# View logs
docker-compose logs -f backend

# Attach debugger
docker-compose exec backend python -m pdb manage.py runserver 0.0.0.0:8000
```

**AI Services**:
```bash
# View logs for specific service
docker-compose logs -f recommender

# Debug mode (verbose logging)
LOGLEVEL=DEBUG docker-compose up recommender
```

**Frontend**:
```bash
# View logs
docker-compose logs -f frontend

# Debug in browser
# Open DevTools → Sources → Set breakpoints
```

---

## Docker Deployment

### Architecture Overview

```
                    ┌──────────────┐
                    │ Load Balancer│
                    │   (Nginx)    │
                    └───────┬──────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐  ┌────────────────┐  ┌──────────────┐
│   Frontend    │  │  Backend API   │  │ API Gateway  │
│  (Next.js)    │  │   (Django)     │  │  (FastAPI)   │
└───────────────┘  └────────────────┘  └──────────────┘
                            │
                ┌───────────┴───────────┐
                │                       │
        ┌───────▼───────┐       ┌──────▼──────┐
        │   Database    │       │  AI Services│
        │  (Postgres)   │       │  (7 FastAPI)│
        └───────────────┘       └─────────────┘
```

### Single-Server Deployment

**For staging or small-scale production**

#### 1. Server Setup

```bash
# SSH into your server
ssh user@your-server.com

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

#### 2. Clone Repository

```bash
git clone https://github.com/your-org/ecommerce-platform.git
cd ecommerce-platform
```

#### 3. Configure Production Environment

```bash
cp infrastructure/env/.env.example infrastructure/env/.env.production

# Edit with production values
nano infrastructure/env/.env.production
```

**Production Environment Variables**:

```bash
# Django
SECRET_KEY=generate-a-secure-random-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database (use managed service recommended)
DATABASE_URL=postgresql://user:password@db-host:5432/ecommerce_prod

# Redis (use managed service recommended)
REDIS_URL=redis://redis-host:6379/0

# Security
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=your-sendgrid-api-key

# Stripe (live keys)
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# AWS S3 (for file storage)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_STORAGE_BUCKET_NAME=your-bucket-name
AWS_S3_REGION_NAME=us-east-1

# Monitoring
SENTRY_DSN=https://your-sentry-dsn
```

#### 4. SSL Certificate Setup

```bash
# Install Certbot
sudo apt-get update
sudo apt-get install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Certificates will be in /etc/letsencrypt/live/yourdomain.com/
```

#### 5. Build and Deploy

```bash
# Build production images
docker-compose -f infrastructure/docker-compose.yaml \
               -f infrastructure/docker-compose.prod.yaml build

# Start services
docker-compose -f infrastructure/docker-compose.yaml \
               -f infrastructure/docker-compose.prod.yaml up -d

# Run migrations
docker-compose exec backend python manage.py migrate

# Collect static files
docker-compose exec backend python manage.py collectstatic --no-input

# Create superuser
docker-compose exec backend python manage.py createsuperuser
```

#### 6. Configure Nginx

```nginx
# /etc/nginx/sites-available/ecommerce
upstream backend {
    server localhost:8000;
}

upstream frontend {
    server localhost:3000;
}

upstream gateway {
    server localhost:8080;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;

    # API requests
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # AI Services (via gateway)
    location /ai/ {
        proxy_pass http://gateway;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Frontend
    location / {
        proxy_pass http://frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_cache_bypass $http_upgrade;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/ecommerce /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

#### 7. Setup Monitoring

```bash
# Start monitoring stack
docker-compose -f infrastructure/docker-compose.yaml \
               -f infrastructure/docker-compose.monitoring.yaml up -d

# Access Grafana
# http://your-server:3001
# Default credentials: admin/admin (change immediately)
```

#### 8. Automated Backups

```bash
# Create backup script
cat > /opt/ecommerce/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backups/$(date +%Y-%m-%d)"
mkdir -p $BACKUP_DIR

# Backup database
docker-compose exec -T postgres pg_dump -U postgres ecommerce > $BACKUP_DIR/db.sql

# Backup media files
docker-compose exec -T backend tar czf - /app/media > $BACKUP_DIR/media.tar.gz

# Upload to S3
aws s3 cp $BACKUP_DIR s3://your-backup-bucket/$(date +%Y-%m-%d)/ --recursive

# Clean old backups (keep 30 days)
find /backups -type d -mtime +30 -exec rm -rf {} +
EOF

chmod +x /opt/ecommerce/backup.sh

# Add to crontab (daily at 2 AM)
echo "0 2 * * * /opt/ecommerce/backup.sh" | crontab -
```

---

## Kubernetes Deployment

### Prerequisites

```bash
# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Install Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Verify installations
kubectl version --client
helm version
```

### Cluster Setup

#### Option 1: AWS EKS

```bash
# Install eksctl
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin

# Create cluster
eksctl create cluster \
  --name ecommerce-prod \
  --version 1.28 \
  --region us-east-1 \
  --nodegroup-name standard-workers \
  --node-type t3.xlarge \
  --nodes 3 \
  --nodes-min 3 \
  --nodes-max 10 \
  --managed

# Configure kubectl
aws eks update-kubeconfig --region us-east-1 --name ecommerce-prod
```

#### Option 2: GCP GKE

```bash
# Install gcloud CLI
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Create cluster
gcloud container clusters create ecommerce-prod \
  --zone us-central1-a \
  --num-nodes 3 \
  --machine-type n1-standard-4 \
  --enable-autoscaling \
  --min-nodes 3 \
  --max-nodes 10

# Get credentials
gcloud container clusters get-credentials ecommerce-prod --zone us-central1-a
```

### Deploy to Kubernetes

#### 1. Create Namespace

```bash
kubectl create namespace ecommerce-prod
kubectl config set-context --current --namespace=ecommerce-prod
```

#### 2. Create Secrets

```bash
# Database credentials
kubectl create secret generic db-credentials \
  --from-literal=POSTGRES_PASSWORD=your-db-password \
  --from-literal=DATABASE_URL=postgresql://user:pass@host:5432/db

# Django secret key
kubectl create secret generic django-secret \
  --from-literal=SECRET_KEY=your-secret-key

# Stripe API keys
kubectl create secret generic stripe-keys \
  --from-literal=STRIPE_SECRET_KEY=sk_live_... \
  --from-literal=STRIPE_PUBLISHABLE_KEY=pk_live_...

# AWS credentials
kubectl create secret generic aws-credentials \
  --from-literal=AWS_ACCESS_KEY_ID=your-access-key \
  --from-literal=AWS_SECRET_ACCESS_KEY=your-secret-key
```

#### 3. Create ConfigMaps

```bash
kubectl create configmap backend-config \
  --from-env-file=infrastructure/env/.env.production
```

#### 4. Deploy Services

```bash
# Apply all Kubernetes manifests
kubectl apply -f infrastructure/k8s/

# Or use Helm (recommended)
helm install ecommerce ./infrastructure/helm/ecommerce \
  --namespace ecommerce-prod \
  --values infrastructure/helm/ecommerce/values-prod.yaml
```

#### 5. Verify Deployment

```bash
# Check pods
kubectl get pods

# Check services
kubectl get services

# Check deployments
kubectl get deployments

# View logs
kubectl logs -f deployment/backend

# Get external IP
kubectl get service nginx-ingress-controller
```

#### 6. Configure DNS

```bash
# Get LoadBalancer IP
export LOAD_BALANCER_IP=$(kubectl get service nginx-ingress-controller -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# Add DNS A record
# yourdomain.com -> $LOAD_BALANCER_IP
# www.yourdomain.com -> $LOAD_BALANCER_IP
```

### Scaling

#### Manual Scaling

```bash
# Scale backend
kubectl scale deployment backend --replicas=5

# Scale AI services
kubectl scale deployment recommender --replicas=3
```

#### Auto-scaling (HPA)

```bash
# Enable metrics server (if not installed)
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Create HPA for backend
kubectl autoscale deployment backend \
  --cpu-percent=70 \
  --min=3 \
  --max=10

# Create HPA for AI services
kubectl autoscale deployment recommender \
  --cpu-percent=80 \
  --min=2 \
  --max=8
```

### Rolling Updates

```bash
# Update image
kubectl set image deployment/backend backend=your-repo/backend:v2.0.0

# Monitor rollout
kubectl rollout status deployment/backend

# Rollback if needed
kubectl rollout undo deployment/backend
```

### Blue-Green Deployment

```bash
# Deploy new version (green)
kubectl apply -f infrastructure/k8s/backend-green.yaml

# Test green deployment
kubectl port-forward deployment/backend-green 8001:8000

# Switch traffic
kubectl patch service backend -p '{"spec":{"selector":{"version":"green"}}}'

# Remove old version (blue) after verification
kubectl delete deployment backend-blue
```

---

## Environment Configuration

### Environment Variables by Service

#### Backend (Django)

```bash
# Core Django
SECRET_KEY=required
DEBUG=False
ALLOWED_HOSTS=comma,separated,hosts

# Database
DATABASE_URL=postgresql://user:pass@host:port/db

# Cache
REDIS_URL=redis://host:port/db

# Security
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=user
EMAIL_HOST_PASSWORD=pass
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

# Stripe
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# AWS S3
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_STORAGE_BUCKET_NAME=your-bucket
AWS_S3_REGION_NAME=us-east-1

# Monitoring
SENTRY_DSN=https://...
```

#### AI Services

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:port/ai_db

# Redis
REDIS_URL=redis://host:port/0

# Vector DB
QDRANT_URL=http://qdrant:6333

# RabbitMQ
RABBITMQ_URL=amqp://user:pass@host:port/

# OpenAI (for chatbot)
OPENAI_API_KEY=sk-...

# Model paths
MODEL_PATH=/models

# Logging
LOG_LEVEL=INFO
```

#### Frontend

```bash
# Next.js
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_...
NEXT_PUBLIC_SENTRY_DSN=https://...

# Build
NODE_ENV=production
```

---

## Database Setup

### PostgreSQL Production Setup

#### Managed Database (Recommended)

**AWS RDS**:
```bash
# Create RDS instance
aws rds create-db-instance \
  --db-instance-identifier ecommerce-prod \
  --db-instance-class db.t3.large \
  --engine postgres \
  --engine-version 15.3 \
  --master-username postgres \
  --master-user-password YourSecurePassword \
  --allocated-storage 100 \
  --storage-type gp3 \
  --backup-retention-period 30 \
  --multi-az \
  --publicly-accessible false
```

**Connection String**:
```
postgresql://postgres:password@ecommerce-prod.xxxxx.us-east-1.rds.amazonaws.com:5432/ecommerce
```

#### Self-Hosted PostgreSQL

```bash
# Install PostgreSQL
sudo apt-get update
sudo apt-get install postgresql-15

# Configure for production
sudo nano /etc/postgresql/15/main/postgresql.conf
```

**Key Configuration**:
```conf
max_connections = 200
shared_buffers = 4GB
effective_cache_size = 12GB
maintenance_work_mem = 1GB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 10MB
```

### Migrations

```bash
# Run migrations
docker-compose exec backend python manage.py migrate

# Or in Kubernetes
kubectl exec -it deployment/backend -- python manage.py migrate
```

### Database Backup & Restore

**Backup**:
```bash
# Docker
docker-compose exec postgres pg_dump -U postgres ecommerce > backup.sql

# Kubernetes
kubectl exec deployment/postgres -- pg_dump -U postgres ecommerce > backup.sql
```

**Restore**:
```bash
# Docker
docker-compose exec -T postgres psql -U postgres ecommerce < backup.sql

# Kubernetes
kubectl exec -i deployment/postgres -- psql -U postgres ecommerce < backup.sql
```

---

## Monitoring Setup

### Prometheus + Grafana

#### Install Prometheus Operator

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace
```

#### Access Grafana

```bash
# Get password
kubectl get secret --namespace monitoring prometheus-grafana \
  -o jsonpath="{.data.admin-password}" | base64 --decode

# Port forward
kubectl port-forward --namespace monitoring service/prometheus-grafana 3000:80

# Access: http://localhost:3000
# Username: admin
# Password: (from above command)
```

#### Import Dashboards

1. Django Dashboard: Import ID 12718
2. FastAPI Dashboard: Import ID 14439
3. PostgreSQL Dashboard: Import ID 9628
4. Redis Dashboard: Import ID 11835

### Application Monitoring (Sentry)

```python
# Install Sentry SDK (already in requirements.txt)
pip install sentry-sdk

# Backend configuration (in settings.py)
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn=os.getenv('SENTRY_DSN'),
    integrations=[DjangoIntegration()],
    traces_sample_rate=0.1,
    environment='production',
)
```

---

## Troubleshooting

### Common Issues

#### Issue: Services Can't Connect to Database

**Symptoms**: Connection refused errors in logs

**Solutions**:
```bash
# Check if database is running
docker-compose ps postgres

# Check database logs
docker-compose logs postgres

# Verify connection string
echo $DATABASE_URL

# Test connection
docker-compose exec backend python manage.py dbshell
```

#### Issue: AI Service Out of Memory

**Symptoms**: Service crashes, OOMKilled in Kubernetes

**Solutions**:
```bash
# Increase memory limit in docker-compose
services:
  recommender:
    mem_limit: 4g

# Or in Kubernetes
resources:
  limits:
    memory: "4Gi"
  requests:
    memory: "2Gi"

# Optimize model loading
# Use model quantization
# Enable model caching
```

#### Issue: Slow API Response

**Symptoms**: High latency, timeouts

**Solutions**:
```bash
# Check service health
./scripts/health_check.py

# Monitor database queries
docker-compose exec backend python manage.py debugsqlshell

# Check Redis cache hit rate
redis-cli info stats

# Scale services
kubectl scale deployment backend --replicas=5

# Add database indexes
# Review slow query logs
```

#### Issue: SSL Certificate Expired

**Symptoms**: Browser warnings, SSL errors

**Solutions**:
```bash
# Renew Let's Encrypt certificate
sudo certbot renew

# Test renewal
sudo certbot renew --dry-run

# Reload Nginx
sudo systemctl reload nginx
```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Django debug mode (development only!)
export DEBUG=True

# View all logs
docker-compose logs --tail=100 -f

# Specific service logs
docker-compose logs -f backend
```

---

## Production Checklist

### Pre-Deployment

- [ ] All tests passing (backend, frontend, AI services)
- [ ] Security audit completed
- [ ] Load testing completed
- [ ] Database migrations tested
- [ ] Backup strategy configured
- [ ] Monitoring alerts configured
- [ ] SSL certificates obtained
- [ ] DNS records configured
- [ ] Environment variables set
- [ ] Secrets rotated
- [ ] API rate limits configured
- [ ] CDN configured (if applicable)

### Post-Deployment

- [ ] Verify all services healthy
- [ ] Run smoke tests
- [ ] Check monitoring dashboards
- [ ] Verify database connectivity
- [ ] Test authentication flow
- [ ] Test payment processing
- [ ] Verify email sending
- [ ] Check logs for errors
- [ ] Monitor resource usage
- [ ] Verify backup job running

### Security Checklist

- [ ] `DEBUG=False` in production
- [ ] Strong `SECRET_KEY` generated
- [ ] `ALLOWED_HOSTS` configured
- [ ] HTTPS enforced
- [ ] Secure cookies enabled
- [ ] CORS configured correctly
- [ ] Rate limiting enabled
- [ ] SQL injection protection (using ORM)
- [ ] XSS protection enabled
- [ ] CSRF protection enabled
- [ ] Dependencies updated
- [ ] Security headers configured
- [ ] Firewall rules configured
- [ ] Database access restricted
- [ ] Secrets not in version control

---

## Support & Resources

- **Documentation**: https://docs.yourdomain.com
- **GitHub Issues**: https://github.com/your-org/ecommerce-platform/issues
- **Slack Channel**: #ecommerce-platform
- **Email**: support@yourdomain.com

---

## Next Steps

1. Complete local development setup
2. Deploy to staging environment
3. Run integration tests
4. Load testing
5. Security audit
6. Deploy to production
7. Monitor and optimize

For detailed troubleshooting, see [Troubleshooting Guide](./troubleshooting.md).
For API documentation, see [API Reference](./api_reference.md).
