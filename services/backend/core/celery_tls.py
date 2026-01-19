"""TLS helpers for Celery brokers."""

import os
import ssl
from typing import Dict, Optional
from django.conf import settings


def get_redis_tls_config() -> Dict:
    """Redis TLS settings for the Celery broker."""
    if not getattr(settings, 'REDIS_TLS_ENABLED', False):
        return {}

    tls_config = {
        'ssl_cert_reqs': ssl.CERT_REQUIRED,  # Require valid certificate
        'ssl_check_hostname': True,  # Verify hostname matches certificate
    }

    verify_mode = getattr(settings, 'REDIS_TLS_VERIFY_MODE', 'required').lower()
    if verify_mode == 'none':
        tls_config['ssl_cert_reqs'] = ssl.CERT_NONE
        tls_config['ssl_check_hostname'] = False
    elif verify_mode == 'optional':
        tls_config['ssl_cert_reqs'] = ssl.CERT_OPTIONAL

    ca_cert_path = getattr(settings, 'REDIS_TLS_CA_CERT', None)
    if ca_cert_path and os.path.exists(ca_cert_path):
        tls_config['ssl_ca_certs'] = ca_cert_path

    cert_file = getattr(settings, 'REDIS_TLS_CERT_FILE', None)
    key_file = getattr(settings, 'REDIS_TLS_KEY_FILE', None)

    if cert_file and key_file:
        if os.path.exists(cert_file) and os.path.exists(key_file):
            tls_config['ssl_certfile'] = cert_file
            tls_config['ssl_keyfile'] = key_file

    return tls_config


def get_broker_url_with_tls() -> str:
    """Broker URL with TLS enabled."""
    broker_url = getattr(settings, 'CELERY_BROKER_URL', '')

    if not broker_url:
        raise ValueError("CELERY_BROKER_URL not configured")

    tls_enabled = getattr(settings, 'REDIS_TLS_ENABLED', False) or \
                  getattr(settings, 'RABBITMQ_TLS_ENABLED', False)

    if not tls_enabled:
        return broker_url

    if broker_url.startswith('redis://'):
        broker_url = broker_url.replace('redis://', 'rediss://', 1)

    elif broker_url.startswith('amqp://'):
        broker_url = broker_url.replace('amqp://', 'amqps://', 1)

    return broker_url


def get_celery_redis_backend_kwargs() -> Dict:
    """Redis backend kwargs for TLS."""
    kwargs = {}

    if getattr(settings, 'REDIS_TLS_ENABLED', False):
        tls_config = get_redis_tls_config()

        kwargs['redis_backend_use_ssl'] = tls_config

    return kwargs
