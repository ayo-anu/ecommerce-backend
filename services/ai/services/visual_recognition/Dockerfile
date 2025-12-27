# ==============================================================================
# Visual Recognition - Optimized Multi-Stage Dockerfile
# Computer vision requires OpenCV build dependencies
# ==============================================================================

# ==============================================================================
# Stage 1: Builder - Install dependencies
# ==============================================================================
# Use latest Debian Bookworm base image for security updates
FROM python:3.14-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=300

WORKDIR /build

# Install build dependencies for OpenCV and torch
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    python3-dev \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy base requirements first (needed for -r reference)
COPY ai/requirements-base.txt /requirements-base.txt
# Copy service requirements
COPY ai/services/visual_recognition/requirements.txt ./
RUN pip install --default-timeout=600 --retries 10 --upgrade pip setuptools wheel && \
    pip install --default-timeout=600 --retries 10 -r requirements.txt && \
    pip install --default-timeout=600 --retries 10 httpx

# ==============================================================================
# Stage 2: Runtime - Minimal production image
# ==============================================================================
# Use latest Debian Bookworm base image for security updates
FROM python:3.14-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Install ONLY runtime dependencies for OpenCV (not build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder (NO gcc, NO build tools)
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY ai/services/visual_recognition/ /app/
COPY shared/ /app/shared/

# Create models directory
RUN mkdir -p /models/vision

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app /opt/venv /models

USER appuser

# Expose port
EXPOSE 8007

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8007/health', timeout=5)" || exit 1

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8007", "--workers", "2"]
