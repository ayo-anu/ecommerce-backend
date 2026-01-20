from .base import *


DEBUG = True


DATABASES = {

    'default': {

        'ENGINE': 'django.db.backends.sqlite3',

        'NAME': ':memory:',

    }

}


PASSWORD_HASHERS = [

    'django.contrib.auth.hashers.MD5PasswordHasher',

]


class DisableMigrations:

    def __contains__(self, item):

        return True

    def __getitem__(self, item):

        return None


MIGRATION_MODULES = DisableMigrations()


CACHES = {

    'default': {

        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',

    }

}


EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


CELERY_TASK_ALWAYS_EAGER = True

CELERY_TASK_EAGER_PROPAGATES = True


REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {

    'anon': '10000/hour',

    'user': '10000/hour',

}

