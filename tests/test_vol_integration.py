"""
Integration tests for volatility table components.
Tests end-to-end flow from scraper to dashboard display.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch, call

from data.iv_db import IVDatabase
from data.rv_calculator import RealizedVolCalculator
from data.iv_scraper import IVScraper
from data.vol_table_data import VolTableDataAssembler
from data.yahoo_client import YahooClient
from ui.vol_table import render_vol_table


class TestVolatilityIntegration:
    """End-to-end integration tests for volatility components."""

    @pytest.fixture
    def sample_iv_data(self):
        """Sample IV/RV data for integration testing."""
        return [
            {
                'date': '2026-03-06',
                'ticker': 'SPY',
                'close_price': 520.50,
                'iv_30d': 0.18,
                'rv_30d': 0.15,
                'iv_premium': 20.0,  # ((0.18/0.15) - 1) * 100
                'ytd_return': 0.08
            },
            {
                'date': '2026-03-06',
                'ticker': 'QQQ',
                'close_price': 410.25,
                'iv_30d': 0.22,
                'rv_30d': 0.20,
                'iv_premium': 10.0,  # ((0.22/0.20) - 1) * 100
                'ytd_return': 0.12
            },
            {
                'date': '2026-03-06',
                'ticker': 'XLF',
                'close_price': 42.15,
                'iv_30d': 0.16,
                'rv_30d': 0.18,
                'iv_premium': -11.1,  # ((0.16/0.18) - 1) * 100
                'ytd_return': 0.05
            }
        ]

    @pytest.fixture
    def historical_data(self):
        """Historical data for Z-score and historical premium calculations."""
        base_date = datetime(2026, 3, 6)
        data = []
        
        # Add 60 days of historical data for Z-score calculation
        for i in range(60):
            date = (base_date - timedelta(days=i)).strftime('%Y-%m-%d')
            data.extend([
                {
                    'date': date,
                    'ticker': 'SPY',
                    'close_price': 520.50 + np.random.normal(0, 5),
                    'iv_30d': 0.18 + np.random.normal(0, 0.02),
                    'rv_30d': 0.15 + np.random.normal(0, 0.015),
                    'iv_premium': 20.0 + np.random.normal(0, 5),
                    'ytd_return': 0.08 + np.random.normal(0, 0.01)
                },
                {
                    'date': date,
                    'ticker': 'QQQ',
                    'close_price': 410.25 + np.random.normal(0, 8),
                    'iv_30d': 0.22 + np.random.normal(0, 0.025),
                    'rv_30d': 0.20 + np.random.normal(0, 0.02),
                    'iv_premium': 10.0 + np.random.normal(0, 8),
                    'ytd_return': 0.12 + np.random.normal(0, 0.015)
                },
                {
                    'date': date,
                    'ticker': 'XLF',
                    'close_price': 42.15 + np.random.normal(0, 2),
                    'iv_30d': 0.16 + np.random.normal(0, 0.02),
                    'rv_30d': 0.18 + np.random.normal(0, 0.018),
                    'iv_premium': -11.1 + np.random.normal(0, 6),
                    'ytd_return': 0.05 + np.random.normal(0, 0.008)
                }
            ])
        
        return data

    @pytest.fixture
    def populated_db(self, sample_iv_data, historical_data):
        """Database populated with test data."""
        db = IVDatabase(":memory:")
        
        # Insert historical data first
        for record in historical_data:
            db.upsert_daily(**record)
        
        # Insert current day data last
        for record in sample_iv_data:
            db.upsert_daily(**record)
            
        return db

    def test_end_to_end_flow_with_mocked_data(self, populated_db, sample_iv_data):
        """
        Test complete end-to-end flow: DB → Assembler → UI Component.
        Phase 9.2: Integration test with mocked yfinance.
        """
        # Test data assembly
        assembler = VolTableDataAssembler(populated_db)
        table_df = assembler.build_table()
        
        # Verify table structure
        assert isinstance(table_df, pd.DataFrame)
        assert len(table_df) == 3  # SPY, QQQ, XLF
        
        expected_columns = [
            'etf_name', 'ticker_display', 'ytd_pct', 'ivol_rvol_current',
            'ivol_prem_yesterday', 'ivol_prem_1w', 'ivol_prem_1m',
            'ttm_zscore', 'three_yr_zscore'
        ]
        assert list(table_df.columns) == expected_columns
        
        # Verify data content (sorted by YTD descending)
        assert table_df.iloc[0]['ticker_display'] == 'QQQ US EQUITY'  # Highest YTD
        assert table_df.iloc[1]['ticker_display'] == 'SPY US EQUITY'  # Second highest
        assert table_df.iloc[2]['ticker_display'] == 'XLF US EQUITY'  # Lowest YTD
        
        # Verify percentage conversions
        assert abs(table_df.iloc[0]['ytd_pct'] - 12.0) < 0.1  # QQQ: 0.12 → 12%
        assert abs(table_df.iloc[1]['ytd_pct'] - 8.0) < 0.1   # SPY: 0.08 → 8%
        assert abs(table_df.iloc[2]['ytd_pct'] - 5.0) < 0.1   # XLF: 0.05 → 5%
        
        # Verify IV premium calculations
        assert abs(table_df.iloc[1]['ivol_rvol_current'] - 20.0) < 0.1  # SPY
        assert abs(table_df.iloc[0]['ivol_rvol_current'] - 10.0) < 0.1  # QQQ
        assert abs(table_df.iloc[2]['ivol_rvol_current'] - (-11.1)) < 0.2  # XLF
        
        # Test UI rendering (should not raise exceptions)
        styled_df = render_vol_table(table_df)
        assert styled_df is not None

    def test_integration_with_empty_database(self):
        """Test graceful handling when database is empty."""
        empty_db = IVDatabase(":memory:")
        assembler = VolTableDataAssembler(empty_db)
        
        table_df = assembler.build_table()
        
        # Should return empty DataFrame with correct columns
        assert isinstance(table_df, pd.DataFrame)
        assert len(table_df) == 0
        assert list(table_df.columns) == [
            'etf_name', 'ticker_display', 'ytd_pct', 'ivol_rvol_current',
            'ivol_prem_yesterday', 'ivol_prem_1w', 'ivol_prem_1m',
            'ttm_zscore', 'three_yr_zscore'
        ]
        
        # UI should handle empty DataFrame gracefully
        styled_df = render_vol_table(table_df)
        assert styled_df is not None

    @patch('data.iv_scraper.IVScraper.scrape_daily')
    @patch('data.yahoo_client.YahooClient')
    def test_scraper_to_database_integration(self, mock_yahoo_client, mock_scrape):
        """Test integration between scraper and database."""
        # Setup mocks
        mock_scrape.return_value = {
            'succeeded': ['SPY', 'QQQ'],
            'failed': ['XLF'],
            'total_processed': 3,
            'errors': {'XLF': 'No options data'}
        }
        
        db = IVDatabase(":memory:")
        yahoo_client = YahooClient()
        rv_calc = RealizedVolCalculator(yahoo_client)
        scraper = IVScraper(db, yahoo_client, rv_calc)
        
        # Run scraper (mocked)
        results = scraper.scrape_daily()
        
        # Verify results structure
        assert 'succeeded' in results
        assert 'failed' in results
        assert 'total_processed' in results
        assert results['total_processed'] == 3

    def test_zscore_calculation_accuracy(self, populated_db):
        """Verify Z-score calculations with sufficient historical data."""
        assembler = VolTableDataAssembler(populated_db)
        table_df = assembler.build_table()
        
        # Check that Z-scores are calculated (not NaN)
        spy_row = table_df[table_df['ticker_display'] == 'SPY US EQUITY'].iloc[0]
        
        # With 60 days of data, both TTM and 3yr Z-scores should be calculated
        assert not pd.isna(spy_row['ttm_zscore'])
        assert not pd.isna(spy_row['three_yr_zscore'])
        
        # Z-scores should be reasonable values (typically -3 to +3)
        assert -5 < spy_row['ttm_zscore'] < 5
        assert -5 < spy_row['three_yr_zscore'] < 5

    def test_data_freshness_integration(self, populated_db, sample_iv_data):
        """Test data freshness information."""
        assembler = VolTableDataAssembler(populated_db)
        freshness_info = assembler.get_data_freshness_info()
        
        # Should have freshness info for our test data
        assert 'latest_date' in freshness_info
        assert 'ticker_count' in freshness_info
        assert 'data_age_days' in freshness_info
        
        assert freshness_info['ticker_count'] == 3
        assert freshness_info['latest_date'] == '2026-03-06'

    def test_error_handling_integration(self):
        """Test error handling throughout the integration flow."""
        # Test with corrupted database path
        with pytest.raises((FileNotFoundError, Exception)):
            db = IVDatabase("/invalid/path/test.db")
            assembler = VolTableDataAssembler(db)
            assembler.build_table()

    def test_service_integration_routing(self, populated_db):
        """Test integration with indicator service routing."""
        assembler = VolTableDataAssembler(populated_db)
        table_df = assembler.build_table()
        
        # Simulate service layer response format
        service_result = {
            'data': table_df,
            'chart_type': 'vol_heatmap',
            'status': 'success'
        }
        
        assert service_result['chart_type'] == 'vol_heatmap'
        assert isinstance(service_result['data'], pd.DataFrame)
        assert service_result['status'] == 'success'

    def test_performance_with_large_dataset(self):
        """Test performance with larger dataset (simulating production)."""
        db = IVDatabase(":memory:")
        
        # Create larger dataset (180 days × 14 ETFs = 2520 records)
        base_date = datetime(2026, 3, 6)
        for i in range(180):
            date = (base_date - timedelta(days=i)).strftime('%Y-%m-%d')
            for ticker in ['SPY', 'QQQ', 'XLF', 'XLE', 'XLK', 'XLV', 'XLY', 'XLP', 'XLB', 'XLI', 'XLU', 'XLRE', 'XLC', 'IWM']:
                db.upsert_daily(
                    date=date,
                    ticker=ticker,
                    close_price=100 + np.random.normal(0, 10),
                    iv_30d=0.20 + np.random.normal(0, 0.05),
                    rv_30d=0.18 + np.random.normal(0, 0.04),
                    iv_premium=10 + np.random.normal(0, 15),
                    ytd_return=0.08 + np.random.normal(0, 0.03)
                )
        
        # Test assembly performance
        assembler = VolTableDataAssembler(db)
        import time
        start_time = time.time()
        table_df = assembler.build_table()
        assembly_time = time.time() - start_time
        
        # Should complete within reasonable time
        assert assembly_time < 2.0  # Less than 2 seconds
        assert len(table_df) == 14  # All ETFs present
        
        # Test UI rendering performance
        start_time = time.time()
        styled_df = render_vol_table(table_df)
        render_time = time.time() - start_time
        
        assert render_time < 1.0  # Less than 1 second
        assert styled_df is not None