"""Test configuration and fixtures for Macro Dashboard."""

import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import Mock, MagicMock
from datetime import datetime, date
from src.config.indicator_registry import IndicatorConfig, INDICATOR_REGISTRY


# Test data directory
TEST_DATA_DIR = Path(__file__).parent / "data" / "cache"


@pytest.fixture
def mock_fred_client():
    """Mock FredClient that returns pre-built DataFrames from cached CSV files."""
    client = Mock()
    
    def mock_fetch_series(series_id: str, start_date=None, end_date=None, frequency=None):
        """Return cached data for known series IDs."""
        csv_file = TEST_DATA_DIR / f"{series_id}.csv"
        if csv_file.exists():
            df = pd.read_csv(csv_file, parse_dates=['date'])
            df = df.set_index('date')
            # Apply date filtering if specified
            if start_date:
                df = df[df.index >= pd.to_datetime(start_date)]
            if end_date:
                df = df[df.index <= pd.to_datetime(end_date)]
            return df
        else:
            # Return empty DataFrame for unknown series
            return pd.DataFrame(columns=['value'], index=pd.DatetimeIndex([], name='date'))
    
    client.fetch_series = mock_fetch_series
    return client


@pytest.fixture
def mock_yahoo_client():
    """Mock YahooFinanceClient for commodity data."""
    client = Mock()
    
    def mock_fetch_data(symbol: str, start_date=None, end_date=None):
        """Return cached data for known Yahoo symbols."""
        csv_file = TEST_DATA_DIR / f"{symbol}.csv"
        if csv_file.exists():
            df = pd.read_csv(csv_file, parse_dates=['Date'])
            df = df.set_index('Date')
            # Apply date filtering if specified
            if start_date:
                df = df[df.index >= pd.to_datetime(start_date)]
            if end_date:
                df = df[df.index <= pd.to_datetime(end_date)]
            return df
        else:
            # Return empty DataFrame for unknown symbols
            columns = ['Open', 'High', 'Low', 'Close', 'Volume', 'Adj Close']
            return pd.DataFrame(columns=columns, index=pd.DatetimeIndex([], name='Date'))
    
    client.fetch_data = mock_fetch_data
    return client


@pytest.fixture
def test_indicator_config():
    """Sample IndicatorConfig for testing."""
    return IndicatorConfig(
        key="test_indicator",
        display_name="Test Indicator",
        emoji="🧪",
        fred_series=["ICSA"],
        chart_type="line",
        value_column="value",
        periods=12,
        frequency="w",
        bullish_condition="below_threshold",
        threshold=400000,
        warning_description="Test indicator for unit testing",
        chart_color="#1f77b4",
        card_chart_height=360,
        fred_link="https://fred.stlouisfed.org/series/ICSA"
    )


@pytest.fixture
def sample_indicator_data():
    """Sample indicator data structure for testing."""
    dates = pd.date_range('2023-01-01', periods=10, freq='W')
    df = pd.DataFrame({
        'value': [400000, 390000, 385000, 395000, 380000, 375000, 385000, 390000, 370000, 365000]
    }, index=dates)
    
    return {
        'data': df,
        'latest_value': 365000,
        'previous_value': 370000,
        'change_pct': -1.35,
        'status': 'Bullish',
        'trend': 'Decreasing'
    }


@pytest.fixture
def empty_indicator_data():
    """Empty indicator data for testing error handling."""
    return {
        'data': pd.DataFrame(columns=['value'], index=pd.DatetimeIndex([], name='date')),
        'latest_value': None,
        'previous_value': None,
        'change_pct': None,
        'status': 'Neutral',
        'trend': 'Unknown'
    }


@pytest.fixture
def all_indicator_configs():
    """All indicator configurations from registry."""
    return INDICATOR_REGISTRY.copy()


@pytest.fixture
def mock_streamlit():
    """Mock Streamlit components for UI testing."""
    import sys
    from unittest.mock import MagicMock
    
    # Create a mock streamlit module
    mock_st = MagicMock()
    
    # Mock common streamlit functions
    mock_st.markdown = MagicMock()
    mock_st.metric = MagicMock()
    mock_st.plotly_chart = MagicMock()
    mock_st.expander = MagicMock()
    mock_st.columns = MagicMock(return_value=[MagicMock(), MagicMock()])
    mock_st.container = MagicMock()
    mock_st.error = MagicMock()
    mock_st.warning = MagicMock()
    mock_st.info = MagicMock()
    
    # Add to sys.modules if not already there
    if 'streamlit' not in sys.modules:
        sys.modules['streamlit'] = mock_st
    
    return mock_st


@pytest.fixture
def cached_data_sample():
    """Load a sample of cached data for testing."""
    icsa_file = TEST_DATA_DIR / "ICSA.csv"
    if icsa_file.exists():
        df = pd.read_csv(icsa_file, parse_dates=['date'])
        return df.tail(10)  # Return last 10 rows
    else:
        # Fallback synthetic data
        dates = pd.date_range('2024-01-01', periods=10, freq='W')
        return pd.DataFrame({
            'date': dates,
            'value': [380000, 375000, 385000, 390000, 370000, 365000, 380000, 375000, 360000, 355000]
        })


@pytest.fixture(scope="session")
def test_cache_manager():
    """Mock CacheManager for testing."""
    from unittest.mock import MagicMock
    
    cache_manager = MagicMock()
    cache_manager.get = MagicMock(return_value=None)  # Always cache miss
    cache_manager.set = MagicMock()
    cache_manager.clear = MagicMock()
    cache_manager.get_size = MagicMock(return_value=0)
    
    return cache_manager


# Fixtures for specific indicator types
@pytest.fixture
def threshold_indicator_data():
    """Data for threshold-based indicators."""
    dates = pd.date_range('2024-01-01', periods=5, freq='W')
    return pd.DataFrame({
        'value': [390000, 410000, 395000, 380000, 375000]  # Mix above/below 400k threshold
    }, index=dates)


@pytest.fixture
def trend_indicator_data():
    """Data for trend-based indicators.""" 
    dates = pd.date_range('2024-01-01', periods=5, freq='M')
    return pd.DataFrame({
        'value': [2.5, 2.3, 2.1, 2.0, 1.8]  # Decreasing trend
    }, index=dates)


@pytest.fixture
def multi_series_data():
    """Multi-series data for complex indicators like USD Liquidity."""
    dates = pd.date_range('2024-01-01', periods=5, freq='W')
    return {
        'WALCL': pd.DataFrame({'value': [7000, 7100, 7050, 7200, 7150]}, index=dates),
        'RRPONTTLD': pd.DataFrame({'value': [2500, 2400, 2350, 2300, 2200]}, index=dates),
        'WTREGEN': pd.DataFrame({'value': [600, 595, 590, 585, 580]}, index=dates)
    }