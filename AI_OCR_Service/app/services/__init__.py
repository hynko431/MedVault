"""
Services Package

This package contains all business logic services organized by domain:
- ocr/ - OCR services (Gemini, Google Vision, PaddleOCR, etc.)
- chat/ - Chat and LLM services (Claude, RAG, etc.)
- search/ - Search services (Elasticsearch, embeddings, reranking)
- utils/ - Utility services (formatters, etc.)

Example:
    >>> from app.services.ocr import vision_ocr
    >>> from app.services.chat import claude_chat
    >>> from app.services.search import search_indexer
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.services.ocr import vision_ocr, gemini_ocr, google_vision_ocr, paddle_ocr, hf_paddle_ocr, ocr_integration, ocr_cleaner, image_downloader
    from app.services.chat import claude_chat, claude_chat_rag, claude_extractor, enhanced_medicine_chat
    from app.services.chat import models as chat_models
    from app.services.search import search_indexer, embeddings, intent_classifier, reranker, learning_to_rank
    from app.services.utils import medicine_response_formatter

# Package metadata
__version__ = "1.0.0"


def __getattr__(name: str) -> Any:
    """
    Lazy attribute accessor for services.
    """
    lazy_exports = {
        # OCR services
        "vision_ocr": "app.services.ocr.vision_ocr",
        "gemini_ocr": "app.services.ocr.gemini_ocr",
        "google_vision_ocr": "app.services.ocr.google_vision_ocr",
        "paddle_ocr": "app.services.ocr.paddle_ocr",
        "hf_paddle_ocr": "app.services.ocr.hf_paddle_ocr",
        "ocr_integration": "app.services.ocr.ocr_integration",
        "ocr_cleaner": "app.services.ocr.ocr_cleaner",
        "image_downloader": "app.services.ocr.image_downloader",
        
        # Chat services
        "claude_chat": "app.services.chat.claude_chat",
        "claude_chat_rag": "app.services.chat.claude_chat_rag",
        "claude_extractor": "app.services.chat.claude_extractor",
        "enhanced_medicine_chat": "app.services.chat.enhanced_medicine_chat",
        "chat_models": "app.services.chat.models",
        
        # Search services
        "search_indexer": "app.services.search.search_indexer",
        "embeddings": "app.services.search.embeddings",
        "intent_classifier": "app.services.search.intent_classifier",
        "reranker": "app.services.search.reranker",
        "learning_to_rank": "app.services.search.learning_to_rank",
        
        # Utils
        "medicine_response_formatter": "app.services.utils.medicine_response_formatter",
    }
    
    if name in lazy_exports:
        module_path = lazy_exports[name]
        import importlib
        return importlib.import_module(module_path)
    
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    # OCR
    "vision_ocr",
    "gemini_ocr",
    "google_vision_ocr",
    "paddle_ocr",
    "hf_paddle_ocr",
    "ocr_integration",
    "ocr_cleaner",
    "image_downloader",
    
    # Chat
    "claude_chat",
    "claude_chat_rag",
    "claude_extractor",
    "enhanced_medicine_chat",
    "chat_models",
    
    # Search
    "search_indexer",
    "embeddings",
    "intent_classifier",
    "reranker",
    "learning_to_rank",
    
    # Utils
    "medicine_response_formatter",
]