from .base import *

import importlib.util

import logging


DEBUG = True


ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')


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


CACHES = {

    'default': {

        'BACKEND': 'django_redis.cache.RedisCache',

        'LOCATION': config('REDIS_URL', default='redis://:redis_password@redis:6379/0'),

        'OPTIONS': {

            'CLIENT_CLASS': 'django_redis.client.DefaultClient',

        },

    }

}


CORS_ALLOW_ALL_ORIGINS = True

CORS_ALLOW_CREDENTIALS = True


EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')

EMAIL_HOST = config('EMAIL_HOST', default='mailhog')

EMAIL_PORT = config('EMAIL_PORT', default=1025, cast=int)

EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=False, cast=bool)

EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')

EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')

DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@example.com')


USE_S3 = False


SECURE_SSL_REDIRECT = False

SESSION_COOKIE_SECURE = False

CSRF_COOKIE_SECURE = False


DEVELOPMENT_APPS = [

    'debug_toolbar',

    'nplusone.ext.django',

    'silk',

]


for app in DEVELOPMENT_APPS:

    try:

        available = importlib.util.find_spec(app) is not None

    except ModuleNotFoundError:

        available = False

    if available and app not in INSTALLED_APPS:

        INSTALLED_APPS.append(app)


DEVELOPMENT_MIDDLEWARE = [

    'debug_toolbar.middleware.DebugToolbarMiddleware',

    'nplusone.ext.django.NPlusOneMiddleware',

    'silk.middleware.SilkyMiddleware',

]


for middleware in DEVELOPMENT_MIDDLEWARE:

    module_name = middleware.rsplit('.', 1)[0]

    try:

        available = importlib.util.find_spec(module_name) is not None

    except ModuleNotFoundError:

        available = False

    if available and middleware not in MIDDLEWARE:

        if 'django_prometheus.middleware.PrometheusAfterMiddleware' in MIDDLEWARE:

            MIDDLEWARE.insert(-1, middleware)

        else:

            MIDDLEWARE.append(middleware)


INTERNAL_IPS = [

    '127.0.0.1',

]


NPLUSONE_RAISE = False

NPLUSONE_LOGGER = logging.getLogger('nplusone')

NPLUSONE_LOG_LEVEL = logging.WARN


SILKY_PYTHON_PROFILER = True

SILKY_PYTHON_PROFILER_BINARY = True

SILKY_META = True

SILKY_INTERCEPT_PERCENT = 100


CELERY_TASK_ALWAYS_EAGER = False                                    

CELERY_TASK_EAGER_PROPAGATES = False                                             


REST_FRAMEWORK = {

    **REST_FRAMEWORK,

    'DEFAULT_THROTTLE_RATES': {

        'anon': '10000/hour',

        'user': '10000/hour',

        'login': '10000/minute',

    },

}


CELERY_BROKER_URL = config(

    'CELERY_BROKER_URL',

    default='redis://:redis_password@redis:6379/0'

)

CELERY_RESULT_BACKEND = config(

    'CELERY_RESULT_BACKEND',

    default='redis://:redis_password@redis:6379/1'

)


OPENSEARCH_DSL = {

    'default': {

        'hosts': config('ELASTICSEARCH_URL', default='http://localhost:9200')

    },

}

ELASTICSEARCH_DSL = OPENSEARCH_DSL
