# Infrastructure Configuration

This directory contains the Docker Compose configurations for the E-Commerce platform.

## Overview

**Single Source of Truth:** All Docker Compose configurations are centralized here to prevent configuration drift and maintain consistency across environments.

## Files

### Core Configuration Files

| File | Purpose | Usage |
|------|---------|-------|
| `docker-compose.yaml` | **BASE** configuration with all services | Always required |
| `docker-compose.dev.yaml` | Development overrides (port exposures, hot-reload, dev tools) | Development only |
| `docker-compose.prod.yaml` | Production overrides (security hardening, resource limits) | Production only |
| `docker-compose.network-policy.yaml` | Advanced network security policies | Optional |
| `docker-compose.base.yaml` | Legacy base file | Consider for removal |

### Development Tools (included in dev.yaml)

The development configuration includes additional tools for easier debugging:

- **Mailhog** (ports 1025, 8025) - Email testing and capture
- **pgAdmin** (port 5050) - PostgreSQL database management UI
- **Redis Commander** (port 8081) - Redis data browser and management

## Usage

### Development Environment

```bash
# Using Makefile (recommended)
make up

# Or using docker-compose directly
docker-compose -f infrastructure/docker-compose.yaml \
               -f infrastructure/docker-compose.dev.yaml up -d
```

### Production Environment

```bash
docker-compose -f infrastructure/docker-compose.yaml \
               -f infrastructure/docker-compose.prod.yaml up -d
```

### Specific Services Only

```bash
# Start only databases
docker-compose -f infrastructure/docker-compose.yaml \
               -f infrastructure/docker-compose.dev.yaml \
               up -d postgres redis elasticsearch

# Start backend services
docker-compose -f infrastructure/docker-compose.yaml \
               -f infrastructure/docker-compose.dev.yaml \
               up -d backend celery-worker celery-beat
```

## Architecture

### Network Segmentation

The platform uses a **4-network architecture** for security and isolation:

#### Development
```
public_network       → Nginx ↔ API Gateway (external traffic)
backend_network      → API Gateway ↔ Backend + Databases
ai_network           → API Gateway ↔ AI Services
monitoring_network   → Prometheus ↔ All Services
```

#### Production
```
public_network       → Nginx ONLY (ports 80/443 exposed)
backend_network      → INTERNAL (no external access)
ai_network           → INTERNAL (no external access)
monitoring_network   → INTERNAL (metrics collection only)
```

### Service Categories

#### Infrastructure (15+ services)
- **Databases:** postgres, postgres_ai, redis, elasticsearch, qdrant
- **Queue:** rabbitmq
- **Connection Pooling:** pgbouncer
- **Monitoring:** prometheus, grafana, jaeger

#### Application (10+ services)
- **Backend:** backend, celery-worker, celery-beat
- **Gateway:** api_gateway (FastAPI reverse proxy)
- **AI Services:** recommender, search, pricing, chatbot, fraud, forecasting, vision

#### Development Only
- **Email Testing:** mailhog
- **Database UI:** pgadmin
- **Cache UI:** redis-commander

## Environment Variables

Environment variables are loaded from:
1. `infrastructure/env/.env.development` (development)
2. `infrastructure/env/.env.production` (production)
3. `.env` (root, if present - legacy)

Set the environment file in your Makefile or docker-compose command:
```bash
ENV_FILE=infrastructure/env/.env.production docker-compose -f infrastructure/docker-compose.yaml -f infrastructure/docker-compose.prod.yaml up -d
```

## Port Mappings (Development)

### Infrastructure Services
| Service | Port(s) | Purpose |
|---------|---------|---------|
| postgres | 5432 | Main database |
| postgres_ai | 5433 | AI services database |
| redis | 6379 | Cache & queues |
| rabbitmq | 5672, 15672 | Message queue + management UI |
| elasticsearch | 9200, 9300 | Search engine |
| qdrant | 6333, 6334 | Vector database |

### Application Services
| Service | Port | Purpose |
|---------|------|---------|
| backend | 8000 | Django REST API |
| api_gateway | 8080 | AI services gateway |
| recommender | 8001 | Recommendation engine |
| search | 8002 | Semantic search |
| pricing | 8003 | Dynamic pricing |
| chatbot | 8004 | RAG chatbot |
| fraud | 8005 | Fraud detection |
| forecasting | 8006 | Demand forecasting |
| vision | 8007 | Visual recognition |

### Monitoring & Dev Tools
| Service | Port | Purpose |
|---------|------|---------|
| prometheus | 9090 | Metrics collection |
| grafana | 3001 | Metrics visualization |
| jaeger | 16686 | Distributed tracing UI |
| mailhog | 1025, 8025 | Email testing |
| pgadmin | 5050 | Database management |
| redis-commander | 8081 | Redis browser |

