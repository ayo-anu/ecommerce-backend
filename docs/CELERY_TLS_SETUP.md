# Celery Broker TLS Setup

## Overview

This guide explains how to secure Celery broker connections (Redis/RabbitMQ) with TLS encryption.

**SECURITY RISK**: Without TLS, task messages are transmitted in plaintext, exposing:
- Sensitive task data (user info, payment details, etc.)
- Authentication credentials
- Business logic and operations

## Redis TLS Configuration

### 1. Generate TLS Certificates

For production, use certificates from a trusted CA. For development/testing:

```bash
# Generate CA certificate
openssl req -x509 -newkey rsa:4096 -keyout ca-key.pem -out ca-cert.pem -days 365 -nodes -subj "/CN=Redis CA"

# Generate Redis server certificate
openssl req -newkey rsa:4096 -nodes -keyout redis-server-key.pem -out redis-server-req.pem -subj "/CN=redis"
openssl x509 -req -in redis-server-req.pem -CA ca-cert.pem -CAkey ca-key.pem -CAcreateserial -out redis-server-cert.pem -days 365

# Generate client certificate (optional, for mutual TLS)
openssl req -newkey rsa:4096 -nodes -keyout redis-client-key.pem -out redis-client-req.pem -subj "/CN=celery-client"
openssl x509 -req -in redis-client-req.pem -CA ca-cert.pem -CAkey ca-key.pem -CAcreateserial -out redis-client-cert.pem -days 365

# Set permissions
chmod 600 *.pem
```

### 2. Configure Redis Server

Create `redis-tls.conf`:

```conf
# TLS Configuration
port 0
tls-port 6379
tls-cert-file /tls/redis-server-cert.pem
tls-key-file /tls/redis-server-key.pem
tls-ca-cert-file /tls/ca-cert.pem

# Require client certificates (mutual TLS)
tls-auth-clients yes

# TLS protocols
tls-protocols "TLSv1.2 TLSv1.3"
tls-ciphers "HIGH:!aNULL:!MD5"

# Standard Redis configuration
requirepass your_redis_password
maxmemory 1gb
maxmemory-policy allkeys-lru
appendonly yes
```

### 3. Update Docker Compose

```yaml
services:
  redis:
    image: redis:7-alpine
    volumes:
      - ./infrastructure/tls:/tls:ro
      - ./infrastructure/redis/redis-tls.conf:/usr/local/etc/redis/redis.conf:ro
    command: redis-server /usr/local/etc/redis/redis.conf
    networks:
      - backend_network
```

### 4. Configure Django Settings

Add to your `backend/config/settings/production.py`:

```python
# Enable Redis TLS
REDIS_TLS_ENABLED = config('REDIS_TLS_ENABLED', default=True, cast=bool)
REDIS_TLS_CA_CERT = config('REDIS_TLS_CA_CERT', default='/app/tls/ca-cert.pem')
REDIS_TLS_CERT_FILE = config('REDIS_TLS_CERT_FILE', default='/app/tls/redis-client-cert.pem')
REDIS_TLS_KEY_FILE = config('REDIS_TLS_KEY_FILE', default='/app/tls/redis-client-key.pem')
REDIS_TLS_VERIFY_MODE = config('REDIS_TLS_VERIFY_MODE', default='required')

# Update Celery broker URL (use rediss:// for TLS)
from core.celery_tls import get_broker_url_with_tls, get_celery_redis_backend_kwargs

CELERY_BROKER_URL = get_broker_url_with_tls()
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_REDIS_BACKEND_USE_SSL = get_celery_redis_backend_kwargs()
```

### 5. Environment Variables

Add to `.env.production`:

```bash
# Redis TLS Configuration
REDIS_TLS_ENABLED=true
REDIS_TLS_CA_CERT=/app/tls/ca-cert.pem
REDIS_TLS_CERT_FILE=/app/tls/redis-client-cert.pem
REDIS_TLS_KEY_FILE=/app/tls/redis-client-key.pem
REDIS_TLS_VERIFY_MODE=required

# Use rediss:// for secure Redis connections
REDIS_URL=rediss://:your_redis_password@redis:6379/0
CELERY_BROKER_URL=rediss://:your_redis_password@redis:6379/1
CELERY_RESULT_BACKEND=rediss://:your_redis_password@redis:6379/2
```

