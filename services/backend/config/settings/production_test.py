from .production import *


DEBUG = False

ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'testserver']


DATABASES = {

    'default': {

        'ENGINE': 'django.db.backends.postgresql',

        'NAME': 'ecommerce',

        'USER': 'postgres',

        'PASSWORD': 'postgres123',

        'HOST': '127.0.0.1',

        'PORT': '5432',

    }

}


USE_S3 = False

ELASTICSEARCH_DSL = {

    'default': {

        'hosts': 'localhost:9200'

    },

}


SECURE_SSL_REDIRECT = True

SECURE_HSTS_SECONDS = 31536000

SECURE_HSTS_INCLUDE_SUBDOMAINS = True

SECURE_HSTS_PRELOAD = True

SESSION_COOKIE_SECURE = True

CSRF_COOKIE_SECURE = True

SECURE_CONTENT_TYPE_NOSNIFF = True

SECURE_BROWSER_XSS_FILTER = True

X_FRAME_OPTIONS = 'DENY'