**Note:** In production, ONLY Nginx exposes ports 80 and 443. All other services are internal-only.

## Volumes

Persistent data is stored in named Docker volumes:

- `postgres_data` - Main PostgreSQL database
- `postgres_ai_data` - AI services PostgreSQL database
- `redis_data` - Redis persistence
- `elasticsearch_data` - Elasticsearch indices
- `qdrant_data` - Vector embeddings
- `rabbitmq_data` - Message queue state
- `prometheus_data` - Metrics history
- `grafana_data` - Dashboards and settings
- `backend_media` - User uploads
- `backend_static` - Static files (CSS, JS, images)
- `pgadmin_data` - pgAdmin settings (dev only)

## Common Tasks

### View All Services
```bash
docker-compose -f infrastructure/docker-compose.yaml \
               -f infrastructure/docker-compose.dev.yaml config --services
```

### Check Service Health
```bash
docker-compose -f infrastructure/docker-compose.yaml \
               -f infrastructure/docker-compose.dev.yaml ps
```

### View Logs
```bash
# All services
make logs

# Specific service
docker-compose -f infrastructure/docker-compose.yaml \
               -f infrastructure/docker-compose.dev.yaml logs -f backend
```

### Run Migrations
```bash
make migrate

# Or directly
docker-compose -f infrastructure/docker-compose.yaml \
               -f infrastructure/docker-compose.dev.yaml \
               exec backend python manage.py migrate
```

### Access Service Shells
```bash
# Django shell
docker-compose -f infrastructure/docker-compose.yaml \
               -f infrastructure/docker-compose.dev.yaml \
               exec backend python manage.py shell

# PostgreSQL shell
docker-compose -f infrastructure/docker-compose.yaml \
               -f infrastructure/docker-compose.dev.yaml \
               exec postgres psql -U postgres -d ecommerce

# Redis CLI
docker-compose -f infrastructure/docker-compose.yaml \
               -f infrastructure/docker-compose.dev.yaml \
               exec redis redis-cli
```

## Troubleshooting

### Services Not Starting

1. Check if ports are already in use:
   ```bash
   netstat -tuln | grep -E '(5432|6379|8000|8080)'
   ```

2. View service logs:
   ```bash
   docker-compose -f infrastructure/docker-compose.yaml \
                  -f infrastructure/docker-compose.dev.yaml logs <service-name>
   ```

3. Verify environment variables are set:
   ```bash
   docker-compose -f infrastructure/docker-compose.yaml \
                  -f infrastructure/docker-compose.dev.yaml config
   ```

### Network Issues

If services cannot communicate:

1. Check network creation:
   ```bash
   docker network ls | grep ecommerce
   ```

2. Inspect network:
   ```bash
   docker network inspect ecommerce-backend_network
   ```

3. Verify service is on correct network:
   ```bash
   docker inspect <container-name> | grep -A 20 Networks
   ```

### Database Connection Issues

1. Ensure postgres is healthy:
   ```bash
   docker-compose -f infrastructure/docker-compose.yaml \
                  -f infrastructure/docker-compose.dev.yaml ps postgres
   ```

2. Test database connection:
   ```bash
   docker-compose -f infrastructure/docker-compose.yaml \
                  -f infrastructure/docker-compose.dev.yaml \
                  exec postgres pg_isready -U postgres
   ```

## Security Considerations

### Development
- All ports exposed for debugging
- Password authentication disabled for postgres (`POSTGRES_HOST_AUTH_METHOD=trust`)
- Networks not isolated (internal: false)
- Debug mode enabled

### Production
- **Only Nginx exposes ports** (80, 443)
- All internal networks isolated (`internal: true`)
- Strong passwords required (set via environment variables)
- Debug mode disabled
- HTTPS required (SSL/TLS certificates)
- Security headers enabled

## Migration from Root docker-compose.yml

**Previous Setup:**
- Root `docker-compose.yml` with 2-network architecture
- Root `docker-compose.override.yml` with conflicting network references

**Current Setup (Consolidated):**
- All configurations in `infrastructure/` directory
- 4-network architecture for better segmentation
- Properly separated dev/prod configurations
- Additional monitoring and development tools

**Benefits:**
- ✅ Single source of truth
- ✅ No configuration drift
- ✅ Clear dev/prod separation
- ✅ Better security (network isolation)
- ✅ More complete feature set (monitoring, Nginx, etc.)
- ✅ Proper development tools (mailhog, pgadmin, redis-commander)

## Further Documentation

- **Deployment Guide:** See `../docs/deployment_guide.md`
- **Security Audit:** See `../docs/SECURITY_AUDIT_FINDINGS.md`
- **Docker Optimization:** See `../docs/DOCKER_OPTIMIZATION.md`
- **Network Policies:** See `docker-compose.network-policy.yaml`
