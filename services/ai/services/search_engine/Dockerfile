# ==============================================================================
# Search Engine - Optimized Multi-Stage Dockerfile
# Elasticsearch + Vector search with semantic capabilities
# ==============================================================================

# ==============================================================================
# Stage 1: Builder - Install dependencies
# ==============================================================================
# Use latest Debian Bookworm base image for security updates
FROM python:3.11-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install
COPY services/search_engine/requirements.txt ./
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt && \
    pip install httpx

# ==============================================================================
# Stage 2: Runtime - Minimal production image
# ==============================================================================
# Use latest Debian Bookworm base image for security updates
FROM python:3.11-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Copy virtual environment from builder (NO build tools)
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY services/search_engine/ /app/
COPY shared/ /app/shared/

# Create models directory
RUN mkdir -p /models/search

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app /opt/venv /models

USER appuser

# Expose port
EXPOSE 8002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8002/health', timeout=5)" || exit 1

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002", "--workers", "2"]
