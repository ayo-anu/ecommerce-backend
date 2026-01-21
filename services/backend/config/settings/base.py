from pathlib import Path

from decouple import config

from datetime import timedelta

import os


BASE_DIR = Path(__file__).resolve().parent.parent.parent


USE_VAULT = os.getenv('USE_VAULT', 'false').lower() in ('true', '1', 'yes')


try:

    from core.vault_client import get_vault_secret

    VAULT_CLIENT_AVAILABLE = True

except ImportError:

    VAULT_CLIENT_AVAILABLE = False

    def get_vault_secret(env_var_name, vault_path=None, vault_key=None, default=None):

        return os.getenv(env_var_name, default)


if USE_VAULT and not VAULT_CLIENT_AVAILABLE:

    import logging

    logger = logging.getLogger(__name__)

    logger.warning(

        "USE_VAULT=true but core.vault_client module not available. "

        "Falling back to environment variables."

    )

    USE_VAULT = False


SECRET_KEY = get_vault_secret(

    'SECRET_KEY',

    vault_path='secret/data/django' if USE_VAULT else None,

    vault_key='SECRET_KEY' if USE_VAULT else None,

    default=config('SECRET_KEY', default='')

)


INSTALLED_APPS = [

    'apps.accounts',

    'django.contrib.admin',

    'django.contrib.auth',

    'django.contrib.contenttypes',

    'django.contrib.sessions',

    'django.contrib.messages',

    'django.contrib.staticfiles',


    'rest_framework',

    'rest_framework_simplejwt',

    'corsheaders',

    'django_filters',

    'drf_spectacular',

    'django_opensearch_dsl',

    'django_celery_beat',

    'django_prometheus',

    'storages',



    'apps.products',

    'apps.orders',

    'apps.payments',

    'apps.notifications',

    'apps.analytics',

]


MIDDLEWARE = [

    'django_prometheus.middleware.PrometheusBeforeMiddleware',

    'django.middleware.security.SecurityMiddleware',

    'whitenoise.middleware.WhiteNoiseMiddleware',

    'corsheaders.middleware.CorsMiddleware',

    'django.contrib.sessions.middleware.SessionMiddleware',

    'django.middleware.common.CommonMiddleware',

    'django.middleware.csrf.CsrfViewMiddleware',

    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'core.middleware.maintenance.MaintenanceModeMiddleware',

    'django.contrib.messages.middleware.MessageMiddleware',

    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.request_logging.RequestLoggingMiddleware',

    'django_prometheus.middleware.PrometheusAfterMiddleware',

]



DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880       

FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880       

DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000                          


ROOT_URLCONF = 'config.urls'


TEMPLATES = [

    {

        'BACKEND': 'django.template.backends.django.DjangoTemplates',

        'DIRS': [BASE_DIR / 'templates'],

        'APP_DIRS': True,

        'OPTIONS': {

            'context_processors': [

                'django.template.context_processors.debug',

                'django.template.context_processors.request',

                'django.contrib.auth.context_processors.auth',

                'django.contrib.messages.context_processors.messages',

            ],

        },

    },

]


WSGI_APPLICATION = 'config.wsgi.application'


AUTH_USER_MODEL = 'accounts.User'


AUTH_PASSWORD_VALIDATORS = [

    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},

    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},

    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},

    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},

]


PASSWORD_HASHERS = [

    'django.contrib.auth.hashers.Argon2PasswordHasher',

    'django.contrib.auth.hashers.PBKDF2PasswordHasher',

]


LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


STATIC_URL = '/static/'

STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_DIRS = []

if (BASE_DIR / 'static').exists():

    STATICFILES_DIRS.append(BASE_DIR / 'static')

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


MEDIA_URL = '/media/'

MEDIA_ROOT = BASE_DIR / 'media'


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


