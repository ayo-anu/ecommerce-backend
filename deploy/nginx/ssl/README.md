# SSL Certificate Setup

This directory contains SSL/TLS certificates for HTTPS.

## Development/Testing

The Docker build process generates a self-signed certificate for local testing:
- `selfsigned.crt` - Self-signed certificate
- `selfsigned.key` - Private key

**WARNING**: Self-signed certificates should NEVER be used in production!

## Production Setup

### Option 1: Let's Encrypt (Free, Recommended)

1. **Install Certbot** (already included in the Nginx Docker image):
   ```bash
   # Run from the host machine
   docker exec nginx certbot --nginx -d yourdomain.com -d www.yourdomain.com
   ```

2. **Auto-renewal**:
   ```bash
   # Add to crontab for automatic renewal
   0 3 * * * docker exec nginx certbot renew --quiet
   ```

3. **Update nginx configuration** in `deploy/nginx/conf.d/api.conf`:
   ```nginx
   ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
   ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
   ```

### Option 2: Commercial Certificate

1. **Generate CSR**:
   ```bash
   openssl req -new -newkey rsa:2048 -nodes \
     -keyout yourdomain.com.key \
     -out yourdomain.com.csr
   ```

2. **Purchase certificate** from a CA (DigiCert, Comodo, etc.)

3. **Place certificates in this directory**:
   ```
   deploy/nginx/ssl/
   ├── yourdomain.com.crt
   ├── yourdomain.com.key
   └── ca-bundle.crt (if provided)
   ```

4. **Update nginx configuration**:
   ```nginx
   ssl_certificate /etc/nginx/ssl/yourdomain.com.crt;
   ssl_certificate_key /etc/nginx/ssl/yourdomain.com.key;
   ssl_trusted_certificate /etc/nginx/ssl/ca-bundle.crt;
   ```

5. **Reload Nginx**:
   ```bash
   docker exec nginx nginx -s reload
   ```

## Testing SSL Configuration

1. **Check certificate**:
   ```bash
   openssl s_client -connect yourdomain.com:443 -servername yourdomain.com
   ```

2. **Test SSL Labs** (for production):
   Visit: https://www.ssllabs.com/ssltest/analyze.html?d=yourdomain.com

   Target: **A+ rating**

3. **Verify TLS 1.3**:
   ```bash
   openssl s_client -connect yourdomain.com:443 -tls1_3
   ```

## Security Best Practices

- ✅ Use TLS 1.3 only
- ✅ Use strong ciphers (AES 256 GCM, AES 128 GCM)
- ✅ Enable HSTS with preload
- ✅ Enable OCSP stapling
- ✅ Use 2048-bit DH parameters (included in image)
- ✅ Disable SSL session tickets
- ✅ Monitor certificate expiration

## Certificate Expiration Monitoring

Add monitoring alerts for certificate expiration:

```bash
# Check expiration date
openssl x509 -in /etc/nginx/ssl/yourdomain.com.crt -noout -enddate

# Alert if expiring within 30 days
```

## Troubleshooting

### Certificate Not Found
- Verify file paths in nginx config
- Check file permissions (should be readable by nginx user)

### Mixed Content Warnings
- Ensure all resources (CSS, JS, images) are loaded via HTTPS
- Add to nginx config: `add_header Content-Security-Policy "upgrade-insecure-requests";`

### OCSP Stapling Errors
- Verify `ssl_trusted_certificate` points to CA bundle
- Check DNS resolver configuration in nginx.conf

## Files in This Directory

- `dhparam.pem` - Diffie-Hellman parameters (generated during build)
- `selfsigned.crt` - Self-signed certificate for dev/testing
- `selfsigned.key` - Self-signed private key for dev/testing
- Place production certificates here before deployment
