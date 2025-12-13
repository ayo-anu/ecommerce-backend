"""
Celery Broker TLS Configuration.

Provides secure TLS connections between Celery workers and the broker (Redis/RabbitMQ).

SECURITY: Prevents eavesdropping and tampering of task messages.
"""

import os
import ssl
from typing import Dict, Optional
from django.conf import settings


def get_redis_tls_config() -> Dict:
    """
    Get Redis TLS configuration for Celery broker.

    Returns TLS context configuration for secure Redis connections.

    Environment Variables:
        REDIS_TLS_ENABLED: Set to 'true' to enable TLS
        REDIS_TLS_CERT_FILE: Path to client certificate (optional, for mutual TLS)
        REDIS_TLS_KEY_FILE: Path to client private key (optional)
        REDIS_TLS_CA_CERT: Path to CA certificate
        REDIS_TLS_VERIFY_MODE: 'required' (default) or 'optional' or 'none'

    Example Redis URL with TLS:
        rediss://:<password>@redis:6379/0

    Note: Use 'rediss://' (with double 's') for TLS connections.
    """
    if not getattr(settings, 'REDIS_TLS_ENABLED', False):
        return {}

    # Base TLS configuration
    tls_config = {
        'ssl_cert_reqs': ssl.CERT_REQUIRED,  # Require valid certificate
        'ssl_check_hostname': True,  # Verify hostname matches certificate
    }

    # Certificate verification mode
    verify_mode = getattr(settings, 'REDIS_TLS_VERIFY_MODE', 'required').lower()
    if verify_mode == 'none':
        tls_config['ssl_cert_reqs'] = ssl.CERT_NONE
        tls_config['ssl_check_hostname'] = False
    elif verify_mode == 'optional':
        tls_config['ssl_cert_reqs'] = ssl.CERT_OPTIONAL

    # CA certificate for server verification
    ca_cert_path = getattr(settings, 'REDIS_TLS_CA_CERT', None)
    if ca_cert_path and os.path.exists(ca_cert_path):
        tls_config['ssl_ca_certs'] = ca_cert_path

    # Client certificate for mutual TLS (optional)
    cert_file = getattr(settings, 'REDIS_TLS_CERT_FILE', None)
    key_file = getattr(settings, 'REDIS_TLS_KEY_FILE', None)

    if cert_file and key_file:
        if os.path.exists(cert_file) and os.path.exists(key_file):
            tls_config['ssl_certfile'] = cert_file
            tls_config['ssl_keyfile'] = key_file

    return tls_config


def get_broker_url_with_tls() -> str:
    """
    Get Celery broker URL with TLS configuration.

    For Redis: Replace redis:// with rediss://
    For RabbitMQ: Add ?ssl=1 query parameter

    Returns:
        Broker URL string with TLS enabled
    """
    broker_url = getattr(settings, 'CELERY_BROKER_URL', '')

    if not broker_url:
        raise ValueError("CELERY_BROKER_URL not configured")

    # Check if TLS is enabled
    tls_enabled = getattr(settings, 'REDIS_TLS_ENABLED', False) or \
                  getattr(settings, 'RABBITMQ_TLS_ENABLED', False)

    if not tls_enabled:
        return broker_url

    # Redis: Change redis:// to rediss://
    if broker_url.startswith('redis://'):
        broker_url = broker_url.replace('redis://', 'rediss://', 1)

    # RabbitMQ: Add SSL parameter
    elif broker_url.startswith('amqp://'):
        broker_url = broker_url.replace('amqp://', 'amqps://', 1)

    return broker_url


def get_celery_redis_backend_kwargs() -> Dict:
    """
    Get kwargs for Celery Redis result backend with TLS.

    These kwargs are passed to the Redis client for secure connections.

    Returns:
        Dictionary of Redis connection parameters
    """
    kwargs = {}

    if getattr(settings, 'REDIS_TLS_ENABLED', False):
        # Add TLS configuration
        tls_config = get_redis_tls_config()

        # Convert to redis-py compatible format
        kwargs['redis_backend_use_ssl'] = tls_config

    return kwargs
