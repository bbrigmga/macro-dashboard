"""
Optimized indicator calculation services.
High-performance implementations with vectorized operations and parallel processing.
"""
import asyncio
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
import time

from src.config.settings import get_settings
from src.core.caching.cache_manager import CacheManager

logger = logging.getLogger(__name__)


@dataclass
class OptimizationMetrics:
    """Performance metrics for optimization tracking."""
    algorithm_name: str
    execution_time: float
    data_points_processed: int
    memory_usage_mb: float
    cache_hit_rate: float


class OptimizedIndicatorService:
    """Optimized service for high-performance indicator calculations."""

    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        self.cache_manager = CacheManager(self.settings)
        self.metrics: Dict[str, OptimizationMetrics] = {}

    def _track_performance(self, algorithm_name: str, start_time: float,
                          data_size: int, cache_hit: bool = False) -> OptimizationMetrics:
        """Track performance metrics for algorithm optimization."""
        execution_time = time.time() - start_time
        memory_usage = 0  # Could be enhanced with memory profiling

        metric = OptimizationMetrics(
            algorithm_name=algorithm_name,
            execution_time=execution_time,
            data_points_processed=data_size,
            memory_usage_mb=memory_usage,
            cache_hit_rate=100.0 if cache_hit else 0.0
        )

        self.metrics[algorithm_name] = metric
        logger.info(f"{algorithm_name}: {execution_time:.3f}s for {data_size} data points")
        return metric

    async def calculate_usd_liquidity_optimized(self, **kwargs) -> Dict[str, Any]:
        """
        Optimized USD Liquidity calculation using vectorized operations.

        Args:
            **kwargs: Parameters including periods, use_sample_data

        Returns:
            Dictionary with liquidity data and performance metrics
        """
        start_time = time.time()
        algorithm_name = "usd_liquidity_optimized"

        try:
            # Check cache first
            cache_key = f"{algorithm_name}:{kwargs}"
            cached_result = self.cache_manager.get(cache_key)

            if cached_result:
                self._track_performance(algorithm_name, start_time, 0, cache_hit=True)
                return cached_result

            periods = kwargs.get('periods', 120)
            use_sample_data = kwargs.get('use_sample_data', False)

            if use_sample_data:
                result = self._calculate_usd_liquidity_sample()
            else:
                result = await self._calculate_usd_liquidity_vectorized(periods)

            # Cache the result
            self.cache_manager.set(cache_key, result, self.settings.cache.fred_ttl)

            # Track performance
            data_size = len(result.get('data', [])) if 'data' in result else 0
            self._track_performance(algorithm_name, start_time, data_size)

            return result

        except Exception as e:
            logger.error(f"Error in optimized USD liquidity calculation: {e}")
            self._track_performance(algorithm_name, start_time, 0)
            raise

    def _calculate_usd_liquidity_sample(self) -> Dict[str, Any]:
        """Generate optimized sample data for testing."""
        # Generate sample quarterly data for testing
        dates = pd.date_range(end=pd.Timestamp.now(), periods=20, freq='QE')
        np.random.seed(42)  # For reproducible results

        sample_data = []
        base_liquidity = 3.5  # Base liquidity in trillions

        for i, date in enumerate(dates):
            # Simulate trend and volatility
            trend = i * 0.02  # Slight upward trend
            noise = np.random.normal(0, 0.1)
            liquidity = base_liquidity + trend + noise

            sample_data.append({
                'Date': date,
                'WALCL': 7200000 + i * 100000,
                'RRPONTTLD': max(0, 500 - i * 10),
                'WTREGEN': max(0, 800 + i * 20),
                'CURRCIR': 2300 + i * 50,
                'GDPC1': 22000 + i * 200,
                'USD_Liquidity': max(0, liquidity),
                'SP500': 4500 + i * 50 + np.random.normal(0, 100)
            })

        quarterly_data = pd.DataFrame(sample_data)

        return {
            'data': quarterly_data,
            'current_liquidity': quarterly_data['USD_Liquidity'].iloc[-1],
            'current_liquidity_qoq': np.random.normal(0, 2),
            'liquidity_increasing': True,
            'liquidity_decreasing': False,
            'details': {
                'WALCL': 7200000,
                'RRPONTTLD': 500,
                'WTREGEN': 800,
                'CURRCIR': 2300,
                'GDPC1': 22000
            }
        }

    async def _calculate_usd_liquidity_vectorized(self, periods: int) -> Dict[str, Any]:
        """Vectorized USD liquidity calculation with parallel data fetching."""
        try:
            from data.fred_client import FredClient

            fred_client = FredClient(
                cache_enabled=self.settings.cache.enabled,
                max_cache_size=self.settings.cache.max_memory_size
            )

            # Define components to fetch
            components = {
                'WALCL': 'WALCL',                    # Fed Balance Sheet
                'RRPONTTLD': 'RRPONTTLD',           # Reverse Repo
                'WTREGEN': 'WTREGEN',               # Treasury General Account
                'CURRCIR': 'CURRCIR',               # Currency in Circulation
                'GDPC1': 'GDPC1',                   # GDP
                'B235RC1Q027SBEA': 'B235RC1Q027SBEA', # Tariff Receipts
                'SP500': 'SP500'                    # S&P 500
            }

            # Fetch all components in parallel
            fetch_tasks = []
            for series_id in components.values():
                # Use async wrapper for parallel fetching
                task = asyncio.get_event_loop().run_in_executor(
                    None, fred_client.get_series, series_id, None, None, periods, 'Q'
                )
                fetch_tasks.append((series_id, task))

            # Wait for all fetches to complete
            fetch_results = {}
            for series_id, task in fetch_tasks:
                try:
                    df = await task
                    if not df.empty:
                        fetch_results[series_id] = df
                except Exception as e:
                    logger.warning(f"Failed to fetch {series_id}: {e}")

            if not fetch_results:
                raise ValueError("Failed to fetch any USD liquidity components")

            # Merge all data
            merged_df = None
            for series_id, df in fetch_results.items():
                if merged_df is None:
                    merged_df = df.copy()
                else:
                    merged_df = pd.merge(merged_df, df, on='Date', how='outer')

            if merged_df is None or merged_df.empty:
                raise ValueError("No valid data after merging")

            # Vectorized calculation
            result_df = merged_df.copy()

            # Calculate USD Liquidity vectorized
            result_df['USD_Liquidity'] = (
                result_df.get('WALCL', 0) -
                (result_df.get('RRPONTTLD', 0) * 1000) -  # Convert billions to millions
                (result_df.get('WTREGEN', 0) * 1000) -
                result_df.get('CURRCIR', 0) +
                ((result_df.get('B235RC1Q027SBEA', 0) / 4) * 1000)  # Convert SAAR to quarterly
            )

            # Divide by GDP and convert to trillions
            result_df['USD_Liquidity'] = result_df['USD_Liquidity'] / result_df.get('GDPC1', 1)
            result_df['USD_Liquidity'] = result_df['USD_Liquidity'] / 1000

            # Calculate QoQ change
            result_df['USD_Liquidity_QoQ'] = result_df['USD_Liquidity'].pct_change() * 100

            # Get current values
            current_liquidity = result_df['USD_Liquidity'].iloc[-1] if not result_df.empty else 0

            # Determine trend
            recent_values = result_df['USD_Liquidity'].tail(4)
            liquidity_increasing = (
                len(recent_values) >= 3 and
                recent_values.iloc[-1] > recent_values.iloc[-2] > recent_values.iloc[-3]
            )
            liquidity_decreasing = (
                len(recent_values) >= 3 and
                recent_values.iloc[-1] < recent_values.iloc[-2] < recent_values.iloc[-3]
            )

            return {
                'data': result_df[['Date', 'USD_Liquidity', 'USD_Liquidity_QoQ', 'SP500']].dropna(),
                'current_liquidity': current_liquidity,
                'current_liquidity_qoq': result_df['USD_Liquidity_QoQ'].iloc[-1] if not result_df.empty else 0,
                'liquidity_increasing': liquidity_increasing,
                'liquidity_decreasing': liquidity_decreasing,
                'details': self._extract_component_details(result_df)
            }

        except Exception as e:
            logger.error(f"Error in vectorized USD liquidity calculation: {e}")
            raise

    def _extract_component_details(self, df: pd.DataFrame) -> Dict[str, float]:
        """Extract latest component values for details."""
        details = {}

        component_columns = ['WALCL', 'RRPONTTLD', 'WTREGEN', 'CURRCIR', 'GDPC1', 'B235RC1Q027SBEA']
        for col in component_columns:
            if col in df.columns:
                value = df[col].dropna().iloc[-1] if not df[col].dropna().empty else 0
                details[col] = value

        return details

    async def calculate_pmi_proxy_optimized(self, **kwargs) -> Dict[str, Any]:
        """
        Optimized PMI proxy calculation using vectorized operations.

        Args:
            **kwargs: Parameters including periods

        Returns:
            Dictionary with PMI data and performance metrics
        """
        start_time = time.time()
        algorithm_name = "pmi_proxy_optimized"

        try:
            periods = kwargs.get('periods', 36)

            # Check cache
            cache_key = f"{algorithm_name}:{periods}"
            cached_result = self.cache_manager.get(cache_key)

            if cached_result:
                self._track_performance(algorithm_name, start_time, 0, cache_hit=True)
                return cached_result

            # Fetch PMI components in parallel
            components_data = await self._fetch_pmi_components_parallel()

            if components_data is None or components_data.empty:
                raise ValueError("Failed to fetch PMI component data")

            # Vectorized PMI calculation
            pmi_result = self._calculate_pmi_vectorized(components_data)

            # Cache result
            self.cache_manager.set(cache_key, pmi_result, self.settings.cache.fred_ttl)

            # Track performance
            data_size = len(components_data)
            self._track_performance(algorithm_name, start_time, data_size)

            return pmi_result

        except Exception as e:
            logger.error(f"Error in optimized PMI calculation: {e}")
            self._track_performance(algorithm_name, start_time, 0)
            raise

    async def _fetch_pmi_components_parallel(self) -> Optional[pd.DataFrame]:
        """Fetch PMI components in parallel for better performance."""
        try:
            from data.fred_client import FredClient

            fred_client = FredClient(
                cache_enabled=self.settings.cache.enabled,
                max_cache_size=self.settings.cache.max_memory_size
            )

            # PMI component series
            series_ids = [
                'AMTMNO',      # New Orders
                'IPMAN',       # Production
                'MANEMP',      # Employment
                'AMDMUS',      # Supplier Deliveries
                'MNFCTRIMSA'   # Inventories
            ]

            # Fetch in parallel using ThreadPoolExecutor
            def fetch_series(series_id):
                return fred_client.get_series(series_id, periods=36, frequency='M')

            # Use asyncio to run blocking operations in parallel
            loop = asyncio.get_event_loop()
            tasks = [loop.run_in_executor(None, fetch_series, sid) for sid in series_ids]

            # Wait for all to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            valid_dfs = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.warning(f"Failed to fetch PMI component {series_ids[i]}: {result}")
                    continue

                if result is not None and not result.empty:
                    # Rename column to component name
                    df = result.copy()
                    df.columns = ['Date', series_ids[i]]
                    valid_dfs.append(df)

            if not valid_dfs:
                return None

            # Merge all components
            merged_df = valid_dfs[0]
            for df in valid_dfs[1:]:
                merged_df = pd.merge(merged_df, df, on='Date', how='outer')

            return merged_df

        except Exception as e:
            logger.error(f"Error fetching PMI components: {e}")
            return None

    def _calculate_pmi_vectorized(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Vectorized PMI calculation with optimized algorithms."""
        try:
            # Define component weights
            weights = {
                'AMTMNO': 0.30,      # New Orders
                'IPMAN': 0.25,       # Production
                'MANEMP': 0.20,      # Employment
                'AMDMUS': 0.15,      # Supplier Deliveries
                'MNFCTRIMSA': 0.10   # Inventories
            }

            # Get available components
            available_components = [col for col in weights.keys() if col in data.columns]
            if not available_components:
                raise ValueError("No PMI components available in data")

            # Adjust weights for available components only
            total_weight = sum(weights[comp] for comp in available_components)
            adjusted_weights = {comp: weights[comp] / total_weight for comp in available_components}

            # Vectorized percentage change calculation
            pct_changes = data[available_components].pct_change() * 100

            # Optimized rolling standard deviation with fallback
            def robust_rolling_std_optimized(series: pd.Series, window: int = 120) -> pd.Series:
                """Optimized rolling standard deviation calculation."""
                # Try full window first
                std_series = series.rolling(window=window, min_periods=24).std()

                # Fallback to shorter window if needed
                if std_series.isna().all():
                    std_series = series.rolling(window=24, min_periods=12).std()

                # Final fallback to overall std
                if std_series.isna().all():
                    overall_std = series.std()
                    std_series = pd.Series([overall_std] * len(series), index=series.index)

                return std_series.ffill()

            # Calculate standard deviations for all components
            std_devs = pd.DataFrame(index=pct_changes.index, columns=available_components)
            for component in available_components:
                std_devs[component] = robust_rolling_std_optimized(pct_changes[component])

            # Vectorized diffusion index calculation
            def calculate_diffusion_index(pct_change: float, std_dev: float) -> float:
                """Calculate diffusion index with bounds checking."""
                if pd.isna(std_dev) or std_dev <= 0:
                    return 50.0

                # Cap extreme values to prevent outliers
                capped_change = max(min(pct_change / std_dev, 3.0), -3.0)
                result = 50.0 + (capped_change * 10.0)
                return max(0.0, min(100.0, result))

            # Apply diffusion index calculation
            diffusion_indices = pd.DataFrame(index=data.index, columns=available_components)
            for component in available_components:
                component_std = std_devs[component]
                pct_change_series = pct_changes[component]

                # Vectorized calculation
                diffusion_indices[component] = [
                    calculate_diffusion_index(pct, std)
                    for pct, std in zip(pct_change_series, component_std)
                ]

            # Calculate weighted PMI
            weighted_pmi = pd.Series(0.0, index=data.index)
            for component in available_components:
                weighted_pmi += diffusion_indices[component] * adjusted_weights[component]

            # Get current PMI value
            current_pmi = weighted_pmi.iloc[-1] if not weighted_pmi.empty else 50.0
            pmi_below_50 = current_pmi < 50

            return {
                'latest_pmi': current_pmi,
                'pmi_series': weighted_pmi,
                'pmi_below_50': pmi_below_50,
                'component_values': diffusion_indices,
                'component_weights': adjusted_weights,
                'optimization_metrics': {
                    'components_used': len(available_components),
                    'total_components': len(weights),
                    'calculation_method': 'vectorized'
                }
            }

        except Exception as e:
            logger.error(f"Error in vectorized PMI calculation: {e}")
            raise

    def get_optimization_metrics(self) -> Dict[str, OptimizationMetrics]:
        """Get performance metrics for all optimizations."""
        return self.metrics.copy()

    def clear_metrics(self) -> None:
        """Clear performance metrics."""
        self.metrics.clear()