from .development import *

import logging



PASSWORD_HASHERS = [

    'django.contrib.auth.hashers.MD5PasswordHasher',

]


EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


CELERY_TASK_ALWAYS_EAGER = True

CELERY_TASK_EAGER_PROPAGATES = True


ELASTICSEARCH_DSL_AUTOSYNC = False

ELASTICSEARCH_DSL_AUTO_REFRESH = False


if 'default' in ELASTICSEARCH_DSL:

    ELASTICSEARCH_DSL['default']['index_prefix'] = 'test_'


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

print(f"Elasticsearch Auto-sync: {ELASTICSEARCH_DSL_AUTOSYNC}")

print("=" * 80)

