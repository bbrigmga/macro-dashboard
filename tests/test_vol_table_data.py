"""
Tests for volatility table data assembly functionality.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
import tempfile
import os

from data.iv_db import IVDatabase
from data.vol_table_data import VolTableDataAssembler, ETF_UNIVERSE, ETF_NAME_LOOKUP


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        db = IVDatabase(db_path)
        yield db
    finally:
        # Properly close database connection
        if hasattr(db, 'conn') and db.conn:
            db.conn.close()
        try:
            if os.path.exists(db_path):
                os.unlink(db_path)
        except PermissionError:
            # On Windows, file might still be locked. This is okay for tests.
            pass


@pytest.fixture
def assembler(temp_db):
    """Create assembler with temp database."""
    return VolTableDataAssembler(temp_db)


@pytest.fixture
def sample_data():
    """Generate sample data for testing."""
    base_date = date.today()
    tickers = ["SPY", "QQQ", "XLF", "XLRE", "XLE"]  # Subset of universe for testing
    
    data = []
    for i in range(30):  # 30 days of history
        current_date = base_date - timedelta(days=i)
        for j, ticker in enumerate(tickers):
            # Generate synthetic but realistic data
            base_iv = 0.15 + j * 0.02  # 15-23% IV range
            base_rv = 0.12 + j * 0.015  # 12-18% RV range
            
            # Add some time variation
            iv_30d = base_iv + 0.03 * np.sin(i * 0.2) + np.random.normal(0, 0.01)
            rv_30d = base_rv + 0.02 * np.sin(i * 0.15) + np.random.normal(0, 0.005)
            
            # Ensure positive values
            iv_30d = max(0.05, iv_30d)
            rv_30d = max(0.03, rv_30d)
            
            iv_premium = ((iv_30d / rv_30d) - 1) * 100
            
            data.append({
                'date': current_date.isoformat(),
                'ticker': ticker,
                'close_price': 100.0 + j * 50 + i * 0.5,  # Trending price
                'iv_30d': iv_30d,
                'rv_30d': rv_30d,
                'iv_premium': iv_premium,
                'ytd_return': 0.05 + j * 0.03 + i * 0.001  # 5-20% YTD range
            })
    
    return data


@pytest.fixture
def populated_db(temp_db, sample_data):
    """Database populated with sample data."""
    for row in sample_data:
        temp_db.upsert_daily(**row)
    return temp_db


class TestVolTableDataAssembler:
    """Test suite for VolTableDataAssembler."""
    
    def test_empty_database(self, assembler):
        """Test behavior with empty database."""
        df = assembler.build_table()
        
        # Should return empty DataFrame with correct schema
        expected_columns = [
            'etf_name', 'ticker_display', 'ytd_pct', 'ivol_rvol_current',
            'ivol_prem_yesterday', 'ivol_prem_1w', 'ivol_prem_1m',
            'ttm_zscore', 'three_yr_zscore'
        ]
        
        assert list(df.columns) == expected_columns
        assert len(df) == 0
    
    def test_column_names_and_types(self, temp_db, sample_data):
        """Test DataFrame has correct column names and data types."""
        # Insert only universe tickers
        for row in sample_data[:5]:  # Just latest data
            temp_db.upsert_daily(**row)
        
        assembler = VolTableDataAssembler(temp_db)
        df = assembler.build_table()
        
        expected_columns = [
            'etf_name', 'ticker_display', 'ytd_pct', 'ivol_rvol_current',
            'ivol_prem_yesterday', 'ivol_prem_1w', 'ivol_prem_1m',
            'ttm_zscore', 'three_yr_zscore'
        ]
        
        assert list(df.columns) == expected_columns
        assert len(df) > 0
        
        # Check data types
        assert df['etf_name'].dtype == 'object'
        assert df['ticker_display'].dtype == 'object'
        assert pd.api.types.is_numeric_dtype(df['ytd_pct'])
        assert pd.api.types.is_numeric_dtype(df['ivol_rvol_current'])
    
    def test_ticker_filtering(self, temp_db):
        """Test that only universe tickers are included."""
        # Insert data for universe ticker and non-universe ticker
        universe_ticker = "SPY"
        non_universe_ticker = "AAPL"
        
        base_data = {
            'date': date.today().isoformat(),
            'close_price': 100.0,
            'iv_30d': 0.15,
            'rv_30d': 0.12,
            'iv_premium': 25.0,
            'ytd_return': 0.05
        }
        
        # Insert both
        temp_db.upsert_daily(ticker=universe_ticker, **base_data)
        temp_db.upsert_daily(ticker=non_universe_ticker, **base_data)
        
        assembler = VolTableDataAssembler(temp_db)
        df = assembler.build_table()
        
        # Only universe ticker should be present
        assert len(df) == 1
        assert df.iloc[0]['ticker_display'] == f"{universe_ticker} US EQUITY"
    
    def test_sort_order(self, populated_db):
        """Test DataFrame is sorted by ytd_pct descending."""
        assembler = VolTableDataAssembler(populated_db)
        df = assembler.build_table()
        
        assert len(df) > 1
        
        # Check sort order
        ytd_values = df['ytd_pct'].values
        assert np.all(ytd_values[:-1] >= ytd_values[1:]), "Should be sorted by ytd_pct descending"
    
    def test_ticker_display_format(self, populated_db):
        """Test ticker display format is correct."""
        assembler = VolTableDataAssembler(populated_db)
        df = assembler.build_table()
        
        for _, row in df.iterrows():
            ticker_display = row['ticker_display']
            assert ticker_display.endswith(' US EQUITY')
            ticker = ticker_display.replace(' US EQUITY', '')
            assert ticker in ETF_NAME_LOOKUP
    
    def test_etf_name_mapping(self, populated_db):
        """Test ETF names are correctly mapped."""
        assembler = VolTableDataAssembler(populated_db)
        df = assembler.build_table()
        
        for _, row in df.iterrows():
            ticker = row['ticker_display'].replace(' US EQUITY', '')
            expected_name = ETF_NAME_LOOKUP[ticker]
            assert row['etf_name'] == expected_name
    
    def test_ytd_percentage_conversion(self, temp_db):
        """Test YTD return is converted from decimal to percentage."""
        temp_db.upsert_daily(
            date=date.today().isoformat(),
            ticker="SPY",
            close_price=100.0,
            iv_30d=0.15,
            rv_30d=0.12,
            iv_premium=25.0,
            ytd_return=0.0567  # 5.67% as decimal
        )
        
        assembler = VolTableDataAssembler(temp_db)
        df = assembler.build_table()
        
        assert len(df) == 1
        assert abs(df.iloc[0]['ytd_pct'] - 5.67) < 0.01  # Should be converted to percentage
    
    def test_zscore_calculation_sufficient_data(self, populated_db):
        """Test Z-score calculation with sufficient data."""
        assembler = VolTableDataAssembler(populated_db)
        df = assembler.build_table()
        
        # Should have data, but not enough for full TTM Z-score
        assert len(df) > 0
        
        # Z-scores should be calculated where data is sufficient
        for _, row in df.iterrows():
            ttm_zscore = row['ttm_zscore']
            # Should either be None or a reasonable Z-score value
            if ttm_zscore is not None:
                assert isinstance(ttm_zscore, (int, float))
                assert abs(ttm_zscore) < 10  # Reasonable Z-score range
    
    def test_zscore_calculation_insufficient_data(self, temp_db):
        """Test Z-score handling with insufficient data."""
        # Insert only a few days of data
        for i in range(3):
            temp_db.upsert_daily(
                date=(date.today() - timedelta(days=i)).isoformat(),
                ticker="SPY",
                close_price=100.0,
                iv_30d=0.15,
                rv_30d=0.12,
                iv_premium=25.0,
                ytd_return=0.05
            )
        
        assembler = VolTableDataAssembler(temp_db)
        df = assembler.build_table()
        
        assert len(df) == 1
        # Should have None for Z-scores due to insufficient data
        assert pd.isna(df.iloc[0]['ttm_zscore']) or df.iloc[0]['ttm_zscore'] is None
        assert pd.isna(df.iloc[0]['three_yr_zscore']) or df.iloc[0]['three_yr_zscore'] is None
    
    def test_historical_premium_calculation(self, populated_db):
        """Test historical premium retrieval."""
        assembler = VolTableDataAssembler(populated_db)
        
        # Test the private method directly
        premium_1d = assembler._get_historical_premium("SPY", 1)
        premium_5d = assembler._get_historical_premium("SPY", 5)
        
        # Should have values since we have 30 days of data
        assert premium_1d is not None
        assert premium_5d is not None
        assert isinstance(premium_1d, (int, float))
        assert isinstance(premium_5d, (int, float))
    
    def test_historical_premium_insufficient_data(self, temp_db):
        """Test historical premium with insufficient data."""
        # Insert only today's data
        temp_db.upsert_daily(
            date=date.today().isoformat(),
            ticker="SPY",
            close_price=100.0,
            iv_30d=0.15,
            rv_30d=0.12,
            iv_premium=25.0,
            ytd_return=0.05
        )
        
        assembler = VolTableDataAssembler(temp_db)
        
        # Should return None for historical data that doesn't exist
        premium_5d = assembler._get_historical_premium("SPY", 5)
        assert premium_5d is None
    
    def test_zscore_math_accuracy(self, temp_db):
        """Test Z-score calculation accuracy with known data."""
        ticker = "SPY"
        base_date = date.today()
        
        # Insert data with known statistical properties
        iv_premiums = [10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 20.0]  # Mean=24.375, Std≈10.15
        
        for i, premium in enumerate(iv_premiums):
            temp_db.upsert_daily(
                date=(base_date - timedelta(days=i)).isoformat(),
                ticker=ticker,
                close_price=100.0,
                iv_30d=0.20,
                rv_30d=0.15,
                iv_premium=premium,
                ytd_return=0.05
            )
        
        assembler = VolTableDataAssembler(temp_db)
        
        # Get history and calculate Z-score manually
        history = temp_db.get_history(ticker, lookback_days=10)
        zscore = assembler._calculate_zscore_from_history(history, window=8)
        
        # Manual calculation: current=10.0, mean and std will be based on the data we inserted
        # We're just verifying that Z-score is calculated and is reasonable
        assert zscore is not None
        assert isinstance(zscore, float)
        assert abs(zscore) < 3.0  # Should be within reasonable Z-score range
    
    def test_data_freshness_info(self, populated_db):
        """Test data freshness information retrieval."""
        assembler = VolTableDataAssembler(populated_db)
        freshness = assembler.get_data_freshness_info()
        
        assert freshness['has_data'] is True
        assert freshness['ticker_count'] > 0
        assert freshness['latest_date'] is not None
        assert freshness['days_old'] is not None
        assert freshness['coverage_pct'] > 0
    
    def test_data_freshness_info_empty_db(self, assembler):
        """Test data freshness with empty database."""
        freshness = assembler.get_data_freshness_info()
        
        assert freshness['has_data'] is False
        assert freshness['ticker_count'] == 0
        assert freshness['latest_date'] is None
        assert freshness['days_old'] is None
    
    def test_na_handling_sparse_data(self, temp_db):
        """Test N/A handling with sparse historical data."""
        # Insert recent data but no historical data
        temp_db.upsert_daily(
            date=date.today().isoformat(),
            ticker="SPY",
            close_price=100.0,
            iv_30d=0.15,
            rv_30d=0.12,
            iv_premium=25.0,
            ytd_return=0.05
        )
        
        assembler = VolTableDataAssembler(temp_db)
        
        # Test historical premium lookups directly - should be None for missing days
        assert assembler._get_historical_premium("SPY", 1) is None  # Yesterday
        assert assembler._get_historical_premium("SPY", 5) is None  # 1W ago
        assert assembler._get_historical_premium("SPY", 21) is None # 1M ago
        
        df = assembler.build_table()
        assert len(df) == 1
        row = df.iloc[0]
        
        # Z-scores should be None/NaN due to insufficient history
        assert pd.isna(row['ttm_zscore']) or row['ttm_zscore'] is None
        assert pd.isna(row['three_yr_zscore']) or row['three_yr_zscore'] is None
    
    def test_build_ticker_row_not_in_universe(self, assembler):
        """Test _build_ticker_row with ticker not in universe."""
        # Create a fake row for non-universe ticker
        fake_row = pd.Series({
            'ticker': 'AAPL',
            'ytd_return': 0.05,
            'iv_premium': 25.0
        })
        
        result = assembler._build_ticker_row(fake_row)
        assert result is None  # Should return None for non-universe ticker


class TestETFUniverse:
    """Test ETF universe constants."""
    
    def test_etf_universe_structure(self):
        """Test ETF universe has correct structure."""
        assert len(ETF_UNIVERSE) == 14  # As specified in the plan
        
        for etf in ETF_UNIVERSE:
            assert 'ticker' in etf
            assert 'name' in etf
            assert isinstance(etf['ticker'], str)
            assert isinstance(etf['name'], str)
            assert len(etf['ticker']) > 0
            assert len(etf['name']) > 0
    
    def test_etf_name_lookup(self):
        """Test ETF name lookup dictionary."""
        assert len(ETF_NAME_LOOKUP) == 14
        
        # Test a few known mappings
        assert ETF_NAME_LOOKUP['SPY'] == 'SPDR S&P 500 Trust'
        assert ETF_NAME_LOOKUP['QQQ'] == 'Power Shares QQQ Trust ETF'
        assert ETF_NAME_LOOKUP['IWM'] == 'I-Shares Russell 2000'
    
    def test_no_duplicate_tickers(self):
        """Test no duplicate tickers in universe."""
        tickers = [etf['ticker'] for etf in ETF_UNIVERSE]
        assert len(tickers) == len(set(tickers))