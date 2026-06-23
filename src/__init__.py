"""
Source package for Macro Dashboard.
Contains configuration, services, and core functionality.
"""

from .config.settings import get_settings, Settings
from .core.caching import CacheManager, MemoryCache, DiskCache, CacheEntry

__version__ = "3.0.0"
__all__ = [
    "get_settings", "Settings",
    "CacheManager", "MemoryCache", "DiskCache", "CacheEntry",
    "IndicatorService", "IndicatorResult",
]


def __getattr__(name: str):
    if name == "IndicatorService":
        from .services import IndicatorService
        return IndicatorService
    if name == "IndicatorResult":
        from .services import IndicatorResult
        return IndicatorResult
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
