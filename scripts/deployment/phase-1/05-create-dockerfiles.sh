#!/bin/bash
# ==============================================================================
# Phase 1 - Step 5: Create Multi-Stage Production Dockerfiles
# ==============================================================================

set -euo pipefail

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[Step 5]${NC} $1"; }
info() { echo -e "${BLUE}[Step 5]${NC} $1"; }

log "Creating production multi-stage Dockerfiles..."

# Create backend production Dockerfile
log "Creating deploy/docker/images/services/backend/Dockerfile.production"
cat > deploy/docker/images/services/backend/Dockerfile.production << 'EOF'
# ==============================================================================
# Production Django Backend - Multi-Stage Build
# Target Size: ~200-300MB (vs ~800MB+ with dev dependencies)
# ==============================================================================

# ==============================================================================
# Stage 1: Base Python with Security Hardening
# ==============================================================================
FROM python:3.11-slim-bookworm AS base

# Security: Run as non-root user
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser

# Install security updates and runtime dependencies only
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        libpq5 \
        curl \
        tini && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# ==============================================================================
# Stage 2: Builder - Install Dependencies
# ==============================================================================
FROM base AS builder

# Build arguments
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        gcc \
        g++ \
        python3-dev && \
    rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements
WORKDIR /build
COPY services/services/backend/requirements/base.txt services/services/backend/requirements/prod.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r prod.txt && \
    find /opt/venv -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true && \
    find /opt/venv -type f -name "*.pyc" -delete && \
    find /opt/venv -type f -name "*.pyo" -delete

# ==============================================================================
# Stage 3: Runtime - Minimal Production Image
# ==============================================================================
FROM base AS runtime

# Build arguments
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0

# Metadata
LABEL org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.title="E-Commerce Backend" \
      org.opencontainers.image.description="Django REST Framework backend service"

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    WORKERS=4 \
    THREADS=2 \
    TIMEOUT=60 \
    MAX_REQUESTS=1000

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder --chown=appuser:appuser /opt/venv /opt/venv

# Copy application code
COPY --chown=appuser:appuser services/services/backend/ /app/

# Create necessary directories with correct permissions
RUN mkdir -p /app/logs /app/staticfiles /app/media /app/tmp && \
    chown -R appuser:appuser /app && \
    chmod 750 /app

# Security: Remove unnecessary packages and files
RUN apt-get purge -y --auto-remove && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* && \
    rm -rf /root/.cache

# Security: Make Python files read-only where possible
RUN chmod 444 /app/manage.py 2>/dev/null || true && \
    find /app/config -type f -name "*.py" -exec chmod 444 {} \; 2>/dev/null || true && \
    find /app/apps -type f -name "*.py" -exec chmod 444 {} \; 2>/dev/null || true

# Copy entrypoint
COPY --chmod=755 services/services/backend/entrypoint.sh /entrypoint.sh

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Expose port
EXPOSE 8000

# Use tini as init system (proper signal handling)
ENTRYPOINT ["/usr/bin/tini", "--", "/entrypoint.sh"]

# Default command
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--threads", "2", \
     "--worker-class", "gthread", \
     "--worker-tmp-dir", "/dev/shm", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "50", \
     "--timeout", "60", \
     "--graceful-timeout", "30", \
     "--keep-alive", "5", \
     "--preload", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info"]
EOF

# Create .dockerignore for backend
log "Creating deploy/docker/images/services/backend/.dockerignore"
cat > deploy/docker/images/services/backend/.dockerignore << 'EOF'
**/__pycache__
**/*.pyc
**/*.pyo
**/*.pyd
.Python
*.so
*.egg
*.egg-info
dist
build
.git
.github
.vscode
.idea
*.md
!README.md
.env
.env.*
!.env.example
logs/
*.log
staticfiles/
media/
*.sqlite3
.coverage
htmlcov/
.pytest_cache/
.mypy_cache/
.ruff_cache/
EOF

# Create AI services template (will be used for all AI microservices)
log "Creating deploy/docker/images/services/ai/Dockerfile.template"
cat > deploy/docker/images/services/ai/Dockerfile.template << 'EOF'
# ==============================================================================
# AI Services - Production Multi-Stage Dockerfile Template
# ARG SERVICE_NAME must be passed during build
# ==============================================================================

ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim-bookworm AS base

ARG SERVICE_NAME
ENV SERVICE_NAME=${SERVICE_NAME}

# Security: Non-root user
RUN groupadd -r aiuser && useradd -r -g aiuser -u 1001 aiuser

# Runtime dependencies
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        libgomp1 \
        libglib2.0-0 \
        curl \
        tini && \
    rm -rf /var/lib/apt/lists/*

# ==============================================================================
# Builder Stage
# ==============================================================================
FROM base AS builder

# Build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        g++ \
        git && \
    rm -rf /var/lib/apt/lists/*

# Virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /build

# Copy requirements
COPY services/ai/services/${SERVICE_NAME}/requirements.txt .
COPY services/ai/shared/requirements.txt shared_requirements.txt

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r shared_requirements.txt && \
    find /opt/venv -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true && \
    find /opt/venv -type f -name "*.pyc" -delete

# ==============================================================================
# Runtime Stage
# ==============================================================================
FROM base AS runtime

ARG SERVICE_NAME
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    SERVICE_NAME=${SERVICE_NAME} \
    WORKERS=2 \
    PORT=8000

WORKDIR /app

# Copy virtual environment
COPY --from=builder --chown=aiuser:aiuser /opt/venv /opt/venv

# Copy application code
COPY --chown=aiuser:aiuser services/ai/services/${SERVICE_NAME}/ /app/
COPY --chown=aiuser:aiuser services/ai/shared/ /app/shared/

# Create directories
RUN mkdir -p /app/logs /app/models /app/tmp && \
    chown -R aiuser:aiuser /app && \
    chmod 750 /app

USER aiuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

EXPOSE ${PORT}

ENTRYPOINT ["/usr/bin/tini", "--"]

CMD ["uvicorn", "main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2", \
     "--loop", "uvloop", \
     "--http", "httptools"]
EOF

log "✅ Multi-stage Dockerfiles created"

info "Created files:"
info "  - deploy/docker/images/services/backend/Dockerfile.production"
info "  - deploy/docker/images/services/backend/.dockerignore"
info "  - deploy/docker/images/services/ai/Dockerfile.template"
