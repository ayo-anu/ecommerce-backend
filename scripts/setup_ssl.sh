#!/bin/bash
# ==============================================================================
# SSL/TLS Setup Script with Let's Encrypt
# ==============================================================================
# This script automates the process of obtaining SSL certificates using
# Let's Encrypt and Certbot for your e-commerce platform.
#
# Prerequisites:
# - Domain names configured and pointing to your server
# - Docker and docker-compose installed
# - Nginx service running
#
# Usage:
#   ./scripts/setup_ssl.sh yourdomain.com admin@yourdomain.com
# ==============================================================================

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DOMAIN="${1:-yourdomain.com}"
EMAIL="${2:-admin@yourdomain.com}"
STAGING="${3:-0}"  # Use Let's Encrypt staging for testing

# Derived domains
WWW_DOMAIN="www.${DOMAIN}"
API_DOMAIN="api.${DOMAIN}"
MONITORING_DOMAIN="monitoring.${DOMAIN}"

echo -e "${BLUE}===================================================================${NC}"
echo -e "${BLUE}SSL/TLS Setup for E-Commerce Platform${NC}"
echo -e "${BLUE}===================================================================${NC}"
echo ""
echo -e "${GREEN}Domain:${NC} $DOMAIN"
echo -e "${GREEN}Email:${NC} $EMAIL"
echo -e "${GREEN}Subdomains:${NC} $WWW_DOMAIN, $API_DOMAIN, $MONITORING_DOMAIN"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}Warning: This script may require sudo privileges${NC}"
fi

# Check prerequisites
echo -e "${BLUE}Checking prerequisites...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Error: docker-compose is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ All prerequisites met${NC}"
echo ""

# Create required directories
echo -e "${BLUE}Creating required directories...${NC}"
mkdir -p infrastructure/docker/certbot/conf
mkdir -p infrastructure/docker/certbot/www
echo -e "${GREEN}✓ Directories created${NC}"
echo ""

# Step 1: Start services without SSL
echo -e "${BLUE}Step 1: Starting Nginx in HTTP-only mode...${NC}"
cat > infrastructure/docker/nginx/nginx.http.conf << 'EOF'
server {
    listen 80;
    listen [::]:80;
    server_name _;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 200 'Server is ready for SSL setup';
        add_header Content-Type text/plain;
    }
}
EOF

# Start nginx temporarily
docker-compose -f deploy/docker/compose/base.yaml up -d nginx || true
echo -e "${GREEN}✓ Nginx started${NC}"
echo ""

# Step 2: Obtain SSL certificates
echo -e "${BLUE}Step 2: Obtaining SSL certificates from Let's Encrypt...${NC}"

CERTBOT_STAGING=""
if [ "$STAGING" = "1" ]; then
    CERTBOT_STAGING="--staging"
    echo -e "${YELLOW}Using Let's Encrypt staging environment (for testing)${NC}"
fi

# Check if certificate already exists
if [ -d "infrastructure/docker/certbot/conf/live/${DOMAIN}" ]; then
    echo -e "${YELLOW}Certificate for ${DOMAIN} already exists${NC}"
    read -p "Do you want to renew it? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${GREEN}Skipping certificate generation${NC}"
    else
        CERTBOT_ACTION="--force-renewal"
    fi
else
    CERTBOT_ACTION=""
fi

# Run certbot
docker run -it --rm \
    -v "$(pwd)/infrastructure/docker/certbot/conf:/etc/letsencrypt" \
    -v "$(pwd)/infrastructure/docker/certbot/www:/var/www/certbot" \
    -v "$(pwd)/infrastructure/docker/certbot/logs:/var/log/letsencrypt" \
    certbot/certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    $CERTBOT_STAGING \
    $CERTBOT_ACTION \
    -d "$DOMAIN" \
    -d "$WWW_DOMAIN" \
    -d "$API_DOMAIN" \
    -d "$MONITORING_DOMAIN"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ SSL certificates obtained successfully${NC}"
