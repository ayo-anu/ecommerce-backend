"""
Health check endpoints for Kubernetes probes.

Liveness: Checks if the application process is alive
Readiness: Checks if the application is ready to serve traffic
"""
import logging
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
from django.conf import settings
import redis as redis_client

logger = logging.getLogger(__name__)


def liveness_check(request):
    """
    Liveness probe endpoint.

    This endpoint checks if the application process is alive.
    If this fails, Kubernetes will restart the pod.

    Should be lightweight and fast - only checks critical application health.
    """
    try:
        # Basic check - if we can return this response, the process is alive
        return JsonResponse({
            'status': 'alive',
            'service': 'ecommerce-backend'
        }, status=200)
    except Exception as e:
        logger.error(f"Liveness check failed: {str(e)}")
        return JsonResponse({
            'status': 'dead',
            'error': str(e)
        }, status=500)


def readiness_check(request):
    """
    Readiness probe endpoint.

    This endpoint checks if the application is ready to serve traffic.
    If this fails, Kubernetes will stop sending traffic to the pod.

    Checks all critical dependencies:
    - Database connection
    - Cache (Redis) connection
    - Elasticsearch connection (if available)
    """
    checks = {
        'database': False,
        'cache': False,
        'elasticsearch': False,
    }

    all_ready = True
    errors = []

    # Check database
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        checks['database'] = True
    except Exception as e:
        all_ready = False
        error_msg = f"Database check failed: {str(e)}"
        errors.append(error_msg)
        logger.error(error_msg)

    # Check cache (Redis)
    try:
        cache.set('health_check', 'ok', timeout=10)
        result = cache.get('health_check')
        if result == 'ok':
            checks['cache'] = True
        else:
            raise Exception("Cache value mismatch")
    except Exception as e:
        all_ready = False
        error_msg = f"Cache check failed: {str(e)}"
        errors.append(error_msg)
        logger.error(error_msg)

    # Check Elasticsearch (optional - don't fail readiness if ES is down)
    try:
        from elasticsearch import Elasticsearch
        es_url = getattr(settings, 'ELASTICSEARCH_URL', None)
        if es_url:
            es = Elasticsearch([es_url])
            if es.ping():
                checks['elasticsearch'] = True
            else:
                logger.warning("Elasticsearch ping failed")
                checks['elasticsearch'] = False
        else:
            checks['elasticsearch'] = True  # Not configured, skip check
    except Exception as e:
        # Elasticsearch is not critical for readiness
        logger.warning(f"Elasticsearch check failed (non-critical): {str(e)}")
        checks['elasticsearch'] = True  # Don't fail readiness

    status_code = 200 if all_ready else 503

    return JsonResponse({
        'status': 'ready' if all_ready else 'not_ready',
        'service': 'ecommerce-backend',
        'checks': checks,
        'errors': errors if errors else None
    }, status=status_code)


def health_check(request):
    """
    General health check endpoint.

    Provides detailed health information about the service.
    This is not used by Kubernetes probes but useful for monitoring.
    """
    checks = {
        'database': {'status': 'unknown', 'latency_ms': None},
        'cache': {'status': 'unknown', 'latency_ms': None},
        'elasticsearch': {'status': 'unknown', 'latency_ms': None},
        'vault': {'status': 'unknown'},
    }

    overall_status = 'healthy'

    # Check Vault integration status
    try:
        from core.vault_client import vault_health_check
        vault_status = vault_health_check()
        checks['vault'] = vault_status
    except Exception as e:
        logger.warning(f"Vault health check failed: {str(e)}")
        checks['vault'] = {
            'enabled': False,
            'implemented': False,
            'message': f'Vault check failed: {str(e)}'
        }

    # Check database with latency
    import time
    try:
        start = time.time()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        latency = (time.time() - start) * 1000
        checks['database'] = {
            'status': 'healthy',
            'latency_ms': round(latency, 2)
        }
    except Exception as e:
        checks['database'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        overall_status = 'degraded'

    # Check cache with latency
    try:
        start = time.time()
        cache.set('health_check_detailed', 'ok', timeout=10)
        result = cache.get('health_check_detailed')
        latency = (time.time() - start) * 1000

        if result == 'ok':
            checks['cache'] = {
                'status': 'healthy',
                'latency_ms': round(latency, 2)
            }
        else:
            checks['cache'] = {
                'status': 'unhealthy',
                'error': 'Cache value mismatch'
            }
            overall_status = 'degraded'
    except Exception as e:
        checks['cache'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        overall_status = 'degraded'

    # Check Elasticsearch
    try:
        from elasticsearch import Elasticsearch
        es_url = getattr(settings, 'ELASTICSEARCH_URL', None)
        if es_url:
            start = time.time()
            es = Elasticsearch([es_url])
            if es.ping():
                latency = (time.time() - start) * 1000
                checks['elasticsearch'] = {
                    'status': 'healthy',
                    'latency_ms': round(latency, 2)
                }
            else:
                checks['elasticsearch'] = {
                    'status': 'unhealthy',
                    'error': 'Ping failed'
                }
                overall_status = 'degraded'
        else:
            checks['elasticsearch'] = {
                'status': 'not_configured',
            }
    except Exception as e:
        checks['elasticsearch'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        overall_status = 'degraded'

    # Get application info
    import sys
    import django

    return JsonResponse({
        'status': overall_status,
        'service': 'ecommerce-backend',
        'version': getattr(settings, 'VERSION', '1.0.0'),
        'python_version': sys.version,
        'django_version': django.get_version(),
        'checks': checks,
    }, status=200)
