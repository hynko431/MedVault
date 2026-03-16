"""
AI OCR Service Application Package.

This package contains the core application components including:
- API endpoints (OCR, Chat, Search)
- Service layer (OCR extraction, AI processing, search indexing)
- Core utilities (config, logging, schemas)
- Models and data schemas

Structure:
    app/
    ├── api/          # FastAPI routers
    ├── core/         # Config, logging, utilities
    ├── models/       # Pydantic schemas
    └── services/     # Business logic and integrations

Example:
    >>> from app import create_app, get_settings
    >>> from app.models.schemas import OCRRequest, OCRResponse
    >>> from app.services.ocr.vision_ocr import extract_text_with_fallback
"""

from typing import TYPE_CHECKING, Optional, Any

if TYPE_CHECKING:
    from fastapi import FastAPI
    from app.core.config.config import Settings

# Package metadata
__version__ = "1.0.0"
__app_name__ = "AI OCR & Search Service"

# Lazy-loaded singletons
_settings_instance: Optional["Settings"] = None
_app_instance: Optional["FastAPI"] = None


def get_settings() -> "Settings":
    """
    Get application settings singleton.
    
    Returns:
        Settings: Application configuration object
        
    Example:
        >>> from app import get_settings
        >>> settings = get_settings()
        >>> print(settings.GEMINI_MODEL)
    """
    global _settings_instance
    if _settings_instance is None:
        from app.core.config.config import settings
        _settings_instance = settings
    return _settings_instance


def create_app() -> "FastAPI":
    """
    Create and configure FastAPI application.
    
    Returns:
        FastAPI: Configured application instance
        
    Example:
        >>> from app import create_app
        >>> app = create_app()
    """
    global _app_instance
    if _app_instance is None:
        from app.main import app
        _app_instance = app
    return _app_instance


def get_logger(name: str) -> Any:
    """
    Get a configured logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger: Configured logger instance
        
    Example:
        >>> from app import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("Application started")
    """
    from app.core.logging.logger import get_logger as _get_logger
    return _get_logger(name)


# Public API exports - these are safe to import without heavy dependencies
__all__ = [
    # Metadata
    "__version__",
    "__app_name__",
    
    # Core utilities
    "get_settings",
    "create_app",
    "get_logger",
]

# Optional: Pre-import commonly used items for IDE autocomplete
# These are imported lazily to avoid circular dependencies
__lazy_exports__ = {
    "OCRRequest": "app.models.schemas",
    "OCRResponse": "app.models.schemas",
    "DynamicPrescriptionExtracted": "app.models.schemas",
    "settings": "app.core.config",
}


def __getattr__(name: str) -> Any:
    """
    Lazy attribute accessor for optional heavy imports.
    
    This allows importing heavy modules only when accessed,
    improving startup time.
    """
    if name in __lazy_exports__:
        module_path = __lazy_exports__[name]
        import importlib
        module = importlib.import_module(module_path)
        return getattr(module, name)
    
    # Fall back to normal attribute error
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


# Convenience: Add lazy exports to __all__ for documentation
__all__.extend(__lazy_exports__.keys())
