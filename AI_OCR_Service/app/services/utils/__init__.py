"""
Utils Services Package

Provides utility services:
- Medicine Response Formatter (format medicine info for display)

Example:
    >>> from app.services.utils import medicine_response_formatter
    >>> formatted = medicine_response_formatter.format_medicine(medicine)
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.services.utils import medicine_response_formatter  # type: ignore

# Public API
__all__ = [
    "medicine_response_formatter",
]


def __getattr__(name: str) -> Any:
    """
    Lazy attribute accessor for utils services.
    """
    lazy_exports = {
        "medicine_response_formatter": "app.services.utils.medicine_response_formatter",
    }
    
    if name in lazy_exports:
        module_path = lazy_exports[name]
        import importlib
        return importlib.import_module(module_path)
    
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")