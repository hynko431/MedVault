"""
API Routes Package

This package contains FastAPI routers:
- ocr.py - OCR extraction endpoints
- chat.py - Chat and medicine Q&A endpoints
- search.py - Search endpoints (medicine, doctor, semantic, hybrid)
- autocomplete.py - Autocomplete suggestions

Example:
    >>> from app.api import ocr, chat, search, autocomplete
    >>> app.include_router(ocr.router, prefix="/ocr")
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fastapi import APIRouter
    from app.api import ocr, chat, search, autocomplete  # type: ignore

# Public API
__all__ = [
    "ocr",
    "chat",
    "search",
    "autocomplete",
]


def __getattr__(name: str) -> Any:
    """
    Lazy attribute accessor for API modules.
    """
    lazy_exports = {
        "ocr": "app.api.ocr",
        "chat": "app.api.chat",
        "search": "app.api.search",
        "autocomplete": "app.api.autocomplete",
    }
    
    if name in lazy_exports:
        module_path = lazy_exports[name]
        import importlib
        return importlib.import_module(module_path)
    
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")