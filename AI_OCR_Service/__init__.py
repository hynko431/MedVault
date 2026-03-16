"""
AI OCR Service - A comprehensive medical prescription OCR and search service.

This package provides OCR extraction, structured data extraction, search indexing,
and intelligent chat capabilities for medical prescriptions.

Features:
- Multi-tier OCR fallback (Gemini → Google Vision → PaddleOCR)
- AI-powered structured data extraction with multiple provider fallback
- Elasticsearch search with fuzzy matching and autocomplete
- Intelligent medicine chat with RAG integration
- Dynamic schema prescription extraction

Example:
    >>> from AI_OCR_Service import create_app
    >>> app = create_app()
    >>> # Or run directly
    >>> from AI_OCR_Service.app.main import app

Version: 0.3
"""

__version__ = "0.3"
__author__ = "MedVault Team"
__description__ = "AI OCR & Search Service for Medical Prescriptions"

__all__ = [
    "__version__",
    "__author__",
    "__description__",
    "create_app",
    "get_version",
]

# Package-level imports for convenience
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI

# Lazy import to avoid heavy module loading at package import
_app_instance: "FastAPI | None" = None


def create_app() -> "FastAPI":
    """
    Factory function to create and configure the FastAPI application.
    
    This allows for proper application factory pattern usage and testing.
    
    Returns:
        FastAPI: Configured FastAPI application instance
        
    Example:
        >>> from AI_OCR_Service import create_app
        >>> app = create_app()
        >>> # Now you can use the app for testing or custom server setup
    """
    global _app_instance
    if _app_instance is None:
        from AI_OCR_Service.app.main import app
        _app_instance = app
    
    if _app_instance is None:
        from fastapi import FastAPI
        return FastAPI()
        
    return _app_instance


def get_version() -> str:
    """Get the current package version."""
    return __version__