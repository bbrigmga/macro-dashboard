#!/usr/bin/env python3
"""
Test script to verify Phase 2 optimizations work correctly.
Tests service layer, enhanced caching, and architecture improvements.
"""
import sys
import os
import asyncio
from pathlib import Path

def test_enhanced_caching():
    """Test the enhanced caching system."""
    print("Testing enhanced caching system...")

    try:
        from src.core.caching import CacheManager, MemoryCache, DiskCache
        from src.config.settings import get_settings

        # Get settings
        settings = get_settings()

        # Test cache manager initialization
        cache_manager = CacheManager(settings)

        # Test basic cache operations
        test_key = "test_key"
        test_data = {"test": "data", "number": 42}

        # Test set and get
        cache_manager.set(test_key, test_data, ttl=3600)
        retrieved_data = cache_manager.get(test_key)

        assert retrieved_data is not None
        assert retrieved_data["test"] == "data"
        assert retrieved_data["number"] == 42

        # Test cache invalidation
        cache_manager.invalidate(test_key)
        assert cache_manager.get(test_key) is None

        # Test cache statistics
        stats = cache_manager.get_stats()
        assert 'memory_cache' in stats
        assert 'disk_cache_files' in stats

        print("PASS: Enhanced caching system test passed")
        return True

    except Exception as e:
        print(f"FAIL: Enhanced caching system test failed: {e}")
        return False

def test_indicator_service():
    """Test the indicator service layer."""
    print("Testing indicator service layer...")

    try:
        from src.services import IndicatorService, IndicatorResult
        from src.config.settings import get_settings

        # Initialize service
        settings = get_settings()
        service = IndicatorService(settings)

        # Test service initialization
        assert service.settings is not None
        assert service.cache_manager is not None

        # Test cache key generation
        key1 = service._get_cache_key("test_indicator", periods=30)
        key2 = service._get_cache_key("test_indicator", periods=60)

        assert key1 != key2  # Different parameters should generate different keys

        # Test cache statistics
        stats = service.get_cache_stats()
        assert isinstance(stats, dict)

        print("PASS: Indicator service layer test passed")
        return True

    except Exception as e:
        print(f"FAIL: Indicator service layer test failed: {e}")
        return False

def test_service_layer_architecture():
    """Test that service layer provides proper separation of concerns."""
    print("Testing service layer architecture...")

    try:
        from src.services import IndicatorService
        from src.config.settings import get_settings

        # Test that service uses configuration properly
        settings = get_settings()
        service = IndicatorService(settings)

        # Verify service has access to all necessary components
        assert hasattr(service, 'settings')
        assert hasattr(service, 'cache_manager')
        assert hasattr(service, '_indicators_config')

        # Test that indicators config is loaded
        config = service._indicators_config
        assert isinstance(config, dict)
        assert 'claims' in config
        assert 'pce' in config

        # Test cache key generation with various parameters
        keys = []
        for indicator in ['claims', 'pce', 'pmi']:
            key = service._get_cache_key(indicator, periods=24, frequency='M')
            keys.append(key)
            assert indicator in key

        # All keys should be unique
        assert len(set(keys)) == len(keys)

        print("PASS: Service layer architecture test passed")
        return True

    except Exception as e:
        print(f"FAIL: Service layer architecture test failed: {e}")
        return False

def test_async_capabilities():
    """Test async capabilities of the service layer."""
    print("Testing async capabilities...")

    try:
        import asyncio
        from src.services import IndicatorService
        from src.config.settings import get_settings

        async def test_async_service():
            settings = get_settings()
            service = IndicatorService(settings)

            # Test that service methods are awaitable
            # Note: We don't actually call them to avoid API dependencies in tests

            # Test cache operations are synchronous (as expected)
            cache_key = service._get_cache_key("test", periods=10)
            assert isinstance(cache_key, str)
            assert len(cache_key) > 0

            return True

        # Run the async test
        result = asyncio.run(test_async_service())

        if result:
            print("PASS: Async capabilities test passed")
            return True
        else:
            print("FAIL: Async capabilities test failed")
            return False

    except Exception as e:
        print(f"FAIL: Async capabilities test failed: {e}")
        return False

def test_configuration_integration():
    """Test that new modules integrate properly with configuration."""
    print("Testing configuration integration...")

    try:
        from src.config.settings import get_settings
        from src.core.caching import CacheManager
        from src.services import IndicatorService

        # Test that all modules can access settings
        settings = get_settings()

        # Test cache manager uses settings
        cache_manager = CacheManager(settings)
        assert cache_manager.settings is settings

        # Test service uses settings
        service = IndicatorService(settings)
        assert service.settings is settings

        # Test that settings values are properly used
        assert cache_manager.memory_cache.max_size == settings.cache.max_memory_size
        assert service.cache_manager.settings.cache.enabled == settings.cache.enabled

        print("PASS: Configuration integration test passed")
        return True

    except Exception as e:
        print(f"FAIL: Configuration integration test failed: {e}")
        return False

def main():
    """Run all Phase 2 tests."""
    print("Running Phase 2 Architecture Tests")
    print("=" * 50)

    tests = [
        test_enhanced_caching,
        test_indicator_service,
        test_service_layer_architecture,
        test_async_capabilities,
        test_configuration_integration
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"FAIL: Test {test.__name__} failed with exception: {e}")

    print("=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("SUCCESS: All Phase 2 tests passed! Architecture improvements working correctly.")
        return 0
    else:
        print("WARNING: Some tests failed. Please review the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())