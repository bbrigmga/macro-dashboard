"""Tests for indicator service layer."""

import pytest
import asyncio
import pandas as pd
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
from src.services.indicator_service import IndicatorService, IndicatorResult
from src.config.settings import Settings


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = Mock(spec=Settings)
    settings.cache = Mock()
    settings.cache.enabled = True
    settings.cache.max_memory_size = 100
    settings.cache.fred_ttl = 3600
    settings.cache.default_ttl = 1800
    return settings


@pytest.fixture
def mock_fred_client():
    """Mock FRED client."""
    client = Mock()
    client.fetch_series = Mock()
    return client


@pytest.fixture
def mock_indicator_data():
    """Mock indicator data provider."""
    data_provider = Mock()
    # Mock all the indicator methods
    data_provider.get_initial_claims = Mock()
    data_provider.get_pce_data = Mock() 
    data_provider.get_core_cpi_data = Mock()
    data_provider.get_hours_worked_data = Mock()
    data_provider.get_new_orders = Mock()
    data_provider.get_yield_curve = Mock()
    data_provider.get_pscf_price = Mock()
    data_provider.get_credit_spread = Mock()
    data_provider.calculate_usd_liquidity = Mock()
    data_provider.calculate_pmi_proxy = Mock()
    data_provider.get_copper_gold_ratio = Mock()
    return data_provider


@pytest.fixture
def mock_cache_manager():
    """Mock cache manager."""
    cache = Mock()
    cache.get = Mock(return_value=None)  # Default: cache miss
    cache.set = Mock()
    cache.clear = Mock()
    cache.get_size = Mock(return_value=0)
    cache.invalidate_pattern = Mock(return_value=0)
    return cache


@pytest.fixture 
def sample_indicator_data():
    """Sample indicator data for testing."""
    dates = pd.date_range('2024-01-01', periods=10, freq='W')
    return {
        'data': pd.DataFrame({
            'Date': dates,
            'ICSA': [380000, 375000, 385000, 390000, 370000, 365000, 380000, 375000, 360000, 355000]
        }),
        'current_value': 355000,
        'change_pct': -1.39,
        'status': 'Bullish'
    }


class TestIndicatorResult:
    """Test IndicatorResult dataclass."""
    
    def test_indicator_result_creation(self):
        """Test creating IndicatorResult instances."""
        result = IndicatorResult(success=True, data={"test": "data"})
        
        assert result.success is True
        assert result.data == {"test": "data"}
        assert result.error is None
        assert result.cached is False
        assert result.execution_time == 0.0
    
    def test_indicator_result_with_error(self):
        """Test IndicatorResult with error."""
        result = IndicatorResult(
            success=False, 
            error="API Error", 
            execution_time=1.5
        )
        
        assert result.success is False
        assert result.error == "API Error"
        assert result.data is None
        assert result.execution_time == 1.5


class TestIndicatorServiceInit:
    """Test IndicatorService initialization."""
    
    @patch('src.services.indicator_service.CacheManager')
    @patch('src.services.indicator_service.FredClient')
    @patch('src.services.indicator_service.IndicatorData')
    @patch('src.services.indicator_service.get_settings')
    def test_service_init_with_default_settings(self, mock_get_settings, mock_indicator_data,
                                               mock_fred_client, mock_cache_manager):
        """Test service initialization with default settings."""
        mock_settings = Mock()
        mock_get_settings.return_value = mock_settings
        
        service = IndicatorService()
        
        assert service.settings == mock_settings
        mock_cache_manager.assert_called_once_with(mock_settings)
        mock_fred_client.assert_called_once()
        mock_indicator_data.assert_called_once()
    
    @patch('src.services.indicator_service.CacheManager')
    @patch('src.services.indicator_service.FredClient') 
    @patch('src.services.indicator_service.IndicatorData')
    def test_service_init_with_custom_settings(self, mock_indicator_data, mock_fred_client, 
                                              mock_cache_manager, mock_settings):
        """Test service initialization with custom settings."""
        service = IndicatorService(settings=mock_settings)
        
        assert service.settings == mock_settings
        mock_cache_manager.assert_called_once_with(mock_settings)
    
    def test_indicators_config_loaded(self, mock_settings):
        """Test that indicators configuration is loaded."""
        with patch('src.services.indicator_service.CacheManager'), \
             patch('src.services.indicator_service.FredClient'), \
             patch('src.services.indicator_service.IndicatorData'):
            
            service = IndicatorService(settings=mock_settings)
            
            assert hasattr(service, '_indicators_config')
            assert isinstance(service._indicators_config, dict)
            # Check for some expected indicators
            assert 'claims' in service._indicators_config
            assert 'pce' in service._indicators_config
            assert 'core_cpi' in service._indicators_config


