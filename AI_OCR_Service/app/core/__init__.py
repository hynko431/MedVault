"""
Core package for AI OCR Service.
Provides logging, DB, monitoring, and utility sub-packages.
"""

# Lazy imports — only imported when accessed to avoid circular dependencies.
# Use relative imports so this works regardless of where the project is installed.

from __future__ import annotations

from .config.config import settings

def get_settings():
    """Get application settings."""
    return settings

from . import logging
from . import db
from . import monitoring
from . import utils
from . import config
from . import resilience
from . import storage

__all__ = [
    "settings",
    "get_settings",
    "logging",
    "db",
    "monitoring",
    "utils",
    "config",
    "resilience",
    "storage",
]