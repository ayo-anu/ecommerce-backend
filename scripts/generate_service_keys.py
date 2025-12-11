#!/usr/bin/env python3
"""
Generate unique cryptographic keys for service-to-service authentication.

This script generates secure random keys for each microservice to prevent
cross-service token forgery.

Usage:
    python scripts/generate_service_keys.py

Output:
    Prints environment variables to copy into your .env file
"""

import secrets
import sys


def generate_key() -> str:
    """Generate a secure random key using urlsafe base64 encoding."""
    return secrets.token_urlsafe(64)


def main():
    """Generate keys for all services."""
    services = [
        ('DJANGO_BACKEND', 'Django backend application'),
        ('API_GATEWAY', 'AI Services API Gateway'),
        ('CELERY_WORKER', 'Celery background worker'),
        ('RECOMMENDATION_ENGINE', 'AI recommendation service'),
        ('SEARCH_ENGINE', 'AI search service'),
        ('PRICING_ENGINE', 'Dynamic pricing service'),
        ('CHATBOT_RAG', 'Chatbot with RAG'),
        ('FRAUD_DETECTION', 'Fraud detection service'),
        ('FORECASTING', 'Demand forecasting service'),
        ('VISUAL_RECOGNITION', 'Visual recognition service'),
    ]

    print("# ==============================================================================")
    print("# SERVICE-TO-SERVICE AUTHENTICATION KEYS")
    print("# ==============================================================================")
    print("# CRITICAL: Each service MUST have a unique signing key.")
    print("# These keys are used to sign and verify JWT tokens for inter-service auth.")
    print("# DO NOT reuse Django SECRET_KEY or share keys between services.")
    print("#")
    print("# Generated with: python scripts/generate_service_keys.py")
    print("# ==============================================================================\n")

    for service_name, description in services:
        key = generate_key()
        print(f"# {description}")
        print(f"SERVICE_AUTH_SECRET_{service_name}={key}\n")

    print("\n# ==============================================================================")
    print("# KEY ROTATION (Optional)")
    print("# ==============================================================================")
    print("# For key rotation, generate additional keys with _V2, _V3 suffixes:")
    print("# SERVICE_AUTH_SECRET_DJANGO_BACKEND_V2=<new_key>")
    print("#")
    print("# Then specify kid parameter when generating tokens:")
    print("# token = ServiceTokenManager.generate_token(")
    print("#     service_name='django-backend',")
    print("#     scopes=['ai-services:*'],")
    print("#     kid='v2'")
    print("# )")
    print("# ==============================================================================")

    return 0


if __name__ == '__main__':
    sys.exit(main())
