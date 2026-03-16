"""
OCR Services Package

Provides multiple OCR providers with automatic fallback:
- Gemini OCR (primary)
- Google Vision OCR (secondary)
- Hugging Face PaddleOCR (tertiary)
- Local PaddleOCR (fallback)

Example:
    >>> from app.services.ocr import vision_ocr
    >>> text = await vision_ocr.extract_text_with_fallback(image_bytes)
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.services.ocr.vision_ocr import extract_text_with_fallback  # type: ignore
    from app.services.ocr import (  # type: ignore
        vision_ocr, gemini_ocr, google_vision_ocr, paddle_ocr,
        hf_paddle_ocr, ocr_integration, ocr_cleaner, image_downloader
    )

# Public API
__all__ = [
    "vision_ocr",
    "gemini_ocr",
    "google_vision_ocr",
    "paddle_ocr",
    "hf_paddle_ocr",
    "ocr_integration",
    "ocr_cleaner",
    "image_downloader",
]


def __getattr__(name: str) -> Any:
    """
    Lazy attribute accessor for OCR services.
    """
    lazy_exports = {
        "vision_ocr": "app.services.ocr.vision_ocr",
        "gemini_ocr": "app.services.ocr.gemini_ocr",
        "google_vision_ocr": "app.services.ocr.google_vision_ocr",
        "paddle_ocr": "app.services.ocr.paddle_ocr",
        "hf_paddle_ocr": "app.services.ocr.hf_paddle_ocr",
        "ocr_integration": "app.services.ocr.ocr_integration",
        "ocr_cleaner": "app.services.ocr.ocr_cleaner",
        "image_downloader": "app.services.ocr.image_downloader",
    }
    
    if name in lazy_exports:
        module_path = lazy_exports[name]
        import importlib
        return importlib.import_module(module_path)
    
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")