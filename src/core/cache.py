"""Cache management for CiteScan."""
import hashlib
import json
from typing import Any, Callable, Optional
from functools import wraps
from cachetools import TTLCache
import threading

from .config import settings
from .logging import get_logger

logger = get_logger(__name__)


class CacheManager:
    """Thread-safe cache manager using TTLCache."""

    def __init__(self):
        """Initialize cache manager."""
        self._cache: Optional[TTLCache] = None
        self._lock = threading.Lock()
        self._initialize_cache()

    def _initialize_cache(self) -> None:
        """Initialize the cache based on settings."""
        if settings.cache_enabled:
            self._cache = TTLCache(
                maxsize=settings.cache_max_size,
                ttl=settings.cache_ttl
            )
            logger.info(
                f"Cache initialized: max_size={settings.cache_max_size}, "
                f"ttl={settings.cache_ttl}s"
            )
        else:
            logger.info("Cache disabled")

    def _generate_key(self, *args, **kwargs) -> str:
        """Generate a cache key from arguments.

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Cache key as hex string
        """
        # Create a stable string representation
        key_data = {
            "args": args,
            "kwargs": sorted(kwargs.items())
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_str.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        if not settings.cache_enabled or self._cache is None:
            return None

        with self._lock:
            value = self._cache.get(key)
            if value is not None:
                logger.debug(f"Cache hit: {key}")
            return value

    def set(self, key: str, value: Any) -> None:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        if not settings.cache_enabled or self._cache is None:
            return

        with self._lock:
            self._cache[key] = value
            logger.debug(f"Cache set: {key}")

    def delete(self, key: str) -> None:
        """Delete value from cache.

        Args:
            key: Cache key
        """
        if not settings.cache_enabled or self._cache is None:
            return

        with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Cache deleted: {key}")

    def clear(self) -> None:
        """Clear all cache entries."""
        if not settings.cache_enabled or self._cache is None:
            return

        with self._lock:
            self._cache.clear()
            logger.info("Cache cleared")

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        if not settings.cache_enabled or self._cache is None:
            return {
                "enabled": False,
                "size": 0,
                "max_size": 0,
                "ttl": 0
            }

        with self._lock:
            return {
                "enabled": True,
                "size": len(self._cache),
                "max_size": self._cache.maxsize,
                "ttl": self._cache.ttl
            }

    def cached(self, key_prefix: str = "") -> Callable:
        """Decorator to cache function results.

        Args:
            key_prefix: Optional prefix for cache key

        Returns:
            Decorator function
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Generate cache key
                cache_key = f"{key_prefix}:{func.__name__}:{self._generate_key(*args, **kwargs)}"

                # Try to get from cache
                cached_value = self.get(cache_key)
                if cached_value is not None:
                    return cached_value

                # Call function and cache result
                result = func(*args, **kwargs)
                self.set(cache_key, result)
                return result

            return wrapper
        return decorator


# Global cache manager instance
cache_manager = CacheManager()
