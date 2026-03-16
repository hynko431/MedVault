"""
Central Import Helper Module

This module provides centralized imports for commonly used components across the application.
It ensures consistent import patterns and helps avoid circular dependencies.

Usage:
    from app.core.imports import settings, get_logger, cache_manager

Available Exports:
    - Configuration: settings, get_settings
    - Logging: get_logger, get_async_logger, log_performance
    - Database: get_es_client, check_es_health, get_es
    - Storage: cache_manager, cached, get_redis_client, check_redis_health
    - Monitoring: performance_tracker, latency_collector
    - Resilience: rate_limiter, RateLimitType, RateLimitExceeded, CircuitBreaker
    - Validation: ValidationError, validate_image_url, validate_prescription_id
"""

from typing import TYPE_CHECKING

# =============================================================================
# Configuration
# =============================================================================

if TYPE_CHECKING:
    from app.core.config.config import Settings

from app.core.config.config import settings as _settings

def get_settings() -> "Settings":
    """Get application settings singleton."""
    return _settings

# Alias for compatibility
settings = _settings


# =============================================================================
# Logging
# =============================================================================

from app.core.logging.logger import get_logger as _get_logger
from app.core.logging.async_logger import get_async_logger as _get_async_logger, log_performance

def get_logger(name: str):
    """Get a configured logger instance."""
    return _get_logger(name)

def get_async_logger(name: str):
    """Get an async-capable logger instance."""
    return _get_async_logger(name)


# =============================================================================
# Database - Elasticsearch
# =============================================================================

from app.core.db.elasticsearch import (
    get_es_client,
    close_es_client,
    get_es,
    check_es_health,
)
from app.core.db.es_client import es_client_manager


# =============================================================================
# Storage - Cache
# =============================================================================

from app.core.storage.cache import (
    cache_manager,
    cached,
    get_redis_client,
    get_memory_cache,
    check_redis_health,
    close_cache_manager,
)


# =============================================================================
# Monitoring - Performance
# =============================================================================

from app.core.monitoring.performance import (
    performance_tracker,
    PerformanceTracker,
    PerformanceMetrics,
    timed,
    RateLimiter,
    CircuitBreaker,
    CircuitBreakerOpen,
)

from app.core.monitoring.telemetry import (
    latency_collector,
    SystemTelemetry,
)


# =============================================================================
# Resilience - Rate Limiter
# =============================================================================

from app.core.resilience.rate_limiter import (
    rate_limiter,
    RateLimitType,
    RateLimitExceeded,
    TokenBucket,
    RateLimiter as TokenBucketRateLimiter,
)

from app.core.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpen,
)


# =============================================================================
# Validation
# =============================================================================

from app.core.utils.validation import (
    ValidationError,
    validate_image_url,
    validate_prescription_id,
    validate_user_id,
    validate_base64_image,
    sanitize_filename,
)


# =============================================================================
# Disclaimer
# =============================================================================

from app.core.utils.disclaimer import (
    MEDICAL_DISCLAIMER,
    PRESCRIPTION_DISCLAIMER,
    MEDICINE_INFO_DISCLAIMER,
    SYMPTOM_SEARCH_DISCLAIMER,
    CHAT_DISCLAIMER,
    DisclaimerManager,
    get_medical_disclaimer,
    add_disclaimer_to_response,
)


# =============================================================================
# Convenience aliases for backward compatibility
# =============================================================================

logger = get_logger
async_logger = get_async_logger
es_client = get_es_client


__all__ = [
    # Configuration
    "settings",
    "get_settings",
    
    # Logging
    "get_logger",
    "get_async_logger",
    "log_performance",
    "logger",
    "async_logger",
    
    # Database
    "get_es_client",
    "close_es_client",
    "get_es",
    "check_es_health",
    "es_client_manager",
    
    # Storage
    "cache_manager",
    "cached",
    "get_redis_client",
    "get_memory_cache",
    "check_redis_health",
    "close_cache_manager",
    
    # Monitoring
    "performance_tracker",
    "PerformanceTracker",
    "PerformanceMetrics",
    "timed",
    "RateLimiter",
    "latency_collector",
    "SystemTelemetry",
    
    # Resilience
    "rate_limiter",
    "RateLimitType",
    "RateLimitExceeded",
    "TokenBucket",
    "CircuitBreaker",
    "CircuitBreakerOpen",
    
    # Validation
    "ValidationError",
    "validate_image_url",
    "validate_prescription_id",
    "validate_user_id",
    "validate_base64_image",
    "sanitize_filename",
    
    # Disclaimer
    "MEDICAL_DISCLAIMER",
    "PRESCRIPTION_DISCLAIMER",
    "MEDICINE_INFO_DISCLAIMER",
    "SYMPTOM_SEARCH_DISCLAIMER",
    "CHAT_DISCLAIMER",
    "DisclaimerManager",
    "get_medical_disclaimer",
    "add_disclaimer_to_response",
]
