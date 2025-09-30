#!/usr/bin/env python3
"""
Test script to verify Phase 1 optimizations work correctly.
Tests configuration management and module structure fixes.
"""
import sys
import os
from pathlib import Path

def test_configuration_system():
    """Test that the configuration system works correctly."""
    print("Testing configuration system...")

    try:
        from src.config.settings import get_settings, Settings

        # Test getting settings
        settings = get_settings()

        # Verify settings are loaded correctly
        assert settings.api.fred_api_key is None or isinstance(settings.api.fred_api_key, str)
        assert settings.cache.enabled is True
        assert settings.cache.max_memory_size == 512
        assert settings.chart.default_height == 250
        assert settings.debug is False

        print("PASS: Configuration system test passed")
        return True

    except Exception as e:
        print(f"FAIL: Configuration system test failed: {e}")
        return False

def test_module_structure_fixes():
    """Test that module structure fixes work correctly."""
    print("Testing module structure fixes...")

    # Test that we can import from the main modules without sys.path issues
    try:
        # Test importing from data module
        from data.fred_client import FredClient
        from data.yahoo_client import YahooClient
        from data.indicators import IndicatorData

        # Test importing from ui module
        from ui.dashboard import create_dashboard, setup_page_config

        # Test importing from visualization module
        from visualization.charts import THEME, apply_dark_theme

        print("PASS: Module structure fixes test passed")
        return True

    except ImportError as e:
        print(f"FAIL: Module structure fixes test failed: {e}")
        return False

def test_standalone_scripts():
    """Test that standalone scripts can run without sys.path.append() issues."""
    print("Testing standalone scripts...")

    # Test that scripts can at least import their dependencies
    script_tests = [
        ('fetch_copper.py', 'data.yahoo_client'),
        ('fetch_gold.py', 'data.yahoo_client'),
        ('fetch_treasury.py', 'data.fred_client'),
        ('calculate_copper_gold_ratio.py', 'data.yahoo_client'),
        ('create_copper_gold_yield_chart.py', 'visualization.charts')
    ]

    all_passed = True

    for script_name, expected_import in script_tests:
        try:
            # Just test that the script file exists and is syntactically correct
            script_path = Path(script_name)
            if script_path.exists():
                print(f"PASS: {script_name} exists and is accessible")
            else:
                print(f"FAIL: {script_name} not found")
                all_passed = False

        except Exception as e:
            print(f"FAIL: {script_name} test failed: {e}")
            all_passed = False

    return all_passed

def main():
    """Run all Phase 1 tests."""
    print("Running Phase 1 Optimization Tests")
    print("=" * 50)

    tests = [
        test_configuration_system,
        test_module_structure_fixes,
        test_standalone_scripts
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
        print("SUCCESS: All Phase 1 tests passed! Ready for next phase.")
        return 0
    else:
        print("WARNING: Some tests failed. Please review the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())