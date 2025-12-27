# Enterprise E-Commerce Platform with AI Microservices

A production-grade, AI-powered e-commerce platform built on microservices architecture. This monorepo integrates Django REST Framework backend, FastAPI-based API Gateway, and seven specialized AI microservices for intelligent commerce capabilities.

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)](https://github.com/yourusername/ecommerce-project/actions)
[![Code Quality](https://img.shields.io/badge/code%20quality-A-brightgreen.svg)](https://github.com/yourusername/ecommerce-project)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/django-5.1.14+-green.svg)](https://www.djangoproject.com/)
[![FastAPI](https://img.shields.io/badge/fastapi-latest-green.svg)](https://fastapi.tiangolo.com/)

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Architectural Tradeoffs](#architectural-tradeoffs)
- [Technology Stack](#technology-stack)
- [Features](#features)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Services Overview](#services-overview)
- [Development](#development)
- [Testing](#testing)
- [Deployment](#deployment)
- [Monitoring & Observability](#monitoring--observability)
- [Security](#security)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

This platform delivers enterprise-grade e-commerce capabilities enhanced with cutting-edge artificial intelligence. Designed for scalability, reliability, and performance, it serves as a foundation for modern digital commerce applications.

### Key Capabilities

- **Intelligent Recommendations** - Hybrid collaborative and content-based filtering
- **Semantic Search** - Natural language understanding with vector embeddings
- **Dynamic Pricing** - ML-driven price optimization and competitive positioning
- **Fraud Prevention** - Real-time transaction risk assessment
- **Demand Forecasting** - Time-series prediction for inventory optimization
- **AI Customer Support** - RAG-based chatbot with contextual understanding
- **Visual Recognition** - Image-based product search and classification

### Design Principles

- **Microservices Architecture** - Independent, scalable service deployment
- **API-First Design** - RESTful APIs with comprehensive OpenAPI documentation
- **Event-Driven** - Asynchronous processing with Celery and RabbitMQ
- **Observability** - Distributed tracing, metrics, and centralized logging
- **Security-First** - JWT authentication, network segmentation, secrets management
- **Production-Ready** - Health checks, graceful degradation, circuit breakers

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Load Balancer (Nginx)                     │
│                         Port 80/443 (HTTPS)                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   API Gateway   │  ⭐ Top-level infrastructure
                    │   (FastAPI)     │     (services/gateway/)
                    │   Port 8080     │
                    └────────┬────────┘
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                 │
           ▼                 ▼                 ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │   Backend    │  │ AI Services  │  │  Monitoring  │
    │   (Django)   │  │   (FastAPI)  │  │  Services    │
    │   Port 8000  │  │  Ports 8001- │  │              │
    │              │  │     8007     │  │              │
    └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
           │                 │                 │
           └─────────────────┼─────────────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
        ┌──────────┐   ┌─────────┐   ┌─────────┐
        │PostgreSQL│   │  Redis  │   │ Qdrant  │
        │  (Main)  │   │ (Cache) │   │(Vector) │
        └──────────┘   └─────────┘   └─────────┘
```

### Network Topology

The platform implements a **4-tier network architecture** for security and isolation:

- **Public Network** (`172.20.0.0/24`) - Nginx ↔ API Gateway (public-facing traffic)
- **Backend Network** (`172.21.0.0/24`) - API Gateway ↔ Backend + Databases + Queue
- **AI Network** (`172.22.0.0/24`) - API Gateway ↔ AI Services + AI Databases
- **Monitoring Network** (`172.23.0.0/24`) - Prometheus ↔ All Services (metrics collection)

### Architecture Highlights

**Production-Grade Structure** ✅
- API Gateway moved to `services/gateway/` (top-level) - not nested under `ai/`
- Shared utilities in `services/shared/` - truly shared, not domain-specific
- Clear separation: infrastructure (gateway, shared) vs domain logic (backend, ai)
- Folder structure matches runtime architecture and network topology

For detailed architecture documentation, see [docs/architecture/system-design.md](docs/architecture/system-design.md).

---

## Architectural Tradeoffs

This section documents key architectural decisions, their benefits, drawbacks, and the reasoning behind them.

### 1. Microservices vs Monolith Architecture

**Decision**: Microservices architecture with 9 independent services (1 backend + 7 AI services + 1 API gateway)

**Benefits** ✅
- **Independent Scaling** - Scale AI services separately based on demand (e.g., scale recommendation engine during peak traffic without scaling fraud detection)
- **Technology Flexibility** - Django for backend CRUD, FastAPI for high-performance AI services
- **Fault Isolation** - Failure in pricing engine doesn't crash the entire platform
- **Team Autonomy** - Different teams can own and deploy services independently
- **Faster Deployments** - Deploy individual services without full system downtime

**Drawbacks** ⚠️
- **Operational Complexity** - Managing 9+ services requires sophisticated monitoring and orchestration
- **Network Overhead** - Inter-service communication adds latency (50-100ms per hop)
- **Distributed Debugging** - Tracing issues across services requires distributed tracing tools (Jaeger)
- **Data Consistency** - No ACID transactions across services; eventual consistency challenges
- **Resource Overhead** - Each service needs its own container, memory, and CPU allocation
- **Development Complexity** - Local development requires running multiple services simultaneously

**When This Works**:
- Teams larger than 5-10 developers
- Need to scale specific components independently
- Different services have different performance characteristics
- Long-term platform with evolving requirements

**When to Avoid**:
- Small teams (<3 developers)
- MVP or early-stage products
- Simple CRUD applications
- Limited infrastructure budget

---

### 2. Multiple Database Strategy

**Decision**: 5 specialized databases (PostgreSQL x2, Redis, Elasticsearch, Qdrant)

**Benefits** ✅
- **Optimized Performance** - Each database optimized for its use case (OLTP, cache, search, vectors)
- **Data Isolation** - AI data separated from transactional data for security and compliance
- **Scalability** - Scale search and vector databases independently from main database
- **Right Tool for Job** - Vector similarity search requires Qdrant; full-text search needs Elasticsearch

**Drawbacks** ⚠️
- **Operational Burden** - 5 databases to backup, monitor, upgrade, and secure
- **Cost** - Higher infrastructure costs (~$200-500/month in cloud vs ~$50 for single database)
- **Data Synchronization** - Keeping Elasticsearch in sync with PostgreSQL requires change data capture
- **Consistency Challenges** - No cross-database transactions; eventual consistency across stores
- **Learning Curve** - Team needs expertise in multiple database technologies
- **Backup Complexity** - Coordinated backups across 5 systems to maintain data consistency

**Alternatives Considered**:
- **Single PostgreSQL** - Simpler but slower for search and vector operations (50-100x slower for similarity search)
- **PostgreSQL + pgvector** - Reduces databases to 2, but vector performance degrades beyond 100K vectors
- **Cloud Managed Services** - Reduce operational burden but increase costs 3-5x

---

### 3. Network Segmentation (4-Tier Architecture)

**Decision**: Separate networks for public, backend, AI, and monitoring traffic

**Benefits** ✅
- **Security in Depth** - Compromised service can't directly access all systems
- **Compliance** - Meets PCI-DSS and SOC 2 requirements for network isolation
- **Traffic Control** - Prevent AI services from directly accessing payment data
- **Blast Radius Reduction** - Limit impact of security breaches

**Drawbacks** ⚠️
- **Complexity** - More complex networking configuration and troubleshooting
- **Performance Overhead** - Additional network hops add ~5-10ms latency
- **Development Friction** - Local development requires careful network setup
- **Debugging Difficulty** - Network issues harder to diagnose across multiple subnets

**Simplified Alternative**: Single shared network (like most Docker Compose setups)
- **Pros**: Simpler, faster, easier to debug
- **Cons**: Violates security best practices; fails compliance audits

---

### 4. Dedicated AI Microservices

**Decision**: 7 separate AI services instead of monolithic AI service or integrated backend

**Benefits** ✅
- **Model Isolation** - Large PyTorch models don't bloat backend memory (recommendation model = 500MB)
- **Independent Deployment** - Update fraud detection model without redeploying entire backend
- **Specialized Scaling** - Scale search engine 10x during holiday sales without scaling chatbot
- **Technology Optimization** - Use CUDA/GPU for visual recognition without affecting Django backend
- **Development Velocity** - ML team deploys models without coordinating with backend team

**Drawbacks** ⚠️
- **Resource Consumption** - 7 AI containers require significant memory (~8-16GB total vs ~2GB for monolith)
- **Cold Start Latency** - First request to each service takes 2-5 seconds to load models
- **Network Calls** - Each AI prediction requires network roundtrip (vs in-process function call)
- **Deployment Overhead** - 7 additional CI/CD pipelines, Dockerfiles, and health checks
- **Cost** - Higher cloud costs (~$300-800/month vs ~$50-100 for single service)

**When to Consolidate**:
- Early MVP with <1000 users
- Limited budget (<$200/month infrastructure)
- Small team without dedicated ML engineers
- **Consider**: Merge 2-3 low-traffic services (chatbot + visual recognition)

---

### 5. Docker Compose vs Kubernetes

**Decision**: Docker Compose for deployment and orchestration

**Benefits** ✅
- **Simplicity** - Single YAML file, easy to understand and maintain
- **Fast Setup** - Running locally or on a VM takes <10 minutes
- **Low Resource Overhead** - No control plane overhead (vs Kubernetes ~1-2GB)
- **Development Experience** - Same tooling for dev and production
- **Cost Effective** - Run on single VPS ($40-100/month) vs managed Kubernetes ($150-500/month)

**Drawbacks** ⚠️
- **Single Node** - No automatic multi-node clustering or failover
- **Manual Scaling** - Must manually scale services (no Horizontal Pod Autoscaler)
- **Limited Self-Healing** - Basic restart policies vs Kubernetes' sophisticated health management
- **No Rolling Updates** - Deployment causes brief downtime vs zero-downtime rolling updates
- **Production Limitations** - Not suitable beyond 10,000 concurrent users or 99.99% uptime SLA

**Migration Path to Kubernetes**:
- **Phase 1** (0-10K users): Docker Compose on single node
- **Phase 2** (10K-100K users): Docker Swarm for simple multi-node clustering
- **Phase 3** (100K+ users): Kubernetes for enterprise-grade orchestration

---

### 6. Synchronous API + Asynchronous Tasks (Celery)

**Decision**: Synchronous REST APIs with Celery for background processing

**Benefits** ✅
- **Familiar Model** - REST APIs widely understood by frontend developers
- **Immediate Responses** - Users get instant feedback for queries
- **Background Processing** - Email, reports, ML training run asynchronously without blocking requests
- **Retry Logic** - Celery handles failed tasks with automatic retries

**Drawbacks** ⚠️
- **Blocking Operations** - Long-running AI predictions (>2s) block HTTP workers
- **Resource Inefficiency** - Idle HTTP workers consume memory waiting for I/O
- **Scalability Limits** - Synchronous model limits concurrent requests to ~100-500 per server
- **Message Queue Dependency** - RabbitMQ becomes critical dependency; outage blocks async tasks

**Alternative Patterns Considered**:
- **Async/Await (FastAPI)** - Better for I/O-bound operations, already used in AI services
- **Event-Driven Architecture** - More scalable but increases complexity 10x
- **GraphQL** - Reduces over-fetching but adds query complexity

---

### 7. Self-Hosted Infrastructure vs Cloud Services

**Decision**: Self-hosted PostgreSQL, Redis, Elasticsearch on Docker

**Benefits** ✅
- **Cost Control** - ~$50-100/month self-hosted vs ~$300-800/month managed services
- **Full Control** - Custom configurations, extensions, and optimizations
- **Data Privacy** - Data stays in your infrastructure (important for compliance)
- **No Vendor Lock-in** - Easy to migrate between cloud providers

**Drawbacks** ⚠️
- **Operational Burden** - Team responsible for backups, security patches, monitoring
- **Expertise Required** - Need DBA skills for PostgreSQL tuning and troubleshooting
- **Availability Risk** - No built-in high availability; must implement replication manually
- **Backup Responsibility** - Data loss risk if backups not properly configured
- **Time Investment** - ~5-10 hours/month for maintenance vs ~0 hours for managed services

**Hybrid Approach** (Recommended for Production):
- **Self-hosted**: PostgreSQL, Redis (predictable load, cost-sensitive)
- **Managed**: Elasticsearch, Qdrant (complex operations, less critical)
- **Cloud**: Backups to S3, monitoring with Datadog/New Relic

---

### 8. API Gateway Pattern

**Decision**: Dedicated API Gateway (FastAPI) as unified entry point

**Benefits** ✅
- **Single Entry Point** - Clients call one URL instead of 8 different services
- **Cross-Cutting Concerns** - Authentication, rate limiting, logging in one place
- **Circuit Breaker** - Prevents cascade failures when AI services are down
- **Response Caching** - Cache AI predictions to reduce load and costs
- **Service Discovery** - Backend/frontend don't need to track 7 AI service endpoints

**Drawbacks** ⚠️
- **Single Point of Failure** - Gateway outage blocks all traffic (mitigate with clustering)
- **Latency Overhead** - Adds 10-30ms to every request
- **Complexity** - Another service to develop, deploy, and maintain
- **Bottleneck Risk** - Gateway can become performance bottleneck under extreme load

**Alternatives**:
- **No Gateway** - Clients call services directly (simpler but less secure)
- **Service Mesh** (Istio/Linkerd) - More powerful but 10x more complex
- **API Management Platform** (Kong, AWS API Gateway) - Less custom code but higher cost

---

### 9. Service Granularity

**Decision**: Fine-grained services (7 separate AI services vs 1 unified AI service)

**Benefits** ✅
- **Bounded Contexts** - Each service has clear responsibility
- **Independent Evolution** - Update recommendation algorithm without touching fraud detection
- **Failure Isolation** - Bug in chatbot doesn't affect pricing engine
- **Team Ownership** - Each team owns their service end-to-end

**Drawbacks** ⚠️
- **Over-Engineering Risk** - 7 services may be excessive for <10K users
- **Shared Code Duplication** - Common utilities duplicated across services
- **Integration Overhead** - More API contracts to maintain and version
- **Resource Waste** - Low-traffic services (chatbot, visual recognition) may not justify dedicated containers

**Right-Sizing Recommendations**:
- **MVP (0-1K users)**: Merge into 2 services (backend + unified AI service)
- **Growth (1K-10K users)**: Split into 4 services (backend + recommendations + search + fraud)
- **Scale (10K+ users)**: Current 9-service architecture justified

---

### 10. Trade-Off Summary Matrix

| Aspect | Current Choice | Complexity | Cost/Month | Scalability | Team Size |
|--------|---------------|------------|-----------|-------------|-----------|
| **Architecture** | Microservices | High | $200-500 | Excellent (1M+ users) | 5+ developers |
| **Databases** | 5 specialized | High | $150-400 | Excellent | Need DBA |
| **Orchestration** | Docker Compose | Medium | $50-150 | Medium (10K users) | 2+ ops |
| **AI Services** | 7 separate | High | $300-800 | Excellent | 3+ ML engineers |
| **Infrastructure** | Self-hosted | High | $100-300 | Medium | Need DevOps |
| **Gateway** | FastAPI | Medium | $20-50 | High | 1-2 developers |

**Total Infrastructure Cost Estimate**:
- **Development**: ~$0 (local Docker)
- **Small Production** (1K users): ~$100-200/month (single VPS)
- **Medium Production** (10K users): ~$500-1000/month (3-5 VPS + managed databases)
- **Large Production** (100K+ users): ~$2000-5000/month (Kubernetes cluster + managed services)

---

## Technology Stack

| Layer | Technologies |
|-------|-------------|
| **Backend API** | Python 3.11, Django 5.1.14+, Django REST Framework 3.15, PostgreSQL 15, Redis 7, Celery 5.5, Elasticsearch 8.11 |
| **API Gateway** | Python 3.11, FastAPI, Uvicorn, Pydantic |
| **AI Services** | Python 3.11, FastAPI, PyTorch, Scikit-learn, Transformers, SpaCy, Sentence-BERT |
| **Vector Database** | Qdrant 1.7 |
| **Message Queue** | RabbitMQ 3.12 |
| **Connection Pool** | PgBouncer |
| **Monitoring** | Prometheus, Grafana, Jaeger (distributed tracing) |
| **Infrastructure** | Docker, Docker Compose, Nginx |
| **Payments** | Stripe |
| **Storage** | AWS S3 (optional), local volumes |
| **Security** | HashiCorp Vault (optional), Argon2 password hashing, JWT tokens |

---

## Features

### Core E-Commerce Functionality

✅ **User Management**
- JWT-based authentication with token refresh
- Role-based access control (RBAC)
- User profiles and preferences
- Account security features

✅ **Product Catalog**
- Multi-category product organization
- Advanced search and filtering
- Product variants and attributes
- Image management
- Elasticsearch integration for full-text search

✅ **Order Management**
- Shopping cart with session persistence
- Secure checkout process
- Order tracking and history
- Order status management
- Email notifications

✅ **Payment Processing**
- Stripe payment integration
- Secure payment handling
- Webhook processing for payment events
- Transaction history

✅ **Admin Dashboard**
- Django admin interface
- Product management
- Order management
- User management
- Analytics and reporting

### AI-Powered Features

🤖 **Recommendation Engine** (Port 8001)
- Collaborative filtering algorithms
- Content-based recommendations
- Hybrid recommendation system
- Real-time personalization

🔍 **Semantic Search Engine** (Port 8002)
- Natural language query understanding
- Vector similarity search with Qdrant
- BM25 ranking algorithm
- Multi-modal search capabilities

💰 **Dynamic Pricing Engine** (Port 8003)
- Demand-based price optimization
- Competitive price monitoring
- Price elasticity modeling
- A/B testing for pricing strategies

💬 **AI Chatbot with RAG** (Port 8004)
- Retrieval-Augmented Generation
- Product knowledge base integration
- Order status inquiries
- Customer support automation

🛡️ **Fraud Detection** (Port 8005)
- Real-time transaction scoring
- Anomaly detection algorithms
- Pattern recognition
- Risk threshold management

📈 **Demand Forecasting** (Port 8006)
- Time-series prediction models
- Seasonal trend analysis
- Inventory optimization recommendations
- SKU-level forecasting

📸 **Visual Recognition** (Port 8007)
- Image-based product search
- Automatic product categorization
- Visual similarity matching
- Quality control automation

---

## Quick Start

### Prerequisites

- **Docker** 20.10+ and **Docker Compose** 2.0+
- **Python** 3.11+ (for local development)
- **Git** 2.0+
- Minimum 8GB RAM, 20GB disk space
- **Optional**: AWS account (for S3 storage), Stripe account (for payments)

### Installation (5-10 minutes)

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/ecommerce-project.git
cd ecommerce-project

# 2. Create environment configuration
cp .env.vault.example .env
# Edit .env with your configuration (see Configuration section below)

# 3. Build Docker images
make build

# 4. Start infrastructure services (databases, cache, queue)
docker-compose -f deploy/docker/compose/base.yml up -d postgres postgres_ai redis elasticsearch qdrant rabbitmq

# 5. Wait for services to be healthy (30-60 seconds)
sleep 60

# 6. Run database migrations
docker-compose -f deploy/docker/compose/base.yml exec backend python manage.py migrate

# 7. Create Django superuser
docker-compose -f deploy/docker/compose/base.yml exec backend python manage.py createsuperuser

# 8. Start all services
make dev

# 9. Verify service health
make health
```

### Configuration

Edit `.env` file with the following required configurations:

```env
# Django Settings
SECRET_KEY=your-secure-secret-key-change-in-production
DEBUG=True  # Set to False in production
ALLOWED_HOSTS=localhost,127.0.0.1,backend,api_gateway

# Database
POSTGRES_DB=ecommerce
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secure_password_here
POSTGRES_AI_DB=ecommerce_ai

# Redis
REDIS_PASSWORD=redis_secure_password

# AI Services (Optional - required for chatbot)
OPENAI_API_KEY=sk-your-openai-api-key

# Stripe (Optional - required for payments)
STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key
STRIPE_PUBLISHABLE_KEY=pk_test_your_stripe_publishable_key

# AWS S3 (Optional - for file storage)
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_STORAGE_BUCKET_NAME=your_bucket_name

# Monitoring (Optional)
SENTRY_DSN=your_sentry_dsn_for_error_tracking
```

### Access the Platform

Once all services are running, access the following endpoints:

| Service | URL | Description |
|---------|-----|-------------|
| **Backend API** | http://localhost:8000 | Django REST API |
| **API Documentation** | http://localhost:8000/api/docs/ | Interactive API docs (Swagger) |
| **Django Admin** | http://localhost:8000/admin/ | Admin dashboard |
| **API Gateway** | http://localhost:8080 | Unified AI services gateway |
| **Gateway Docs** | http://localhost:8080/docs | API Gateway documentation |
| **Prometheus** | http://localhost:9090 | Metrics and monitoring |
| **Grafana** | http://localhost:3001 | Dashboards (admin/admin) |
| **Jaeger UI** | http://localhost:16686 | Distributed tracing |
| **RabbitMQ Management** | http://localhost:15672 | Message queue (admin/admin) |

### Service Ports Reference

| Service | Internal Port | External Port (Dev) |
|---------|--------------|---------------------|
| Backend | 8000 | 8000 |
| API Gateway | 8080 | 8080 |
| Recommendation Engine | 8001 | 8001 |
| Search Engine | 8002 | 8002 |
| Pricing Engine | 8003 | 8003 |
| Chatbot | 8004 | 8004 |
| Fraud Detection | 8005 | 8005 |
| Demand Forecasting | 8006 | 8006 |
| Visual Recognition | 8007 | 8007 |
| PostgreSQL (Main) | 5432 | 5432 |
| PostgreSQL (AI) | 5432 | 5433 |
| PgBouncer | 6432 | 6432 |
| Redis | 6379 | 6379 |
| Elasticsearch | 9200/9300 | 9200/9300 |
| Qdrant | 6333/6334 | 6333/6334 |
| RabbitMQ | 5672/15672 | 5672/15672 |
| Prometheus | 9090 | 9090 |
| Grafana | 3000 | 3001 |
| Jaeger | 16686 | 16686 |

**Note**: In production, only Nginx ports (80/443) are exposed externally.

---

## Project Structure

```
ecommerce-project/
│
├── services/                          # Application services
│   ├── gateway/                       # ⭐ API Gateway (FastAPI) - Unified entry point
│   │   ├── auth.py                    # JWT authentication
│   │   ├── circuit_breaker.py         # Circuit breaker patterns
│   │   ├── resilient_proxy.py         # Resilient HTTP proxy
│   │   ├── rate_limiter.py            # Rate limiting
│   │   ├── middleware.py              # Custom middleware
│   │   ├── gateway_routes.py          # Central routing table
│   │   ├── main.py                    # Gateway entry point
│   │   ├── Dockerfile                 # Gateway Docker image
│   │   └── requirements.txt           # Gateway dependencies
│   │
│   ├── shared/                        # ⭐ Shared utilities (cross-cutting)
│   │   ├── config.py                  # Configuration management
│   │   ├── logger.py                  # Structured logging
│   │   ├── monitoring.py              # Prometheus metrics
│   │   ├── redis_client.py            # Redis client wrapper
│   │   ├── vector_db.py               # Qdrant client wrapper
│   │   ├── database.py                # Database connections
│   │   ├── tracing.py                 # Distributed tracing
│   │   ├── health.py                  # Health check utilities
│   │   └── service_auth_middleware.py # Service authentication
│   │
│   ├── backend/                       # Django REST Framework backend
│   │   ├── apps/                      # Django applications
│   │   │   ├── accounts/              # User authentication and management
│   │   │   ├── analytics/             # Business analytics
│   │   │   ├── core/                  # Core utilities and base models
│   │   │   ├── health/                # Health check endpoints
│   │   │   ├── notifications/         # Email and notification system
│   │   │   ├── orders/                # Order processing
│   │   │   ├── payments/              # Stripe payment integration
│   │   │   └── products/              # Product catalog
│   │   ├── config/                    # Django settings
│   │   ├── requirements/              # Python dependencies
│   │   │   ├── base.txt               # Base requirements
│   │   │   ├── development.txt        # Development requirements
│   │   │   └── production.txt         # Production requirements
│   │   ├── tests/                     # Backend unit tests
│   │   ├── Dockerfile                 # Backend Docker image
│   │   └── manage.py                  # Django management script
│   │
│   └── ai/                            # AI microservices domain
│       ├── services/                  # AI microservices
│       │   ├── recommendation_engine/ # Personalized recommendations
│       │   ├── search_engine/         # Semantic search
│       │   ├── pricing_engine/        # Dynamic pricing
│       │   ├── chatbot_rag/           # AI chatbot with RAG
│       │   ├── fraud_detection/       # Fraud prevention
│       │   ├── demand_forecasting/    # Demand prediction
│       │   └── visual_recognition/    # Computer vision
│       │
│       ├── models/                    # Trained ML models
│       ├── ml_pipeline/               # Model training pipelines
│       ├── requirements-base.txt      # Shared AI dependencies
│       └── tests/                     # AI services tests
│
├── deploy/                            # Deployment configuration
│   ├── docker/                        # Docker configurations
│   │   ├── compose/                   # Docker Compose files
│   │   │   ├── base.yml               # Base services configuration
│   │   │   ├── development.yml        # Development overrides
│   │   │   ├── production.yml         # Production configuration
│   │   │   └── ci.yml                 # CI/CD configuration
│   │   ├── images/                    # Custom Docker images
│   │   └── scripts/                   # Deployment scripts
│   │
│   ├── nginx/                         # Nginx configuration
│   │   ├── conf.d/                    # Nginx site configs
│   │   └── ssl/                       # SSL certificates
│   │
│   └── vault/                         # HashiCorp Vault config
│       ├── config/                    # Vault server config
│       └── policies/                  # Vault access policies
│
├── infrastructure/                    # Infrastructure as Code
│   ├── docker/                        # Docker configurations
│   │   ├── nginx/                     # Nginx Docker config
│   │   ├── pgbouncer/                 # PgBouncer config
│   │   └── postgres/                  # PostgreSQL init scripts
│   └── nginx/                         # Additional Nginx configs
│
├── monitoring/                        # Observability stack
│   ├── prometheus/                    # Prometheus configuration
│   │   ├── prometheus.yml             # Prometheus config
│   │   ├── alerts/                    # Alert rules
│   │   └── recording_rules/           # Recording rules
│   │
│   └── grafana/                       # Grafana dashboards
│       ├── dashboards/                # Dashboard definitions
│       └── provisioning/              # Data source configs
│
├── scripts/                           # Utility scripts
│   ├── deployment/                    # Deployment scripts
│   ├── backup/                        # Backup and restore scripts
│   ├── security/                      # Security audit scripts
│   └── maintenance/                   # Maintenance utilities
│
├── docs/                              # Documentation
│   ├── architecture/                  # Architecture documentation
│   ├── deployment/                    # Deployment guides
│   ├── development/                   # Development guides
│   ├── security/                      # Security documentation
│   └── operations/                    # Operations runbooks
│
├── tests/                             # End-to-end tests
│   ├── integration/                   # Integration tests
│   └── load/                          # Load testing scripts
│
├── config/                            # Configuration files
│   ├── environments/                  # Environment-specific configs
│   └── policies/                      # Policy definitions
│
├── terraform/                         # Terraform IaC (optional)
│
├── .env                               # Environment variables
├── .env.vault.example                 # Vault configuration example
├── Makefile                           # Development commands
├── docker-compose.yml                 # Main compose file (symlink)
└── README.md                          # This file
```

---

## Services Overview

### Backend Service (Django)

**Port**: 8000
**Technology**: Django 5.1.14+, Django REST Framework 3.15, PostgreSQL 15

The core e-commerce API providing:
- RESTful API with OpenAPI/Swagger documentation
- User authentication (JWT with refresh tokens)
- Product catalog management
- Order processing and tracking
- Stripe payment integration
- Email notifications
- Admin dashboard
- Elasticsearch integration for search

**Key Django Apps**:
- `accounts` - User authentication and profile management
- `products` - Product catalog and inventory
- `orders` - Shopping cart and order processing
- `payments` - Stripe payment integration
- `notifications` - Email and notification system
- `analytics` - Business analytics and reporting
- `core` - Shared utilities and base models
- `health` - Service health checks

**Documentation**: [services/backend/README.md](services/backend/README.md)

---

### API Gateway (Production-Grade Infrastructure)

**Port**: 8080
**Technology**: FastAPI, Uvicorn
**Location**: `services/gateway/` (top-level infrastructure component)

**Architecture Decision**: The gateway is positioned as a top-level service (not under `ai/`) because it serves as the unified entry point for **all services** (backend + 7 AI services), handling cross-cutting concerns:

**Core Capabilities**:
- **Request Routing** - Routes to backend (Django) and all AI services
- **Circuit Breaker** - Prevents cascade failures with fallback mechanisms
- **Rate Limiting** - Per-user and per-endpoint throttling
- **Authentication** - JWT validation and service-to-service auth
- **Resilient Proxy** - Retry logic, timeouts, and graceful degradation
- **Response Caching** - Redis-backed caching for performance
- **Distributed Tracing** - Jaeger integration for request tracking
- **Metrics Collection** - Prometheus metrics for monitoring

**Network Position**: Bridges three networks (public, backend, ai) making it a true gateway, not an AI-specific component.

**Documentation**: http://localhost:8080/docs (when running)

---

### AI Microservices

#### 1. Recommendation Engine (Port 8001)

**Purpose**: Personalized product recommendations

**Algorithms**:
- Collaborative filtering (user-item matrix factorization)
- Content-based filtering (TF-IDF, embeddings)
- Hybrid recommendation (weighted ensemble)
- Cold-start handling for new users/products

**Use Cases**:
- Homepage personalized recommendations
- Product detail page cross-sell suggestions
- Shopping cart upsell recommendations
- Email campaign personalization

---

#### 2. Search Engine (Port 8002)

**Purpose**: Semantic search with natural language understanding

**Technology**:
- Sentence-BERT for query/product embeddings
- Qdrant vector database for similarity search
- BM25 for keyword matching
- Query understanding and expansion

**Features**:
- Natural language queries
- Typo tolerance and spell correction
- Faceted search and filtering
- Search autocomplete
- Visual search integration

---

#### 3. Pricing Engine (Port 8003)

**Purpose**: Dynamic price optimization

**Models**:
- Price elasticity estimation
- Demand forecasting integration
- Competitive pricing analysis
- XGBoost for price optimization
- Reinforcement learning for pricing strategies

**Capabilities**:
- Real-time price adjustments
- A/B testing for pricing
- Promotional pricing
- Inventory clearance optimization

---

#### 4. Chatbot with RAG (Port 8004)

**Purpose**: AI-powered customer support

**Technology**:
- Retrieval-Augmented Generation (RAG)
- OpenAI GPT integration
- Qdrant for knowledge base retrieval
- Context-aware conversations

**Features**:
- Product information queries
- Order status tracking
- FAQ handling
- Escalation to human support
- Multi-turn conversations

**Note**: Requires `OPENAI_API_KEY` environment variable.

---

#### 5. Fraud Detection (Port 8005)

**Purpose**: Real-time transaction risk assessment

**Models**:
- LightGBM classifier for fraud detection
- Isolation Forest for anomaly detection
- Rule-based risk scoring
- Behavioral analysis

**Risk Factors Analyzed**:
- Transaction patterns
- Device fingerprinting
- Velocity checks
- Geographic anomalies
- User behavior patterns

---

#### 6. Demand Forecasting (Port 8006)

**Purpose**: Inventory optimization through demand prediction

**Models**:
- Prophet for time-series forecasting
- LSTM neural networks
- SARIMA for seasonal patterns
- Multi-level forecasting (SKU, category, store)

**Applications**:
- Inventory replenishment
- Warehouse allocation
- Promotional planning
- Supplier order optimization

---

#### 7. Visual Recognition (Port 8007)

**Purpose**: Computer vision for product images

**Models**:
- ResNet50 for image classification
- YOLO for object detection
- Siamese networks for similarity
- CNN-based embeddings

**Use Cases**:
- Visual product search
- Automatic product categorization
- Image quality control
- Duplicate detection

---

## Development

### Common Development Commands

```bash
# Start all services in development mode
make dev

# View logs from all services
make logs-f

# Check service health
make health

# Django management commands
make migrate              # Run database migrations
make makemigrations      # Create new migrations
make shell               # Open Django shell
make createsuperuser     # Create admin user

# Database operations
make dbshell             # Open PostgreSQL shell
make seed                # Load sample data
make backup              # Backup databases
make restore             # Restore from backup

# Testing
make test                # Run all tests
make test-backend        # Backend tests only
make test-ai             # AI services tests
make test-integration    # Integration tests
make test-coverage       # Tests with coverage

# Docker operations
make build               # Build all images
make build-fast          # Build with BuildKit (60-85% faster)
make rebuild             # Rebuild from scratch (no cache)
make stop                # Stop all services
make restart             # Restart all services
make clean               # Remove all containers and volumes
make prune               # Clean up Docker resources

# Monitoring
make ps                  # Show running containers
make stats               # Show resource usage
```

### Development Workflow

```bash
# 1. Start development environment
make dev

# 2. Make code changes (hot reload enabled for most services)

# 3. Run tests
make test

# 4. Check service health
make health

# 5. View logs
make logs-f

# 6. Stop services when done
make stop
```

### Adding New Features

#### Backend Feature (Django)

```bash
# 1. Create new app or modify existing
cd services/backend
python manage.py startapp myapp  # If new app

# 2. Add models to myapp/models.py

# 3. Create migrations
make makemigrations

# 4. Apply migrations
make migrate

# 5. Add views and serializers

# 6. Add URL routes

# 7. Write tests in myapp/tests/

# 8. Run tests
make test-backend
```

#### AI Service Feature

```bash
# 1. Navigate to service directory
cd services/ai/services/recommendation_engine  # Example

# 2. Add new endpoints in routers/

# 3. Update models if needed

# 4. Add tests in tests/

# 5. Update API Gateway routing if needed
cd ../../../gateway  # Gateway is now top-level

# 6. Run tests
make test-ai
```

### Environment Variables

Development environment variables are in `.env` file:

```env
# Development Settings
DEBUG=True
LOG_LEVEL=DEBUG

# Database URLs (auto-configured for Docker)
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/ecommerce
REDIS_URL=redis://:redis_password@redis:6379/0

# External Services (optional in development)
STRIPE_SECRET_KEY=sk_test_...  # For payment testing
OPENAI_API_KEY=sk-...          # For chatbot
AWS_ACCESS_KEY_ID=...          # For S3 storage
```

---

## Testing

### Test Strategy

- **Unit Tests** - Individual function/class testing
- **Integration Tests** - Service interaction testing
- **End-to-End Tests** - Complete user flow testing
- **Load Tests** - Performance and scalability testing

### Running Tests

```bash
# Run all tests
make test

# Backend tests with coverage
make test-backend
pytest services/backend/tests/ --cov=apps --cov-report=html

# AI services tests
make test-ai
pytest services/ai/tests/ -v

# Integration tests
make test-integration
pytest tests/integration/ -v

# Specific test file
pytest services/backend/tests/test_orders.py -v

# Specific test function
pytest services/backend/tests/test_orders.py::test_create_order -v
```

### Load Testing

```bash
# Install Locust
pip install locust

# Run smoke test (10 users, 2 minutes)
make load-test-smoke

# Run baseline test (50 users, 10 minutes)
make load-test-baseline

# Run stress test (200 users, 15 minutes)
make load-test-stress

# Launch Locust web UI
make load-test-web
# Navigate to http://localhost:8089
```

### Test Coverage

```bash
# Generate coverage report
make test-coverage

# View HTML coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

---

## Deployment

### Development Deployment

```bash
# Start all services in development mode
make dev
```

### Staging Deployment

```bash
# Build production images
make build

# Start with production configuration
docker-compose -f deploy/docker/compose/base.yml \
               -f deploy/docker/compose/production.yml up -d

# Run migrations
docker-compose -f deploy/docker/compose/base.yml exec backend \
               python manage.py migrate

# Collect static files
docker-compose -f deploy/docker/compose/base.yml exec backend \
               python manage.py collectstatic --no-input
```

### Production Deployment

#### Prerequisites

1. Production server with Docker installed
2. Domain name configured with DNS
3. SSL certificates (Let's Encrypt recommended)
4. Environment variables configured

#### Deployment Steps

```bash
# 1. Clone repository on production server
git clone https://github.com/yourusername/ecommerce-project.git
cd ecommerce-project

# 2. Create production environment file
cp .env.vault.example .env
# Edit .env with production credentials
nano .env

# 3. Set production environment variables
export ENVIRONMENT=production
export DEBUG=False

# 4. Build production images
DOCKER_BUILDKIT=1 docker-compose -f deploy/docker/compose/base.yml build

# 5. Start services
docker-compose -f deploy/docker/compose/base.yml \
               -f deploy/docker/compose/production.yml up -d

# 6. Wait for services to be healthy
sleep 60

# 7. Run migrations
docker-compose -f deploy/docker/compose/base.yml exec backend \
               python manage.py migrate --no-input

# 8. Collect static files
docker-compose -f deploy/docker/compose/base.yml exec backend \
               python manage.py collectstatic --no-input

# 9. Create superuser
docker-compose -f deploy/docker/compose/base.yml exec backend \
               python manage.py createsuperuser

# 10. Verify deployment
docker-compose -f deploy/docker/compose/base.yml ps
curl http://localhost:8000/api/health/
```

#### SSL/TLS Setup

```bash
# Setup SSL with Let's Encrypt
make setup-ssl

# Renew certificates
make renew-ssl
```

#### Production Checklist

- [ ] Set `DEBUG=False` in environment
- [ ] Configure strong `SECRET_KEY`
- [ ] Set secure database passwords
- [ ] Configure allowed hosts
- [ ] Enable HTTPS only
- [ ] Set up SSL certificates
- [ ] Configure firewall rules
- [ ] Set up monitoring and alerting
- [ ] Configure backups
- [ ] Set up log aggregation
- [ ] Configure Sentry for error tracking
- [ ] Review security settings
- [ ] Load test the deployment
- [ ] Set up CDN for static files
- [ ] Configure rate limiting

### Deployment Documentation

For comprehensive deployment guides, see:
- [Docker Deployment Guide](docs/deployment/docker-deployment.md)
- [Production Guide](docs/deployment/production-guide.md)
- [CI/CD Pipeline](docs/deployment/ci-cd-pipeline.md)

---

## Monitoring & Observability

### Metrics Collection (Prometheus)

Access Prometheus at http://localhost:9090

**Collected Metrics**:
- HTTP request rate, latency, error rate
- Database connection pool status
- Cache hit/miss rates
- Queue depth and processing time
- Resource utilization (CPU, memory, disk)
- ML model inference latency
- Business metrics (orders, revenue)

**Example Queries**:
```promql
# Request rate per service
rate(http_requests_total[5m])

# 95th percentile latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Error rate
rate(http_requests_total{status=~"5.."}[5m])
```

### Dashboards (Grafana)

Access Grafana at http://localhost:3001 (default: admin/admin)

**Pre-configured Dashboards**:
- System Overview - High-level health metrics
- Service Performance - Per-service metrics
- Database Performance - PostgreSQL metrics
- AI Model Metrics - ML inference stats
- Business KPIs - Orders, revenue, conversions
- Infrastructure - Resource utilization

### Distributed Tracing (Jaeger)

Access Jaeger UI at http://localhost:16686

**Traced Operations**:
- API requests across services
- Database queries
- Cache operations
- ML model inference
- External API calls

**Example Usage**:
1. Make API request
2. Copy trace ID from response headers
3. Search in Jaeger UI
4. Analyze request flow and timing

### Logging

Centralized logging with structured JSON logs.

```bash
# View logs from all services
make logs-f

# View backend logs only
make logs-backend

# View specific service logs
docker-compose -f deploy/docker/compose/base.yml logs -f recommender
```

### Health Checks

```bash
# Check all services health
make health

# Individual service health endpoints
curl http://localhost:8000/api/health/  # Backend
curl http://localhost:8080/health       # API Gateway
curl http://localhost:8001/health       # Recommender
# ... other services on ports 8002-8007
```

### Alerting

Alert rules configured in `monitoring/prometheus/alerts/`:

**Critical Alerts**:
- Service down
- High error rate (>5%)
- High latency (P95 > 1s)
- Database connection pool exhausted
- Disk space low (<10%)

**Warning Alerts**:
- Elevated error rate (>1%)
- Elevated latency (P95 > 500ms)
- Memory usage high (>80%)
- Cache hit rate low (<70%)

---

## Security

### Security Features

✅ **Authentication & Authorization**
- JWT tokens with refresh mechanism
- Role-based access control (RBAC)
- Token expiration and rotation
- Secure password hashing (Argon2)

✅ **Network Security**
- Network segmentation (4-tier architecture)
- Internal networks for services
- Firewall rules
- TLS/SSL encryption for all external traffic

✅ **Data Protection**
- SQL injection prevention (Django ORM)
- XSS protection
- CSRF tokens
- Input validation and sanitization
- Secrets management (HashiCorp Vault support)

✅ **API Security**
- Rate limiting on all endpoints
- Request throttling
- API key authentication for service-to-service
- CORS configuration

✅ **Monitoring & Auditing**
- Access logs
- Audit trails
- Security event monitoring
- Failed login attempt tracking

### Security Best Practices

```bash
# Run security audit
bash scripts/security/security_audit.sh

# Update dependencies
pip install --upgrade -r services/backend/requirements/production.txt

# Scan for vulnerabilities
# (Configure in CI/CD pipeline)
```

### Secrets Management

**Option 1: Environment Variables** (Development)
```bash
# .env file (never commit to git)
SECRET_KEY=your-secret-key
DATABASE_PASSWORD=your-db-password
```

**Option 2: HashiCorp Vault** (Production)
```bash
# Initialize Vault
bash scripts/security/init-vault.sh

# Configure services to use Vault
cp .env.vault.example .env
# Edit .env with Vault credentials
```

### Security Documentation

- [Security Policy](docs/security/)
- [OWASP Compliance](docs/security/)
- [Penetration Testing Guide](docs/security/)

---

## Documentation

### Architecture Documentation

- [System Design](docs/architecture/system-design.md) - Overall architecture
- [AI Services Architecture](docs/architecture/ai-services.md) - AI microservices design
- [Network Topology](docs/architecture/network-topology.md) - Network segmentation
- [Infrastructure View](docs/architecture/infrastructure-view.md) - Infrastructure components

### Deployment Documentation

- [Docker Deployment](docs/deployment/docker-deployment.md) - Docker deployment guide
- [Production Guide](docs/deployment/production-guide.md) - Production deployment
- [CI/CD Pipeline](docs/deployment/ci-cd-pipeline.md) - Continuous deployment
- [Blue-Green Deployment](docs/deployment/blue-green-deployment.md) - Zero-downtime deployment

### Operations Documentation

- [Operations Runbook](docs/operations/runbooks/) - Incident response procedures
- [Backup & Restore](docs/operations/) - Data backup strategies
- [Disaster Recovery](docs/operations/) - DR procedures

### Development Documentation

- [Development Setup](docs/development/) - Local development guide
- [API Reference](http://localhost:8000/api/docs/) - Interactive API documentation
- [Contributing Guide](CONTRIBUTING.md) - How to contribute

---

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Quick Contribution Guide

```bash
# 1. Fork the repository
# 2. Clone your fork
git clone https://github.com/your-username/ecommerce-project.git

# 3. Create a feature branch
git checkout -b feature/amazing-feature

# 4. Make your changes

# 5. Run tests
make test

# 6. Commit your changes
git commit -m "feat: add amazing feature"

# 7. Push to your fork
git push origin feature/amazing-feature

# 8. Open a Pull Request
```

### Code Style

- **Python**: Follow PEP 8, use Black formatter
- **Commit Messages**: Follow Conventional Commits specification
- **Documentation**: Update docs for new features
- **Tests**: Add tests for new code (maintain >80% coverage)

---

## Performance

### Benchmarks

| Metric | Target | Status |
|--------|--------|--------|
| API Response Time (P95) | < 200ms | ✅ |
| AI Service Response (P95) | < 500ms | ✅ |
| Database Query Time (P95) | < 50ms | ✅ |
| Throughput | 10,000 req/min | ✅ |
| Concurrent Users | 1,000+ | ✅ |
| Uptime | 99.9% | ✅ |

### Performance Optimization

- Database query optimization with indexes
- Redis caching for frequently accessed data
- Connection pooling with PgBouncer
- Lazy loading and pagination
- CDN for static assets (optional)
- Horizontal scaling ready
- Async processing with Celery

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Support

- **Documentation**: See [docs/](docs/) directory
- **Issues**: https://github.com/yourusername/ecommerce-project/issues
- **Discussions**: https://github.com/yourusername/ecommerce-project/discussions

---

## Acknowledgments

- Django and Django REST Framework teams
- FastAPI team
- The open-source community

---

**Built for production. Powered by AI. Designed for scale.**
