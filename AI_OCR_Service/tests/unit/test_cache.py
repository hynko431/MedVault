"""
Unit tests for caching layer.

Tests cache functionality without requiring Redis or external services.
"""
import pytest
import time
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Any

from app.core.storage.cache import (
    TTLCache,
    generate_cache_key,
    cache_result,
    invalidate_cache,
    CacheManager,
    get_memory_cache,
    cache_manager,
)


class TestTTLCache:
    """Test TTLCache implementation."""

    def test_ttl_cache_basic_operations(self):
        """Test basic cache set and get operations."""
        cache = TTLCache(maxsize=100, ttl=10)
        
        cache["key1"] = "value1"
        assert "key1" in cache
        assert cache["key1"] == "value1"
    
    def test_ttl_cache_expiration(self):
        """Test that cache entries expire after TTL."""
        cache = TTLCache(maxsize=100, ttl=0.1)  # 100ms TTL
        
        cache["key1"] = "value1"
        assert "key1" in cache
        
        # Wait for expiration
        time.sleep(0.15)
        
        # Should be expired now
        assert "key1" not in cache
    
    def test_ttl_cache_maxsize(self):
        """Test that cache respects maxsize."""
        cache = TTLCache(maxsize=3, ttl=100)
        
        cache["key1"] = "value1"
        cache["key2"] = "value2"
        cache["key3"] = "value3"
        
        # All three should be present
        assert "key1" in cache
        assert "key2" in cache
        assert "key3" in cache
        
        # Add fourth item - should evict oldest
        cache["key4"] = "value4"
        
        # One of the original keys should be evicted
        present_count = sum(1 for k in ["key1", "key2", "key3", "key4"] if k in cache)
        assert present_count == 3
    
    def test_ttl_cache_delete(self):
        """Test cache deletion."""
        cache = TTLCache(maxsize=100, ttl=100)
        
        cache["key1"] = "value1"
        assert "key1" in cache
        
        del cache["key1"]
        assert "key1" not in cache
    
    def test_ttl_cache_get_with_default(self):
        """Test get method with default value."""
        cache = TTLCache(maxsize=100, ttl=100)
        
        # Should return default for missing key
        result = cache.get("missing_key", "default_value")
        assert result == "default_value"
        
        # Should return actual value for existing key
        cache["existing_key"] = "actual_value"
        result = cache.get("existing_key", "default_value")
        assert result == "actual_value"
    
    def test_ttl_cache_clear(self):
        """Test cache clear operation."""
        cache = TTLCache(maxsize=100, ttl=100)
        
        cache["key1"] = "value1"
        cache["key2"] = "value2"
        
        cache.clear()
        
        assert "key1" not in cache
        assert "key2" not in cache
        assert len(cache.keys()) == 0


class TestCacheKeyGeneration:
    """Test cache key generation."""

    def test_generate_cache_key_basic(self):
        """Test basic key generation."""
        key1 = generate_cache_key("arg1", "arg2")
        key2 = generate_cache_key("arg1", "arg2")
        
        # Same arguments should produce same key
        assert key1 == key2
        assert isinstance(key1, str)
        assert len(key1) == 64  # SHA256 hex digest
    
    def test_generate_cache_key_different_args(self):
        """Test that different arguments produce different keys."""
        key1 = generate_cache_key("arg1")
        key2 = generate_cache_key("arg2")
        
        assert key1 != key2
    
    def test_generate_cache_key_with_kwargs(self):
        """Test key generation with keyword arguments."""
        key1 = generate_cache_key("arg1", kwarg1="value1")
        key2 = generate_cache_key("arg1", kwarg1="value1")
        
        assert key1 == key2
    
    def test_generate_cache_key_complex_types(self):
        """Test key generation with complex types."""
        key1 = generate_cache_key([1, 2, 3], {"a": "b"})
        key2 = generate_cache_key([1, 2, 3], {"a": "b"})
        
        assert key1 == key2


class TestCacheResultDecorator:
    """Test cache_result decorator."""

    def test_sync_function_caching(self):
        """Test that sync functions are cached."""
        call_count = 0
        
        @cache_result(ttl=60, key_prefix="test")
        def test_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2
        
        # First call should execute function
        result1 = test_function(5)
        assert result1 == 10
        assert call_count == 1
        
        # Second call should use cache
        result2 = test_function(5)
        assert result2 == 10
        assert call_count == 1  # Function not called again
    
    def test_sync_function_different_args(self):
        """Test caching with different arguments."""
        call_count = 0
        
        @cache_result(ttl=60, key_prefix="test")
        def test_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2
        
        result1 = test_function(5)
        result2 = test_function(10)
        
        assert result1 == 10
        assert result2 == 20
        assert call_count == 2
    
    def test_cache_skip_args(self):
        """Test that skip_args parameter works."""
        call_count = 0
        
        @cache_result(ttl=60, key_prefix="test", skip_args=[1])
        def test_function(x: int, y: int) -> int:
            nonlocal call_count
            call_count += 1
            return x + y
        
        # These should share cache (y is skipped)
        result1 = test_function(5, 10)
        result2 = test_function(5, 20)
        
        assert result1 == 15
        # Should use cached value even though y is different
        assert call_count == 1
    
    def test_cache_invalidation(self):
        """Test cache invalidation."""
        call_count = 0
        
        @cache_result(ttl=60, key_prefix="invalidate_test")
        def test_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2
        
        test_function(5)
        assert call_count == 1
        
        # Invalidate cache
        invalidate_cache("invalidate_test")
        
        # Should execute function again
        test_function(5)
        assert call_count == 2


class TestCacheManager:
    """Test CacheManager class."""

    @pytest.mark.asyncio
    async def test_cache_manager_get_missing_key(self):
        """Test getting missing key returns None."""
        # Clear memory cache first
        get_memory_cache().clear()
        
        result = await cache_manager.get("nonexistent_key")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_cache_manager_set_and_get(self):
        """Test setting and getting values."""
        # Clear cache
        get_memory_cache().clear()
        
        await cache_manager.set("test_key", "test_value", ttl=60)
        
        result = await cache_manager.get("test_key")
        assert result == "test_value"
    
    @pytest.mark.asyncio
    async def test_cache_manager_delete(self):
        """Test deleting cache entries."""
        # Clear cache
        get_memory_cache().clear()
        
        await cache_manager.set("delete_key", "delete_value", ttl=60)
        assert await cache_manager.get("delete_key") == "delete_value"
        
        await cache_manager.delete("delete_key")
        assert await cache_manager.get("delete_key") is None
    
    @pytest.mark.asyncio
    async def test_cache_manager_clear(self):
        """Test clearing all cache entries."""
        # Clear cache
        get_memory_cache().clear()
        
        await cache_manager.set("key1", "value1", ttl=60)
        await cache_manager.set("key2", "value2", ttl=60)
        
        await cache_manager.clear()
        
        assert await cache_manager.get("key1") is None
        assert await cache_manager.get("key2") is None


class TestAsyncCaching:
    """Test async function caching."""

    @pytest.mark.asyncio
    async def test_async_function_caching(self):
        """Test that async functions are cached."""
        call_count = 0
        
        @cache_result(ttl=60, key_prefix="async_test")
        async def async_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.001)  # Simulate async work
            return x * 2
        
        # First call should execute function
        result1 = await async_function(5)
        assert result1 == 10
        assert call_count == 1
        
        # Second call should use cache
        result2 = await async_function(5)
        assert result2 == 10
        assert call_count == 1  # Function not called again


if __name__ == "__main__":
    pytest.main([__file__, "-v"])