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
from src.config.indicator_registry import INDICATOR_REGISTRY, list_service_fetch_keys
from src.core.caching.cache_manager import CacheManager
from data.fred_client import FredClient
from data.indicators import IndicatorData
from data.iv_db import IVDatabase
from data.vol_table_data import VolTableDataAssembler

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

    CACHE_SCHEMA_VERSION = "v6"

    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        self.cache_manager = CacheManager(self.settings)
        self._fred_client = FredClient(
            cache_enabled=self.settings.cache.enabled,
            max_cache_size=self.settings.cache.max_memory_size
        )
        self.indicator_data = IndicatorData(self._fred_client)
        self._indicators_config = self._load_indicators_config()

    @property
    def fred_client(self) -> FredClient:
        """Expose the shared FRED client used by this service."""
        return self._fred_client

    def _load_indicators_config(self) -> Dict[str, Any]:
        """Build service fetch configuration from the indicator registry."""
        config_map: Dict[str, Any] = {}
        for registry_config in INDICATOR_REGISTRY.values():
            service_key = registry_config.service_key or registry_config.key
            config_map[service_key] = {
                "registry_key": registry_config.key,
                "series_id": registry_config.fred_series[0] if registry_config.fred_series else None,
                "frequency": registry_config.frequency or "M",
                "cache_ttl": registry_config.cache_ttl or self.settings.cache.default_ttl,
                "default_periods": registry_config.periods,
                "default_years": 3,
                "default_lookback_days": registry_config.periods,
                "source": "fred" if registry_config.fred_series else ("yahoo" if registry_config.yahoo_series else "custom"),
                "tickers": registry_config.yahoo_series or []
            }

        # Preserve historical behavior for indicators that fetch in year windows.
        if "pscf_price" in config_map:
            config_map["pscf_price"]["default_years"] = 5
        if "credit_spread" in config_map:
            config_map["credit_spread"]["default_years"] = 5
        if "xlp_xly_ratio" in config_map:
            config_map["xlp_xly_ratio"]["default_years"] = 3

        return config_map

    def _get_cache_key(self, indicator_name: str, **kwargs) -> str:
        """Generate cache key for indicator."""
        key_parts = [self.CACHE_SCHEMA_VERSION, indicator_name]

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
                if indicator_name == "regime_quadrant":
                    from analysis.regime_backtest import enrich_regime_quadrant_data
                    cached_data = enrich_regime_quadrant_data(cached_data)
                return IndicatorResult(
                    success=True,
                    data=cached_data,
                    cached=True,
                    execution_time=time.time() - start_time
                )

            # Fetch fresh data
            logger.info(f"Cache miss for {indicator_name}, fetching fresh data")

            if indicator_name == 'usd_liquidity':
                result = await asyncio.to_thread(self._get_usd_liquidity_data, **kwargs)
            elif indicator_name == 'pmi':
                result = await asyncio.to_thread(self._get_pmi_data, **kwargs)
            elif indicator_name == 'copper_gold_ratio':
                result = await asyncio.to_thread(self._get_copper_gold_ratio_data, **kwargs)
            elif indicator_name == 'regime_quadrant':
                result = await asyncio.to_thread(self._get_regime_quadrant_data, **kwargs)
            elif indicator_name == 'implied_realized_vol':
                result = await asyncio.to_thread(self._get_implied_realized_vol_data, **kwargs)
            else:
                result = await asyncio.to_thread(self._get_basic_indicator_data, indicator_name, **kwargs)

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
            indicators = list_service_fetch_keys()

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

    def _get_basic_indicator_data(self, indicator_name: str, **kwargs) -> IndicatorResult:
        """Get basic FRED indicator data."""
        try:
            indicator_methods = {
                'claims': lambda: self.indicator_data.get_initial_claims(
                    periods=kwargs.get('periods', self._indicators_config['claims']['default_periods'])
                ),
                'pce': lambda: self.indicator_data.get_pce(
                    periods=kwargs.get('periods', self._indicators_config['pce']['default_periods'])
                ),
                'core_cpi': lambda: self.indicator_data.get_core_cpi(
                    periods=kwargs.get('periods', self._indicators_config['core_cpi']['default_periods'])
                ),
                'hours_worked': lambda: self.indicator_data.get_hours_worked(
                    periods=kwargs.get('periods', self._indicators_config['hours_worked']['default_periods'])
                ),
                'new_orders': lambda: self.indicator_data.get_new_orders(
                    periods=kwargs.get('periods', self._indicators_config['new_orders']['default_periods'])
                ),
                'yield_curve': lambda: self.indicator_data.get_yield_curve(
                    periods=kwargs.get('periods', self._indicators_config['yield_curve']['default_periods']),
                    frequency=kwargs.get('frequency', self._indicators_config['yield_curve']['frequency'])
                ),
                'pscf_price': lambda: self.indicator_data.get_pscf_price(
                    years=kwargs.get('years', 5)
                ),
                'credit_spread': lambda: self.indicator_data.get_credit_spread(
                    years=kwargs.get('years', 5)
                ),
                'xlp_xly_ratio': lambda: self.indicator_data.get_xlp_xly_ratio(
                    years=kwargs.get('years', 3)
                ),
                'korea_exports_spy_eps': lambda: self.indicator_data.get_korea_exports_vs_spy_eps(
                    periods=kwargs.get('periods', self._indicators_config['korea_exports_spy_eps']['default_periods'])
                )
            }

            method = indicator_methods.get(indicator_name)
            if method:
                return IndicatorResult(success=True, data=method())

            config = self._indicators_config.get(indicator_name)
            if not config:
                return IndicatorResult(success=False, error=f"Unknown indicator: {indicator_name}")

            periods = kwargs.get('periods', config.get('default_periods', 24))
            frequency = kwargs.get('frequency', config.get('frequency', 'M'))

            df = self._fred_client.get_series(
                config['series_id'],
                periods=periods,
                frequency=frequency
            )

            if df is None or df.empty:
                return IndicatorResult(success=False, error="No data received")

            return IndicatorResult(success=True, data=df)

        except Exception as e:
            return IndicatorResult(success=False, error=str(e))

    def _get_usd_liquidity_data(self, **kwargs) -> IndicatorResult:
        """Get USD liquidity data."""
        try:
            config = self._indicators_config.get("usd_liquidity", {})
            result = self.indicator_data.get_usd_liquidity(
                periods=kwargs.get('periods', config.get('default_periods', 120)),
                use_sample_data=kwargs.get('use_sample_data', False)
            )

            return IndicatorResult(success=True, data=result)

        except Exception as e:
            return IndicatorResult(success=False, error=str(e))

    def _get_pmi_data(self, **kwargs) -> IndicatorResult:
        """Get PMI proxy data."""
        try:
            config = self._indicators_config.get("pmi", {})
            result = self.indicator_data.calculate_pmi_proxy(
                periods=kwargs.get('periods', config.get('default_periods', 36))
            )

            return IndicatorResult(success=True, data=result)

        except Exception as e:
            return IndicatorResult(success=False, error=str(e))

    def _get_copper_gold_ratio_data(self, **kwargs) -> IndicatorResult:
        """Get copper/gold ratio data."""
        try:
            config = self._indicators_config.get("copper_gold_ratio", {})
            result = self.indicator_data.get_copper_gold_ratio(
                periods=kwargs.get('periods', config.get('default_periods', 365))
            )
            data_df = result.get('data') if isinstance(result, dict) else None
            if not isinstance(result, dict) or result.get('current_value') is None or data_df is None or data_df.empty:
                raise ValueError("Copper/gold ratio data unavailable")

            return IndicatorResult(success=True, data=result)

        except Exception as e:
            return IndicatorResult(success=False, error=str(e))
    
    def _get_regime_quadrant_data(self, **kwargs) -> IndicatorResult:
        """Get regime quadrant data from Yahoo Finance proxies."""
        try:
            config = self._indicators_config.get("regime_quadrant", {})
            result = self.indicator_data.get_regime_quadrant_data(
                lookback_days=kwargs.get('lookback_days', config.get('default_lookback_days', 900)),
                trail_days=kwargs.get('trail_days', 252)
            )
            from analysis.regime_backtest import enrich_regime_quadrant_data
            result = enrich_regime_quadrant_data(result)
            return IndicatorResult(success=True, data=result)
        except Exception as e:
            return IndicatorResult(success=False, error=str(e))

    def _get_implied_realized_vol_data(self, **kwargs) -> IndicatorResult:
        """Get implied vs realized volatility table data."""
        try:
            with IVDatabase() as db:
                assembler = VolTableDataAssembler(db)
                table_data = assembler.build_table()
            return IndicatorResult(success=True, data={"data": table_data, "table_type": "vol_heatmap"})
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
