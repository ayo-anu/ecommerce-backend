# Monorepo Structure and Boundaries

## Overview

This document defines the structure, boundaries, and conventions for the e-commerce platform monorepo. Following these guidelines ensures modularity, maintainability, and clear separation of concerns.

**Version**: 1.0
**Last Updated**: 2025-12-04

---

## Table of Contents

1. [Repository Structure](#repository-structure)
2. [Module Boundaries](#module-boundaries)
3. [Dependency Rules](#dependency-rules)
4. [File Organization](#file-organization)
5. [Naming Conventions](#naming-conventions)
6. [Import Guidelines](#import-guidelines)
7. [Enforcement](#enforcement)
8. [Migration Guide](#migration-guide)

---

## Repository Structure

```
ecommerce-project/
├── .github/                    # CI/CD workflows and GitHub configs
│   ├── workflows/
│   │   ├── ci.yml             # Main CI pipeline
│   │   ├── security-scan.yml  # Security scanning
│   │   ├── code-quality.yml   # Linting and type checking
│   │   └── docker-build-cache.yml
│   └── dependabot.yml
│
├── backend/                    # Django REST API
│   ├── apps/                  # Django applications
│   │   ├── accounts/          # User management
│   │   ├── products/          # Product catalog
│   │   ├── orders/            # Order management
│   │   ├── payments/          # Payment processing
│   │   ├── analytics/         # Analytics and reporting
│   │   ├── notifications/     # Notifications system
│   │   └── health/            # Health checks
│   ├── config/                # Django configuration
│   │   ├── settings/          # Environment-specific settings
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── development.py
│   │   │   ├── production.py
│   │   │   └── test.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── core/                  # Shared utilities
│   │   ├── middleware/
│   │   ├── service_tokens.py  # Service authentication
│   │   ├── jwks.py            # Key management
│   │   ├── celery_config.py   # Celery configuration
│   │   ├── database_routers.py
│   │   └── ...
│   ├── tests/                 # Backend tests
│   ├── requirements/          # Python dependencies
│   │   ├── base.txt
│   │   ├── dev.txt
│   │   └── prod.txt
│   ├── Dockerfile
│   └── manage.py
│
├── ai-services/               # AI microservices
│   ├── api_gateway/           # API Gateway
│   │   ├── main.py
│   │   ├── middleware.py
│   │   ├── waf.py             # Web Application Firewall
│   │   ├── rate_limiter.py
│   │   ├── circuit_breaker.py
│   │   └── Dockerfile
│   ├── services/              # Individual AI services
│   │   ├── recommendation_engine/
│   │   ├── search_engine/
│   │   ├── pricing_engine/
│   │   ├── chatbot_rag/
│   │   ├── fraud_detection/
│   │   ├── demand_forecasting/
│   │   └── visual_recognition/
│   ├── shared/                # Shared libraries
│   │   ├── health.py          # Health check utilities
│   │   ├── json_logger.py     # Structured logging
│   │   ├── exceptions.py      # Custom exceptions
│   │   ├── validation.py      # Input validation
│   │   ├── tracing.py         # Distributed tracing
│   │   └── config.py
│   ├── tests/                 # AI services tests
│   └── requirements.txt
│
├── infrastructure/            # Infrastructure as Code
│   ├── docker-compose.yaml    # Base compose file
│   ├── docker-compose.dev.yaml
│   ├── docker-compose.prod.yaml
│   ├── env/
│   │   ├── .env.example
│   │   ├── .env.development
│   │   └── .env.production
│   └── nginx/
│       └── nginx.conf
│
├── k8s/                       # Kubernetes manifests
│   ├── base/                  # Base configurations
│   ├── overlays/              # Environment-specific overlays
│   │   ├── dev/
│   │   ├── staging/
│   │   └── production/
│   └── helm/                  # Helm charts (if used)
│
├── terraform/                 # Terraform infrastructure
│   ├── modules/
│   ├── environments/
│   │   ├── dev/
│   │   ├── staging/
│   │   └── production/
│   └── main.tf
│
├── monitoring/                # Monitoring configurations
│   ├── prometheus/
│   │   ├── prometheus.yml
│   │   └── alerts/
│   ├── grafana/
│   │   ├── dashboards/
│   │   └── provisioning/
│   └── alertmanager/
│       └── alertmanager.yml
│
├── tests/                     # Integration & E2E tests
│   ├── integration/
│   │   ├── test_e2e_order_flow.py
│   │   ├── test_security_features.py
│   │   └── test_payment_security.py
│   └── load/
│       └── locustfile.py
│
├── scripts/                   # Utility scripts
│   ├── backup_databases.sh
│   ├── generate_service_keys.py
│   ├── health_check.py
│   └── setup_backup_cron.sh
│
├── docs/                      # Documentation
│   ├── COMPLETE_ARCHITECTURE.md
│   ├── DEPLOYMENT_RUNBOOK.md
│   ├── SECRETS_MANAGEMENT.md
│   ├── THREAT_MODEL.md
│   ├── PAYMENT_ISOLATION_AND_PCI_COMPLIANCE.md
│   └── MONOREPO_STRUCTURE.md (this file)
│
├── .gitignore
├── .dockerignore
├── .pre-commit-config.yaml
├── pyproject.toml             # Python project configuration
├── Makefile                   # Common development tasks
└── README.md
```

---

## Module Boundaries

### 1. Backend Boundaries

#### Django Apps Structure

Each Django app should be **self-contained** with clear responsibilities:

```
backend/apps/products/
├── __init__.py
├── models.py           # Database models
├── serializers.py      # API serializers
├── views.py            # API views/viewsets
├── urls.py             # URL routing
├── admin.py            # Admin interface
├── tasks.py            # Celery tasks (if needed)
├── services.py         # Business logic (optional)
├── tests.py            # Unit tests
└── migrations/
```

**Boundary Rules**:
- ✅ Apps can import from `core/` (shared utilities)
- ✅ Apps can import from other apps' models (via ForeignKey)
- ⚠️ Apps should minimize importing from other apps' views/serializers
- ❌ Apps should NOT have circular dependencies

**Example - Good**:
```python
# backend/apps/orders/models.py
from apps.products.models import Product  # ✅ OK - importing model
from apps.payments.models import Payment  # ✅ OK - importing model
```

**Example - Bad**:
```python
# backend/apps/orders/views.py
from apps.products.views import ProductViewSet  # ❌ BAD - coupling views
```

### 2. AI Services Boundaries

#### Service Independence

Each AI service should be **independently deployable**:

```
ai-services/services/recommendation_engine/
├── main.py             # FastAPI app entry point
├── models.py           # Pydantic models
├── recommender.py      # Core logic
├── config.py           # Service-specific config
├── Dockerfile          # Service-specific build
├── requirements.txt    # Service-specific deps
└── tests/
```

**Boundary Rules**:
- ✅ Services can import from `services/ai/shared/`
- ✅ Services communicate via HTTP/REST (not direct imports)
- ❌ Services should NOT import from each other
- ❌ Services should NOT share database connections

**Example - Good**:
```python
# ai-services/services/recommendation_engine/main.py
from shared.health import create_health_router  # ✅ OK - shared utility
from shared.json_logger import setup_json_logging  # ✅ OK
```

**Example - Bad**:
```python
# ai-services/services/recommendation_engine/recommender.py
from services.search_engine.searcher import search  # ❌ BAD - tight coupling
```

### 3. Frontend Boundaries (Future)

When frontend is implemented:

```
frontend/src/
├── app/                # Next.js app directory
├── components/         # Reusable UI components
├── lib/               # Utilities
│   ├── api/           # API clients
│   └── hooks/         # React hooks
├── store/             # State management
└── types/             # TypeScript types
```

**Boundary Rules**:
- ✅ Components can use shared hooks
- ✅ Pages can import components
- ❌ Components should NOT directly call API (use hooks)

---

## Dependency Rules

### Layer Architecture

```
┌─────────────────────────────────────────┐
│          Presentation Layer             │  (Views, API endpoints)
│  backend/apps/*/views.py                │
│  ai-services/services/*/main.py         │
└──────────────┬──────────────────────────┘
               │ calls
               ▼
┌─────────────────────────────────────────┐
│          Business Logic Layer           │  (Services, business rules)
│  backend/apps/*/services.py             │
│  ai-services/services/*/recommender.py  │
└──────────────┬──────────────────────────┘
               │ uses
               ▼
┌─────────────────────────────────────────┐
│          Data Access Layer              │  (Models, repositories)
│  backend/apps/*/models.py               │
│  ai-services/services/*/database.py     │
└──────────────┬──────────────────────────┘
               │ accesses
               ▼
┌─────────────────────────────────────────┐
│          Infrastructure Layer           │  (Database, external services)
│  PostgreSQL, Redis, Elasticsearch       │
└─────────────────────────────────────────┘
```

**Rules**:
1. Upper layers can depend on lower layers
2. Lower layers should NOT depend on upper layers
3. Each layer should be replaceable

### Allowed Dependencies

| From | To | Allowed? | Notes |
|------|-----|----------|-------|
| Backend app → Backend app | Models only | ⚠️ Limited | Prefer loose coupling |
| Backend app → `core/` | Any | ✅ Yes | Shared utilities |
| Backend app → AI service | API only | ✅ Yes | Via HTTP |
| AI service → AI service | API only | ✅ Yes | Via API Gateway |
| AI service → `shared/` | Any | ✅ Yes | Shared libraries |
| AI service → Backend | API only | ✅ Yes | Via REST API |
| `core/` → Backend app | None | ❌ No | Circular dependency |
| `shared/` → AI service | None | ❌ No | Circular dependency |

---

## File Organization

### Configuration Files

**Root Level** (monorepo-wide):
- `.gitignore` - Git ignore patterns
- `.dockerignore` - Docker ignore patterns
- `pyproject.toml` - Python project config (Black, isort, mypy)
- `.pre-commit-config.yaml` - Pre-commit hooks
- `Makefile` - Development commands

**Backend**:
- `services/backend/requirements/` - Dependency management
- `services/backend/config/settings/` - Django settings

**AI Services**:
- `services/ai/requirements.txt` - Shared dependencies
- `services/ai/services/*/requirements.txt` - Service-specific deps

### Environment Files

```
infrastructure/env/
├── .env.example          # Template with all variables
├── .env.development      # Development defaults
└── .env.production       # Production (secrets injected)
```

**Never commit**:
- `.env.local`
- `.env.production` (with real secrets)

### Test Organization

```
tests/
├── integration/          # Cross-service tests
│   ├── conftest.py      # Shared fixtures
│   ├── test_e2e_order_flow.py
│   └── test_security_features.py
├── load/                # Performance tests
│   └── locustfile.py
└── requirements.txt     # Test dependencies

backend/tests/           # Backend unit tests
backend/apps/*/tests.py  # App-specific tests

ai-services/tests/       # AI service tests
ai-services/services/*/tests/
```

---

## Naming Conventions

### Files and Directories

| Type | Convention | Example |
|------|-----------|---------|
| Python modules | `snake_case.py` | `service_tokens.py` |
| Python packages | `snake_case/` | `api_gateway/` |
| Django apps | `snake_case` | `products`, `payments` |
| Test files | `test_*.py` | `test_authentication.py` |
| Config files | `lowercase.yaml` | `docker-compose.yaml` |
| Documentation | `UPPERCASE.md` | `README.md` |

### Code Elements

| Type | Convention | Example |
|------|-----------|---------|
| Classes | `PascalCase` | `ProductViewSet` |
| Functions | `snake_case` | `create_payment_intent()` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_RETRY_ATTEMPTS` |
| Environment vars | `UPPER_SNAKE_CASE` | `DATABASE_URL` |
| API endpoints | `kebab-case` | `/api/v1/payment-intents/` |

### Git Branches

```
main              # Production-ready code
develop           # Development integration branch
feature/*         # New features: feature/user-authentication
bugfix/*          # Bug fixes: bugfix/payment-error
hotfix/*          # Production hotfixes: hotfix/critical-security
release/*         # Release preparation: release/v1.2.0
```

---

## Import Guidelines

### Python Import Order

Follow PEP 8 with isort configuration:

```python
# 1. Standard library
import os
import sys
from typing import List, Dict

# 2. Third-party libraries
import django
from rest_framework import viewsets
from fastapi import FastAPI

# 3. Local application imports
from apps.products.models import Product
from core.service_tokens import ServiceTokenManager

# 4. Relative imports (avoid if possible)
from .models import Order
```

**isort configuration** (in `pyproject.toml`):
```toml
[tool.isort]
profile = "black"
line_length = 100
known_first_party = ["apps", "core", "config"]
sections = ["FUTURE", "STDLIB", "THIRDPARTY", "FIRSTPARTY", "LOCALFOLDER"]
```

### Absolute vs Relative Imports

**Preferred**: Absolute imports
```python
from apps.products.models import Product  # ✅ Clear and explicit
```

**Avoid**: Relative imports across apps
```python
from ..products.models import Product  # ❌ Confusing
```

**Acceptable**: Relative imports within same app
```python
from .models import Order  # ✅ OK within same Django app
```

---

## Enforcement

### 1. Automated Tools

#### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: check-imports
        name: Check import boundaries
        entry: python scripts/check_import_boundaries.py
        language: system
        pass_filenames: false
```

#### Import Linter

```toml
# pyproject.toml
[tool.importlinter]
root_package = "backend"

[[tool.importlinter.contracts]]
name = "Apps should not import from each other's views"
type = "forbidden"
source_modules = ["apps.*"]
forbidden_modules = ["apps.*.views"]
```

### 2. Code Review Checklist

During PR review, verify:
- [ ] No circular dependencies introduced
- [ ] Imports follow layer architecture
- [ ] New files follow naming conventions
- [ ] Tests are in correct location
- [ ] No hardcoded secrets or credentials
- [ ] Documentation updated if structure changed

### 3. CI Checks

```yaml
# .github/workflows/code-quality.yml
- name: Check import boundaries
  run: |
    python scripts/check_import_boundaries.py

- name: Verify folder structure
  run: |
    python scripts/verify_structure.py
```

---

## Migration Guide

### Moving to Stricter Boundaries

If refactoring existing code:

1. **Identify Violations**
   ```bash
   # Find cross-app view imports
   grep -r "from apps\\..*\\.views import" backend/apps/
   ```

2. **Create Service Layer**
   ```python
   # backend/apps/products/services.py
   class ProductService:
       @staticmethod
       def get_product_by_id(product_id):
           return Product.objects.get(id=product_id)

   # Other apps can now import this service
   from apps.products.services import ProductService
   ```

3. **Update Imports Gradually**
   - Create service layer first
   - Update one app at a time
   - Run tests after each change

4. **Enforce in CI**
   - Add import linter rules
   - Enable in CI after cleanup

---

## Best Practices

### 1. Keep Services Small

Each AI service should do **one thing well**:
- ✅ `recommendation_engine` - Product recommendations
- ✅ `search_engine` - Product search
- ❌ `recommendation_and_search` - Too broad

### 2. Use Dependency Injection

```python
# Good - injectable dependency
class OrderService:
    def __init__(self, payment_service):
        self.payment_service = payment_service

    def create_order(self, cart):
        # ...
        self.payment_service.process_payment(amount)

# Usage
payment_service = PaymentService()
order_service = OrderService(payment_service)
```

### 3. API Contracts

Define clear contracts between services:

```python
# ai-services/services/recommendation_engine/models.py
from pydantic import BaseModel

class RecommendationRequest(BaseModel):
    user_id: str
    limit: int = 10

class RecommendationResponse(BaseModel):
    user_id: str
    recommendations: List[Product]
```

### 4. Shared Code

Put truly shared code in:
- `services/backend/core/` - Backend utilities
- `services/ai/shared/` - AI service utilities

Avoid:
- Copying code between services
- Circular dependencies in shared code

---

## Troubleshooting

### Circular Import Error

**Problem**: `ImportError: cannot import name 'X' from 'Y'`

**Solutions**:
1. Move import inside function (lazy import)
2. Use dependency injection
3. Restructure to remove circular dependency

### Import Not Found

**Problem**: `ModuleNotFoundError: No module named 'apps'`

**Solutions**:
1. Check `PYTHONPATH` includes project root
2. Use absolute imports from project root
3. Check `__init__.py` files exist

---

## References

- [Django Best Practices](https://docs.djangoproject.com/en/stable/misc/design-philosophies/)
- [Monorepo Tools](https://monorepo.tools/)
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Python Import System](https://docs.python.org/3/reference/import.html)

---

**Maintained By**: Engineering Team
**Review Schedule**: Quarterly
**Last Review**: 2025-12-04
