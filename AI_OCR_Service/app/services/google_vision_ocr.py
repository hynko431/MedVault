import os
import logging
from google.cloud import vision
from google.api_core import exceptions as google_exceptions
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger("google_vision_ocr")

class OCRError(Exception):
    """Raised when OCR extraction fails"""
    pass


def extract_text_from_image(image_bytes: bytes, timeout: int = 5) -> str:
    """
    Extract text from image using Google Cloud Vision API.
    
    Args:
        image_bytes: Raw image bytes
        timeout: Request timeout in seconds
        
    Returns:
        Extracted text from image
        
    Raises:
        OCRError: When OCR extraction fails
    """
    try:
        # 1️⃣ Validate Credentials Path
        creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if not creds_path:
            raise OCRError(
                "GOOGLE_APPLICATION_CREDENTIALS environment variable not set. "
                "Please configure Google Cloud credentials in your .env file."
            )

        if not os.path.exists(creds_path):
            filename = os.path.basename(creds_path)
            raise OCRError(
                f"Google Cloud credential file '{filename}' not found. "
                f"Path configured: {creds_path}\n"
                f"Please ensure the credentials file exists and the path is correct in .env"
            )

        # 2️⃣ Initialize Client
        logger.debug(f"Initializing Google Vision client with credentials: {creds_path}")
        client = vision.ImageAnnotatorClient()

        image = vision.Image(content=image_bytes)
        
        logger.debug(f"Sending request to Google Vision API (timeout={timeout}s)...")
        response = client.annotate_image({
            'image': image,
            'features': [{'type_': vision.Feature.Type.TEXT_DETECTION}],
        }, timeout=timeout)

        # 3️⃣ Check for API errors
        if response.error.message:
            raise OCRError(
                f"Google Vision API error: {response.error.message}\n"
                f"Status code: {response.error.code}"
            )

        # 4️⃣ Extract text
        texts = response.text_annotations
        if not texts:
            logger.info("OCR result: No text detected in image")
            return ""

        raw_text = texts[0].description

        # Log preview of extracted text
        preview = raw_text[:500].replace("\n", "\\n")
        logger.info(f"✅ Google Vision OCR successful. Extracted {len(raw_text)} characters")
        logger.debug(f"OCR preview (first 500 chars): {preview}")

        return raw_text

    except google_exceptions.GoogleAPICallError as e:
        # Handle Google API specific errors
        raise OCRError(
            f"Google Vision API call failed: {str(e)}\n"
            f"This may indicate a quota issue or service degradation. "
            f"Please check your Google Cloud project settings."
        ) from e
    except TimeoutError as e:
        raise OCRError(f"Google Vision request timed out after {timeout}s") from e
    except OCRError:
        # Re-raise OCRError as-is
        raise
    except Exception as e:
        # Catch any other unexpected errors
        logger.error(f"Unexpected error in Google Vision OCR: {str(e)}", exc_info=True)
        raise OCRError(f"Vision OCR failed: {str(e)}") from e