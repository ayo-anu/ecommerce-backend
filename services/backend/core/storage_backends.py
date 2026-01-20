from storages.backends.s3boto3 import S3Boto3Storage



class StaticStorage(S3Boto3Storage):

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

    location = 'media'

    default_acl = 'public-read'

    file_overwrite = False


    object_parameters = {

        'CacheControl': 'max-age=86400, public',

    }



class PrivateMediaStorage(S3Boto3Storage):

    location = 'media/private'

    default_acl = 'private'

    file_overwrite = False


    object_parameters = {

        'CacheControl': 'no-cache, no-store, must-revalidate',

    }


    querystring_expire = 3600

