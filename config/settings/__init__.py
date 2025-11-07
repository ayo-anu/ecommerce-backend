"""
Django settings module selector based on environment
"""
import os
from decouple import config

# Get environment from .env file, default to development
ENVIRONMENT = config('ENVIRONMENT', default='development')

if ENVIRONMENT == 'production':
    from .production import *
elif ENVIRONMENT == 'test':
    from .test import *
else:
    from .development import *