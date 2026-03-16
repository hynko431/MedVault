"""
Rate limiting module for FastAPI application.
Provides token bucket rate limiting with Redis and in-memory fallback.
"""
import time
import asyncio
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

from app.core.config.config import settings
from app.core.logging.logger import get_logger

logger = get_logger("rate_limiter")


class RateLimitType(str, Enum):
    """Types of rate limits."""
    OCR = "ocr"
    CHAT = "chat"
    SEARCH = "search"
    HEALTH = "health"


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_minute: int
    burst_size: int
    window_seconds: int = 60


# Default rate limit configurations
DEFAULT_RATE_LIMITS: Dict[RateLimitType, RateLimitConfig] = {
    RateLimitType.OCR: RateLimitConfig(requests_per_minute=10, burst_size=3),
    RateLimitType.CHAT: RateLimitConfig(requests_per_minute=30, burst_size=10),
    RateLimitType.SEARCH: RateLimitConfig(requests_per_minute=100, burst_size=20),
    RateLimitType.HEALTH: RateLimitConfig(requests_per_minute=1000, burst_size=100),
}


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, limit: int, reset_time: float, retry_after: int):
        self.limit = limit
        self.reset_time = reset_time
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Retry after {retry_after} seconds.")


class TokenBucket:
    """
    Token bucket implementation for rate limiting.
    Thread-safe and async-safe.
    """
    
    def __init__(self, rate: float, capacity: float):
        """
        Initialize token bucket.
        
        Args:
            rate: Tokens added per second
            capacity: Maximum bucket capacity
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()
        self._lock = asyncio.Lock()
    
    async def acquire(self, tokens: float = 1.0) -> bool:
        """
        Try to acquire tokens from the bucket.
        
        Args:
            tokens: Number of tokens to acquire
            
        Returns:
            True if tokens acquired, False otherwise
        """
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_update
            
            # Add tokens based on elapsed time
            self.tokens = min(
                self.capacity,
                self.tokens + (elapsed * self.rate)
            )
            self.last_update = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            return False
    
    async def get_reset_time(self) -> float:
        """Get the time when bucket will be full."""
        async with self._lock:
            tokens_needed = self.capacity - self.tokens
            if tokens_needed <= 0:
                return time.time()
            return self.last_update + (tokens_needed / self.rate)


class RateLimiter:
    """
    Distributed rate limiter with Redis and in-memory fallback.
    """
    
    def __init__(self):
        self._redis_client = None
        self._memory_buckets: Dict[str, TokenBucket] = {}
        self._lock = asyncio.Lock()
    
    def _get_bucket_key(self, key: str, limit_type: RateLimitType) -> str:
        """Generate bucket key for rate limiting."""
        return f"rate_limit:{limit_type.value}:{key}"
    
    def _get_config(self, limit_type: RateLimitType) -> RateLimitConfig:
        """Get rate limit configuration."""
        # Check for environment variable overrides
        env_prefix = f"RATE_LIMIT_{limit_type.value.upper()}_"
        
        rpm = getattr(settings, f"{env_prefix}RPM", None)
        burst = getattr(settings, f"{env_prefix}BURST", None)
        
        config = DEFAULT_RATE_LIMITS[limit_type]
        
        if rpm is not None:
            config.requests_per_minute = int(rpm)
        if burst is not None:
            config.burst_size = int(burst)
        
        return config
    
    async def _get_redis_bucket(self, key: str, limit_type: RateLimitType) -> Optional[Dict[str, Any]]:
        """Get bucket state from Redis."""
        if not self._redis_client:
            try:
                from app.core.storage.cache import get_redis_client
                self._redis_client = get_redis_client()
            except Exception:
                return None
        
        if not self._redis_client:
            return None
        
        try:
            bucket_key = self._get_bucket_key(key, limit_type)
            data = await self._redis_client.hgetall(bucket_key)
            if data:
                return {
                    "tokens": float(data.get(b"tokens", 0)),
                    "last_update": float(data.get(b"last_update", 0))
                }
        except Exception as e:
            logger.debug(f"Redis rate limit check failed: {e}")
        
        return None
    
    async def _update_redis_bucket(
        self,
        key: str,
        limit_type: RateLimitType,
        tokens: float,
        last_update: float,
        ttl: int = 120
    ) -> None:
        """Update bucket state in Redis."""
        if not self._redis_client:
            return
        
        try:
            bucket_key = self._get_bucket_key(key, limit_type)
            await self._redis_client.hmset(bucket_key, {
                "tokens": str(tokens),
                "last_update": str(last_update)
            })
            await self._redis_client.expire(bucket_key, ttl)
        except Exception as e:
            logger.debug(f"Redis rate limit update failed: {e}")
    
    async def check_rate_limit(
        self,
        key: str,
        limit_type: RateLimitType = RateLimitType.OCR
    ) -> Dict[str, Any]:
        """
        Check rate limit for a key.
        
        Args:
            key: Rate limit key (user_id or IP address)
            limit_type: Type of rate limit
            
        Returns:
            Dict with limit status and headers
            
        Raises:
            RateLimitExceeded: If rate limit is exceeded
        """
        config = self._get_config(limit_type)
        bucket_key = self._get_bucket_key(key, limit_type)
        
        # Calculate rate (tokens per second)
        rate = config.requests_per_minute / 60.0
        
        # Try Redis first (distributed)
        redis_state = await self._get_redis_bucket(key, limit_type)
        
        # Get or create bucket
        async with self._lock:
            if bucket_key not in self._memory_buckets:
                # Initialize from Redis or new
                if redis_state:
                    bucket = TokenBucket(rate, config.burst_size)
                    bucket.tokens = redis_state["tokens"]
                    bucket.last_update = redis_state["last_update"]
                else:
                    bucket = TokenBucket(rate, config.burst_size)
                
                self._memory_buckets[bucket_key] = bucket
            else:
                bucket = self._memory_buckets[bucket_key]
        
        # Try to acquire token
        allowed = await bucket.acquire(1.0)
        
        # Update Redis
        await self._update_redis_bucket(
            key, limit_type, bucket.tokens, bucket.last_update
        )
        
        # Get reset time
        reset_time = await bucket.get_reset_time()
        retry_after = int(reset_time - time.time())
        
        # Build response
        result = {
            "allowed": allowed,
            "limit": config.requests_per_minute,
            "remaining": int(bucket.tokens),
            "reset_time": reset_time,
            "retry_after": max(0, retry_after),
        }
        
        if not allowed:
            raise RateLimitExceeded(
                limit=config.requests_per_minute,
                reset_time=reset_time,
                retry_after=retry_after
            )
        
        return result
    
    def get_rate_limit_headers(self, result: Dict[str, Any]) -> Dict[str, str]:
        """Get rate limit headers for HTTP response."""
        return {
            "X-RateLimit-Limit": str(result["limit"]),
            "X-RateLimit-Remaining": str(result["remaining"]),
            "X-RateLimit-Reset": str(int(result["reset_time"])),
        }


# Global rate limiter instance
rate_limiter = RateLimiter()


async def check_rate_limit(
    key: str,
    limit_type: RateLimitType = RateLimitType.OCR
) -> Dict[str, Any]:
    """
    Convenience function to check rate limit.
    
    Args:
        key: Rate limit key
        limit_type: Type of rate limit
        
    Returns:
        Rate limit status dict
        
    Raises:
        RateLimitExceeded: If rate limit exceeded
    """
    return await rate_limiter.check_rate_limit(key, limit_type)