else
    echo -e "${RED}Error: Failed to obtain SSL certificates${NC}"
    echo -e "${YELLOW}Troubleshooting tips:${NC}"
    echo -e "  1. Ensure your domain DNS is configured correctly"
    echo -e "  2. Make sure ports 80 and 443 are open"
    echo -e "  3. Check that your domain resolves to this server's IP"
    echo -e "  4. Try running with staging flag: ./setup_ssl.sh $DOMAIN $EMAIL 1"
    exit 1
fi
echo ""

# Step 3: Update Nginx configuration
echo -e "${BLUE}Step 3: Updating Nginx configuration with SSL...${NC}"

# Update nginx.conf to use the correct domain
sed -i "s/yourdomain.com/$DOMAIN/g" infrastructure/docker/nginx/nginx.conf

echo -e "${GREEN}✓ Nginx configuration updated${NC}"
echo ""

# Step 4: Restart services
echo -e "${BLUE}Step 4: Restarting services with SSL enabled...${NC}"

docker-compose -f deploy/docker/compose/base.yaml \
               -f deploy/docker/compose/base.prod.yaml restart nginx

echo -e "${GREEN}✓ Services restarted${NC}"
echo ""

# Step 5: Test SSL configuration
echo -e "${BLUE}Step 5: Testing SSL configuration...${NC}"

sleep 5  # Wait for nginx to fully restart

if curl -sf https://"$DOMAIN" > /dev/null; then
    echo -e "${GREEN}✓ HTTPS is working for $DOMAIN${NC}"
else
    echo -e "${YELLOW}Warning: Could not verify HTTPS for $DOMAIN${NC}"
fi

echo ""

# Step 6: Setup auto-renewal
echo -e "${BLUE}Step 6: Setting up automatic certificate renewal...${NC}"

# Create renewal script
cat > scripts/renew_ssl.sh << 'RENEWAL_SCRIPT'
#!/bin/bash
# SSL Certificate Renewal Script
# This script should be run by cron daily

set -e

echo "Attempting to renew SSL certificates..."

docker run --rm \
    -v "$(pwd)/infrastructure/docker/certbot/conf:/etc/letsencrypt" \
    -v "$(pwd)/infrastructure/docker/certbot/www:/var/www/certbot" \
    certbot/certbot renew \
    --quiet \
    --deploy-hook "docker-compose -f deploy/docker/compose/base.yaml restart nginx"

echo "Certificate renewal check completed"
RENEWAL_SCRIPT

chmod +x scripts/renew_ssl.sh

echo -e "${GREEN}✓ Renewal script created at scripts/renew_ssl.sh${NC}"
echo ""

# Display cron setup instructions
echo -e "${BLUE}===================================================================${NC}"
echo -e "${GREEN}SSL Setup Complete!${NC}"
echo -e "${BLUE}===================================================================${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo ""
echo -e "1. Add this cron job to run certificate renewal daily:"
echo -e "   ${BLUE}sudo crontab -e${NC}"
echo -e "   Add this line:"
echo -e "   ${GREEN}0 3 * * * cd $(pwd) && ./scripts/renew_ssl.sh >> /var/log/ssl_renewal.log 2>&1${NC}"
echo ""
echo -e "2. Test your SSL configuration:"
echo -e "   ${BLUE}https://www.ssllabs.com/ssltest/analyze.html?d=$DOMAIN${NC}"
echo ""
echo -e "3. Access your services:"
echo -e "   Frontend:   ${GREEN}https://$DOMAIN${NC}"
echo -e "   API:        ${GREEN}https://$API_DOMAIN${NC}"
echo -e "   Monitoring: ${GREEN}https://$MONITORING_DOMAIN${NC}"
echo ""
echo -e "4. Your certificates will expire in 90 days. The renewal script"
echo -e "   will automatically renew them when they have less than 30 days remaining."
echo ""
echo -e "${BLUE}===================================================================${NC}"
