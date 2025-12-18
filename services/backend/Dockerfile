# ==============================================================================
# Multi-stage build for Django Backend
# Stage 1: Builder - Install dependencies
# Stage 2: Runtime - Copy only necessary files (no build tools)
# ==============================================================================

# ==============================================================================
# Stage 1: Builder
# ==============================================================================
FROM python:3.11-slim AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set work directory
WORKDIR /app

# Install build dependencies (only in builder stage)
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    libpq-dev \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies in a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install Python requirements
COPY requirements/ /app/requirements/
RUN pip install --upgrade pip && \
    pip install -r requirements/prod.txt

# ==============================================================================
# Stage 2: Runtime
# ==============================================================================
FROM python:3.11-slim AS runtime

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Install only runtime dependencies (no gcc, no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy Python virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY . /app/

# Create necessary directories
RUN mkdir -p /app/logs /app/staticfiles /app/media

# Create non-root user and set ownership
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app /opt/venv

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Use entrypoint script for startup
ENTRYPOINT ["/entrypoint.sh"]

# Run gunicorn with production settings
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--threads", "1", \
     "--worker-class", "sync", \
     "--worker-tmp-dir", "/dev/shm", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "50", \
     "--timeout", "30", \
     "--preload-app", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info"]