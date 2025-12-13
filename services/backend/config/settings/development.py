from .base import *
import logging

DEBUG = True

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')

# Database - Use SQLite for easy development or PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': config('DB_ENGINE', default='django.db.backends.postgresql'),
        'NAME': config('DB_NAME', default='ecommerce'),
        'USER': config('DB_USER', default='postgres'),
        'PASSWORD': config('DB_PASSWORD', default='postgres123'),
        'HOST': config('DB_HOST', default='127.0.0.1'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

# Cache - Simple local memory cache for development
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# CORS - Allow all origins in development
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# Email - Console backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Static/Media - Local file storage
USE_S3 = False

# Security - Disabled for development
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

#Testing Tools
DEVELOPMENT_APPS = [
    'debug_toolbar',
    'nplusone.ext.django',
    'silk',
]

for app in DEVELOPMENT_APPS:
    if app not in INSTALLED_APPS:
        INSTALLED_APPS.append(app)


DEVELOPMENT_MIDDLEWARE = [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'nplusone.ext.django.NPlusOneMiddleware',
    'silk.middleware.SilkyMiddleware',
]

for middleware in DEVELOPMENT_MIDDLEWARE:
    if middleware not in MIDDLEWARE:
        MIDDLEWARE.append(middleware)

INTERNAL_IPS = [
    '127.0.0.1',
]

# NPlusOne configuration
NPLUSONE_RAISE = False
NPLUSONE_LOGGER = logging.getLogger('nplusone')
NPLUSONE_LOG_LEVEL = logging.WARN

# Silk configuration
SILKY_PYTHON_PROFILER = True
SILKY_PYTHON_PROFILER_BINARY = True
SILKY_META = True
SILKY_INTERCEPT_PERCENT = 100