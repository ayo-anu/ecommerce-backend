from .development import *

import logging



PASSWORD_HASHERS = [

    'django.contrib.auth.hashers.MD5PasswordHasher',

]


EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


CELERY_TASK_ALWAYS_EAGER = True

CELERY_TASK_EAGER_PROPAGATES = True


OPENSEARCH_DSL_AUTOSYNC = False

OPENSEARCH_DSL_AUTO_REFRESH = False

ELASTICSEARCH_DSL_AUTOSYNC = OPENSEARCH_DSL_AUTOSYNC

ELASTICSEARCH_DSL_AUTO_REFRESH = OPENSEARCH_DSL_AUTO_REFRESH


if 'default' in OPENSEARCH_DSL:

    OPENSEARCH_DSL['default']['index_prefix'] = 'test_'


CACHES = {

    'default': {

        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',

    }

}


REST_FRAMEWORK = {

    **REST_FRAMEWORK,

    'DEFAULT_THROTTLE_RATES': {

        'anon': '10000/hour',

        'user': '10000/hour',

        'login': '10000/minute',

    },

}


LOGGING = {

    'version': 1,

    'disable_existing_loggers': False,

    'handlers': {

        'console': {

            'class': 'logging.StreamHandler',

            'level': 'WARNING',

        },

    },

    'root': {

        'handlers': ['console'],

        'level': 'WARNING',

    },

    'loggers': {

        'django.db.backends': {

            'level': 'WARNING',

        },

        'elasticsearch': {

            'level': 'WARNING',

        },

        'opensearch': {

            'level': 'WARNING',

        },

        'httpx': {

            'level': 'WARNING',

        },

    },

}


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




print("=" * 80)

print("E2E TEST SETTINGS LOADED")

print("=" * 80)

print(f"Database: {DATABASES['default']['ENGINE']} @ {DATABASES['default']['HOST']}")

print(f"Password Hasher: {PASSWORD_HASHERS[0]} (FAST - Test Only)")

print(f"Email Backend: {EMAIL_BACKEND}")

print(f"Celery Eager: {CELERY_TASK_ALWAYS_EAGER}")

print(f"OpenSearch Auto-sync: {OPENSEARCH_DSL_AUTOSYNC}")

print("=" * 80)
