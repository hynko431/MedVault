"""
Performance monitoring and optimization utilities.
Provides performance tracking, profiling, and optimization helpers.
"""

import functools
import time
import asyncio
import logging
import uuid
import itertools
from typing import Any, Callable, Optional, TypeVar, Dict, List, Union, cast
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.core.logging.logger import get_logger

logger = get_logger("performance")

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""
    operation_name: str
    duration_ms: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        # Fix: bypass round() stub issues by using format-based rounding
        d_ms = float(self.duration_ms)
        rounded_duration = float(f"{d_ms:.3f}")
        return {
            "operation_name": str(self.operation_name),
            "duration_ms": rounded_duration,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


class PerformanceTracker:
    """
    Track performance metrics for operations.
    Provides timing, profiling, and reporting capabilities.
    """
    
    def __init__(self, max_history: int = 1000):
        self._metrics: List[PerformanceMetrics] = []
        self._max_history = max_history
        self._active_timers: Dict[str, float] = {}
    
    @contextmanager
    def track(self, operation_name: str, **metadata):
        """
        Context manager for tracking operation performance.
        
        Usage:
            with performance_tracker.track("database_query", table="users"):
                result = db.query()
        """
        # FIX: Memory leak - use unique timer key and cleanup properly
        hex_str = str(uuid.uuid4().hex)
        timer_key = f"{operation_name}_{hex_str[:8]}"
        start_time = time.perf_counter()
        self._active_timers[timer_key] = start_time
        
        try:
            yield self
        finally:
            # Calculate duration and remove from active timers
            duration = (time.perf_counter() - start_time) * 1000
            self._active_timers.pop(timer_key, None)  # FIX: Clean up active timer
            
            metrics = PerformanceMetrics(
                operation_name=operation_name,
                duration_ms=duration,
                metadata=metadata
            )
            self._record(metrics)
    
    def cleanup_orphaned_timers(self, max_age_seconds: float = 300) -> int:
        """
        Clean up orphaned timers that are older than max_age_seconds.
        
        FIX: Prevents memory leak from abandoned timers.
        
        Args:
            max_age_seconds: Maximum age of timers to keep
            
        Returns:
            Number of orphaned timers cleaned up
        """
        now = time.time()
        orphaned = [
            key for key, start_time in list(self._active_timers.items())
            if now - start_time > max_age_seconds
        ]
        
        for key in orphaned:
            self._active_timers.pop(key, None)
            logger.warning(f"Cleaned up orphaned timer: {key}")
        
        return len(orphaned)
    
    def _record(self, metrics: PerformanceMetrics) -> None:
        """Record performance metrics."""
        self._metrics.append(metrics)
        
        # Maintain history limit
        if len(self._metrics) > self._max_history:
            slice_start = int(len(self._metrics) - self._max_history)
            new_metrics: List[PerformanceMetrics] = []
            for i in range(slice_start, len(self._metrics)):
                new_metrics.append(self._metrics[i])
            self._metrics = new_metrics
        
        # Log slow operations (> 1000ms)
        if metrics.duration_ms > 1000:
            logger.warning(
                f"Slow operation detected: {metrics.operation_name} "
                f"took {metrics.duration_ms:.2f}ms"
            )
    
    def get_metrics(
        self,
        operation_name: Optional[str] = None,
        limit: int = 100
    ) -> List[PerformanceMetrics]:
        """
        Get recorded metrics.
        
        Args:
            operation_name: Filter by operation name
            limit: Maximum number of metrics to return
        
        Returns:
            List of performance metrics
        """
        metrics = self._metrics
        
        if operation_name:
            metrics = [m for m in metrics if m.operation_name == operation_name]
        
        # Get last n metrics using a loop to avoid slicing/islice diagnostics
        start_idx = int(max(0, len(metrics) - limit))
        results: List[PerformanceMetrics] = []
        for i in range(start_idx, len(metrics)):
            m = metrics[i]
            results.append(m)
        return results
    
    def get_average_time(self, operation_name: str) -> float:
        """Get average execution time for an operation."""
        metrics = [m for m in self._metrics if m.operation_name == operation_name]
        if not metrics:
            return 0.0
        return sum(m.duration_ms for m in metrics) / len(metrics)
    
    def get_slowest_operations(self, n: int = 10) -> List[PerformanceMetrics]:
        """Get the n slowest operations."""
        sorted_metrics = sorted(self._metrics, key=lambda m: m.duration_ms, reverse=True)
        end_idx = int(min(n, len(sorted_metrics)))
        results: List[PerformanceMetrics] = []
        for i in range(0, end_idx):
            m = sorted_metrics[i]
            results.append(m)
        return results
    
    def reset(self) -> None:
        """Clear all recorded metrics."""
        self._metrics.clear()
        self._active_timers.clear()


def timed(operation_name: Optional[str] = None) -> Callable[[Any], Any]:
    """
    Decorator to time function execution.
    """
    def decorator(func: Any) -> Any:
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                name = operation_name or getattr(func, "__name__", "unknown")
                start_time = time.perf_counter()
                try:
                    return await func(*args, **kwargs)
                finally:
                    duration = (time.perf_counter() - start_time) * 1000
                    logger.debug(f"{name} took {duration:.2f}ms")
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                name = operation_name or getattr(func, "__name__", "unknown")
                start_time = time.perf_counter()
                try:
                    return func(*args, **kwargs)
                finally:
                    duration = (time.perf_counter() - start_time) * 1000
                    logger.debug(f"{name} took {duration:.2f}ms")
            return sync_wrapper
    
    return decorator


class RateLimiter:
    """
    Simple rate limiter using token bucket algorithm.
    """
    
    def __init__(
        self,
        rate: int = 100,  # requests per minute
        burst_size: int = 10  # maximum burst
    ):
        self.rate = rate
        self.burst_size = burst_size
        self.tokens: float = float(burst_size)
        self.last_update = time.time()
        self._lock: asyncio.Lock = asyncio.Lock()
    
    async def acquire(self) -> bool:
        """
        Attempt to acquire a token.
        
        Returns:
            True if token acquired, False if rate limit exceeded
        """
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_update
            
            # Add tokens based on elapsed time
            token_increment = elapsed * float(self.rate) / 60.0
            new_tokens = self.tokens + token_increment
            self.tokens = min(float(self.burst_size), new_tokens)
            self.last_update = now
            
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return True
            
            return False
            
        return False # Fallback for type checkers
    
    async def wait(self) -> None:
        """Wait until a token is available."""
        while True:
            if await self.acquire():
                return
            # Calculate wait time for next token
            wait_time = 60.0 / float(self.rate)
            await asyncio.sleep(wait_time)


# CircuitBreaker and CircuitBreakerOpen are re-exported from resilience module
# to maintain backward compatibility for existing code.
from app.core.resilience.circuit_breaker import CircuitBreaker, CircuitBreakerOpen


# Global performance tracker instance
performance_tracker = PerformanceTracker()


# Export latency_collector from telemetry module for main.py compatibility
try:
    from app.core.monitoring.telemetry import latency_collector
except ImportError:
    # Fallback for type checking
    latency_collector: Any = None


__all__ = [
    "PerformanceTracker",
    "PerformanceMetrics",
    "timed",
    "RateLimiter",
    "CircuitBreaker",
    "CircuitBreakerOpen",
    "performance_tracker",
    "latency_collector",
]