"""
Secure File Upload Validation.

Provides comprehensive validation for user-uploaded files to prevent:
- Malicious file uploads
- Path traversal attacks
- Denial of service via large files
- Executable file uploads
- Image-based attacks

Usage:
    from core.file_validation import FileValidator, validate_uploaded_file

    # In your view/serializer
    validator = FileValidator(max_size_mb=5, allowed_types=['image'])
    validator.validate(uploaded_file)
"""

import os
import magic
import hashlib
import logging
from typing import List, Optional, Set
from pathlib import Path
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from PIL import Image
import io

logger = logging.getLogger(__name__)


class FileValidator:
    """
    Comprehensive file upload validator.

    Security checks performed:
    1. File size limits
    2. Content type validation (magic bytes, not just extension)
    3. Filename sanitization
    4. Image validation (if image file)
    5. Malware signature detection
    6. Path traversal prevention
    """

    # Maximum file sizes by category (in MB)
    MAX_SIZES = {
        'image': 10,  # 10 MB
        'document': 20,  # 20 MB
        'video': 500,  # 500 MB
        'default': 5,  # 5 MB
    }

    # Allowed MIME types by category
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

    # Dangerous file extensions (always blocked)
    BLOCKED_EXTENSIONS = {
        'exe', 'bat', 'cmd', 'com', 'pif', 'scr', 'vbs', 'js',
        'jar', 'msi', 'dll', 'so', 'dylib', 'sh', 'bash', 'php',
        'py', 'rb', 'pl', 'asp', 'aspx', 'jsp', 'cgi',
    }

    # Known malware signatures (simplified - use real AV in production)
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
        """
        Initialize file validator.

        Args:
            max_size_mb: Maximum file size in megabytes
            allowed_types: List of allowed file type categories ('image', 'document', 'video')
            allowed_extensions: Set of explicitly allowed file extensions
        """
        self.max_size_mb = max_size_mb or self.MAX_SIZES['default']
        self.allowed_type_categories = allowed_types or ['image']
        self.allowed_extensions = allowed_extensions

        # Build allowed MIME types from categories
        self.allowed_mime_types = set()
        for category in self.allowed_type_categories:
            self.allowed_mime_types.update(self.ALLOWED_TYPES.get(category, set()))

    def validate(self, uploaded_file: UploadedFile) -> dict:
        """
        Validate an uploaded file.

        Args:
            uploaded_file: Django UploadedFile object

        Returns:
            dict: Validation results with metadata

        Raises:
            ValidationError: If file fails validation
        """
        # 1. Validate filename
        safe_filename = self._validate_filename(uploaded_file.name)

        # 2. Validate file size
        self._validate_size(uploaded_file.size)

        # 3. Validate file extension
        extension = self._validate_extension(safe_filename)

        # 4. Validate content type (magic bytes)
        mime_type = self._validate_content_type(uploaded_file)

        # 5. Check for malware signatures
        self._check_malware(uploaded_file)

        # 6. If image, perform additional validation
        if any(cat == 'image' for cat in self.allowed_type_categories):
            self._validate_image(uploaded_file, mime_type)

        # 7. Calculate file hash for deduplication
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
        """
        Sanitize and validate filename.

        Prevents:
        - Path traversal (../, ..\)
        - Null bytes
        - Control characters
        - Extremely long names
        """
        if not filename:
            raise ValidationError("Filename cannot be empty")

        # Remove any path components
        filename = os.path.basename(filename)

        # Check for null bytes
        if '\x00' in filename:
            raise ValidationError("Invalid characters in filename")

        # Check for path traversal attempts
        if '..' in filename or filename.startswith('/') or filename.startswith('\\'):
            raise ValidationError("Path traversal detected in filename")

        # Remove control characters
        safe_filename = ''.join(char for char in filename if ord(char) >= 32)

        # Limit filename length
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
        """
        Validate actual file content type using magic bytes.

        Don't trust Content-Type header or file extension - check the actual file content.
        """
        # Read first 8KB for magic byte detection
        uploaded_file.seek(0)
        file_head = uploaded_file.read(8192)
        uploaded_file.seek(0)

        # Detect MIME type from content
        mime = magic.Magic(mime=True)
        detected_mime_type = mime.from_buffer(file_head)

        # Verify against allowed types
        if detected_mime_type not in self.allowed_mime_types:
            raise ValidationError(
                f"File type '{detected_mime_type}' not allowed. "
                f"Allowed types: {', '.join(sorted(self.allowed_mime_types))}"
            )

        return detected_mime_type

    def _check_malware(self, uploaded_file: UploadedFile) -> None:
        """
        Basic malware signature detection.

        NOTE: This is a simplified check. In production, integrate with
        real antivirus solutions like ClamAV, VirusTotal API, etc.
        """
        uploaded_file.seek(0)
        file_content = uploaded_file.read()
        uploaded_file.seek(0)

        # Check for known malware signatures
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
        """
        Perform additional validation for image files.

        Prevents:
        - Image bombs (decompression attacks)
        - Malformed images
        - Embedded executables in images
        """
        if not mime_type.startswith('image/'):
            return

        try:
            uploaded_file.seek(0)
            image = Image.open(uploaded_file)

            # Verify image
            image.verify()

            # Check for excessively large dimensions (image bombs)
            if image.width * image.height > 100_000_000:  # 100 megapixels
                raise ValidationError("Image dimensions too large")

            # Re-open after verify() (PIL closes it)
            uploaded_file.seek(0)
            image = Image.open(uploaded_file)

            # Check image mode
            if image.mode not in ['RGB', 'RGBA', 'L', 'P']:
                logger.warning(f"Unusual image mode: {image.mode}")

            # Detect hidden data in images (basic check)
            uploaded_file.seek(0)
            file_content = uploaded_file.read()

            # Check for embedded executables
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

        # Read in chunks for memory efficiency
        for chunk in uploaded_file.chunks(chunk_size=8192):
            file_hash.update(chunk)

        uploaded_file.seek(0)
        return file_hash.hexdigest()


def validate_uploaded_file(
    uploaded_file: UploadedFile,
    max_size_mb: int = 10,
    allowed_types: List[str] = None,
) -> dict:
    """
    Convenience function for file validation.

    Args:
        uploaded_file: Django UploadedFile object
        max_size_mb: Maximum file size in megabytes
        allowed_types: List of allowed type categories

    Returns:
        dict: Validation results

    Raises:
        ValidationError: If validation fails
    """
    validator = FileValidator(
        max_size_mb=max_size_mb,
        allowed_types=allowed_types or ['image'],
    )
    return validator.validate(uploaded_file)


# Example usage in Django REST Framework serializer
"""
from rest_framework import serializers
from core.file_validation import validate_uploaded_file

class ProductImageSerializer(serializers.Serializer):
    image = serializers.ImageField()

    def validate_image(self, value):
        try:
            result = validate_uploaded_file(
                value,
                max_size_mb=5,
                allowed_types=['image']
            )
            # Store hash for deduplication
            self.context['file_hash'] = result['hash']
            return value
        except ValidationError as e:
            raise serializers.ValidationError(str(e))
"""
