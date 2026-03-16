"""
Caching layer for FastAPI application.
Provides Redis caching with fallback to in-memory caching.
"""
import functools
import hashlib
import json
import pickle
import time
import sys
import asyncio
from typing import Any, Callable, Optional, TypeVar, Union, TYPE_CHECKING, cast, overload, Awaitable
from datetime import timedelta
from types import CoroutineType

from app.core.config.config import settings
from app.core.logging.logger import get_logger

logger = get_logger(__name__)

# Try to import Redis, fall back to in-memory if not available
redis: Any = None  # type: ignore
BaseTTLCache: Any = None  # type: ignore

if TYPE_CHECKING:
    import redis.asyncio as redis_module  # type: ignore
    from cachetools import TTLCache as TTLCacheModule  # type: ignore
    redis = redis_module
    BaseTTLCache = TTLCacheModule
    REDIS_AVAILABLE = True
else:
    try:
        import redis.asyncio as redis_module  # type: ignore
        redis = redis_module
        REDIS_AVAILABLE = True
    except ImportError:
        REDIS_AVAILABLE = False
        logger.warning("Redis not available, falling back to in-memory cache")

    try:
        from cachetools import TTLCache as TTLCacheModule  # type: ignore
        BaseTTLCache = TTLCacheModule
    except ImportError:
        pass

if BaseTTLCache is not None:
    # Use cachetools TTLCache with bounded size
    class BoundedTTLCache(BaseTTLCache):
        """TTLCache with stricter memory bounds and cleanup."""
        
        def __init__(self, maxsize: int = 1000, ttl: Union[int, float] = 300):
            super().__init__(maxsize=maxsize, ttl=ttl)
            self._access_count = 0
            self._cleanup_interval = maxsize // 10  # Cleanup every 10% of capacity
        
        def __getitem__(self, key: Any) -> Any:
            self._access_count += 1
            if self._access_count >= self._cleanup_interval:
                self._periodic_cleanup()
            return super().__getitem__(key)
        
        def _periodic_cleanup(self) -> None:
            """Remove expired entries periodically to prevent memory growth."""
            now = time.time()
            expired = [
                key for key, (expires, _) in self._Cache__data.items() 
                if expires <= now
            ]
            for key in expired:
                try:
                    del self[key]
                except KeyError:
                    pass
            self._access_count = 0
        
        def __setitem__(self, key: Any, value: Any) -> None:
            # Ensure we don't exceed maxsize by cleaning before adding
            if len(self._Cache__data) >= self.maxsize:
                self._periodic_cleanup()
            super().__setitem__(key, value)
    
    TTLCache = BoundedTTLCache
else:
    # Fallback implementation if cachetools not available
    class TTLCache:
        def __init__(self, maxsize: int = 1000, ttl: Union[int, float] = 300):
            self._cache: dict[Any, Any] = {}
            self._timestamps: dict[Any, float] = {}
            self.maxsize: int = maxsize
            self.ttl: Union[int, float] = ttl
            self._access_count = 0
            self._cleanup_interval = maxsize // 10
        
        def __contains__(self, key: Any) -> bool:
            if key in self._cache:
                if time.time() - self._timestamps.get(key, 0) < self.ttl:
                    return True
                else:
                    del self._cache[key]
                    del self._timestamps[key]
            return False
        
        def __getitem__(self, key: Any) -> Any:
            self._access_count += 1
            if self._access_count >= self._cleanup_interval:
                self._cleanup_expired()
            return self._cache[key]
        
        def __setitem__(self, key: Any, value: Any) -> None:
            # Clean up before adding if at capacity
            if len(self._cache) >= self.maxsize:
                self._cleanup_expired()
                # If still at capacity, remove oldest
                if len(self._cache) >= self.maxsize:
                    oldest_key = min(self._timestamps.keys(), key=lambda k: self._timestamps[k])
                    del self._cache[oldest_key]
                    del self._timestamps[oldest_key]
            self._cache[key] = value
            self._timestamps[key] = time.time()
        
        def _cleanup_expired(self) -> None:
            """Remove expired entries."""
            now = time.time()
            expired = [
                key for key, timestamp in list(self._timestamps.items())
                if now - timestamp >= self.ttl
            ]
            for key in expired:
                if key in self._cache:
                    del self._cache[key]
                    del self._timestamps[key]
            self._access_count = 0
        
        def __delitem__(self, key: Any) -> None:
            if key in self._cache:
                del self._cache[key]
                if key in self._timestamps:
                    del self._timestamps[key]
        
        def get(self, key: Any, default: Any = None) -> Any:
            if key in self:
                return self._cache[key]
            return default
        
        def clear(self) -> None:
            self._cache.clear()
            self._timestamps.clear()
        
        def keys(self) -> list[Any]:
            return [k for k in list(self._cache.keys()) if k in self]

T = TypeVar("T")

