# Network Topology - 3-Tier Architecture

## Overview

The production deployment uses a **4-network architecture** for enhanced security through network segmentation. This prevents unauthorized access between service tiers and limits the attack surface.

## Network Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL NETWORK                             │
│                    (Public Internet Access)                          │
└─────────────────────────┬───────────────────────────────────────────┘
                          │ Ports: 80, 443 (HTTPS)
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      FRONTEND NETWORK                                │
│                      (172.20.0.0/24)                                 │
│                    Internal: false                                   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                         NGINX                                │   │
│  │  - Reverse Proxy                                             │   │
│  │  - TLS 1.3 Termination                                       │   │
│  │  - Rate Limiting                                             │   │
│  │  - Security Headers                                          │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────┬───────────────────────────────────────────┘
                          │ Internal only
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     APPLICATION NETWORK                              │
│                      (172.21.0.0/24)                                 │
│                    Internal: true (No external access)               │
│                                                                       │
│  ┌────────────────┐    ┌──────────────────────────────────────┐    │
│  │  API Gateway   │◄───┤   AI Microservices (7 services)      │    │
│  │                │    │  - Recommender    - Fraud Detection  │    │
│  └───────┬────────┘    │  - Search         - Forecasting      │    │
│          │             │  - Pricing        - Vision            │    │
│          ▼             │  - Chatbot (RAG)                      │    │
│  ┌────────────────┐    └──────────────────────────────────────┘    │
│  │ Django Backend │                                                  │
│  │ + Celery       │                                                  │
│  └───────┬────────┘                                                  │
└──────────┼──────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      DATABASE NETWORK                                │
│                      (172.22.0.0/24)                                 │
│                    Internal: true (No external access)               │
│                                                                       │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────┐                 │
│  │ PostgreSQL  │  │ PostgreSQL   │  │   Redis    │                 │
│  │  (Main DB)  │  │   (AI DB)    │  │  (Cache)   │                 │
│  └─────────────┘  └──────────────┘  └────────────┘                 │
│                                                                       │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────┐                 │
│  │Elasticsearch│  │   Qdrant     │  │ RabbitMQ   │                 │
│  │  (Search)   │  │  (Vectors)   │  │  (Queue)   │                 │
│  └─────────────┘  └──────────────┘  └────────────┘                 │
│                                                                       │
│  ┌─────────────┐                                                     │
│  │  PgBouncer  │  (Connection Pooler - bridges app & db)            │
│  └─────────────┘                                                     │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                     MONITORING NETWORK                               │
│                      (172.23.0.0/24)                                 │
│                    Internal: true (No external access)               │
│                  Cross-cutting: All services expose metrics          │
│                                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │  Prometheus  │◄─┤   Grafana    │  │    Jaeger    │              │
│  │   (Metrics)  │  │ (Dashboards) │  │   (Traces)   │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
```

## Network Details

### 1. Frontend Network (172.20.0.0/24)

**Purpose:** Public-facing traffic handling
**Internal:** `false` (connected to external)
**Services:**
- Nginx (reverse proxy)

**Security:**
- Only nginx can access this network
- Nginx bridges frontend and application networks
- All TLS termination happens here
- Rate limiting enforced

**Traffic Flow:**
```
Internet → Nginx (80/443) → API Gateway (internal)
```

---

### 2. Application Network (172.21.0.0/24)

**Purpose:** Application logic tier
**Internal:** `true` (no external access)
**Services:**
- API Gateway (orchestration layer)
- Django Backend (main application)
- Celery Worker & Beat (async tasks)
- All AI Microservices (7 services)

**Security:**
- No direct external access
- Only nginx can route traffic here
- Services communicate via internal DNS
- All HTTP traffic is internal (no TLS overhead)

**Communication Patterns:**
```
Nginx → API Gateway → {Backend, AI Services}
Backend → Database Network (via PgBouncer)
AI Services → Database Network (Qdrant, Redis)
```

---

### 3. Database Network (172.22.0.0/24)

**Purpose:** Data persistence tier
**Internal:** `true` (no external access)
**Services:**
- PostgreSQL (main database)
- PostgreSQL AI (AI services database)
- Redis (cache & session store)
- Elasticsearch (full-text search)
- Qdrant (vector database for AI)
- RabbitMQ (message queue)
- PgBouncer (connection pooler)

**Security:**
- Completely isolated from external
- Only application tier can access
- Database credentials never leave this network
- PgBouncer acts as security boundary

**Access Control:**
```
Backend → PgBouncer → PostgreSQL
AI Services → PostgreSQL AI (direct)
All Services → Redis, RabbitMQ (shared resources)
```

---

### 4. Monitoring Network (172.23.0.0/24)

**Purpose:** Observability & metrics collection
**Internal:** `true` (no external access)
**Services:**
- Prometheus (metrics collection)
- Grafana (visualization)
- Jaeger (distributed tracing)

**Cross-Cutting Concern:**
All services join this network to expose metrics:
```
Service → /metrics endpoint → Prometheus
Service → traces → Jaeger
```

**Security:**
- Read-only access to service metrics
- No write access to application data
- Isolated from production traffic

---

## Service Network Mapping

| Service | Frontend | Application | Database | Monitoring |
|---------|----------|-------------|----------|------------|
| **Nginx** | ✅ | ✅ | ❌ | ✅ |
| **API Gateway** | ❌ | ✅ | ✅ | ✅ |
| **Backend** | ❌ | ✅ | ✅ | ✅ |
| **Celery Worker** | ❌ | ✅ | ✅ | ✅ |
| **Celery Beat** | ❌ | ✅ | ✅ | ✅ |
| **AI Services (7)** | ❌ | ✅ | ✅ | ✅ |
| **PostgreSQL** | ❌ | ❌ | ✅ | ✅ |
| **PostgreSQL AI** | ❌ | ❌ | ✅ | ✅ |
| **PgBouncer** | ❌ | ✅ | ✅ | ✅ |
| **Redis** | ❌ | ✅ | ✅ | ✅ |
| **Elasticsearch** | ❌ | ✅ | ✅ | ✅ |
| **Qdrant** | ❌ | ✅ | ✅ | ✅ |
| **RabbitMQ** | ❌ | ✅ | ✅ | ✅ |
| **Prometheus** | ❌ | ❌ | ❌ | ✅ |
| **Grafana** | ❌ | ❌ | ❌ | ✅ |
| **Jaeger** | ❌ | ❌ | ❌ | ✅ |

---

## Security Benefits

### 1. Attack Surface Reduction
- ✅ Only nginx exposed to internet
- ✅ Database tier completely isolated
- ✅ No direct database access from external

### 2. Lateral Movement Prevention
- ✅ Compromised application can't directly access databases
- ✅ Monitoring services isolated from production data
- ✅ Each tier has minimal necessary access

### 3. Defense in Depth
```
Layer 1: External Firewall (host level)
Layer 2: Nginx (TLS, rate limiting, WAF)
Layer 3: Network Segmentation (Docker networks)
Layer 4: Application Authentication
Layer 5: Database Authorization
```

### 4. Compliance
- ✅ PCI-DSS: Database isolation
- ✅ GDPR: Data access controls
- ✅ SOC 2: Network segmentation
- ✅ HIPAA: Access logging & monitoring

---

## Network Testing

### Verify Isolation

**Test 1: Database is NOT accessible externally**
```bash
# Should timeout (no route)
docker run --rm appropriate/curl curl -m 5 http://postgres:5432
```

**Test 2: Backend is NOT accessible externally**
```bash
# Should timeout (no route)
docker run --rm appropriate/curl curl -m 5 http://backend:8000
```

**Test 3: Nginx CAN access API Gateway**
```bash
docker exec nginx curl -f http://api_gateway:8080/health
# Should return: 200 OK
```

**Test 4: Backend CAN access PostgreSQL**
```bash
docker exec backend pg_isready -h postgres -p 5432
# Should return: accepting connections
```

**Test 5: Monitoring CAN scrape metrics**
```bash
docker exec prometheus curl -f http://backend:8000/metrics
# Should return: metrics data
```

### Network Introspection

```bash
# List all networks
docker network ls | grep ecommerce

