"""
Thread-safe Circuit Breaker implementation for production use.

Provides asyncio-based circuit breaker pattern to prevent cascading failures
in distributed systems.
"""

import asyncio
import time
import logging
from typing import Optional, Type, Any
from contextlib import asynccontextmanager
from functools import wraps

logger = logging.getLogger(__name__)


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open."""
    pass


class CircuitBreaker:
    """
    Thread-safe circuit breaker implementation for async operations.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Failing fast, requests are rejected immediately
    - HALF_OPEN: Testing if service has recovered
    
    Attributes:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds to wait before attempting recovery
        expected_exception: Exception type that triggers failure counting
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception,
        name: str = "default"
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.name = name
        
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._state = "CLOSED"
        self._lock = asyncio.Lock()
        
        logger.debug(f"Circuit breaker '{name}' initialized (threshold={failure_threshold}, timeout={recovery_timeout}s)")
    
    @property
    def state(self) -> str:
        """Get current circuit state."""
        return self._state
    
    @property
    def failure_count(self) -> int:
        """Get current failure count."""
        return self._failure_count
    
    async def can_execute(self) -> bool:
        """
        Check if execution is allowed.
        
        Returns:
            True if circuit allows execution, False if open
        
        Raises:
            CircuitBreakerOpen: If circuit is open and recovery timeout hasn't passed
        """
        async with self._lock:
            if self._state == "CLOSED":
                return True
            
            if self._state == "OPEN":
                if self._last_failure_time and \
                   (time.time() - self._last_failure_time) >= self.recovery_timeout:
                    self._state = "HALF_OPEN"
                    logger.info(f"Circuit breaker '{self.name}' entering HALF_OPEN state")
                    return True
                logger.warning(f"Circuit breaker '{self.name}' is OPEN - rejecting request")
                return False
            
            return True  # HALF_OPEN - allow one test request
    
    async def record_success(self) -> None:
        """Record a successful execution."""
        async with self._lock:
            if self._state == "HALF_OPEN":
                logger.info(f"Circuit breaker '{self.name}' closing - service recovered")
            self._failure_count = 0
            self._state = "CLOSED"
    
    async def record_failure(self) -> None:
        """Record a failed execution."""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            if self._failure_count >= self.failure_threshold:
                if self._state != "OPEN":
                    logger.warning(
                        f"Circuit breaker '{self.name}' OPENED after "
                        f"{self._failure_count} failures"
                    )
                self._state = "OPEN"
    
    @asynccontextmanager
    async def __call__(self):
        """
        Context manager for circuit breaker.
        
        Usage:
            async with circuit_breaker():
                # Your code here
                pass
        """
        if not await self.can_execute():
            raise CircuitBreakerOpen(f"Circuit breaker '{self.name}' is open")
        
        try:
            yield self
            await self.record_success()
        except self.expected_exception:
            await self.record_failure()
            raise
    
    def __repr__(self) -> str:
        return (
            f"CircuitBreaker(name='{self.name}', state='{self._state}', "
            f"failures={self._failure_count}/{self.failure_threshold})"
        )


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers."""
    
    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()
    
    async def get_or_create(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception
    ) -> CircuitBreaker:
        """Get existing circuit breaker or create new one."""
        async with self._lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(
                    failure_threshold=failure_threshold,
                    recovery_timeout=recovery_timeout,
                    expected_exception=expected_exception,
                    name=name
                )
            return self._breakers[name]
    
    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name."""
        return self._breakers.get(name)
    
    async def reset(self, name: str) -> bool:
        """Reset a circuit breaker to closed state."""
        async with self._lock:
            if name in self._breakers:
                breaker = self._breakers[name]
                async with breaker._lock:
                    breaker._failure_count = 0
                    breaker._state = "CLOSED"
                    breaker._last_failure_time = None
                logger.info(f"Circuit breaker '{name}' manually reset")
                return True
            return False
    
    async def reset_all(self) -> None:
        """Reset all circuit breakers."""
        async with self._lock:
            for name, breaker in self._breakers.items():
                async with breaker._lock:
                    breaker._failure_count = 0
                    breaker._state = "CLOSED"
                    breaker._last_failure_time = None
            logger.info("All circuit breakers manually reset")
    
    def get_status(self) -> dict[str, dict[str, Any]]:
        """Get status of all circuit breakers."""
        return {
            name: {
                "state": breaker.state,
                "failure_count": breaker.failure_count,
                "failure_threshold": breaker.failure_threshold,
                "recovery_timeout": breaker.recovery_timeout
            }
            for name, breaker in self._breakers.items()
        }


# Global registry instance
circuit_breaker_registry = CircuitBreakerRegistry()


def with_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    expected_exception: Type[Exception] = Exception
):
    """
    Decorator to wrap async functions with circuit breaker.
    
    Usage:
        @with_circuit_breaker("my_service", failure_threshold=3)
        async def my_function():
            # Your code here
            pass
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            breaker = await circuit_breaker_registry.get_or_create(
                name=name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                expected_exception=expected_exception
            )
            
            async with breaker():
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator