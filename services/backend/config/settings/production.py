import dj_database_url
from copy import deepcopy
from .base import *
from .base import get_vault_secret, USE_VAULT
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from django.core.exceptions import ImproperlyConfigured
import sys

DEBUG = False

# ==============================================================================
# Middleware Configuration
# ==============================================================================
# Add observability middleware at the beginning of the stack
MIDDLEWARE.insert(0, 'core.middleware.request_id.RequestIDMiddleware')
if 'django_prometheus.middleware.PrometheusAfterMiddleware' in MIDDLEWARE:
    MIDDLEWARE.insert(
        MIDDLEWARE.index('django_prometheus.middleware.PrometheusAfterMiddleware'),
        'core.middleware.error_logging.ErrorLoggingMiddleware'
    )
else:
    MIDDLEWARE.append('core.middleware.error_logging.ErrorLoggingMiddleware')

# ==============================================================================
# CRITICAL: ALLOWED_HOSTS validation
# ==============================================================================
# SECURITY: NEVER use '*' in production. This prevents host header injection attacks.
# Explicitly list all allowed domains.
_allowed_hosts = config('ALLOWED_HOSTS', default='')
if not _allowed_hosts or _allowed_hosts == '*':
    raise ImproperlyConfigured(
        "ALLOWED_HOSTS must be explicitly configured in production. "
        "Set ALLOWED_HOSTS environment variable with comma-separated domains. "
        "Example: ALLOWED_HOSTS=example.com,www.example.com,api.example.com"
    )
ALLOWED_HOSTS = [host.strip() for host in _allowed_hosts.split(',') if host.strip()]

# ==============================================================================
# Startup validation for critical secrets
# ==============================================================================
def validate_required_settings():
    """
    Validate that all required settings are configured before startup.

    Fails fast to prevent misconfigured production deployments.
    """
    required_settings = {
        'SECRET_KEY': config('SECRET_KEY', default=''),
        'ALLOWED_HOSTS': _allowed_hosts,
        'DATABASE_URL': config('DATABASE_URL', default=''),
    }

    # Validate required service auth keys
    required_service_keys = [
        'SERVICE_AUTH_SECRET_DJANGO_BACKEND',
        'SERVICE_AUTH_SECRET_API_GATEWAY',
        'SERVICE_AUTH_SECRET_CELERY_WORKER',
    ]

    missing_settings = []
    insecure_settings = []

    # Check required settings
    for setting_name, setting_value in required_settings.items():
        if not setting_value:
            missing_settings.append(setting_name)

    secret_key = required_settings['SECRET_KEY']
    if secret_key and ('insecure' in secret_key.lower() or
                       'change' in secret_key.lower() or
                       'django-secret' in secret_key.lower()):
        insecure_settings.append('SECRET_KEY (contains insecure placeholder)')

    for key_name in required_service_keys:
        key_value = config(key_name, default='')
        if not key_value:
            missing_settings.append(key_name)
        elif 'CHANGE_ME' in key_value or len(key_value) < 32:
            insecure_settings.append(f'{key_name} (placeholder or too short)')

    errors = []

    if missing_settings:
        errors.append(
            f"Missing required environment variables:\n" +
            '\n'.join(f"  - {s}" for s in missing_settings)
        )

    if insecure_settings:
        errors.append(
            f"Insecure configuration detected:\n" +
            '\n'.join(f"  - {s}" for s in insecure_settings)
        )

    if errors:
        error_message = (
            "\n" + "=" * 80 + "\n" +
            "PRODUCTION CONFIGURATION ERROR\n" +
            "=" * 80 + "\n" +
            '\n\n'.join(errors) + "\n" +
            "=" * 80 + "\n" +
            "Application startup aborted to prevent insecure production deployment.\n" +
            "=" * 80 + "\n"
        )
        raise ImproperlyConfigured(error_message)

# Run validation during settings load (not during migrations or other management commands)
if 'runserver' in sys.argv or 'gunicorn' in sys.argv[0] or 'daphne' in sys.argv[0]:
    validate_required_settings()


# Get DATABASE_URL from Vault or environment variable
_database_url = get_vault_secret(
    'DATABASE_URL',
    vault_path='secret/data/postgres',
    vault_key='DATABASE_URL',
    default=config('DATABASE_URL', default='')
)