# Global cache instances
_redis_client: Optional[Any] = None
_memory_cache: Optional[TTLCache] = None


def get_redis_client() -> Optional[Any]:
    """Get or create Redis client."""
    global _redis_client
    
    if not REDIS_AVAILABLE or not getattr(settings, 'REDIS_ENABLED', False):
        return None
    
    if _redis_client is None:
        try:
            redis_url = getattr(settings, 'REDIS_URL', None)
            if redis_url is None:
                logger.warning("REDIS_URL not set in configuration, Redis caching disabled")
                return None
            _redis_client = redis.from_url(
                redis_url,
                encoding='utf-8',
                decode_responses=False,  # We'll handle decoding manually
                socket_connect_timeout=5,
                socket_keepalive=True,
                health_check_interval=30,
                max_connections=50,
            )
            logger.info("✅ Redis cache client initialized")
        except Exception as e:
            logger.warning(f"⚠️ Failed to connect to Redis: {e}")
            _redis_client = None
    
    return _redis_client


def get_memory_cache() -> TTLCache:
    """Get or create in-memory cache."""
    global _memory_cache
    
    if _memory_cache is None:
        # Cache up to 1000 items with 5-minute TTL
        _memory_cache = TTLCache(maxsize=1000, ttl=300)
        logger.info("✅ In-memory cache initialized")
    
    return _memory_cache


async def check_redis_health() -> bool:
    """
    Check Redis connectivity.
    
    Returns:
        bool: True if reachable, False otherwise
    """
    if not getattr(settings, 'REDIS_ENABLED', False):
        return False
        
    client = get_redis_client()
    if client is None:
        return False
        
    try:
        # For redis-py async client, ping is awaitable
        return await client.ping()
    except Exception as e:
        logger.warning(f"⚠️ Redis health check failed: {e}")
        return False


def generate_cache_key(*args, **kwargs) -> str:
    """Generate a deterministic cache key from function arguments."""
    key_data = {
        "args": args,
        "kwargs": kwargs
    }
    # Use pickle for consistent serialization, then hash
    key_string = pickle.dumps(key_data, protocol=pickle.HIGHEST_PROTOCOL)
    return hashlib.sha256(key_string).hexdigest()


