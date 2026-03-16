"""
Input validation utilities for OCR service.
Provides comprehensive validation for images, URLs, and other inputs.
"""

import base64
import binascii
import re
from typing import Tuple, Optional
from app.core.config.config import settings
from app.core.logging.logger import get_logger

logger = get_logger("validation")

# Maximum image size (10MB)
MAX_IMAGE_SIZE = 10 * 1024 * 1024

# Allowed image formats
ALLOWED_IMAGE_FORMATS = {"jpeg", "jpg", "png", "gif", "bmp", "tiff", "webp"}


class ValidationError(Exception):
    """Validation error with details."""

    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(message)


def validate_base64_image(image_base64: str) -> Tuple[bytes, str]:
    """
    Validate and decode base64 image.

    Args:
        image_base64: Base64-encoded image string

    Returns:
        Tuple of (decoded_bytes, image_format)

    Raises:
        ValidationError: If validation fails
    """
    if not image_base64:
        raise ValidationError("Image data is empty", "image")

    # Remove data URI prefix if present
    if "," in image_base64:
        image_base64 = image_base64.split(",")[1]

    # Check size before decoding (base64 is ~4/3 of binary)
    estimated_size = len(image_base64) * 0.75
    if estimated_size > MAX_IMAGE_SIZE:
        raise ValidationError(
            f"Image too large: {estimated_size / 1024 / 1024:.1f}MB. "
            f"Maximum allowed: {MAX_IMAGE_SIZE / 1024 / 1024}MB",
            "image",
        )

    # Validate base64 encoding
    try:
        image_bytes = base64.b64decode(image_base64, validate=True)
    except binascii.Error as e:
        raise ValidationError(f"Invalid base64 encoding: {str(e)}", "image")

    # Check actual size
    if len(image_bytes) > MAX_IMAGE_SIZE:
        raise ValidationError(
            f"Image too large: {len(image_bytes) / 1024 / 1024:.1f}MB. "
            f"Maximum allowed: {MAX_IMAGE_SIZE / 1024 / 1024}MB",
            "image",
        )

    # Detect image format from magic bytes
    image_format = None
    if image_bytes.startswith(b"\xff\xd8\xff"):
        image_format = "jpeg"
    elif image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        image_format = "png"
    elif image_bytes.startswith(b"GIF87a") or image_bytes.startswith(b"GIF89a"):
        image_format = "gif"
    elif image_bytes.startswith(b"BM"):
        image_format = "bmp"
    elif image_bytes.startswith(b"RIFF") and len(image_bytes) > 12 and image_bytes[8:12] == b"WEBP":
        image_format = "webp"
    elif image_bytes.startswith(b"II\x2a\x00") or image_bytes.startswith(b"MM\x00\x2a"):
        image_format = "tiff"

    if image_format not in ALLOWED_IMAGE_FORMATS:
        raise ValidationError(
            f"Unsupported image format: {image_format}. "
            f"Allowed: {', '.join(ALLOWED_IMAGE_FORMATS)}",
            "image",
        )

    return image_bytes, image_format


def validate_image_url(url: str) -> None:
    """
    Validate image URL.

    Args:
        url: Image URL to validate

    Raises:
        ValidationError: If validation fails
    """
    if not url:
        raise ValidationError("Image URL is required", "image_url")

    # Check for valid URL scheme
    allowed_schemes = {"http", "https", "gs", "s3"}
    scheme = url.split("://")[0] if "://" in url else ""

    if scheme not in allowed_schemes:
        raise ValidationError(
            f"Invalid URL scheme: {scheme}. Allowed: {', '.join(allowed_schemes)}",
            "image_url",
        )

    # Basic URL length check
    if len(url) > 2048:
        raise ValidationError("URL too long (max 2048 characters)", "image_url")

    # Basic URL format validation
    url_pattern = re.compile(
        r"^(?:http|https|gs|s3)://"  # scheme
        r"(?:[\w-]+\.)*[\w-]+"  # domain
        r"(?::\d+)?"  # optional port
        r"(?:/[^\s]*)?$",  # path
        re.IGNORECASE,
    )

    if not url_pattern.match(url):
        raise ValidationError("Invalid URL format", "image_url")


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal attacks.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Remove any path components
    filename = filename.replace("\\", "/").split("/")[-1]

    # Remove any null bytes
    filename = filename.replace("\x00", "")

    # Keep only safe characters
    filename = re.sub(r"[^\w\s.-]", "", filename)

    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
        filename = name[: 255 - len(ext) - 1] + "." + ext if ext else filename[:255]

    return filename


def validate_prescription_id(prescription_id: str) -> None:
    """
    Validate prescription ID format.

    Args:
        prescription_id: Prescription ID to validate

    Raises:
        ValidationError: If validation fails
    """
    if not prescription_id:
        raise ValidationError("Prescription ID is required", "prescription_id")

    if len(prescription_id) > 128:
        raise ValidationError("Prescription ID too long (max 128 characters)", "prescription_id")

    # Allow alphanumeric, hyphens, underscores
    if not re.match(r"^[\w-]+$", prescription_id):
        raise ValidationError(
            "Prescription ID contains invalid characters. " "Only alphanumeric, hyphens, and underscores allowed",
            "prescription_id",
        )


def validate_user_id(user_id: str) -> None:
    """
    Validate user ID format.

    Args:
        user_id: User ID to validate

    Raises:
        ValidationError: If validation fails
    """
    if not user_id:
        raise ValidationError("User ID is required", "user_id")

    if len(user_id) > 128:
        raise ValidationError("User ID too long (max 128 characters)", "user_id")