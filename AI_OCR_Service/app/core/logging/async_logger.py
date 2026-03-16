"""
Asynchronous logging implementation to prevent I/O blocking.
Uses Loguru for high-performance, non-blocking log operations.
"""
import asyncio
import functools
import time
import inspect
from typing import Any, Optional

from app.core.config.config import settings
from app.core.logging.logger import get_logger as get_loguru_logger

# Use unified Loguru logger
def get_async_logger(name: str):
    """
    Get an async-capable logger instance (Loguru).
    """
    return get_loguru_logger(name)

# Keep backward compatibility with existing code
def get_logger(name: str):
    """
    Alias for get_async_logger.
    """
    return get_async_logger(name)


class PerformanceLogger:
    """
    Context manager for logging function execution time.
    """
    
    def __init__(self, operation_name: str, logger: Optional[Any] = None):
        self.operation_name = operation_name
        self.logger = logger or get_async_logger("performance")
        self.start_time: Optional[float] = None
    
    async def __aenter__(self) -> "PerformanceLogger":
        self.start_time = time.time()
        self.logger.info(f"⏱️  Starting: {self.operation_name}")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        _start: float = self.start_time if self.start_time is not None else time.time()
        duration_ms = (time.time() - _start) * 1000
        if exc_type is not None:
            self.logger.error(f"❌ Failed: {self.operation_name} after {duration_ms:.2f}ms - {exc_val}")
        else:
            self.logger.info(f"✅ Completed: {self.operation_name} in {duration_ms:.2f}ms")
        return False
    
    def __enter__(self) -> "PerformanceLogger":
        self.start_time = time.time()
        self.logger.info(f"⏱️  Starting: {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        _start: float = self.start_time if self.start_time is not None else time.time()
        duration_ms = (time.time() - _start) * 1000
        if exc_type is not None:
            self.logger.error(f"❌ Failed: {self.operation_name} after {duration_ms:.2f}ms - {exc_val}")
        else:
            self.logger.info(f"✅ Completed: {self.operation_name} in {duration_ms:.2f}ms")
        return False


def log_performance(operation_name: str):
    """
    Decorator to log function execution time.
    """
    def decorator(func: Any) -> Any:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            logger = get_async_logger("performance")
            start = time.time()
            logger.info(f"⏱️  Starting: {operation_name}")
            try:
                result = await func(*args, **kwargs)
                duration = (time.time() - start) * 1000
                logger.info(f"✅ Completed: {operation_name} in {duration:.2f}ms")
                return result
            except Exception as e:
                duration = (time.time() - start) * 1000
                logger.error(f"❌ Failed: {operation_name} after {duration:.2f}ms - {e}")
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            logger = get_async_logger("performance")
            start = time.time()
            logger.info(f"⏱️  Starting: {operation_name}")
            try:
                result = func(*args, **kwargs)
                duration = (time.time() - start) * 1000
                logger.info(f"✅ Completed: {operation_name} in {duration:.2f}ms")
                return result
            except Exception as e:
                duration = (time.time() - start) * 1000
                logger.error(f"❌ Failed: {operation_name} after {duration:.2f}ms - {e}")
                raise
        
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator
