"""
Enhanced caching system for Macro Dashboard.
Multi-level caching with memory, disk, and intelligent cache management.
"""
import asyncio
import hashlib
import pickle
import time
from typing import Any, Dict, Optional, Tuple
from pathlib import Path
import logging
import pandas as pd
from dataclasses import dataclass
from src.config.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    data: Any
    timestamp: float
    ttl: int
    access_count: int = 0
    last_accessed: float = None

    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        return time.time() - self.timestamp > self.ttl

    def access(self) -> None:
        """Update access statistics."""
        self.access_count += 1
        self.last_accessed = time.time()


class MemoryCache:
    """In-memory cache with LRU-style eviction."""

    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self.cache: Dict[str, CacheEntry] = {}
        self.access_order: list[str] = []  # For LRU tracking

    def get(self, key: str) -> Optional[Any]:
        """Get value from memory cache."""
        if key not in self.cache:
            return None

        entry = self.cache[key]
        if entry.is_expired():
            del self.cache[key]
            if key in self.access_order:
                self.access_order.remove(key)
            return None

        entry.access()
        # Update access order (move to end for LRU)
        if key in self.access_order:
            self.access_order.remove(key)
        self.access_order.append(key)

        return entry.data

    def set(self, key: str, value: Any, ttl: int) -> None:
        """Set value in memory cache."""
        # Evict if at max size
        if len(self.cache) >= self.max_size and key not in self.cache:
            self._evict_lru()

        entry = CacheEntry(data=value, timestamp=time.time(), ttl=ttl)
        self.cache[key] = entry

        if key not in self.access_order:
            self.access_order.append(key)

    def _evict_lru(self) -> None:
        """Evict least recently used item."""
        if not self.access_order:
            return

        lru_key = self.access_order.pop(0)
        if lru_key in self.cache:
            del self.cache[lru_key]

    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
        self.access_order.clear()

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_entries = len(self.cache)
        expired_entries = sum(1 for entry in self.cache.values() if entry.is_expired())

        return {
            'total_entries': total_entries,
            'expired_entries': expired_entries,
            'active_entries': total_entries - expired_entries,
            'max_size': self.max_size,
            'utilization': total_entries / self.max_size if self.max_size > 0 else 0
        }


class DiskCache:
    """Disk-based cache for persistence."""

    def __init__(self, cache_dir: str = "data/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_file(self, key: str) -> Path:
        """Get cache file path for key."""
        # Use hash for filename to avoid issues with special characters
        hashed_key = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{hashed_key}.pkl"

    def get(self, key: str) -> Optional[Any]:
        """Get value from disk cache."""
        cache_file = self._get_cache_file(key)

        if not cache_file.exists():
            return None

        try:
            with open(cache_file, 'rb') as f:
                entry: CacheEntry = pickle.load(f)

            if entry.is_expired():
                cache_file.unlink(missing_ok=True)
                return None

            return entry.data

        except Exception as e:
            logger.warning(f"Error reading cache file {cache_file}: {e}")
            cache_file.unlink(missing_ok=True)
            return None

    def set(self, key: str, entry: CacheEntry) -> None:
        """Set value in disk cache."""
        cache_file = self._get_cache_file(key)

        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(entry, f)
        except Exception as e:
            logger.warning(f"Error writing cache file {cache_file}: {e}")

    def clear(self) -> None:
        """Clear all disk cache files."""
        for cache_file in self.cache_dir.glob("*.pkl"):
            cache_file.unlink(missing_ok=True)

    def cleanup_expired(self) -> int:
        """Remove expired cache files. Returns number of files removed."""
        removed_count = 0

        for cache_file in self.cache_dir.glob("*.pkl"):
            try:
                with open(cache_file, 'rb') as f:
                    entry: CacheEntry = pickle.load(f)

                if entry.is_expired():
                    cache_file.unlink()
                    removed_count += 1

            except Exception:
                # If we can't read the file, remove it
                cache_file.unlink(missing_ok=True)
                removed_count += 1

        return removed_count


class CacheManager:
    """Enhanced cache manager with multi-level caching."""

    def __init__(self, settings = None):
        if settings is None:
            settings = get_settings()

        self.settings = settings
        self.memory_cache = MemoryCache(max_size=settings.cache.max_memory_size)
        self.disk_cache = DiskCache(settings.cache.disk_cache_dir)

    def _generate_key(self, func_name: str, *args, **kwargs) -> str:
        """Generate deterministic cache key."""
        # Create a string representation of args and kwargs
        key_parts = [func_name]

        for arg in args:
            if isinstance(arg, (pd.DataFrame, pd.Series)):
                # For DataFrames/Series, use shape and column info
                key_parts.append(f"df:{arg.shape}:{list(arg.columns) if hasattr(arg, 'columns') else 'index'}")
            else:
                key_parts.append(str(arg))

        # Sort kwargs for consistent ordering
        for k, v in sorted(kwargs.items()):
            if isinstance(v, (pd.DataFrame, pd.Series)):
                key_parts.append(f"{k}:df:{v.shape}")
            else:
                key_parts.append(f"{k}:{v}")

        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """Get value from multi-level cache."""
        # Try memory first
        value = self.memory_cache.get(key)
        if value is not None:
            return value

        # Try disk cache
        value = self.disk_cache.get(key)
        if value is not None:
            # Promote to memory cache for faster future access
            self.memory_cache.set(key, value, self.settings.cache.default_ttl)
            return value

        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in multi-level cache."""
        if ttl is None:
            ttl = self.settings.cache.default_ttl

        entry = CacheEntry(data=value, timestamp=time.time(), ttl=ttl)

        # Set in both caches
        self.memory_cache.set(key, value, ttl)
        self.disk_cache.set(key, entry)

    def is_valid(self, key: str) -> bool:
        """Check if cache entry exists and is valid."""
        return self.get(key) is not None

    def invalidate(self, key: str) -> bool:
        """Invalidate specific cache entry."""
        # Remove from memory
        if key in self.memory_cache.cache:
            del self.memory_cache.cache[key]
            if key in self.memory_cache.access_order:
                self.memory_cache.access_order.remove(key)

        # Remove from disk
        cache_file = self.disk_cache._get_cache_file(key)
        if cache_file.exists():
            cache_file.unlink()
            return True

        return False

    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all cache entries matching pattern."""
        # This is a simple implementation - in production you might want more sophisticated pattern matching
        count = 0

        # Check memory cache
        keys_to_remove = [key for key in self.memory_cache.cache.keys() if pattern in key]
        for key in keys_to_remove:
            if self.invalidate(key):
                count += 1

        return count

    def clear_all(self) -> None:
        """Clear all caches."""
        self.memory_cache.clear()
        self.disk_cache.clear()

    def cleanup(self) -> Dict[str, Any]:
        """Clean up expired entries and return statistics."""
        expired_disk = self.disk_cache.cleanup_expired()
        memory_stats = self.memory_cache.stats()

        return {
            'expired_disk_entries_removed': expired_disk,
            'memory_cache_stats': memory_stats
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        memory_stats = self.memory_cache.stats()

        # Count disk cache files
        disk_files = len(list(self.disk_cache.cache_dir.glob("*.pkl")))

        return {
            'memory_cache': memory_stats,
            'disk_cache_files': disk_files,
            'cache_dir': str(self.disk_cache.cache_dir)
        }