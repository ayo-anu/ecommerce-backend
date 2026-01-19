"""Secure file upload validation."""

import os
import magic
import hashlib
import logging
from typing import List, Optional, Set
from pathlib import Path
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from PIL import Image

logger = logging.getLogger(__name__)


class FileValidator:
    """Upload validation with content checks and limits."""

    MAX_SIZES = {
        'image': 10,  # 10 MB
        'document': 20,  # 20 MB
        'video': 500,  # 500 MB
        'default': 5,  # 5 MB
    }

    ALLOWED_TYPES = {
        'image': {
            'image/jpeg',
            'image/png',
            'image/gif',
            'image/webp',
            'image/svg+xml',
        },
        'document': {
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'text/plain',
            'text/csv',
        },
        'video': {
            'video/mp4',
            'video/mpeg',
            'video/quicktime',
            'video/x-msvideo',
            'video/webm',
        },
    }

    BLOCKED_EXTENSIONS = {
        'exe', 'bat', 'cmd', 'com', 'pif', 'scr', 'vbs', 'js',
        'jar', 'msi', 'dll', 'so', 'dylib', 'sh', 'bash', 'php',
        'py', 'rb', 'pl', 'asp', 'aspx', 'jsp', 'cgi',
    }

    MALWARE_SIGNATURES = [
        b'X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!',  # EICAR test
        b'MZ',  # PE executable header (position 0)
        b'ELF',  # ELF executable header
    ]

    def __init__(
        self,
        max_size_mb: Optional[int] = None,
        allowed_types: Optional[List[str]] = None,
        allowed_extensions: Optional[Set[str]] = None,
    ):
        self.max_size_mb = max_size_mb or self.MAX_SIZES['default']
        self.allowed_type_categories = allowed_types or ['image']
        self.allowed_extensions = allowed_extensions

        self.allowed_mime_types = set()
        for category in self.allowed_type_categories:
            self.allowed_mime_types.update(self.ALLOWED_TYPES.get(category, set()))

    def validate(self, uploaded_file: UploadedFile) -> dict:
        safe_filename = self._validate_filename(uploaded_file.name)

        self._validate_size(uploaded_file.size)

        extension = self._validate_extension(safe_filename)

        mime_type = self._validate_content_type(uploaded_file)

        self._check_malware(uploaded_file)

        if any(cat == 'image' for cat in self.allowed_type_categories):
            self._validate_image(uploaded_file, mime_type)

        file_hash = self._calculate_hash(uploaded_file)

        logger.info(
            f"File validated successfully",
            extra={
                'filename': safe_filename,
                'size': uploaded_file.size,
                'mime_type': mime_type,
                'hash': file_hash,
            }
        )

        return {
            'safe_filename': safe_filename,
            'extension': extension,
            'mime_type': mime_type,
            'size': uploaded_file.size,
            'hash': file_hash,
        }

    def _validate_filename(self, filename: str) -> str:
        """Sanitize and validate filename."""
        if not filename:
            raise ValidationError("Filename cannot be empty")

        filename = os.path.basename(filename)

        if '\x00' in filename:
            raise ValidationError("Invalid characters in filename")

        if '..' in filename or filename.startswith('/') or filename.startswith('\\'):
            raise ValidationError("Path traversal detected in filename")

        safe_filename = ''.join(char for char in filename if ord(char) >= 32)

        if len(safe_filename) > 255:
            name, ext = os.path.splitext(safe_filename)
            safe_filename = name[:250] + ext

        return safe_filename

    def _validate_size(self, size: int) -> None:
        """Validate file size."""
        max_size_bytes = self.max_size_mb * 1024 * 1024

        if size == 0:
            raise ValidationError("File is empty")

        if size > max_size_bytes:
            raise ValidationError(
                f"File too large. Maximum size: {self.max_size_mb}MB, "
                f"uploaded: {size / (1024 * 1024):.2f}MB"
            )

    def _validate_extension(self, filename: str) -> str:
        """Validate file extension."""
        extension = Path(filename).suffix.lower().lstrip('.')

        if not extension:
            raise ValidationError("File must have an extension")

        # Check against blocked extensions
        if extension in self.BLOCKED_EXTENSIONS:
            raise ValidationError(f"File type '.{extension}' is not allowed for security reasons")

        # If explicit allowed extensions provided, check against that
        if self.allowed_extensions and extension not in self.allowed_extensions:
            raise ValidationError(
                f"File extension '.{extension}' not allowed. "
                f"Allowed: {', '.join(self.allowed_extensions)}"
            )

        return extension

    def _validate_content_type(self, uploaded_file: UploadedFile) -> str:
        """Validate file content using magic bytes."""
        uploaded_file.seek(0)
        file_head = uploaded_file.read(8192)
        uploaded_file.seek(0)

        mime = magic.Magic(mime=True)
        detected_mime_type = mime.from_buffer(file_head)

        if detected_mime_type not in self.allowed_mime_types:
            raise ValidationError(
                f"File type '{detected_mime_type}' not allowed. "
                f"Allowed types: {', '.join(sorted(self.allowed_mime_types))}"
            )

        return detected_mime_type

    def _check_malware(self, uploaded_file: UploadedFile) -> None:
        """Basic malware signature detection."""
        uploaded_file.seek(0)
        file_content = uploaded_file.read()
        uploaded_file.seek(0)

        for signature in self.MALWARE_SIGNATURES:
            if signature in file_content[:1024]:  # Check first 1KB
                logger.warning(
                    f"Malware signature detected in upload",
                    extra={
                        'filename': uploaded_file.name,
                        'signature': signature[:20],
                    }
                )
                raise ValidationError("File failed security scan")

    def _validate_image(self, uploaded_file: UploadedFile, mime_type: str) -> None:
        """Validate images for bombs and suspicious content."""
        if not mime_type.startswith('image/'):
            return

        try:
            uploaded_file.seek(0)
            image = Image.open(uploaded_file)

            image.verify()

            if image.width * image.height > 100_000_000:  # 100 megapixels
                raise ValidationError("Image dimensions too large")

            uploaded_file.seek(0)
            image = Image.open(uploaded_file)

            if image.mode not in ['RGB', 'RGBA', 'L', 'P']:
                logger.warning(f"Unusual image mode: {image.mode}")

            uploaded_file.seek(0)
            file_content = uploaded_file.read()

            if b'MZ' in file_content[100:] or b'ELF' in file_content[100:]:
                raise ValidationError("Suspicious content detected in image")

        except Image.DecompressionBombError:
            raise ValidationError("Image is too large (potential decompression bomb)")
        except Exception as e:
            logger.error(f"Image validation failed: {e}")
            raise ValidationError(f"Invalid image file: {str(e)}")
        finally:
            uploaded_file.seek(0)

    def _calculate_hash(self, uploaded_file: UploadedFile) -> str:
        """Calculate SHA-256 hash of file for deduplication."""
        uploaded_file.seek(0)
        file_hash = hashlib.sha256()

        for chunk in uploaded_file.chunks(chunk_size=8192):
            file_hash.update(chunk)

        uploaded_file.seek(0)
        return file_hash.hexdigest()


def validate_uploaded_file(
    uploaded_file: UploadedFile,
    max_size_mb: int = 10,
    allowed_types: List[str] = None,
) -> dict:
    """Validate an uploaded file."""
    validator = FileValidator(
        max_size_mb=max_size_mb,
        allowed_types=allowed_types or ['image'],
    )
    return validator.validate(uploaded_file)
