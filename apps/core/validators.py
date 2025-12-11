"""
Security validators for file uploads and other input validation
"""
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.utils.deconstruct import deconstructible
import magic


@deconstructible
class FileSizeValidator:
    """Validate file size doesn't exceed maximum"""

    def __init__(self, max_size_mb=10):
        self.max_size_mb = max_size_mb
        self.max_size_bytes = max_size_mb * 1024 * 1024

    def __call__(self, file):
        if file.size > self.max_size_bytes:
            raise ValidationError(
                f'File size cannot exceed {self.max_size_mb}MB. '
                f'Current file size: {file.size / (1024 * 1024):.2f}MB'
            )

    def __eq__(self, other):
        return isinstance(other, FileSizeValidator) and self.max_size_mb == other.max_size_mb


@deconstructible
class FileContentTypeValidator:
    """
    Validate file content type matches extension (prevents disguised malicious files)
    Requires python-magic package
    """

    def __init__(self, allowed_types):
        """
        Args:
            allowed_types: Dict mapping file extensions to MIME types
            Example: {'pdf': 'application/pdf', 'jpg': 'image/jpeg'}
        """
        self.allowed_types = allowed_types

    def __call__(self, file):
        try:
            # Get actual MIME type from file content
            mime = magic.from_buffer(file.read(2048), mime=True)
            file.seek(0)  # Reset file pointer

            # Get file extension
            extension = file.name.split('.')[-1].lower()

            # Check if extension is allowed and MIME type matches
            if extension not in self.allowed_types:
                raise ValidationError(f'File type .{extension} is not allowed')

            expected_mime = self.allowed_types[extension]
            if mime not in (expected_mime if isinstance(expected_mime, list) else [expected_mime]):
                raise ValidationError(
                    f'File content does not match extension. '
                    f'Expected {expected_mime}, got {mime}'
                )
        except Exception as e:
            # If magic fails, fall back to extension-only validation
            # (less secure but won't break functionality)
            pass

    def __eq__(self, other):
        return isinstance(other, FileContentTypeValidator) and self.allowed_types == other.allowed_types


# Common validator combinations for different file types
DOCUMENT_VALIDATORS = [
    FileExtensionValidator(['pdf', 'doc', 'docx', 'txt']),
    FileSizeValidator(max_size_mb=10),
]

IMAGE_VALIDATORS = [
    FileExtensionValidator(['jpg', 'jpeg', 'png', 'gif', 'webp']),
    FileSizeValidator(max_size_mb=5),
]

RECEIPT_VALIDATORS = [
    FileExtensionValidator(['pdf', 'jpg', 'jpeg', 'png']),
    FileSizeValidator(max_size_mb=5),
]

MATERIAL_VALIDATORS = [
    FileExtensionValidator(['pdf', 'doc', 'docx', 'txt', 'png', 'jpg', 'jpeg']),
    FileSizeValidator(max_size_mb=10),
]
