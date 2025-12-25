# ==============================================================================
# Multi-stage build for API Gateway
# Stage 1: Builder - Install dependencies
# Stage 2: Runtime - Copy only necessary files (no build tools)
# ==============================================================================

# ==============================================================================
# Stage 1: Builder
# ==============================================================================
# Use latest Debian Bookworm base image for security updates
FROM python:3.11-slim-bookworm AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set work directory
WORKDIR /app

# Install build dependencies (only in builder stage)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies in a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install Python requirements
COPY api_gateway/requirements.txt ./
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt && \
    pip install httpx

# ==============================================================================
# Stage 2: Runtime
# ==============================================================================
# Use latest Debian Bookworm base image for security updates
FROM python:3.11-slim-bookworm AS runtime

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Set work directory
WORKDIR /app

# Copy Python virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY api_gateway/ /app/
COPY shared/ /app/shared

# Create non-root user and set ownership
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app /opt/venv
USER appuser

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8080/health', timeout=5)" || exit 1

# Run uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "4"]