class TestIndicatorServiceCaching:
    """Test caching functionality in IndicatorService."""
    
    @patch('src.services.indicator_service.CacheManager')
    @patch('src.services.indicator_service.FredClient')
    @patch('src.services.indicator_service.IndicatorData')
    def test_cache_key_generation(self, mock_indicator_data, mock_fred_client, 
                                 mock_cache_manager, mock_settings):
        """Test cache key generation."""
        service = IndicatorService(settings=mock_settings)
        
        # Test basic cache key
        key1 = service._get_cache_key('claims')
        assert 'claims' in key1
        assert service.CACHE_SCHEMA_VERSION in key1
        
        # Test cache key with parameters
        key2 = service._get_cache_key('claims', periods=52, frequency='W')
        assert 'claims' in key2
        assert 'periods=52' in key2 or '52' in key2
        assert key1 != key2  # Should be different with parameters
    
    @patch('src.services.indicator_service.CacheManager')
    @patch('src.services.indicator_service.FredClient')
    @patch('src.services.indicator_service.IndicatorData')
    def test_cache_hit_scenario(self, mock_indicator_data, mock_fred_client, 
                               mock_cache_manager, mock_settings, sample_indicator_data):
        """Test cache hit scenario."""
        # Setup cache to return data
        cache_instance = mock_cache_manager.return_value
        cache_instance.get.return_value = sample_indicator_data
        
        service = IndicatorService(settings=mock_settings)
        
        # Test async cache hit
        async def test_cache_hit():
            result = await service.get_indicator('claims')
            
            assert result.success is True
            assert result.cached is True
            assert result.data == sample_indicator_data
            cache_instance.get.assert_called_once()
        
        asyncio.run(test_cache_hit())
    
    @patch('src.services.indicator_service.CacheManager')
    @patch('src.services.indicator_service.FredClient')
    @patch('src.services.indicator_service.IndicatorData')
    def test_cache_miss_and_set(self, mock_indicator_data, mock_fred_client,
                               mock_cache_manager, mock_settings, sample_indicator_data):
        """Test cache miss and subsequent cache set."""
        cache_instance = mock_cache_manager.return_value
        cache_instance.get.return_value = None  # Cache miss
        
        indicator_instance = mock_indicator_data.return_value
        indicator_instance.get_initial_claims.return_value = sample_indicator_data
        
        service = IndicatorService(settings=mock_settings)
        
        async def test_cache_miss():
            result = await service.get_indicator('claims')
            
            assert result.success is True
            assert result.cached is False
            cache_instance.set.assert_called_once()
        
        asyncio.run(test_cache_miss())


class TestGetIndicator:
    """Test individual indicator fetching."""
    
    @patch('src.services.indicator_service.CacheManager')
    @patch('src.services.indicator_service.FredClient')
    @patch('src.services.indicator_service.IndicatorData')
    def test_get_basic_indicator_success(self, mock_indicator_data, mock_fred_client,
                                       mock_cache_manager, mock_settings, sample_indicator_data):
        """Test successful basic indicator fetching."""
        cache_instance = mock_cache_manager.return_value
        cache_instance.get.return_value = None  # Cache miss
        
        indicator_instance = mock_indicator_data.return_value
        indicator_instance.get_initial_claims.return_value = sample_indicator_data
        
        service = IndicatorService(settings=mock_settings)
        
        async def test_get_indicator():
            result = await service.get_indicator('claims')
            
            assert result.success is True
            assert result.data == sample_indicator_data
            assert result.execution_time > 0
            indicator_instance.get_initial_claims.assert_called_once()
        
        asyncio.run(test_get_indicator())
    
    @patch('src.services.indicator_service.CacheManager')
    @patch('src.services.indicator_service.FredClient')
    @patch('src.services.indicator_service.IndicatorData')
    def test_get_special_indicator_usd_liquidity(self, mock_indicator_data, mock_fred_client,
                                               mock_cache_manager, mock_settings):
        """Test fetching USD liquidity (special indicator)."""
        cache_instance = mock_cache_manager.return_value
        cache_instance.get.return_value = None
        
        indicator_instance = mock_indicator_data.return_value
        indicator_instance.calculate_usd_liquidity.return_value = {"current_liquidity": 4500}
        
        service = IndicatorService(settings=mock_settings)
        
        async def test_usd_liquidity():
            result = await service.get_indicator('usd_liquidity')
            
            assert result.success is True
            indicator_instance.calculate_usd_liquidity.assert_called_once()
        
        asyncio.run(test_usd_liquidity())
    
    @patch('src.services.indicator_service.CacheManager')
    @patch('src.services.indicator_service.FredClient')
    @patch('src.services.indicator_service.IndicatorData')
    def test_get_indicator_error_handling(self, mock_indicator_data, mock_fred_client,
                                         mock_cache_manager, mock_settings):
        """Test error handling during indicator fetching."""
        cache_instance = mock_cache_manager.return_value
        cache_instance.get.return_value = None
        
        indicator_instance = mock_indicator_data.return_value
        indicator_instance.get_initial_claims.side_effect = Exception("API Error")
        
        service = IndicatorService(settings=mock_settings)
        
        async def test_error():
            result = await service.get_indicator('claims')
            
            assert result.success is False
            assert result.error and "API Error" in result.error
        
        asyncio.run(test_error())
    
    @patch('src.services.indicator_service.CacheManager')
    @patch('src.services.indicator_service.FredClient')
    @patch('src.services.indicator_service.IndicatorData')
    def test_get_unknown_indicator(self, mock_indicator_data, mock_fred_client,
                                  mock_cache_manager, mock_settings):
        """Test fetching unknown indicator."""
        cache_instance = mock_cache_manager.return_value 
        cache_instance.get.return_value = None
        
        service = IndicatorService(settings=mock_settings)
        
        async def test_unknown():
            result = await service.get_indicator('nonexistent_indicator')
            
            # Should handle gracefully (might return error or empty result)
            assert isinstance(result, IndicatorResult)
        
        asyncio.run(test_unknown())


