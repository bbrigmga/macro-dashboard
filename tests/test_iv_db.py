"""
Tests for IVDatabase SQLite layer
"""

import pytest
import pandas as pd
from datetime import datetime, date
import sqlite3
from pathlib import Path
import tempfile
import os

from data.iv_db import IVDatabase


class TestIVDatabase:
    """Test suite for IVDatabase class."""
    
    @pytest.fixture
    def temp_db(self, tmp_path):
        """Create a temporary database for testing."""
        db_path = tmp_path / "test_iv_data.db"
        return str(db_path)
    
    @pytest.fixture
    def db(self, temp_db):
        """Create IVDatabase instance with temp database."""
        db_instance = IVDatabase(temp_db)
        yield db_instance
        db_instance.close()
    
    def test_schema_creation(self, temp_db):
        """Test that database schema is created correctly on first initialization."""
        # Ensure database file doesn't exist initially
        assert not Path(temp_db).exists()
        
        # Initialize database
        db = IVDatabase(temp_db)
        
        # Check that database file was created
        assert Path(temp_db).exists()
        
        # Verify tables and indexes exist
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        
        # Check daily_iv table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='daily_iv'")
        assert cursor.fetchone() is not None
        
        # Check index exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_daily_iv_ticker_date'")
        assert cursor.fetchone() is not None
        
        conn.close()
        db.close()
    
    def test_upsert_daily_data(self, db):
        """Test inserting and updating daily data."""
        # Insert new record
        db.upsert_daily(
            date="2024-01-15",
            ticker="SPY",
            close_price=450.25,
            iv_30d=0.18,
            rv_30d=0.15,
            iv_premium=0.03,
            ytd_return=0.05
        )
        
        # Verify record was inserted
        latest = db.get_latest("SPY")
        assert latest is not None
        assert latest["date"] == "2024-01-15"
        assert latest["ticker"] == "SPY"
        assert latest["close_price"] == 450.25
        assert latest["iv_30d"] == 0.18
        assert latest["rv_30d"] == 0.15
        assert latest["iv_premium"] == 0.03
        assert latest["ytd_return"] == 0.05
    
    def test_upsert_idempotency(self, db):
        """Test that upsert doesn't create duplicates for same date+ticker."""
        # Insert original record
        db.upsert_daily(
            date="2024-01-15",
            ticker="SPY",
            close_price=450.25,
            iv_30d=0.18
        )
        
        # Update same date+ticker (should replace, not duplicate)
        db.upsert_daily(
            date="2024-01-15",
            ticker="SPY",
            close_price=452.00,
            iv_30d=0.19
        )
        
        # Verify only one record exists with updated values
        history = db.get_history("SPY", lookback_days=10)
        assert len(history) == 1
        assert history.iloc[0]["close_price"] == 452.00
        assert history.iloc[0]["iv_30d"] == 0.19
    
    def test_get_latest(self, db):
        """Test retrieving latest record for a ticker."""
        # Insert multiple records for same ticker
        db.upsert_daily("2024-01-10", "SPY", 445.00, iv_30d=0.17)
        db.upsert_daily("2024-01-15", "SPY", 450.25, iv_30d=0.18)
        db.upsert_daily("2024-01-12", "SPY", 447.50, iv_30d=0.175)
        
        # Should return the latest date
        latest = db.get_latest("SPY")
        assert latest is not None
        assert latest["date"] == "2024-01-15"
        assert latest["close_price"] == 450.25
        
        # Test non-existent ticker
        latest = db.get_latest("NONEXISTENT")
        assert latest is None
    
    def test_get_history_date_range(self, db):
        """Test that get_history returns correct date range and order."""
        # Insert records with various dates
        dates = ["2024-01-01", "2024-01-05", "2024-01-10", "2024-01-15", "2024-01-20"]
        for i, date_str in enumerate(dates):
            db.upsert_daily(date_str, "SPY", 400.00 + i, iv_30d=0.15 + i * 0.01)
        
        # Get last 3 records
        history = db.get_history("SPY", lookback_days=3)
        
        assert len(history) == 3
        # Should be ordered by date ascending for time series
        assert history.iloc[0]["date"].strftime("%Y-%m-%d") == "2024-01-10"
        assert history.iloc[1]["date"].strftime("%Y-%m-%d") == "2024-01-15"
        assert history.iloc[2]["date"].strftime("%Y-%m-%d") == "2024-01-20"
    
    def test_get_all_latest(self, db):
        """Test retrieving latest record for all tickers."""
        # Insert data for multiple tickers with different latest dates
        db.upsert_daily("2024-01-10", "SPY", 445.00, iv_30d=0.17)
        db.upsert_daily("2024-01-15", "SPY", 450.25, iv_30d=0.18)
        
        db.upsert_daily("2024-01-12", "QQQ", 350.00, iv_30d=0.20)
        db.upsert_daily("2024-01-14", "QQQ", 355.00, iv_30d=0.21)
        
        db.upsert_daily("2024-01-13", "IWM", 200.00, iv_30d=0.25)
        
        all_latest = db.get_all_latest()
        
        # Should have one record per ticker
        assert len(all_latest) == 3
        assert set(all_latest["ticker"]) == {"SPY", "QQQ", "IWM"}
        
        # Should have latest dates for each ticker
        spy_row = all_latest[all_latest["ticker"] == "SPY"].iloc[0]
        assert spy_row["date"].strftime("%Y-%m-%d") == "2024-01-15"
        assert spy_row["close_price"] == 450.25
        
        qqq_row = all_latest[all_latest["ticker"] == "QQQ"].iloc[0]
        assert qqq_row["date"].strftime("%Y-%m-%d") == "2024-01-14"
        assert qqq_row["close_price"] == 355.00
    
    def test_get_snapshot(self, db):
        """Test retrieving data for specific date and ticker."""
        db.upsert_daily("2024-01-15", "SPY", 450.25, iv_30d=0.18)
        db.upsert_daily("2024-01-16", "SPY", 452.00, iv_30d=0.19)
        
        # Test exact date match
        snapshot = db.get_snapshot("2024-01-15", "SPY")
        assert snapshot is not None
        assert snapshot["date"] == "2024-01-15"
        assert snapshot["close_price"] == 450.25
        
        # Test non-existent date
        snapshot = db.get_snapshot("2024-01-01", "SPY")
        assert snapshot is None
        
        # Test non-existent ticker
        snapshot = db.get_snapshot("2024-01-15", "NONEXISTENT")
        assert snapshot is None
    
    def test_context_manager(self, temp_db):
        """Test using IVDatabase as context manager."""
        with IVDatabase(temp_db) as db:
            db.upsert_daily("2024-01-15", "SPY", 450.25)
            latest = db.get_latest("SPY")
            assert latest is not None
            assert latest["ticker"] == "SPY"
        
        # Database should be properly closed after context exit
        # We can verify this by opening a new connection
        with IVDatabase(temp_db) as db2:
            latest = db2.get_latest("SPY")
            assert latest is not None
            assert latest["ticker"] == "SPY"
    
    def test_nullable_fields(self, db):
        """Test that optional fields can be None."""
        # Insert with only required fields
        db.upsert_daily(
            date="2024-01-15",
            ticker="SPY",
            close_price=450.25
        )
        
        latest = db.get_latest("SPY")
        assert latest is not None
        assert latest["close_price"] == 450.25
        assert latest["iv_30d"] is None
        assert latest["rv_30d"] is None
        assert latest["iv_premium"] is None
        assert latest["ytd_return"] is None
    
    def test_get_all_tickers(self, db):
        """Test retrieving list of all tickers."""
        # Initially empty
        tickers = db.get_all_tickers()
        assert tickers == []
        
        # Add some tickers
        db.upsert_daily("2024-01-15", "SPY", 450.25)
        db.upsert_daily("2024-01-15", "QQQ", 350.00)
        db.upsert_daily("2024-01-15", "IWM", 200.00)
        
        tickers = db.get_all_tickers()
        assert sorted(tickers) == ["IWM", "QQQ", "SPY"]
    
    def test_delete_ticker(self, db):
        """Test deleting all data for a ticker."""
        # Add data for multiple tickers
        db.upsert_daily("2024-01-10", "SPY", 445.00)
        db.upsert_daily("2024-01-15", "SPY", 450.25)
        db.upsert_daily("2024-01-15", "QQQ", 350.00)
        
        # Verify data exists
        assert len(db.get_history("SPY", 10)) == 2
        assert db.get_latest("QQQ") is not None
        
        # Delete SPY data
        deleted_count = db.delete_ticker("SPY")
        assert deleted_count == 2
        
        # Verify SPY data is gone but QQQ remains
        assert db.get_latest("SPY") is None
        assert len(db.get_history("SPY", 10)) == 0
        assert db.get_latest("QQQ") is not None
        
        # Test deleting non-existent ticker
        deleted_count = db.delete_ticker("NONEXISTENT")
        assert deleted_count == 0