def cache_result(
    ttl: Union[int, timedelta] = 300,
    key_prefix: str = "",
    skip_args: Optional[list] = None
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to cache function results.
    
    Args:
        ttl: Time-to-live in seconds or timedelta
        key_prefix: Prefix for cache key
        skip_args: Argument indices to skip when generating cache key
    
    Usage:
        @cache_result(ttl=300, key_prefix="search")
        async def search_medicines(query: str, user_id: str):
            # expensive operation
            return results
    """
    if isinstance(ttl, timedelta):
        ttl_seconds = int(ttl.total_seconds())
    else:
        ttl_seconds = ttl
    
    skip_args = skip_args or []
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            # Generate cache key (skip specified argument indices)
            filtered_args = tuple(
                arg for i, arg in enumerate(args) 
                if i not in skip_args
            )
            cache_key = f"{key_prefix}:{generate_cache_key(filtered_args, kwargs)}"
            
            # 1. Try Redis first (Primary)
            redis_client = get_redis_client()
            if redis_client:
                try:
                    cached_data = await redis_client.get(cache_key)
                    if cached_data:
                        result: T = pickle.loads(cached_data)
                        logger.debug(f"🔵 Redis cache hit: {cache_key[:16]}...")
                        return result
                except Exception as e:
                    logger.debug(f"Redis cache read error: {e}")
            
            # 2. Try in-memory cache (Secondary fallback)
            memory_cache = get_memory_cache()
            if cache_key in memory_cache:
                logger.debug(f"🟡 Memory cache hit: {cache_key[:16]}...")
                return cast(T, memory_cache[cache_key])
            
            # 3. Execute function
            raw_result = func(*args, **kwargs)
            if asyncio.iscoroutine(raw_result) or hasattr(raw_result, '__await__'):
                result: T = await cast(Awaitable[T], raw_result)
            else:
                result = cast(T, raw_result)
            
            # 4. Store in BOTH caches (Dual-write)
            try:
                # Always store in memory cache first (lightweight)
                memory_cache[cache_key] = result
                
                # Store in Redis
                if redis_client:
                    try:
                        serialized = pickle.dumps(result, protocol=pickle.HIGHEST_PROTOCOL)
                        await redis_client.setex(cache_key, ttl_seconds, serialized)
                        logger.debug(f"💾 Stored in Redis & Memory: {cache_key[:16]}...")
                    except Exception as e:
                        logger.debug(f"Redis cache write error: {e}")
                else:
                    logger.debug(f"💾 Stored in Memory only: {cache_key[:16]}...")
                
            except Exception as e:
                logger.warning(f"Failed to cache result: {e}")
            
            return result
        
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            # For synchronous functions, use memory cache only
            filtered_args = tuple(
                arg for i, arg in enumerate(args) 
                if i not in skip_args
            )
            cache_key = f"{key_prefix}:{generate_cache_key(filtered_args, kwargs)}"
            
            memory_cache = get_memory_cache()
            if cache_key in memory_cache:
                logger.debug(f"🟡 Memory cache hit: {cache_key[:16]}...")
                return cast(T, memory_cache[cache_key])
            
            # Execute function with timeout protection using concurrent.futures
            import concurrent.futures
            
            def _execute_with_timeout() -> T:
                return func(*args, **kwargs)
            
            # Get timeout from settings or use default (5 seconds)
            timeout_seconds = getattr(settings, 'CACHE_SYNC_TIMEOUT', 5)
            
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(_execute_with_timeout)
                    result: T = future.result(timeout=timeout_seconds)
            except concurrent.futures.TimeoutError:
                logger.warning(f"⏱️ Sync cache operation timed out after {timeout_seconds}s: {func.__name__}")
                # Fall back to direct execution without caching on timeout
                result = func(*args, **kwargs)
                return result
            
            memory_cache[cache_key] = result
            return result
        
        # Return appropriate wrapper based on whether function is async
        if asyncio.iscoroutinefunction(func):
            return cast(Callable[..., T], async_wrapper)
        return cast(Callable[..., T], sync_wrapper)
    
    return cast(Callable[[Callable[..., T]], Callable[..., T]], decorator)


def invalidate_cache(key_pattern: str) -> None:
    """
    Invalidate cache entries matching a pattern.
    Note: This only works with memory cache. Redis pattern deletion requires SCAN.
    """
    memory_cache = get_memory_cache()
    keys_to_delete = [k for k in memory_cache.keys() if key_pattern in k]
    for k in keys_to_delete:
        del memory_cache[k]
    logger.info(f"🗑️  Invalidated {len(keys_to_delete)} cache entries")


class CacheManager:
    """Manage caching operations with both Redis and in-memory fallback."""
    
    def __init__(self):
        self._redis = None
        self._memory = None
    
    @property
    def redis(self):
        if self._redis is None:
            self._redis = get_redis_client()
        return self._redis

    @property
    def memory(self):
        if self._memory is None:
            self._memory = get_memory_cache()
        return self._memory
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache (Redis first, then Memory)."""
        # 1. Try Redis first
        if self.redis:
            try:
                data = await self.redis.get(key)
                if data:
                    return pickle.loads(data)
            except Exception as e:
                logger.debug(f"Redis get error: {e}")
        
        # 2. Fallback to memory
        return self.memory.get(key)
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Union[int, timedelta] = 300
    ) -> bool:
        """Set value in BOTH caches."""
        if isinstance(ttl, timedelta):
            ttl = int(ttl.total_seconds())
        
        # 1. Always set in memory cache
        self.memory[key] = value
        success = True
        
        # 2. Try Redis
        if self.redis:
            try:
                serialized = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
                await self.redis.setex(key, ttl, serialized)
            except Exception as e:
                logger.debug(f"Redis set error: {e}")
                success = False
        
        return success
    
    async def delete(self, key: str) -> bool:
        """Delete value from both caches."""
        success = False
        
        if self.redis:
            try:
                await self.redis.delete(key)
                success = True
            except Exception as e:
                logger.debug(f"Redis delete error: {e}")
        
        if key in self.memory:
            del self.memory[key]
            success = True
        
        return success
    
    async def clear(self) -> bool:
        """Clear all cached values from both."""
        success = False
        
        if self.redis:
            try:
                await self.redis.flushdb()
                success = True
            except Exception as e:
                logger.debug(f"Redis clear error: {e}")
        
        self.memory.clear()
        return success


# Global cache manager instance
cache_manager = CacheManager()


def cached(ttl: int = 300, key_prefix: str = ""):
    """
    Simplified caching decorator using the cache manager.
    
    Usage:
        @cached(ttl=60, key_prefix="es_search")
        async def search_elasticsearch(query: str):
            return await es.search(query)
    """
    return cache_result(ttl=ttl, key_prefix=key_prefix)


async def close_redis_client() -> None:
    """
    Close Redis client connection.
    Should be called during application shutdown.
    """
    global _redis_client
    if _redis_client is not None:
        try:
            await _redis_client.close()
            _redis_client = None
            logger.info("✅ Redis client connection closed")
        except Exception as e:
            logger.warning(f"⚠️ Error closing Redis client: {e}")


async def close_cache_manager() -> None:
    """
    Close all cache connections.
    Should be called during application shutdown.
    """
    # Close Redis connection
    await close_redis_client()
    
    # Clear memory cache
    global _memory_cache
    if _memory_cache is not None:
        _memory_cache.clear()
        logger.info("✅ Memory cache cleared")