if _database_url:
    DATABASES = {
        'default': dj_database_url.config(
            default=_database_url,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    # Fallback to manual configuration
    DATABASES = {
        'default': {
            'ENGINE': config('DB_ENGINE'),
            'NAME': config('DB_NAME'),
            'USER': config('DB_USER'),
            'PASSWORD': config('DB_PASSWORD'),
            'HOST': config('DB_HOST'),
            'PORT': config('DB_PORT'),
            'CONN_MAX_AGE': 600,
            'OPTIONS': {
                'sslmode': 'require' if config('DB_SSL_REQUIRE', default=True, cast=bool) else 'prefer',
                'connect_timeout': 10,
                'options': '-c statement_timeout=30000',
            },
        }
    }


# Get REDIS_URL from Vault or environment variable
REDIS_URL = get_vault_secret(
    'REDIS_URL',
    vault_path='secret/data/redis',
    vault_key='URL',
    default=config('REDIS_URL', default='redis://localhost:6379/0')
)

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_CLASS_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
        },
        'KEY_PREFIX': 'ecommerce',
        'TIMEOUT': 300,
    }
}


CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL


CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='http://localhost:3000').split(',')
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='http://localhost:3000').split(',')
CSRF_COOKIE_HTTPONLY = False  # Must be False for JavaScript to read CSRF token
CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SAMESITE = 'Lax'


EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')

# Logging - disable file handler in production (stdout only on Render)
LOGGING = deepcopy(LOGGING)
LOGGING['handlers'].pop('file', None)
LOGGING['root']['handlers'] = ['console']


# ==============================================================================
# CDN & Static Files Configuration
# ==============================================================================
USE_S3 = config('USE_S3', default=False, cast=bool)
USE_CDN = config('USE_CDN', default=False, cast=bool)

if USE_S3:
    # AWS S3 Configuration - Get credentials from Vault or environment
    AWS_ACCESS_KEY_ID = get_vault_secret(
        'AWS_ACCESS_KEY_ID',
        vault_path='secret/data/aws',
        vault_key='ACCESS_KEY_ID',
        default=config('AWS_ACCESS_KEY_ID', default='')
    )
    AWS_SECRET_ACCESS_KEY = get_vault_secret(
        'AWS_SECRET_ACCESS_KEY',
        vault_path='secret/data/aws',
        vault_key='SECRET_ACCESS_KEY',
        default=config('AWS_SECRET_ACCESS_KEY', default='')
    )
    AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='us-east-1')

    # CDN Configuration
    if USE_CDN:
        # CDN_DOMAIN should be your CloudFront or Cloudflare domain
        # Examples:
        #   CloudFront: d1234567890.cloudfront.net
        #   Cloudflare: cdn.example.com
        CDN_DOMAIN = config('CDN_DOMAIN', default='')

        if CDN_DOMAIN:
            AWS_S3_CUSTOM_DOMAIN = CDN_DOMAIN
        else:
            # Fallback to S3 direct if CDN_DOMAIN not set
            AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
    else:
        AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'

    # S3 Configuration
    AWS_DEFAULT_ACL = None  # Use bucket's default ACL
    AWS_S3_FILE_OVERWRITE = False
    AWS_S3_VERIFY = True

    # Enable S3 Transfer Acceleration (optional, for faster uploads)
    AWS_S3_USE_ACCELERATE_ENDPOINT = config('AWS_S3_USE_ACCELERATE', default=False, cast=bool)

    # Custom storage backends with optimized cache headers
    STATICFILES_STORAGE = 'core.storage_backends.StaticStorage'
    DEFAULT_FILE_STORAGE = 'core.storage_backends.MediaStorage'

    # URLs for static and media files
    STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/static/'
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'

    # Collectstatic configuration
    AWS_LOCATION = 'static'

else:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
    STATIC_ROOT = BASE_DIR / 'staticfiles'
    STATIC_URL = '/static/'

    # WhiteNoise cache headers
    WHITENOISE_MAX_AGE = 31536000  # 1 year for versioned static files
    WHITENOISE_IMMUTABLE_FILE_TEST = lambda path, url: True  # Mark all as immutable

    MEDIA_ROOT = BASE_DIR / 'media'
    MEDIA_URL = '/media/'

# Security Settings
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# Sentry Error Tracking
# Only initialize if SENTRY_DSN is configured
# Gracefully handles invalid DSN without crashing
if config('SENTRY_DSN', default=''):
    try:
        sentry_sdk.init(
            dsn=config('SENTRY_DSN'),
            integrations=[DjangoIntegration()],
            traces_sample_rate=0.1,
            send_default_pii=False,
            environment=config('SENTRY_ENVIRONMENT', default='production'),
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to initialize Sentry: {e}. Continuing without Sentry.")


# ==============================================================================
# Logging Configuration - Production JSON Logs
# ==============================================================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'request_id': {
            '()': 'core.logging.RequestIDFilter',
        },
    },
    'formatters': {
        'json': {
            '()': 'core.logging.JSONFormatter',
        },
        'verbose': {
            'format': '{levelname} {asctime} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
            'filters': ['request_id'],
        },
        'error_console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
            'level': 'ERROR',
            'filters': ['request_id'],
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['error_console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['error_console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'core': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}


REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    'anon': '50/hour',
    'user': '500/hour',
    'login': '5/minute',
}
