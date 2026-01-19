"""Storage backends for CDN-backed static/media files."""
from storages.backends.s3boto3 import S3Boto3Storage


class StaticStorage(S3Boto3Storage):
    """Static files with long cache headers and gzip."""
    location = 'static'
    default_acl = 'public-read'
    file_overwrite = False

    object_parameters = {
        'CacheControl': 'max-age=31536000, public, immutable',
    }

    gzip = True
    gzip_content_types = (
        'text/css',
        'text/javascript',
        'application/javascript',
        'application/json',
        'image/svg+xml',
    )


class MediaStorage(S3Boto3Storage):
    """User uploads with moderate caching."""
    location = 'media'
    default_acl = 'public-read'
    file_overwrite = False

    object_parameters = {
        'CacheControl': 'max-age=86400, public',
    }


class PrivateMediaStorage(S3Boto3Storage):
    """Private media stored in S3 with signed URLs."""
    location = 'media/private'
    default_acl = 'private'
    file_overwrite = False

    object_parameters = {
        'CacheControl': 'no-cache, no-store, must-revalidate',
    }

    querystring_expire = 3600
