# ==============================================================================
# Demand Forecasting - Optimized Multi-Stage Dockerfile
# Time series forecasting with Prophet
# ==============================================================================

# ==============================================================================
# Stage 1: Builder - Install dependencies
# ==============================================================================
# Use latest Debian Bookworm base image for security updates
FROM python:3.11-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=300

WORKDIR /build

# Install build dependencies (Prophet needs gcc, g++)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy base requirements first (needed for -r reference)
COPY ai/requirements-base.txt /requirements-base.txt
# Copy service requirements
COPY ai/services/demand_forecasting/requirements.txt ./
RUN pip install --default-timeout=300 --retries 5 --upgrade pip setuptools wheel && \
    pip install --default-timeout=300 --retries 5 -r requirements.txt && \
    pip install --default-timeout=300 --retries 5 httpx

# ==============================================================================
# Stage 2: Runtime - Minimal production image
# ==============================================================================
# Use latest Debian Bookworm base image for security updates
FROM python:3.11-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Install ONLY runtime PostgreSQL library (not dev packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder (NO build tools)
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY ai/services/demand_forecasting/ /app/
COPY shared/ /app/shared/

# Create models directory
RUN mkdir -p /models/forecasting

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app /opt/venv /models

USER appuser

# Expose port
EXPOSE 8006

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8006/health', timeout=5)" || exit 1

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8006", "--workers", "2"]
