"""
Chat Services Package

Provides chat functionality with RAG support:
- Claude Chat (legacy)
- Claude Chat RAG (with knowledge base)
- Claude Extractor (for prescription data extraction)
- Enhanced Medicine Chat (OCR + LLM integration)
- Chat Models (data models)

Example:
    >>> from app.services.chat import claude_chat_rag
    >>> result = claude_chat_rag.medicine_chat_rag("What is Paracetamol?")
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.services.chat.models import MedicineInfo, ChatContext  # type: ignore
    from app.services.chat import (  # type: ignore
        claude_chat, claude_chat_rag, claude_extractor,
        enhanced_medicine_chat, models
    )

# Public API
__all__ = [
    "claude_chat",
    "claude_chat_rag",
    "claude_extractor",
    "enhanced_medicine_chat",
    "models",
    "MedicineInfo",
    "ChatContext",
]


def __getattr__(name: str) -> Any:
    """
    Lazy attribute accessor for chat services.
    """
    lazy_exports = {
        "claude_chat": "app.services.chat.claude_chat",
        "claude_chat_rag": "app.services.chat.claude_chat_rag",
        "claude_extractor": "app.services.chat.claude_extractor",
        "enhanced_medicine_chat": "app.services.chat.enhanced_medicine_chat",
        "models": "app.services.chat.models",
        "MedicineInfo": "app.services.chat.models",
        "ChatContext": "app.services.chat.models",
    }
    
    if name in lazy_exports:
        module_path = lazy_exports[name]
        import importlib
        module = importlib.import_module(module_path)
        return getattr(module, name, module)
    
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")