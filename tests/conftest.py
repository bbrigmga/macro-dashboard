"""Test-specific configuration and fixtures."""

import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import Mock
import sys
import os

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Test fixtures directory
FIXTURES_DIR = Path(__file__).parent / "fixtures"
CACHE_DIR = Path(__file__).parent.parent / "data" / "cache"


def pytest_configure():
    """Configure pytest environment."""
    # Ensure cache directory exists for fixture loading
    assert CACHE_DIR.exists(), f"Cache directory not found: {CACHE_DIR}"


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    # Disable actual API calls during tests
    os.environ['TESTING'] = '1'
    yield
    # Cleanup
    if 'TESTING' in os.environ:
        del os.environ['TESTING']