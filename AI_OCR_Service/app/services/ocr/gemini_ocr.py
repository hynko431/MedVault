import asyncio
import google.generativeai as genai
from typing import Optional
from app.core.config.config import settings
from app.core.logging.logger import get_logger

logger = get_logger("gemini_ocr")

# Valid image formats supported by Gemini API
VALID_IMAGE_FORMATS = {
    'jpeg': 'image/jpeg',
    'jpg': 'image/jpeg',
    'png': 'image/png',
    'gif': 'image/gif',
    'webp': 'image/webp',
    'bmp': 'image/bmp',
    'tiff': 'image/tiff',
}


def detect_image_format(image_bytes: bytes) -> str:
    """
    Detect image format from magic bytes.
    
    Args:
        image_bytes: Raw image bytes
        
    Returns:
        MIME type string
    """
    if not image_bytes:
        raise ValueError("Empty image bytes")
    
    # Check magic bytes for common formats
    if image_bytes.startswith(b'\xff\xd8\xff'):
        return 'image/jpeg'
    elif image_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'image/png'
    elif image_bytes.startswith(b'GIF87a') or image_bytes.startswith(b'GIF89a'):
        return 'image/gif'
    elif image_bytes.startswith(b'RIFF') and len(image_bytes) > 12:
        # Use simpler slicing for Pyre2
        chunk = image_bytes[0:4]
        if chunk == b'WEBP':
            return 'image/webp'
        return 'image/webp'
    elif image_bytes.startswith(b'BM'):
        return 'image/bmp'
    elif image_bytes.startswith(b'II\x2a\x00') or image_bytes.startswith(b'MM\x00\x2a'):
        return 'image/tiff'
    
    # Default to JPEG if unknown
    logger.warning("Unknown image format, defaulting to JPEG")
    return 'image/jpeg'


class GeminiOCRError(Exception):
    """Custom exception for Gemini OCR errors."""
    pass


async def extract_text_with_gemini(image_bytes: bytes, image_format: Optional[str] = None) -> str:
    """
    Extract text from image using Google Gemini 1.5 Flash.
    
    Args:
        image_bytes: Raw image bytes
        image_format: Optional image format hint (e.g., 'jpeg', 'png', 'gif')
    
    Returns:
        Extracted text from the image
    """
    if not settings.GEMINI_API_KEY:
        raise GeminiOCRError("GEMINI_API_KEY not set")
    
    if not image_bytes:
        raise GeminiOCRError("Empty image bytes provided")

    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(settings.GEMINI_MODEL)
        
        # Detect MIME type from image bytes or use provided format
        if image_format:
            mime_type = VALID_IMAGE_FORMATS.get(image_format.lower(), 'image/jpeg')
        else:
            mime_type = detect_image_format(image_bytes)
        
        logger.debug(f"Processing image with MIME type: {mime_type}")
        
        # Prepare content with correct MIME type
        content = [
            {"mime_type": mime_type, "data": image_bytes},
            "Extract all text from this prescription image accurately."
        ]
        
        response = await asyncio.to_thread(model.generate_content, content)
        
        if not response.text:
            raise GeminiOCRError("Gemini returned empty text")
            
        return response.text
        
    except Exception as e:
        logger.error(f"Gemini OCR error: {e}")
        raise GeminiOCRError(f"Gemini OCR failed: {str(e)}")
