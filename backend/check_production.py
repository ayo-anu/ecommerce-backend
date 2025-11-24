"""
Check production readiness without actually using production settings
"""
import os
import sys

# Temporarily set production-like settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

# Mock production environment
os.environ['DEBUG'] = 'False'
os.environ['ALLOWED_HOSTS'] = 'example.com,www.example.com'

if __name__ == '__main__':
    from django.core.management import execute_from_command_line
    execute_from_command_line(['manage.py', 'check', '--deploy'])