# E-Commerce Platform - AI-Powered Monorepo

A production-grade, AI-powered e-commerce platform built with modern microservices architecture. This monorepo contains a Django REST Framework backend, 7 FastAPI AI microservices, and a Next.js frontend.

[![Backend Tests](https://github.com/your-org/ecommerce-platform/workflows/Backend%20Tests/badge.svg)](https://github.com/your-org/ecommerce-platform/actions)
[![AI Services Tests](https://github.com/your-org/ecommerce-platform/workflows/AI%20Services%20Tests/badge.svg)](https://github.com/your-org/ecommerce-platform/actions)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Node](https://img.shields.io/badge/node-18+-green.svg)](https://nodejs.org/)

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Services](#services)
- [Development](#development)
- [Testing](#testing)
- [Deployment](#deployment)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

This platform combines traditional e-commerce functionality with cutting-edge AI capabilities to provide:

- **Personalized Shopping Experience** - AI-powered product recommendations
- **Intelligent Search** - Semantic search with natural language understanding
- **Dynamic Pricing** - ML-based price optimization
- **Fraud Prevention** - Real-time transaction risk assessment
- **Smart Inventory** - Demand forecasting for optimal stock levels
- **Customer Support** - RAG-based chatbot for instant assistance
- **Visual Search** - Find products by image

### Technology Stack

| Component | Technologies |
|-----------|-------------|
| **Backend** | Python 3.11, Django 5.1, DRF, PostgreSQL, Redis, Celery, Elasticsearch |
| **AI Services** | Python 3.11, FastAPI, PyTorch, Scikit-learn, Transformers, SpaCy |
| **Frontend** | TypeScript, Next.js 14, React 18, Tailwind CSS, Zustand |
| **Infrastructure** | Docker, Docker Compose, Kubernetes, Nginx, Prometheus, Grafana |
| **Payments** | Stripe |
| **Storage** | AWS S3, Qdrant Vector DB |

---

## Features

### Core E-Commerce
- ✅ User authentication & authorization (JWT)
- ✅ Product catalog with categories & filtering
- ✅ Shopping cart & wishlist
- ✅ Order management & tracking
- ✅ Stripe payment integration
- ✅ Email notifications
- ✅ Admin dashboard
- ✅ Search & filtering
- ✅ Reviews & ratings

### AI-Powered Features
- 🤖 **Personalized Recommendations** - Hybrid collaborative and content-based filtering
- 🔍 **Semantic Search** - Natural language product search with embeddings
- 💰 **Dynamic Pricing** - ML-driven price optimization
- 🛡️ **Fraud Detection** - Real-time transaction risk scoring
- 📈 **Demand Forecasting** - Inventory optimization with time series models
- 💬 **AI Chatbot** - RAG-based customer support assistant
- 📸 **Visual Recognition** - Image-based product search and classification

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Load Balancer                           │
└────────────────────────────┬────────────────────────────────────┘
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                 │
           ▼                 ▼                 ▼
    ┌───────────┐     ┌───────────┐    ┌──────────────┐
    │  Frontend │     │  Backend  │    │ API Gateway  │
    │ (Next.js) │     │ (Django)  │    │  (FastAPI)   │
    └───────────┘     └─────┬─────┘    └──────┬───────┘
                            │                  │
                            │   ┌──────────────┘
                            │   │
                    ┌───────┴───┴────────┐
                    │   7 AI Services    │
                    │   - Recommender    │
                    │   - Search         │
                    │   - Pricing        │
                    │   - Fraud          │
                    │   - Forecasting    │
                    │   - Chatbot        │
                    │   - Vision         │
                    └─────────┬──────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
        ┌──────────┐    ┌─────────┐    ┌─────────┐
        │PostgreSQL│    │  Redis  │    │ Qdrant  │
        └──────────┘    └─────────┘    └─────────┘
```

For detailed architecture documentation, see [docs/architecture.md](docs/architecture.md).

---

## Quick Start

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- Python 3.11+
- Node.js 18+
- Make (optional but recommended)

### Installation (5 minutes)

```bash
# 1. Clone the repository
git clone https://github.com/your-org/ecommerce-platform.git
cd ecommerce-platform

# 2. Copy environment file
cp infrastructure/env/.env.example infrastructure/env/.env.development

# 3. Edit environment variables (add your API keys)
nano infrastructure/env/.env.development

# 4. Start all services
make install
make dev

# 5. Wait for services to be healthy
./scripts/health_check.py --wait

# 6. Create a superuser
make createsuperuser

# 7. (Optional) Load sample data
make seed
```

### Access the Platform

| Service | URL | Default Credentials |
|---------|-----|---------------------|
| Frontend | http://localhost:3000 | - |
| Backend API | http://localhost:8000/api/docs/ | - |
| Django Admin | http://localhost:8000/admin/ | (created in step 6) |
| API Gateway | http://localhost:8080/docs | - |
| Prometheus | http://localhost:9090 | - |
| Grafana | http://localhost:3001 | admin / admin |
| RabbitMQ Management | http://localhost:15672 | admin / admin |

---

## Project Structure

```
ecommerce-platform/
├── backend/                    # Django REST Framework backend
│   ├── apps/                  # Django applications
│   │   ├── accounts/          # User management
│   │   ├── products/          # Product catalog
│   │   ├── orders/            # Order processing
│   │   ├── payments/          # Stripe integration
│   │   ├── notifications/     # Notifications
│   │   └── analytics/         # Business analytics
│   ├── config/                # Django settings
│   ├── requirements/          # Python dependencies
│   └── tests/                 # Backend tests
│
├── ai-services/               # AI microservices
│   ├── services/
│   │   ├── recommendation_engine/
│   │   ├── search_engine/
│   │   ├── pricing_engine/
│   │   ├── chatbot_rag/
│   │   ├── fraud_detection/
│   │   ├── demand_forecasting/
│   │   └── visual_recognition/
│   ├── api_gateway/           # API Gateway
│   ├── shared/                # Shared utilities
│   └── models/                # Trained ML models
│
├── frontend/                  # Next.js frontend
│   ├── src/
│   │   ├── app/              # App router pages
│   │   ├── components/       # React components
│   │   ├── lib/              # API clients & utilities
│   │   └── types/            # TypeScript types
│   └── public/               # Static assets
│
├── infrastructure/            # Infrastructure as code
│   ├── docker-compose.yaml   # Main compose file
│   ├── docker-compose.dev.yaml
│   ├── docker-compose.prod.yaml
│   ├── k8s/                  # Kubernetes manifests
│   └── env/                  # Environment configs
│
├── docs/                      # Documentation
│   ├── architecture.md       # System architecture
│   ├── ai_services_overview.md
│   └── deployment_guide.md
│
├── scripts/                   # Utility scripts
│   ├── health_check.py       # Service health checker
│   ├── test_all.sh           # Run all tests
│   └── local_dev.sh          # Local dev setup
│
├── tests/                     # Integration tests
│   └── integration/
│
├── monitoring/                # Monitoring configs
│   ├── prometheus/
│   └── grafana/
│
├── Makefile                   # Development commands
└── README.md                  # This file
```

---

## Services

### Backend (Django) - Port 8000

The core e-commerce API built with Django REST Framework.

**Features:**
- User authentication (JWT)
- Product management (CRUD, categories, search)
- Order processing (cart, checkout, order tracking)
- Payment integration (Stripe webhooks)
- Admin dashboard
- API documentation (OpenAPI/Swagger)

**Tech Stack:** Django 5.1, DRF 3.15, PostgreSQL, Redis, Celery, Elasticsearch

[Backend Documentation](backend/README.md)

### AI Services

#### 1. Recommendation Engine - Port 8001
Generates personalized product recommendations using hybrid ML models.
- **Models:** Collaborative filtering, content-based, hybrid
- **Use Cases:** Homepage recommendations, cross-sell, upsell

#### 2. Search Engine - Port 8002
Provides semantic search with natural language understanding.
- **Models:** Sentence-BERT embeddings, BM25, vector similarity
- **Use Cases:** Product search, autocomplete, visual search

#### 3. Pricing Engine - Port 8003
Optimizes product prices dynamically based on demand and competition.
- **Models:** Reinforcement learning, XGBoost, price elasticity
- **Use Cases:** Dynamic pricing, flash sales, competitive positioning

#### 4. Chatbot (RAG) - Port 8004
AI-powered customer support chatbot with retrieval-augmented generation.
- **Models:** GPT-based LLM, sentence embeddings
- **Use Cases:** Customer support, product Q&A, order tracking

#### 5. Fraud Detection - Port 8005
Real-time transaction risk scoring and fraud prevention.
- **Models:** LightGBM, Isolation Forest, anomaly detection
- **Use Cases:** Payment fraud, account takeover, bot detection

#### 6. Demand Forecasting - Port 8006
Predicts product demand for inventory optimization.
- **Models:** Prophet, LSTM, SARIMA
- **Use Cases:** Inventory planning, purchase orders, warehouse allocation

#### 7. Visual Recognition - Port 8007
Computer vision for product classification and visual search.
- **Models:** ResNet50, YOLO, CNN embeddings
- **Use Cases:** Image search, auto-tagging, quality control

[AI Services Documentation](docs/ai_services_overview.md)

### Frontend (Next.js) - Port 3000

Modern, responsive web interface built with Next.js 14 and TypeScript.

**Features:**
- Server-side rendering (SSR) for SEO
- Client-side routing with App Router
- Responsive design (mobile-first)
- State management (Zustand, React Query)
- Form validation (Zod, React Hook Form)
- Real-time updates

**Tech Stack:** Next.js 14, React 18, TypeScript, Tailwind CSS, Axios

---

## Development

### Common Commands

```bash
# Start development environment
make dev

# View logs
make logs-f

# Run migrations
make migrate

# Create new migrations
make makemigrations

# Open Django shell
make shell

# Check service health
make health

# Run tests
make test

# Stop services
make stop

# Clean up everything
make clean
```

### Environment Setup

1. **Copy environment template:**
   ```bash
   cp infrastructure/env/.env.example infrastructure/env/.env.development
   ```

2. **Configure required variables:**
   ```env
   # Required for AI services
   OPENAI_API_KEY=sk-your-key-here

   # Required for payments
   STRIPE_SECRET_KEY=sk_test_your-key

   # Optional: AWS S3 for file storage
   AWS_ACCESS_KEY_ID=your-key
   AWS_SECRET_ACCESS_KEY=your-secret
   ```

3. **Start services:**
   ```bash
   make dev
   ```

### Development Workflow

1. **Make changes** to code (hot reload enabled)
2. **Run tests:** `make test`
3. **Check health:** `make health`
4. **View logs:** `make logs-f`
5. **Commit changes** and push

### Adding New Features

1. **Backend feature:**
   - Add to appropriate Django app in `backend/apps/`
   - Create migrations: `make makemigrations`
   - Apply migrations: `make migrate`
   - Add tests in `tests/`

2. **AI service feature:**
   - Add endpoint in service's `routers/` folder
   - Update model in `models/` if needed
   - Add tests in `tests/`
   - Update API Gateway routing

3. **Frontend feature:**
   - Add page in `frontend/src/app/`
   - Create components in `frontend/src/components/`
   - Add API client in `frontend/src/lib/api/`
   - Update types in `frontend/src/types/`

---

## Testing

### Run All Tests

```bash
make test
```

### Run Specific Test Suites

```bash
# Backend tests only
make test-backend

# AI services tests
make test-ai

# Frontend tests
make test-frontend

# Integration tests
make test-integration

# With coverage report
make test-coverage
```

### Manual Testing

```bash
# Backend API
curl http://localhost:8000/api/products/

# AI Service
curl http://localhost:8001/health

# Frontend
open http://localhost:3000
```

### Load Testing

```bash
# Install locust
pip install locust

# Run load tests
cd tests/load
locust -f locustfile.py
```

---

## Deployment

### Development

```bash
make dev
```

### Staging

```bash
# Build images
make build

# Start with production configs
docker-compose -f infrastructure/docker-compose.yaml \
               -f infrastructure/docker-compose.prod.yaml up -d
```

### Production

#### Docker (Single Server)

```bash
# 1. Clone repository on server
git clone <repository-url>
cd ecommerce-platform

# 2. Configure production environment
cp infrastructure/env/.env.example infrastructure/env/.env.production
nano infrastructure/env/.env.production

# 3. Build and start
make prod

# 4. Run migrations
make migrate

# 5. Collect static files
make collectstatic

# 6. Create superuser
make createsuperuser
```

#### Kubernetes

```bash
# 1. Create namespace
kubectl create namespace ecommerce-prod

# 2. Create secrets
kubectl create secret generic app-secrets \
  --from-env-file=infrastructure/env/.env.production \
  -n ecommerce-prod

# 3. Deploy
kubectl apply -f infrastructure/k8s/ -n ecommerce-prod

# 4. Verify
kubectl get pods -n ecommerce-prod
```

For detailed deployment instructions, see [docs/deployment_guide.md](docs/deployment_guide.md).

---

## Documentation

- **[Architecture Overview](docs/architecture.md)** - System architecture and design decisions
- **[AI Services Guide](docs/ai_services_overview.md)** - Detailed AI services documentation
- **[Deployment Guide](docs/deployment_guide.md)** - Step-by-step deployment instructions
- **[API Documentation](http://localhost:8000/api/docs/)** - Interactive API docs (when running)
- **[Contributing Guidelines](CONTRIBUTING.md)** - How to contribute to this project

---

## Performance

### Benchmarks

| Metric | Target | Status |
|--------|--------|--------|
| API Response Time (P95) | < 200ms | ✅ |
| AI Service Response (P95) | < 500ms | ✅ |
| Page Load Time | < 2s | ✅ |
| Throughput | 10K req/min | ✅ |
| Uptime | 99.9% | ✅ |

### Optimization

- Database query optimization with indexes
- Redis caching for frequently accessed data
- CDN for static assets
- Lazy loading for frontend
- Connection pooling
- Horizontal scaling ready

---

## Monitoring

### Prometheus Metrics

- Request rate, latency, error rate
- Resource utilization (CPU, memory, disk)
- Business metrics (orders, revenue, conversions)
- ML model performance

### Grafana Dashboards

- System overview
- Service health
- Database performance
- AI model metrics
- Business KPIs

Access Grafana at http://localhost:3001 (admin/admin)

---

## Security

### Best Practices

- ✅ JWT authentication with token refresh
- ✅ HTTPS enforced in production
- ✅ Secure password hashing (Argon2)
- ✅ SQL injection protection (ORM)
- ✅ XSS protection enabled
- ✅ CSRF tokens required
- ✅ Rate limiting on API endpoints
- ✅ Input validation and sanitization
- ✅ Secrets management (not in code)
- ✅ Regular dependency updates

### Security Audit

```bash
# Run security checks
make security-audit
```

---

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

### Quick Contribution Guide

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`make test`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Support

- **Documentation:** https://docs.yourdomain.com
- **Issues:** https://github.com/your-org/ecommerce-platform/issues
- **Discussions:** https://github.com/your-org/ecommerce-platform/discussions
- **Email:** support@yourdomain.com

---

## Acknowledgments

- Django REST Framework team
- FastAPI team
- Next.js team
- The open-source community

---

## Roadmap

- [ ] GraphQL API
- [ ] Mobile app (React Native)
- [ ] Multi-vendor marketplace
- [ ] Real-time notifications (WebSocket)
- [ ] Advanced analytics dashboard
- [ ] Multi-language support
- [ ] Multi-currency support
- [ ] Progressive Web App (PWA)

---

**Built with ❤️ by the E-Commerce Platform Team**
