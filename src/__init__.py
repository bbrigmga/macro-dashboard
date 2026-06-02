"""
Source package for Macro Dashboard.
Contains configuration, services, and core functionality.
"""

from .config.settings import get_settings, reload_settings, Settings
from .core.caching import CacheManager, MemoryCache, DiskCache, CacheEntry
from .services import (
    IndicatorService, IndicatorResult
)

__version__ = "3.0.0"
__all__ = [
    "get_settings", "reload_settings", "Settings",
    "CacheManager", "MemoryCache", "DiskCache", "CacheEntry",
    "IndicatorService", "IndicatorResult"
]