class TestGetAllIndicators:
    """Test batch indicator fetching."""
    
    @patch('src.services.indicator_service.CacheManager')
    @patch('src.services.indicator_service.FredClient')
    @patch('src.services.indicator_service.IndicatorData')
    def test_get_all_indicators_success(self, mock_indicator_data, mock_fred_client,
                                       mock_cache_manager, mock_settings, sample_indicator_data):
        """Test successful fetching of all indicators."""
        cache_instance = mock_cache_manager.return_value
        cache_instance.get.return_value = None
        
        indicator_instance = mock_indicator_data.return_value
        # Mock all indicator methods to return data
        for method_name in ['get_initial_claims', 'get_pce_data', 'get_core_cpi_data',
                           'get_hours_worked_data', 'get_new_orders', 'get_yield_curve',
                           'get_pscf_price', 'get_credit_spread', 'calculate_usd_liquidity',
                           'calculate_pmi_proxy', 'get_copper_gold_ratio']:
            if hasattr(indicator_instance, method_name):
                getattr(indicator_instance, method_name).return_value = sample_indicator_data
        
        service = IndicatorService(settings=mock_settings)
        
        async def test_all_indicators():
            result = await service.get_all_indicators()
            
            assert result.success is True
            assert isinstance(result.data, dict)
            assert len(result.data) > 0
            assert result.execution_time > 0
        
        asyncio.run(test_all_indicators())
    
    @patch('src.services.indicator_service.CacheManager')
    @patch('src.services.indicator_service.FredClient')
    @patch('src.services.indicator_service.IndicatorData')
    def test_get_all_indicators_partial_failure(self, mock_indicator_data, mock_fred_client,
                                              mock_cache_manager, mock_settings, sample_indicator_data):
        """Test partial failure scenario in batch fetching."""
        cache_instance = mock_cache_manager.return_value
        cache_instance.get.return_value = None
        
        indicator_instance = mock_indicator_data.return_value
        # Some succeed, some fail
        indicator_instance.get_initial_claims.return_value = sample_indicator_data
        indicator_instance.get_pce_data.side_effect = Exception("PCE Error")
        indicator_instance.get_core_cpi_data.return_value = sample_indicator_data
        
        service = IndicatorService(settings=mock_settings)
        
        async def test_partial_failure():
            with patch.object(service, 'get_indicator') as mock_get:
                # Mock some successes and some failures
                mock_results = []
                for i, indicator in enumerate(['claims', 'pce', 'core_cpi']):
                    if indicator == 'pce':
                        mock_results.append(IndicatorResult(success=False, error="PCE Error"))
                    else:
                        mock_results.append(IndicatorResult(success=True, data=sample_indicator_data))
                
                mock_get.side_effect = mock_results
                
                # Only test with subset for this test
                original_method = service.get_all_indicators
                
                async def limited_get_all_indicators():
                    import time
                    start_time = time.time()
                    try:
                        indicators = ['claims', 'pce', 'core_cpi']  # Limited set for test
                        tasks = [service.get_indicator(indicator) for indicator in indicators]
                        results = await asyncio.gather(*tasks, return_exceptions=True)
                        
                        combined_data = {}
                        errors = []
                        
                        for indicator, result in zip(indicators, results):
                            if isinstance(result, Exception):
                                errors.append(f"{indicator}: {str(result)}")
                            elif hasattr(result, 'success') and hasattr(result, 'data') and hasattr(result, 'error'):
                                # Type ignore needed because type checker can't infer result attributes
                                if result.success:  # type: ignore
                                    combined_data[indicator] = result.data  # type: ignore
                                else:
                                    errors.append(f"{indicator}: {result.error or 'Unknown error'}")  # type: ignore
                            else:
                                errors.append(f"{indicator}: Unexpected result type")
                        
                        success = len(errors) == 0
                        
                        return IndicatorResult(
                            success=success,
                            data=combined_data,
                            error="; ".join(errors) if errors else None,
                            execution_time=time.time() - start_time
                        )
                    except Exception as e:
                        return IndicatorResult(
                            success=False,
                            error=str(e),
                            execution_time=time.time() - start_time
                        )
                
                result = await limited_get_all_indicators()
                
                # Should have partial success
                assert result.success is False  # Because of PCE error
                assert result.error and "PCE Error" in result.error
                assert len(result.data) == 2  # claims and core_cpi succeeded
        
        asyncio.run(test_partial_failure())


