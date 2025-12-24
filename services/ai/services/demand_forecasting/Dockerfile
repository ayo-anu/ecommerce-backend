# ==============================================================================
# Demand Forecasting - Optimized Multi-Stage Dockerfile
# Time series forecasting with Prophet
# ==============================================================================

# ==============================================================================
# Stage 1: Builder - Install dependencies
# ==============================================================================
FROM python:3.14-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

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

# Copy requirements and install
COPY services/demand_forecasting/requirements.txt ./
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt && \
    pip install httpx

# ==============================================================================
# Stage 2: Runtime - Minimal production image
# ==============================================================================
FROM python:3.14-slim AS runtime

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
COPY services/demand_forecasting/ /app/
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
