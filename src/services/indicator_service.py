"""
Service layer for economic indicator operations.
Provides high-level business logic with caching and error handling.
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import pandas as pd

from src.config.settings import get_settings
from src.core.caching.cache_manager import CacheManager

logger = logging.getLogger(__name__)


@dataclass
class IndicatorResult:
    """Result wrapper for indicator data."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    cached: bool = False
    execution_time: float = 0.0


class IndicatorService:
    """Service layer for economic indicator operations."""

    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        self.cache_manager = CacheManager(self.settings)
        self._indicators_config = self._load_indicators_config()

    def _load_indicators_config(self) -> Dict[str, Any]:
        """Load indicator configuration from settings."""
        return {
            'claims': {
                'series_id': 'ICSA',
                'frequency': 'W',
                'cache_ttl': self.settings.cache.fred_ttl,
                'default_periods': 52
            },
            'pce': {
                'series_id': 'PCE',
                'frequency': 'M',
                'cache_ttl': self.settings.cache.fred_ttl,
                'default_periods': 24
            },
            'core_cpi': {
                'series_id': 'CPILFESL',
                'frequency': 'M',
                'cache_ttl': self.settings.cache.fred_ttl,
                'default_periods': 24
            },
            'hours_worked': {
                'series_id': 'AWHAETP',
                'frequency': 'M',
                'cache_ttl': self.settings.cache.fred_ttl,
                'default_periods': 24
            },
            'new_orders': {
                'series_id': 'NEWORDER',
                'frequency': 'M',
                'cache_ttl': self.settings.cache.fred_ttl,
                'default_periods': 24
            },
            'yield_curve': {
                'series_id': 'T10Y2Y',
                'frequency': 'D',
                'cache_ttl': self.settings.cache.fred_ttl,
                'default_periods': 36
            }
        }

    def _get_cache_key(self, indicator_name: str, **kwargs) -> str:
        """Generate cache key for indicator."""
        key_parts = [indicator_name]

        # Add relevant parameters to cache key
        relevant_params = ['periods', 'frequency', 'start_date', 'end_date']
        for param in relevant_params:
            if param in kwargs:
                key_parts.append(f"{param}:{kwargs[param]}")

        return "|".join(key_parts)

    async def get_indicator(self, indicator_name: str, **kwargs) -> IndicatorResult:
        """
        Get a specific economic indicator with caching.

        Args:
            indicator_name: Name of the indicator to fetch
            **kwargs: Additional parameters (periods, frequency, etc.)

        Returns:
            IndicatorResult: Wrapped result with success status and data
        """
        import time
        start_time = time.time()

        try:
            # Check cache first
            cache_key = self._get_cache_key(indicator_name, **kwargs)
            cached_data = self.cache_manager.get(cache_key)

            if cached_data is not None:
                logger.info(f"Cache hit for {indicator_name}")
                return IndicatorResult(
                    success=True,
                    data=cached_data,
                    cached=True,
                    execution_time=time.time() - start_time
                )

            # Fetch fresh data
            logger.info(f"Cache miss for {indicator_name}, fetching fresh data")

            if indicator_name == 'usd_liquidity':
                result = await self._get_usd_liquidity_data(**kwargs)
            elif indicator_name == 'pmi':
                result = await self._get_pmi_data(**kwargs)
            elif indicator_name == 'copper_gold_ratio':
                result = await self._get_copper_gold_ratio_data(**kwargs)
            else:
                result = await self._get_basic_indicator_data(indicator_name, **kwargs)

            if result.success:
                # Cache the result
                cache_ttl = self._indicators_config.get(indicator_name, {}).get('cache_ttl', self.settings.cache.default_ttl)
                self.cache_manager.set(cache_key, result.data, cache_ttl)

            result.execution_time = time.time() - start_time
            return result

        except Exception as e:
            logger.error(f"Error fetching {indicator_name}: {e}")
            return IndicatorResult(
                success=False,
                error=str(e),
                execution_time=time.time() - start_time
            )

    async def get_all_indicators(self) -> IndicatorResult:
        """
        Get all economic indicators in parallel.

        Returns:
            IndicatorResult: Combined result with all indicators
        """
        import time
        start_time = time.time()

        try:
            # Define all indicators to fetch
            indicators = [
                'claims', 'pce', 'core_cpi', 'hours_worked',
                'pmi', 'usd_liquidity', 'new_orders', 'yield_curve', 'copper_gold_ratio'
            ]

            # Fetch all indicators in parallel
            tasks = [self.get_indicator(indicator) for indicator in indicators]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            combined_data = {}
            errors = []

            for indicator, result in zip(indicators, results):
                if isinstance(result, Exception):
                    errors.append(f"{indicator}: {str(result)}")
                    logger.error(f"Failed to fetch {indicator}: {result}")
                elif result.success:
                    combined_data[indicator] = result.data
                else:
                    errors.append(f"{indicator}: {result.error}")

            success = len(errors) == 0

            return IndicatorResult(
                success=success,
                data=combined_data,
                error="; ".join(errors) if errors else None,
                execution_time=time.time() - start_time
            )

        except Exception as e:
            logger.error(f"Error in get_all_indicators: {e}")
            return IndicatorResult(
                success=False,
                error=str(e),
                execution_time=time.time() - start_time
            )

    async def _get_basic_indicator_data(self, indicator_name: str, **kwargs) -> IndicatorResult:
        """Get basic FRED indicator data."""
        try:
            from data.fred_client import FredClient

            config = self._indicators_config.get(indicator_name)
            if not config:
                return IndicatorResult(success=False, error=f"Unknown indicator: {indicator_name}")

            fred_client = FredClient(
                cache_enabled=self.settings.cache.enabled,
                max_cache_size=self.settings.cache.max_memory_size
            )

            periods = kwargs.get('periods', config.get('default_periods', 24))
            frequency = kwargs.get('frequency', config.get('frequency', 'M'))

            df = fred_client.get_series(
                config['series_id'],
                periods=periods,
                frequency=frequency
            )

            if df is None or df.empty:
                return IndicatorResult(success=False, error="No data received")

            return IndicatorResult(success=True, data=df)

        except Exception as e:
            return IndicatorResult(success=False, error=str(e))

    async def _get_usd_liquidity_data(self, **kwargs) -> IndicatorResult:
        """Get USD liquidity data."""
        try:
            from data.indicators import IndicatorData
            from data.fred_client import FredClient

            fred_client = FredClient(
                cache_enabled=self.settings.cache.enabled,
                max_cache_size=self.settings.cache.max_memory_size
            )

            indicator_data = IndicatorData(fred_client)
            result = indicator_data.get_usd_liquidity(
                periods=kwargs.get('periods', 120),
                use_sample_data=kwargs.get('use_sample_data', False)
            )

            return IndicatorResult(success=True, data=result)

        except Exception as e:
            return IndicatorResult(success=False, error=str(e))

    async def _get_pmi_data(self, **kwargs) -> IndicatorResult:
        """Get PMI proxy data."""
        try:
            from data.indicators import IndicatorData
            from data.fred_client import FredClient

            fred_client = FredClient(
                cache_enabled=self.settings.cache.enabled,
                max_cache_size=self.settings.cache.max_memory_size
            )

            indicator_data = IndicatorData(fred_client)
            result = indicator_data.calculate_pmi_proxy(
                periods=kwargs.get('periods', 36)
            )

            return IndicatorResult(success=True, data=result)

        except Exception as e:
            return IndicatorResult(success=False, error=str(e))

    async def _get_copper_gold_ratio_data(self, **kwargs) -> IndicatorResult:
        """Get copper/gold ratio data."""
        try:
            from data.indicators import IndicatorData
            from data.fred_client import FredClient

            fred_client = FredClient(
                cache_enabled=self.settings.cache.enabled,
                max_cache_size=self.settings.cache.max_memory_size
            )

            indicator_data = IndicatorData(fred_client)
            result = indicator_data.get_copper_gold_ratio(
                periods=kwargs.get('periods', 365)
            )

            return IndicatorResult(success=True, data=result)

        except Exception as e:
            return IndicatorResult(success=False, error=str(e))

    def invalidate_indicator_cache(self, indicator_name: str = None) -> int:
        """
        Invalidate cache for specific indicator or all indicators.

        Args:
            indicator_name: Name of indicator to invalidate, or None for all

        Returns:
            Number of cache entries invalidated
        """
        if indicator_name:
            pattern = indicator_name
            return self.cache_manager.invalidate_pattern(pattern)
        else:
            # Clear all cache
            self.cache_manager.clear_all()
            return -1  # Indicate full cache clear

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        return self.cache_manager.get_stats()

    def cleanup_cache(self) -> Dict[str, Any]:
        """Clean up expired cache entries."""
        return self.cache_manager.cleanup()