# 4. Docker Compose for Local Development

Date: 2025-12-04

## Status

Accepted

## Context

Developers need a consistent local development environment that:
- Matches production as closely as possible
- Is easy to set up (minimal "works on my machine" issues)
- Supports hot-reloading for rapid development
- Includes all dependencies (databases, caches, queues)

Options:
1. Native installation (Python, PostgreSQL, Redis, etc. on host)
2. Virtual machines (Vagrant, VMware)
3. Docker Compose
4. Kubernetes (minikube, kind)

## Decision

Use **Docker Compose** for local development environment.

### Configuration

```yaml
# docker-compose.yaml
services:
  backend:
    build: backend/
    volumes:
      - ./backend:/app  # Hot reload
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy

  postgres:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine

  # ... other services
```

## Consequences

### Positive

- **Consistency**: Same Docker images used in development and production
- **Easy Setup**: `docker-compose up` gets full environment running
- **Isolation**: Services don't pollute host system
- **Version Control**: Infrastructure defined in code
- **Parity**: 85%+ dev/prod parity (documented in `ENVIRONMENT_PARITY.md`)
- **Hot Reload**: Volume mounts enable rapid development
- **Multi-Service**: All microservices run locally
- **CI/CD Alignment**: Same Docker images tested in CI

### Negative

- **Resource Usage**: Docker containers use more RAM than native
- **Performance**: Slight overhead vs native (especially on Mac/Windows)
- **Learning Curve**: Team needs to learn Docker basics
- **Debugging**: Slightly more complex than native (but still manageable)

### Neutral

- **Storage**: Docker images and volumes consume disk space
- **Network**: Need to understand Docker networking

## Implementation

### Development Workflow

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Run migrations
docker-compose exec backend python manage.py migrate

# Run tests
docker-compose exec backend pytest

# Stop all services
docker-compose down
```

### Hot Reload Configuration

```dockerfile
# Development Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements/ requirements/
RUN pip install -r requirements/dev.txt

# Don't copy code - use volume mount instead
# This enables hot reload

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

### Multi-Stage Builds

- Development: Uses volume mounts for hot reload
- Production: Copies code into image (immutable)

## Design Decisions

### Why Docker Compose vs Native Installation?

**Docker Compose chosen** because:
- Consistent across team (Linux, Mac, Windows)
- Easy to onboard new developers
- Matches production environment
- Can test full stack locally

**Native installation rejected** because:
- "Works on my machine" problems
- Version conflicts (Python, PostgreSQL, etc.)
- Difficult to keep in sync
- Can't easily test multi-service interactions

### Why Docker Compose vs Kubernetes?

**Docker Compose chosen for development** because:
- Simpler for local development
- Faster startup than Kubernetes
- Easier to debug
- Don't need K8s features locally (auto-scaling, etc.)

**Kubernetes used for staging/production** because:
- Production requirements (HA, scaling, etc.)
- Can still test K8s manifests in CI

## Alternatives Considered

### Vagrant/VirtualBox

**Rejected** because:
- Heavier than Docker
- Slower startup
- More resource intensive
- Docker is industry standard

### minikube/kind (Kubernetes Locally)

**Rejected for development** because:
- Overkill for local dev
- Slower iteration cycle
- More complex debugging
- Higher resource usage

**Still used in CI** for testing K8s manifests

### Native Installation

**Rejected** because:
- Inconsistent across developers
- Difficult to onboard
- Version conflicts
- Can't easily test full stack

## Trade-offs Accepted

1. **Performance**: Accept slight performance overhead for consistency
2. **Resources**: Accept higher RAM usage for isolation
3. **Complexity**: Accept Docker learning curve for long-term benefits

## Migration Path

Existing developers:

1. Install Docker Desktop
2. Clone repository
3. Run `docker-compose up`
4. Access services at documented ports

No migration needed for CI/CD (already using Docker).

## Success Metrics

- ✅ New developers productive in < 30 minutes
- ✅ "Works on my machine" issues eliminated
- ✅ Dev/prod parity increased from ~60% to 85%
- ✅ Integration testing easier (full stack available)

## References

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [12-Factor App - Dev/Prod Parity](https://12factor.net/dev-prod-parity)
- [Development Environment Best Practices](https://docs.docker.com/develop/dev-best-practices/)
