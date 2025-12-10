FROM nginx:1.25-alpine

# Install certbot for Let's Encrypt
RUN apk add --no-cache certbot certbot-nginx

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Create directory for Let's Encrypt challenges
RUN mkdir -p /var/www/certbot

# Create directory for SSL certificates
RUN mkdir -p /etc/letsencrypt

# Expose HTTP and HTTPS
EXPOSE 80 443

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
