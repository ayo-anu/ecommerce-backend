# ==============================================================================
# Production Nginx Dockerfile
# ==============================================================================
# Features:
# - TLS 1.3 support
# - Security headers
# - Brotli compression
# - Health checks
# - Blue-green deployment support
# ==============================================================================

FROM nginx:1.25-alpine AS base

# Install additional packages
RUN apk add --no-cache \
    certbot \
    certbot-nginx \
    openssl \
    curl \
    && rm -rf /var/cache/apk/*

# Create necessary directories
RUN mkdir -p \
    /etc/nginx/conf.d \
    /etc/nginx/ssl \
    /var/www/certbot \
    /var/log/nginx \
    /var/cache/nginx

# Generate self-signed certificate for initial setup (replace with real certs in production)
RUN openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/selfsigned.key \
    -out /etc/nginx/ssl/selfsigned.crt \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

# Generate Diffie-Hellman parameters for stronger security
RUN openssl dhparam -out /etc/nginx/ssl/dhparam.pem 2048

# Copy nginx configuration files
COPY deploy/nginx/nginx.conf /etc/nginx/nginx.conf
COPY deploy/nginx/conf.d/* /etc/nginx/conf.d/

# Set proper permissions for nginx user
RUN chown -R nginx:nginx /var/log/nginx /var/cache/nginx /etc/nginx/ssl /var/www/certbot && \
    chmod 755 /var/log/nginx /var/cache/nginx && \
    chmod 644 /etc/nginx/ssl/selfsigned.crt && \
    chmod 600 /etc/nginx/ssl/selfsigned.key /etc/nginx/ssl/dhparam.pem

# Note: Nginx master process runs as root to bind to privileged ports (80/443)
# Worker processes run as nginx user (defined in nginx.conf)
# This is standard practice for nginx in production

# Expose HTTP and HTTPS ports
EXPOSE 80 443

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