# Inspect specific network
docker network inspect ecommerce-production_application

# Check which containers are on a network
docker network inspect ecommerce-production_database \
  --format '{{range .Containers}}{{.Name}} {{end}}'
```

---

## Troubleshooting

### Service Can't Connect to Database

**Symptom:** Connection refused or timeout

**Check:**
1. Verify both services are on the same network:
   ```bash
   docker inspect <service> | grep -A 10 Networks
   ```

2. Check network configuration in docker-compose:
   ```yaml
   services:
     backend:
       networks:
         - database  # Must be present
   ```

3. Verify DNS resolution:
   ```bash
   docker exec backend nslookup postgres
   ```

### Monitoring Not Collecting Metrics

**Symptom:** Prometheus shows targets as down

**Check:**
1. Service is on monitoring network
2. Service exposes /metrics endpoint
3. Port is correct (8000 for Django, 8080 for FastAPI)

### Nginx Can't Reach Backend Services

**Symptom:** 502 Bad Gateway

**Check:**
1. Nginx is on both `frontend` and `application` networks
2. Services are running (`docker ps`)
3. Check nginx error logs:
   ```bash
   docker logs nginx 2>&1 | tail -20
   ```

---

## Performance Considerations

### Network Overhead

**Bridge Networks:** ~0.1-0.5ms latency
**Impact:** Negligible for most applications
**Benefit:** Outweighs security gains

### Connection Pooling

**PgBouncer** reduces connection overhead:
- Without: Each request = new DB connection
- With: Connections reused from pool
- Latency savings: ~10-50ms per request

### DNS Caching

Docker's embedded DNS caches service IPs:
- First lookup: ~1-2ms
- Cached: <0.1ms
- TTL: 600 seconds

---

## Migration Path

### From Development to Production

1. **Development:** All services on default bridge
2. **Staging:** 2-tier (frontend + backend)
3. **Production:** 4-tier (this architecture)

### Gradual Rollout

Week 1: Add networks, keep ports exposed
Week 2: Remove port exposure for backend
Week 3: Enforce network policies
Week 4: Full production deployment

---

## Related Documentation

- [Production Deployment Guide](../deployment/production-guide.md)
- [Security Best Practices](../security/best-practices.md)
- [Monitoring Setup](../monitoring/prometheus-setup.md)

---

**Document Version:** 1.0
**Last Updated:** 2025-12-18
**Status:** Production Ready
**Owner:** Platform Engineering Team
