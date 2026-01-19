"""
E2E Test Settings
Optimized for end-to-end testing while maintaining data integrity

This configuration:
- Uses real PostgreSQL database (not in-memory) for E2E testing
- Optimizes slow operations (password hashing, email, indexing)
- Maintains security and validation logic
- Disables unnecessary background tasks
"""
from .development import *
import logging

# ==============================================================================
# DATABASE - Use real PostgreSQL for E2E tests
# ==============================================================================
# E2E tests need the real database that the backend is using
# This is already configured via environment variables in development.py

# ==============================================================================
# PASSWORD HASHING - Use fast hasher for tests
# ==============================================================================
# CRITICAL: Only for testing! Production uses Argon2
# MD5 is ~1000x faster than Argon2, reducing registration time from 20s to 20ms
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# ==============================================================================
# EMAIL - Console backend (no actual sending)
# ==============================================================================
# Email operations are I/O bound and slow
# Console backend is instant and logs to stdout
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ==============================================================================
# CELERY - Run tasks synchronously but don't block
# ==============================================================================
# For E2E tests, we want tasks to run immediately but not block the response
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# ==============================================================================
# ELASTICSEARCH - Disable auto-indexing during tests
# ==============================================================================
# Auto-indexing on every save is slow
# Tests can manually trigger indexing when needed
ELASTICSEARCH_DSL_AUTOSYNC = False
ELASTICSEARCH_DSL_AUTO_REFRESH = False

# Optional: Use a separate test index
if 'default' in ELASTICSEARCH_DSL:
    ELASTICSEARCH_DSL['default']['index_prefix'] = 'test_'

# ==============================================================================
# CACHING - Use dummy cache to avoid stale data
# ==============================================================================
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# ==============================================================================
# THROTTLING - Disable rate limiting for tests
# ==============================================================================
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    'DEFAULT_THROTTLE_RATES': {
        'anon': '10000/hour',
        'user': '10000/hour',
        'login': '10000/minute',  # High limit for test runs
    },
}

# ==============================================================================
# LOGGING - Reduce verbosity during tests
# ==============================================================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'WARNING',  # Only show warnings and errors
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    # Silence noisy loggers
    'loggers': {
        'django.db.backends': {
            'level': 'WARNING',
        },
        'elasticsearch': {
            'level': 'WARNING',
        },
        'httpx': {
            'level': 'WARNING',
        },
    },
}

# ==============================================================================
# PERFORMANCE OPTIMIZATIONS
# ==============================================================================
# Disable debug toolbar and profiling tools in E2E tests
INSTALLED_APPS = [app for app in INSTALLED_APPS if app not in [
    'debug_toolbar',
    'silk',
    'nplusone.ext.django',
]]

MIDDLEWARE = [mw for mw in MIDDLEWARE if not any([
    'debug_toolbar' in mw,
    'silk' in mw,
    'nplusone' in mw,
])]

# ==============================================================================
# SECURITY - Keep enabled to test real behavior
# ==============================================================================
# We don't disable CSRF, permissions, or other security features
# E2E tests should test the real security implementation

# ==============================================================================
# SESSION - Use database-backed sessions like production
# ==============================================================================
# Tests should use same session backend as production

print("=" * 80)
print("E2E TEST SETTINGS LOADED")
print("=" * 80)
print(f"Database: {DATABASES['default']['ENGINE']} @ {DATABASES['default']['HOST']}")
print(f"Password Hasher: {PASSWORD_HASHERS[0]} (FAST - Test Only)")
print(f"Email Backend: {EMAIL_BACKEND}")
print(f"Celery Eager: {CELERY_TASK_ALWAYS_EAGER}")
print(f"Elasticsearch Auto-sync: {ELASTICSEARCH_DSL_AUTOSYNC}")
print("=" * 80)
