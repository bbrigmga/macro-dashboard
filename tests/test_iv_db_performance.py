"""
Tests for IV Database Performance Optimizations

Tests the batch operations and performance enhancements added in Phase 10.
"""

import pytest
import tempfile
import pandas as pd
from datetime import datetime, date, timedelta

from data.iv_db import IVDatabase


class TestIVDatabasePerformance:
    """Test performance optimization methods in IVDatabase"""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db = IVDatabase(tmp.name)
            yield db
            db.close()
    
    def test_upsert_daily_batch(self, temp_db):
        """Test batch upsert operation"""
        # Prepare batch data
        records = [
            {
                'date': '2024-01-01',
                'ticker': 'SPY',
                'close_price': 450.0,
                'iv_30d': 0.15,
                'rv_30d': 0.12,
                'iv_premium': 0.03,
                'ytd_return': 0.0
            },
            {
                'date': '2024-01-02',
                'ticker': 'SPY',
                'close_price': 452.0,
                'iv_30d': 0.16,
                'rv_30d': 0.13,
                'iv_premium': 0.03,
                'ytd_return': 0.004
            },
            {
                'date': '2024-01-01',
                'ticker': 'QQQ',
                'close_price': 350.0,
                'iv_30d': 0.18,
                'rv_30d': 0.14,
                'iv_premium': 0.04,
                'ytd_return': 0.0
            }
        ]
        
        # Test batch upsert
        result = temp_db.upsert_daily_batch(records)
        assert result == 3
        
        # Verify data was inserted correctly
        spy_data = temp_db.get_history('SPY', lookback_days=30)
        assert len(spy_data) == 2
        
        qqq_data = temp_db.get_history('QQQ', lookback_days=30)
        assert len(qqq_data) == 1
        
        # Test upsert (update existing records)
        updated_records = [
            {
                'date': '2024-01-01',
                'ticker': 'SPY',
                'close_price': 451.0,  # Updated price
                'iv_30d': 0.155,      # Updated IV
                'rv_30d': 0.12,
                'iv_premium': 0.035,
                'ytd_return': 0.0
            }
        ]
        
        result = temp_db.upsert_daily_batch(updated_records)
        assert result == 1
        
        # Check that record was updated, not duplicated
        spy_data = temp_db.get_history('SPY', lookback_days=30)
        assert len(spy_data) == 2  # Still only 2 records
        
        jan_1_record = spy_data[spy_data['date'] == '2024-01-01'].iloc[0]
        assert jan_1_record['close_price'] == 451.0  # Updated value
        assert jan_1_record['iv_30d'] == 0.155       # Updated value
    
    def test_get_multiple_latest(self, temp_db):
        """Test batch retrieval of latest data for multiple tickers"""
        # Add sample data for multiple tickers
        sample_data = [
            ('2024-01-01', 'SPY', 450.0, 0.15, 0.12, 0.03, 0.0),
            ('2024-01-02', 'SPY', 452.0, 0.16, 0.13, 0.03, 0.004),
            ('2024-01-01', 'QQQ', 350.0, 0.18, 0.14, 0.04, 0.0),
            ('2024-01-02', 'QQQ', 355.0, 0.17, 0.15, 0.02, 0.014),
            ('2024-01-01', 'XLF', 35.0, 0.20, 0.16, 0.04, 0.0),
        ]
        
        for date_str, ticker, close, iv, rv, prem, ytd in sample_data:
            temp_db.upsert_daily(date_str, ticker, close, iv, rv, prem, ytd)
        
        # Test getting latest for multiple tickers
        tickers = ['SPY', 'QQQ', 'XLF']
        latest_df = temp_db.get_multiple_latest(tickers)
        
        assert len(latest_df) == 3
        assert set(latest_df['ticker'].values) == {'SPY', 'QQQ', 'XLF'}
        
        # Check that we got the latest data for each ticker
        spy_row = latest_df[latest_df['ticker'] == 'SPY'].iloc[0]
        assert spy_row['date'].strftime('%Y-%m-%d') == '2024-01-02'  # Latest SPY data
        assert spy_row['close_price'] == 452.0
        
        qqq_row = latest_df[latest_df['ticker'] == 'QQQ'].iloc[0]
        assert qqq_row['date'].strftime('%Y-%m-%d') == '2024-01-02'  # Latest QQQ data
        assert qqq_row['close_price'] == 355.0
        
        xlf_row = latest_df[latest_df['ticker'] == 'XLF'].iloc[0]
        assert xlf_row['date'].strftime('%Y-%m-%d') == '2024-01-01'  # Only XLF data
        assert xlf_row['close_price'] == 35.0
    
    def test_get_multiple_latest_empty_request(self, temp_db):
        """Test batch latest with empty ticker list"""
        result = temp_db.get_multiple_latest([])
        assert result.empty
    
    def test_get_multiple_latest_nonexistent_tickers(self, temp_db):
        """Test batch latest with tickers that don't exist"""
        result = temp_db.get_multiple_latest(['NONEXISTENT', 'ALSO_FAKE'])
        assert result.empty
    
    def test_get_multiple_history(self, temp_db):
        """Test batch retrieval of historical data for multiple tickers"""
        # Add historical data for multiple tickers
        dates = ['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05']
        tickers = ['SPY', 'QQQ']
        
        for i, date_str in enumerate(dates):
            for j, ticker in enumerate(tickers):
                close = 450.0 + i + j * 100  # Different prices for each ticker/date
                temp_db.upsert_daily(date_str, ticker, close, 0.15, 0.12, 0.03, 0.0)
        
        # Test getting history for multiple tickers
        history_df = temp_db.get_multiple_history(['SPY', 'QQQ'], lookback_days=3)
        
        # Should get 3 records for each ticker (6 total)
        assert len(history_df) == 6
        
        spy_records = history_df[history_df['ticker'] == 'SPY']
        qqq_records = history_df[history_df['ticker'] == 'QQQ']
        
        assert len(spy_records) == 3
        assert len(qqq_records) == 3
        
        # Data should be ordered by date descending within each ticker
        spy_dates = [d.strftime('%Y-%m-%d') for d in spy_records['date'].tolist()]
        assert spy_dates == ['2024-01-05', '2024-01-04', '2024-01-03']
    
    def test_get_multiple_history_with_limit(self, temp_db):
        """Test that lookback_days parameter works correctly"""
        # Add 10 days of data
        for i in range(10):
            date_str = (date.today() - timedelta(days=i)).isoformat()
            temp_db.upsert_daily(date_str, 'SPY', 450.0 + i, 0.15, 0.12, 0.03, 0.0)
        
        # Request only 5 days back
        history_df = temp_db.get_multiple_history(['SPY'], lookback_days=5)
        
        # Should get exactly 5 records
        assert len(history_df) == 5
    
    def test_vacuum_database(self, temp_db):
        """Test database vacuum operation doesn't crash"""
        # Add some data
        temp_db.upsert_daily('2024-01-01', 'SPY', 450.0, 0.15, 0.12, 0.03, 0.0)
        
        # Delete some data to create space to vacuum
        temp_db.delete_ticker('SPY')
        
        # Vacuum should complete without error
        temp_db.vacuum_database()
        
        # Database should still be functional
        temp_db.upsert_daily('2024-01-02', 'QQQ', 350.0, 0.18, 0.14, 0.04, 0.0)
        latest = temp_db.get_latest('QQQ')
        assert latest is not None
    
    def test_enable_wal_mode(self, temp_db):
        """Test WAL mode enablement doesn't crash"""
        temp_db.enable_wal_mode()
        
        # Database should still be functional after enabling WAL
        temp_db.upsert_daily('2024-01-01', 'SPY', 450.0, 0.15, 0.12, 0.03, 0.0)
        latest = temp_db.get_latest('SPY')
        assert latest is not None
    
    def test_optimize_connection(self, temp_db):
        """Test connection optimization doesn't break functionality"""
        # optimization is already called in __init__, but test explicit call
        temp_db.optimize_connection()
        
        # Database should still be functional
        temp_db.upsert_daily('2024-01-01', 'SPY', 450.0, 0.15, 0.12, 0.03, 0.0)
        latest = temp_db.get_latest('SPY')
        assert latest is not None
        assert latest['close_price'] == 450.0