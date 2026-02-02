"""
Unified OCR service with intelligent fallback pipeline.
Priority chain: Gemini → Google Vision → TrOCR

This module provides robust OCR extraction with automatic fallback mechanisms
to handle provider failures and ensure high availability.

Architecture:
    1. Primary (Fastest): Gemini 3.0 Flash (GEMINI_API_KEY)
       - Cloud-based, fast response
       - No credentials file needed
    
    2. Secondary (Most Accurate): Google Cloud Vision (GOOGLE_APPLICATION_CREDENTIALS)
       - Highest accuracy for medical documents
       - Requires credentials file
    
    3. Tertiary (Fallback): TrOCR (No credentials needed)
       - Local ML model, no API calls
       - Slower but reliable
    
    4. Failure: Raises UnifiedOCRError if all providers fail
"""

import os
import time
import logging
from typing import Optional
from functools import wraps

from app.core.config import settings
from app.core.logger import get_logger
from app.services.google_vision_ocr import extract_text_from_image as google_vision_extract
from app.services.google_vision_ocr import OCRError as GoogleOCRError
from app.services.gemini_ocr import extract_text_with_gemini, GeminiOCRError
from app.services.trocr_service import extract_text_with_trocr, TrOCRError

logger = get_logger("vision_ocr")

class UnifiedOCRError(Exception):
    """Raised when all OCR providers fail"""
    pass


def retry_with_backoff(max_retries: int = 2, backoff_factor: float = 2.0):
    """
    Decorator for retrying failed API calls with exponential backoff.
    
    Implements smart fast-fail strategy:
    - Configuration errors: Fail immediately
    - Timeout/network errors: Retry with backoff
    
    Args:
        max_retries: Maximum number of retry attempts
        backoff_factor: Exponential backoff multiplier (wait = 1 * backoff_factor^attempt)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception: Optional[Exception] = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    # Fast-fail on configuration errors (missing API keys, credentials, etc)
                    error_str = str(e).lower()
                    if any(config_error in error_str for config_error in 
                           ["not set", "not configured", "not found", "credentials", "api_key"]):
                        logger.error(f"Configuration error in {func.__name__}: {str(e)}. Failing fast without retry.")
                        raise
                    
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = backoff_factor ** attempt
                        logger.warning(
                            f"{func.__name__} attempt {attempt + 1}/{max_retries} failed. "
                            f"Retrying in {wait_time}s... Error: {str(e)}"
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_retries} attempts. "
                            f"Final error: {str(e)}"
                        )
            # This should never happen, but satisfies type checker
            if last_exception is None:
                raise RuntimeError(f"{func.__name__} completed without success or exception")
            raise last_exception
        return wrapper
    return decorator


@retry_with_backoff(max_retries=2)
def _try_gemini(image_bytes: bytes) -> str:
    """
    Primary OCR provider: Google Gemini 3.0 Flash.
    
    Pros: API-based (no credentials file needed), fast, reliable
    Cons: Requires GEMINI_API_KEY
    
    Characteristics:
        - Cloud-based API
        - Quick response time
        - Good accuracy for medical documents
    """
    logger.info("🤖 Attempting OCR with Gemini  Flash (Primary)...")
    try:
        text = extract_text_with_gemini(image_bytes)
        logger.info(f"✅ Gemini succeeded. Extracted {len(text)} characters.")
        return text
    except GeminiOCRError as e:
        logger.warning(f"❌ Gemini failed: {str(e)}")
        raise


@retry_with_backoff(max_retries=1)
def _try_google_vision(image_bytes: bytes) -> str:
    """
    Secondary OCR provider: Google Cloud Vision API.
    
    Pros: Most accurate for medical prescriptions
    Cons: Requires credentials file (GOOGLE_APPLICATION_CREDENTIALS)
    
    Characteristics:
        - Highest accuracy among cloud providers
        - Excellent for medical document OCR
        - Requires service account credentials
    """
    logger.info("🔍 Attempting OCR with Google Cloud Vision (Secondary)...")
    try:
        text = google_vision_extract(image_bytes)
        logger.info(f"✅ Google Vision succeeded. Extracted {len(text)} characters.")
        return text
    except GoogleOCRError as e:
        logger.warning(f"❌ Google Vision failed: {str(e)}")
        raise


@retry_with_backoff(max_retries=2)
def _try_trocr(image_bytes: bytes) -> str:
    """
    Tertiary OCR provider: TrOCR (Transformer-based OCR).
    
    Pros: No API key needed, open-source, good fallback
    Cons: Slower, requires model download on first run
    """
    logger.info("📚 Attempting OCR with TrOCR (Tertiary)...")
    try:
        text = extract_text_with_trocr(image_bytes)
        logger.info(f"✅ TrOCR succeeded. Extracted {len(text)} characters.")
        return text
    except TrOCRError as e:
        logger.warning(f"❌ TrOCR failed: {str(e)}")
        raise


def extract_text_with_fallback(image_bytes: bytes) -> str:
    """
    Extract text from image using intelligent fallback pipeline.
    
    Tries providers in this priority order:
    1. Gemini 3.0 Flash (fastest, requires GEMINI_API_KEY)
    2. Google Cloud Vision (most accurate, requires GOOGLE_APPLICATION_CREDENTIALS)
    3. TrOCR (offline fallback, no credentials needed)
    
    Each provider is retried with exponential backoff (2 attempts, 1-2s delay).
    If all providers fail, raises UnifiedOCRError with details of all failures.
    
    Args:
        image_bytes: Raw image bytes to extract text from
        
    Returns:
        Extracted text from the image
        
    Raises:
        UnifiedOCRError: When all OCR providers fail, includes details from all attempts
    
    Example:
        >>> image_bytes = open("prescription.jpg", "rb").read()
        >>> text = extract_text_with_fallback(image_bytes)
        >>> print(text)  # Extracted prescription text
    """
    errors = []
    
    # 1️⃣ Try Gemini (Primary) - Fastest, cloud-based
    try:
        return _try_gemini(image_bytes)
    except Exception as e:
        error_msg = f"Gemini: {str(e)}"
        logger.warning(error_msg)
        errors.append(error_msg)
    
    # 2️⃣ Try Google Vision (Secondary) - Most accurate
    try:
        return _try_google_vision(image_bytes)
    except Exception as e:
        error_msg = f"Google Vision: {str(e)}"
        logger.warning(error_msg)
        errors.append(error_msg)
    
    # 3️⃣ Try TrOCR (Tertiary) - Local fallback, no credentials
    try:
        return _try_trocr(image_bytes)
    except Exception as e:
        error_msg = f"TrOCR: {str(e)}"
        logger.warning(error_msg)
        errors.append(error_msg)
    
    # ❌ All providers failed
    error_details = " | ".join(errors)
    logger.error(f"🚨 All OCR providers failed: {error_details}")
    raise UnifiedOCRError(
        f"Unable to extract text from image. All OCR providers failed:\n{error_details}"
    )


# Backward compatibility: if legacy code calls extract_text_from_image,
# it now uses the fallback pipeline
def extract_text_from_image(image_bytes: bytes) -> str:
    """
    Legacy interface - now routes through fallback pipeline.
    
    This maintains backward compatibility with existing code while
    providing automatic failover to alternative OCR providers.
    """
    return extract_text_with_fallback(image_bytes)