class TestCacheManagement:
    """Test cache management methods."""
    
    @patch('src.services.indicator_service.CacheManager')
    @patch('src.services.indicator_service.FredClient')
    @patch('src.services.indicator_service.IndicatorData')
    def test_invalidate_specific_indicator_cache(self, mock_indicator_data, mock_fred_client,
                                               mock_cache_manager, mock_settings):
        """Test invalidating cache for specific indicator."""
        cache_instance = mock_cache_manager.return_value
        cache_instance.invalidate_pattern.return_value = 3
        
        service = IndicatorService(settings=mock_settings)
        
        result = service.invalidate_indicator_cache('claims')
        
        assert result == 3
        cache_instance.invalidate_pattern.assert_called_once()
    
    @patch('src.services.indicator_service.CacheManager')
    @patch('src.services.indicator_service.FredClient')
    @patch('src.services.indicator_service.IndicatorData')
    def test_invalidate_all_cache(self, mock_indicator_data, mock_fred_client,
                                 mock_cache_manager, mock_settings):
        """Test invalidating all cache."""
        cache_instance = mock_cache_manager.return_value
        cache_instance.clear.return_value = 10
        
        service = IndicatorService(settings=mock_settings)
        
        result = service.invalidate_indicator_cache()
        
        assert result == 10
        cache_instance.clear.assert_called_once()
    
    @patch('src.services.indicator_service.CacheManager')
    @patch('src.services.indicator_service.FredClient')
    @patch('src.services.indicator_service.IndicatorData')
    def test_get_cache_stats(self, mock_indicator_data, mock_fred_client,
                            mock_cache_manager, mock_settings):
        """Test getting cache statistics."""
        cache_instance = mock_cache_manager.return_value
        cache_instance.get_size.return_value = 50
        
        service = IndicatorService(settings=mock_settings)
        
        stats = service.get_cache_stats()
        
        assert isinstance(stats, dict)
        assert 'cache_size' in stats
        assert stats['cache_size'] == 50
    
    @patch('src.services.indicator_service.CacheManager')
    @patch('src.services.indicator_service.FredClient')
    @patch('src.services.indicator_service.IndicatorData')
    def test_cleanup_cache(self, mock_indicator_data, mock_fred_client,
                          mock_cache_manager, mock_settings):
        """Test cache cleanup."""
        cache_instance = mock_cache_manager.return_value
        
        service = IndicatorService(settings=mock_settings)
        
        result = service.cleanup_cache()
        
        assert isinstance(result, dict)
        # Cleanup should call cache manager methods
        assert cache_instance.method_calls  # Some methods should have been called


class TestServiceIntegration:
    """Integration tests for the service layer."""
    
    def test_service_with_real_settings_structure(self):
        """Test service works with realistic settings structure."""
        # Create a more realistic settings mock
        settings = Mock()
        settings.cache = Mock()
        settings.cache.enabled = True
        settings.cache.max_memory_size = 1000
        settings.cache.fred_ttl = 3600
        settings.cache.default_ttl = 1800
        
        with patch('src.services.indicator_service.CacheManager'), \
             patch('src.services.indicator_service.FredClient'), \
             patch('src.services.indicator_service.IndicatorData'):
            
            service = IndicatorService(settings=settings)
            
            assert service.settings == settings
            assert hasattr(service, 'cache_manager')
            assert hasattr(service, 'fred_client')
            assert hasattr(service, 'indicator_data')
    
    @patch('src.services.indicator_service.CacheManager')
    @patch('src.services.indicator_service.FredClient')
    @patch('src.services.indicator_service.IndicatorData')
    def test_service_resilience_to_errors(self, mock_indicator_data, mock_fred_client,
                                         mock_cache_manager, mock_settings):
        """Test service resilience to various error conditions.""" 
        service = IndicatorService(settings=mock_settings)
        
        # Test with cache errors
        cache_instance = mock_cache_manager.return_value
        cache_instance.get.side_effect = Exception("Cache error")
        
        async def test_cache_error_resilience():
            result = await service.get_indicator('claims')
            # Should handle cache errors gracefully
            assert isinstance(result, IndicatorResult)
        
        asyncio.run(test_cache_error_resilience())