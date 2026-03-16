import os
import asyncio
from typing import Optional
from google.cloud import vision

from app.core.config.config import settings
from app.core.logging.logger import get_logger

logger = get_logger("google_vision_ocr")

class OCRError(Exception):
    """Custom exception for Google Vision OCR errors."""
    pass

async def extract_text_from_image(image_bytes: bytes) -> str:
    """
    Extract text from image using Google Cloud Vision API.
    """
    if not settings.GOOGLE_APPLICATION_CREDENTIALS:
        raise OCRError("GOOGLE_APPLICATION_CREDENTIALS not set")

    try:
        # Initialize client
        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=image_bytes)
        
        # Perform text detection using annotate_image which is a known method
        response = await asyncio.to_thread(
            client.annotate_image,
            {"image": {"content": image_bytes}, "features": [{"type_": vision.Feature.Type.TEXT_DETECTION}]}
        )
        
        if response.error.message:
            raise OCRError(f"API Error: {response.error.message}")
            
        texts = response.text_annotations
        if not texts:
            return ""
            
        return texts[0].description
        
    except Exception as e:
        logger.error(f"Google Vision OCR error: {e}")
        raise OCRError(f"Google Vision OCR failed: {str(e)}")