## RabbitMQ TLS Configuration

### 1. Generate Certificates

Similar to Redis, generate CA and server/client certificates.

### 2. Configure RabbitMQ

Create `rabbitmq.conf`:

```conf
listeners.ssl.default = 5671

ssl_options.cacertfile = /tls/ca-cert.pem
ssl_options.certfile = /tls/rabbitmq-server-cert.pem
ssl_options.keyfile = /tls/rabbitmq-server-key.pem
ssl_options.verify = verify_peer
ssl_options.fail_if_no_peer_cert = true

# TLS versions
ssl_options.versions.1 = tlsv1.3
ssl_options.versions.2 = tlsv1.2

# Disable insecure TLS versions
ssl_options.honor_cipher_order = true
ssl_options.ciphers.1 = ECDHE-ECDSA-AES256-GCM-SHA384
ssl_options.ciphers.2 = ECDHE-RSA-AES256-GCM-SHA384
ssl_options.ciphers.3 = ECDHE-ECDSA-AES128-GCM-SHA256
ssl_options.ciphers.4 = ECDHE-RSA-AES128-GCM-SHA256
```

### 3. Update Environment Variables

```bash
RABBITMQ_TLS_ENABLED=true
RABBITMQ_TLS_CA_CERT=/app/tls/ca-cert.pem
RABBITMQ_TLS_CERT_FILE=/app/tls/rabbitmq-client-cert.pem
RABBITMQ_TLS_KEY_FILE=/app/tls/rabbitmq-client-key.pem

# Use amqps:// for secure connections
CELERY_BROKER_URL=amqps://admin:password@rabbitmq:5671//
```

## Testing TLS Configuration

### 1. Test Redis TLS Connection

```bash
# Using redis-cli
redis-cli --tls \
  --cacert /path/to/ca-cert.pem \
  --cert /path/to/redis-client-cert.pem \
  --key /path/to/redis-client-key.pem \
  -h redis -p 6379 PING

# Expected output: PONG
```

### 2. Test Celery Connection

```python
# Run in Django shell
python manage.py shell

from celery import current_app
result = current_app.control.inspect().stats()
print(result)  # Should show connected workers
```

### 3. Verify TLS in Logs

```bash
# Check Celery worker logs
docker-compose logs celery_worker | grep -i tls

# Should see messages about TLS connection establishment
```

## Troubleshooting

### Common Issues

1. **Certificate verification failed**
   ```
   Error: [SSL: CERTIFICATE_VERIFY_FAILED]
   ```
   - Solution: Ensure CA certificate matches server certificate
   - Check certificate expiration dates
   - Verify hostname in certificate matches server hostname

2. **Connection refused**
   ```
   Error: [Errno 111] Connection refused
   ```
   - Solution: Ensure Redis/RabbitMQ is listening on TLS port
   - Check firewall rules
   - Verify Docker network connectivity

3. **Permission denied**
   ```
   Error: [Errno 13] Permission denied: '/app/tls/redis-client-key.pem'
   ```
   - Solution: Fix file permissions
   ```bash
   chmod 600 /path/to/*.pem
   chown appuser:appuser /path/to/*.pem
   ```

## Production Checklist

- [ ] Generate strong certificates from trusted CA
- [ ] Store certificates securely (use secrets manager)
- [ ] Enable `tls-auth-clients yes` for mutual TLS
- [ ] Set `REDIS_TLS_VERIFY_MODE=required`
- [ ] Use TLSv1.2 or TLSv1.3 only
- [ ] Rotate certificates before expiration
- [ ] Monitor certificate expiration dates
- [ ] Test failover scenarios
- [ ] Document certificate renewal process
- [ ] Set up alerts for certificate expiration

## Performance Considerations

- TLS adds ~5-10% overhead to Redis operations
- Use connection pooling to minimize TLS handshake costs
- Consider using Unix sockets for same-host communication (even more secure)
- Monitor latency metrics before and after TLS enablement

## References

- [Redis TLS Documentation](https://redis.io/docs/management/security/encryption/)
- [RabbitMQ TLS Guide](https://www.rabbitmq.com/ssl.html)
- [Celery Security Best Practices](https://docs.celeryproject.org/en/stable/userguide/security.html)
