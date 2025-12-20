"""
Custom storage backends for CDN integration

This module provides storage backends for serving static and media files
through a CDN. Supports both AWS CloudFront and Cloudflare CDN.

Usage:
    Set USE_CDN=true in environment variables to enable CDN serving
    Set CDN_DOMAIN to your CDN domain (e.g., d1234567890.cloudfront.net)
"""
from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage


class StaticStorage(S3Boto3Storage):
    """
    Storage backend for static files with CDN support

    This backend stores files in S3 and serves them through a CDN
    if CDN_DOMAIN is configured. Otherwise, serves directly from S3.

    Features:
    - Long-term caching (1 year) for immutable static assets
    - Gzip compression support
    - Versioned filenames for cache busting
    """
    location = 'static'
    default_acl = 'public-read'
    file_overwrite = False

    # Aggressive caching for static files (1 year)
    # Static files should have versioned/hashed names for cache busting
    object_parameters = {
        'CacheControl': 'max-age=31536000, public, immutable',
    }

    # Enable gzip compression
    gzip = True
    gzip_content_types = (
        'text/css',
        'text/javascript',
        'application/javascript',
        'application/json',
        'image/svg+xml',
    )


class MediaStorage(S3Boto3Storage):
    """
    Storage backend for user-uploaded media files with CDN support

    This backend stores user uploads in S3 and serves them through a CDN
    if CDN_DOMAIN is configured.

    Features:
    - Moderate caching (24 hours) for frequently accessed media
    - Unique filenames to prevent overwrites
    - Public read access for images/videos
    """
    location = 'media'
    default_acl = 'public-read'
    file_overwrite = False

    # Moderate caching for media files (24 hours)
    # Media files can be updated, so shorter cache time
    object_parameters = {
        'CacheControl': 'max-age=86400, public',
    }


class PrivateMediaStorage(S3Boto3Storage):
    """
    Storage backend for private/sensitive media files

    This backend stores sensitive files in S3 with private access.
    Files are served through signed URLs with expiration.

    Use cases:
    - User documents
    - Private images
    - Invoices/receipts
    """
    location = 'media/private'
    default_acl = 'private'
    file_overwrite = False

    # No caching for private files
    object_parameters = {
        'CacheControl': 'no-cache, no-store, must-revalidate',
    }

    # Signed URLs expire after 1 hour
    querystring_expire = 3600