REST_FRAMEWORK = {

    'DEFAULT_AUTHENTICATION_CLASSES': (

        'rest_framework_simplejwt.authentication.JWTAuthentication',

    ),

    'DEFAULT_PERMISSION_CLASSES': (

        'rest_framework.permissions.IsAuthenticatedOrReadOnly',

    ),

    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',

    'PAGE_SIZE': 20,

    'DEFAULT_FILTER_BACKENDS': (

        'django_filters.rest_framework.DjangoFilterBackend',

        'rest_framework.filters.SearchFilter',

        'rest_framework.filters.OrderingFilter',

    ),

    'DEFAULT_THROTTLE_CLASSES': (

        'rest_framework.throttling.AnonRateThrottle',

        'rest_framework.throttling.UserRateThrottle',

    ),

    'DEFAULT_THROTTLE_RATES': {

        'anon': '100/hour',

        'user': '1000/hour',

        'login': '5/minute',

    },

    'DEFAULT_RENDERER_CLASSES': (

        'rest_framework.renderers.JSONRenderer',

    ),

    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',

    'EXCEPTION_HANDLER': 'core.exceptions.custom_exception_handler',

}


SIMPLE_JWT = {

    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),

    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),

    'ROTATE_REFRESH_TOKENS': True,

    'BLACKLIST_AFTER_ROTATION': True,

    'UPDATE_LAST_LOGIN': True,

    'ALGORITHM': 'HS256',

    'SIGNING_KEY': SECRET_KEY,

}


CELERY_BROKER_URL = config('CELERY_BROKER_URL')

CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND')

CELERY_ACCEPT_CONTENT = ['json']

CELERY_TASK_SERIALIZER = 'json'

CELERY_RESULT_SERIALIZER = 'json'

CELERY_TIMEZONE = TIME_ZONE



ELASTICSEARCH_URL = config('ELASTICSEARCH_URL', default='')

OPENSEARCH_DSL = {

    'default': {

        'hosts': ELASTICSEARCH_URL

    },

} if ELASTICSEARCH_URL else {}

ELASTICSEARCH_DSL = OPENSEARCH_DSL



FRONTEND_URL = config('FRONTEND_URL', default='http://localhost:3000')


STRIPE_SECRET_KEY = get_vault_secret(

    'STRIPE_SECRET_KEY',

    vault_path='secret/data/stripe' if USE_VAULT else None,

    vault_key='SECRET_KEY' if USE_VAULT else None,

    default=config('STRIPE_SECRET_KEY', default='')

)

STRIPE_PUBLISHABLE_KEY = get_vault_secret(

    'STRIPE_PUBLISHABLE_KEY',

    vault_path='secret/data/stripe' if USE_VAULT else None,

    vault_key='PUBLISHABLE_KEY' if USE_VAULT else None,

    default=config('STRIPE_PUBLISHABLE_KEY', default='')

)

STRIPE_WEBHOOK_SECRET = get_vault_secret(

    'STRIPE_WEBHOOK_SECRET',

    vault_path='secret/data/stripe' if USE_VAULT else None,

    vault_key='WEBHOOK_SECRET' if USE_VAULT else None,

    default=config('STRIPE_WEBHOOK_SECRET', default='')

)


STRIPE_API_VERSION = '2023-10-16'

STRIPE_DEFAULT_CURRENCY = 'usd'


LOGGING = {

    'version': 1,

    'disable_existing_loggers': False,

    'formatters': {

        'verbose': {

            'format': '{levelname} {asctime} {module} {message}',

            'style': '{',

        },

    },

    'handlers': {

        'console': {

            'class': 'logging.StreamHandler',

            'formatter': 'verbose',

        },

        'file': {

            'class': 'logging.handlers.RotatingFileHandler',

            'filename': BASE_DIR / 'logs' / 'django.log',

            'maxBytes': 1024 * 1024 * 10,

            'backupCount': 10,

            'formatter': 'verbose',

        },

    },

    'root': {

        'handlers': ['console', 'file'],

        'level': 'INFO',

    },

}
