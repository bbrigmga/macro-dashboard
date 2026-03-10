"""
Tests for IV Scraper functionality.

Tests implied volatility extraction from yfinance options chains
with comprehensive mocking and edge case coverage.
"""
import datetime as dt
from unittest.mock import Mock, patch, MagicMock
import numpy as np
import pandas as pd
import pytest

from data.iv_scraper import IVScraper, ETF_UNIVERSE, run_scraper
from data.iv_db import IVDatabase


@pytest.fixture
def mock_db():
    """Mock IVDatabase instance."""
    db = Mock(spec=IVDatabase)
    db.__enter__ = Mock(return_value=db)
    db.__exit__ = Mock(return_value=None)
    return db


@pytest.fixture
def mock_yahoo_client():
    """Mock YahooClient instance."""
    return Mock()


@pytest.fixture
def mock_rv_calculator():
    """Mock RealizedVolCalculator instance."""
    calc = Mock()
    calc.get_rv_for_ticker.return_value = 0.20  # 20% annualized RV
    return calc


@pytest.fixture
def iv_scraper(mock_db):
    """IV scraper instance with mocked dependencies."""
    with patch('data.iv_scraper.YahooClient') as mock_yc_class, \
         patch('data.iv_scraper.RealizedVolCalculator') as mock_rv_class:
        
        scraper = IVScraper(mock_db)
        return scraper


def create_mock_options_chain(strikes, call_ivs, put_ivs):
    """
    Create mock options chain data.
    
    Args:
        strikes: List of strike prices
        call_ivs: List of call implied volatilities (same length as strikes)
        put_ivs: List of put implied volatilities (same length as strikes)
        
    Returns:
        Mock options chain object with calls and puts DataFrames
    """
    calls_data = {
        'strike': strikes,
        'impliedVolatility': call_ivs
    }
    
    puts_data = {
        'strike': strikes,
        'impliedVolatility': put_ivs
    }
    
    chain = Mock()
    chain.calls = pd.DataFrame(calls_data)
    chain.puts = pd.DataFrame(puts_data)
    
    return chain


class TestIVScraper:
    """Test cases for IVScraper functionality."""
    
    def test_etf_universe_constants(self):
        """Test that ETF universe contains expected tickers."""
        expected_tickers = {
            'XLRE', 'XLF', 'XLE', 'XLC', 'XLK', 'QQQ', 'SPY',
            'XLV', 'XLB', 'XLI', 'XLY', 'IWM', 'XLU', 'XLP'
        }
        
        actual_tickers = {etf['ticker'] for etf in ETF_UNIVERSE}
        assert actual_tickers == expected_tickers
        
        # Check that all entries have both ticker and name
        for etf in ETF_UNIVERSE:
            assert 'ticker' in etf
            assert 'name' in etf
            assert isinstance(etf['ticker'], str)
            assert isinstance(etf['name'], str)
            assert len(etf['ticker']) > 0
            assert len(etf['name']) > 0

    def test_days_to_expiration(self, iv_scraper):
        """Test calculation of days to expiration."""
        today = dt.date.today()
        
        # Test future date
        future_date = (today + dt.timedelta(days=30)).strftime('%Y-%m-%d')
        dte = iv_scraper._days_to_expiration(future_date)
        assert dte == 30
        
        # Test past date
        past_date = (today - dt.timedelta(days=10)).strftime('%Y-%m-%d')
        dte = iv_scraper._days_to_expiration(past_date)
        assert dte == -10
        
        # Test today
        today_str = today.strftime('%Y-%m-%d')
        dte = iv_scraper._days_to_expiration(today_str)
        assert dte == 0
        
        # Test invalid date format
        dte = iv_scraper._days_to_expiration('invalid-date')
        assert dte == 0

    def test_find_atm_strike(self, iv_scraper):
        """Test ATM strike selection logic."""
        current_price = 100.0
        
        # Test exact match
        strikes = [95.0, 100.0, 105.0]
        atm = iv_scraper._find_atm_strike(current_price, strikes)
        assert atm == 100.0
        
        # Test between strikes (closer to lower)
        strikes = [95.0, 105.0]
        current_price = 98.0
        atm = iv_scraper._find_atm_strike(current_price, strikes)
        assert atm == 95.0
        
        # Test between strikes (closer to upper)
        current_price = 103.0
        atm = iv_scraper._find_atm_strike(current_price, strikes)
        assert atm == 105.0
        
        # Test empty strikes list
        atm = iv_scraper._find_atm_strike(current_price, [])
        assert atm == current_price

    def test_get_iv_at_strike(self, iv_scraper):
        """Test IV extraction at specific strike."""
        # Create test options data
        options_data = pd.DataFrame({
            'strike': [95.0, 100.0, 105.0],
            'impliedVolatility': [0.25, 0.20, 0.22]
        })
        
        # Test exact strike match — returns (iv, quality_dict) tuple
        result = iv_scraper._get_iv_at_strike(options_data, 100.0)
        assert result[0] == 0.20
        
        # Test nearby strike fallback
        result = iv_scraper._get_iv_at_strike(options_data, 101.0)
        assert result[0] == 0.20  # Should find 100.0 as closest within 5%
        
        # Test no valid IV (NaN)
        invalid_data = pd.DataFrame({
            'strike': [100.0],
            'impliedVolatility': [np.nan]
        })
        result = iv_scraper._get_iv_at_strike(invalid_data, 100.0)
        assert result is None
        
        # Test empty DataFrame
        empty_data = pd.DataFrame()
        result = iv_scraper._get_iv_at_strike(empty_data, 100.0)
        assert result is None

    @patch('data.iv_scraper.yf.Ticker')
    def test_get_current_price(self, mock_yf_ticker, iv_scraper):
        """Test current price extraction."""
        # Ensure YahooClient cache returns empty so we fall through to yfinance
        iv_scraper.yahoo_client.get_historical_prices.return_value = pd.DataFrame()

        # Test successful price from fast_info.last_price (yfinance 1.x attribute)
        mock_ticker_instance = Mock()
        mock_ticker_instance.fast_info = Mock(last_price=150.50)
        mock_yf_ticker.return_value = mock_ticker_instance
        
        price = iv_scraper._get_current_price('SPY')
        assert price == 150.50
        
        # Test fallback to info dict when fast_info.last_price is None/falsy
        mock_ticker_instance.fast_info = Mock(last_price=None)
        mock_ticker_instance.info = {'currentPrice': 151.25}
        
        price = iv_scraper._get_current_price('SPY')
        assert price == 151.25
        
        # Test no price available
        mock_ticker_instance.fast_info = Mock(last_price=None)
        mock_ticker_instance.info = {}
        
        price = iv_scraper._get_current_price('SPY')
        assert price is None
        
        # Test exception handling
        mock_yf_ticker.side_effect = Exception("Network error")
        
        price = iv_scraper._get_current_price('SPY')
        assert price is None

    def test_extract_iv_for_expiration(self, iv_scraper):
        """Test IV extraction for specific expiration."""
        # Mock _get_option_chain_direct (replaces yf.Ticker.option_chain)
        calls_df = pd.DataFrame({
            'strike': [95.0, 100.0, 105.0],
            'impliedVolatility': [0.25, 0.20, 0.22],
        })
        puts_df = pd.DataFrame({
            'strike': [95.0, 100.0, 105.0],
            'impliedVolatility': [0.26, 0.21, 0.23],
        })

        with patch.object(iv_scraper, '_get_option_chain_direct', return_value=(calls_df, puts_df)):
            # Test normal case — returns (iv, quality_dict) tuple
            result = iv_scraper._extract_iv_for_expiration('SPY', '2024-04-19', 100.0)
            expected_iv = (0.20 + 0.21) / 2.0  # Average at ATM strike 100.0
            assert abs(result[0] - expected_iv) < 1e-6

        # Test only calls available
        with patch.object(iv_scraper, '_get_option_chain_direct', return_value=(calls_df, pd.DataFrame())):
            result = iv_scraper._extract_iv_for_expiration('SPY', '2024-04-19', 100.0)
            assert result[0] == 0.20  # Should use call IV only

        # Test no options available
        with patch.object(iv_scraper, '_get_option_chain_direct', return_value=(pd.DataFrame(), pd.DataFrame())):
            result = iv_scraper._extract_iv_for_expiration('SPY', '2024-04-19', 100.0)
            assert result is None

    def test_get_atm_iv_single_expiration(self, iv_scraper):
        """Test ATM IV extraction with single expiration."""
        future_date = (dt.date.today() + dt.timedelta(days=30)).strftime('%Y-%m-%d')

        calls_df = pd.DataFrame({'strike': [95.0, 100.0, 105.0], 'impliedVolatility': [0.25, 0.20, 0.22]})
        puts_df  = pd.DataFrame({'strike': [95.0, 100.0, 105.0], 'impliedVolatility': [0.26, 0.21, 0.23]})

        with patch.object(iv_scraper, '_get_current_price', return_value=100.0), \
             patch.object(iv_scraper, '_get_option_expirations', return_value=(future_date,)), \
             patch.object(iv_scraper, '_get_option_chain_direct', return_value=(calls_df, puts_df)):
            result = iv_scraper._get_atm_iv('SPY')

        expected_iv = (0.20 + 0.21) / 2.0  # Average at ATM strike
        assert abs(result[0] - expected_iv) < 1e-6

    def test_get_atm_iv_interpolation(self, iv_scraper):
        """Test ATM IV with interpolation between two expirations."""
        # Two expirations: 25 days and 35 days (bracketing 30)
        date_25d = (dt.date.today() + dt.timedelta(days=25)).strftime('%Y-%m-%d')
        date_35d = (dt.date.today() + dt.timedelta(days=35)).strftime('%Y-%m-%d')

        chain_25d = (pd.DataFrame({'strike': [100.0], 'impliedVolatility': [0.20]}),
                     pd.DataFrame({'strike': [100.0], 'impliedVolatility': [0.20]}))
        chain_35d = (pd.DataFrame({'strike': [100.0], 'impliedVolatility': [0.30]}),
                     pd.DataFrame({'strike': [100.0], 'impliedVolatility': [0.30]}))

        def mock_chain_direct(ticker, exp_date):
            return chain_25d if exp_date == date_25d else chain_35d

        with patch.object(iv_scraper, '_get_current_price', return_value=100.0), \
             patch.object(iv_scraper, '_get_option_expirations', return_value=(date_25d, date_35d)), \
             patch.object(iv_scraper, '_get_option_chain_direct', side_effect=mock_chain_direct):
            result = iv_scraper._get_atm_iv('SPY')

        # Should interpolate between 0.20 (25d) and 0.30 (35d) for 30d target
        # Weight = (30 - 25) / (35 - 25) = 0.5
        # Interpolated = 0.20 + 0.5 * (0.30 - 0.20) = 0.25
        expected_iv = 0.25
        assert abs(result[0] - expected_iv) < 1e-6

    def test_get_atm_iv_edge_cases(self, iv_scraper):
        """Test ATM IV edge cases."""
        # Test no options available (empty expirations)
        with patch.object(iv_scraper, '_get_current_price', return_value=100.0), \
             patch.object(iv_scraper, '_get_option_expirations', return_value=()):
            iv = iv_scraper._get_atm_iv('SPY')
            assert iv is None

        # Test _get_option_expirations raises exception
        with patch.object(iv_scraper, '_get_current_price', return_value=100.0), \
             patch.object(iv_scraper, '_get_option_expirations', side_effect=Exception("No options")):
            iv = iv_scraper._get_atm_iv('SPY')
            assert iv is None

    def test_get_ytd_return_success(self, iv_scraper):
        """Test YTD return calculation success."""
        # Create mock price data using get_historical_prices format
        price_data = pd.DataFrame({
            'Date': pd.date_range('2024-01-01', periods=4, freq='D'),
            'value': [100.0, 105.0, 110.0, 115.0]  # 15% return
        })
        
        iv_scraper.yahoo_client.get_historical_prices.return_value = price_data
        
        ytd_return = iv_scraper._get_ytd_return('SPY')
        expected_return = (115.0 / 100.0) - 1.0  # 15%
        assert abs(ytd_return - expected_return) < 1e-6

    def test_get_ytd_return_no_data(self, iv_scraper):
        """Test YTD return with no price data."""
        iv_scraper.yahoo_client.get_historical_prices.return_value = pd.DataFrame()
        
        ytd_return = iv_scraper._get_ytd_return('SPY')
        assert ytd_return is None

    @patch.object(IVScraper, '_get_current_price')
    @patch.object(IVScraper, '_get_atm_iv')
    @patch.object(IVScraper, '_get_ytd_return')
    def test_scrape_daily_success(self, mock_ytd, mock_iv, mock_price, iv_scraper):
        """Test successful daily scraping."""
        # Mock successful responses
        mock_price.return_value = 150.0
        mock_iv.return_value = (0.25, {'quality_score': 80.0, 'volume': 100, 'bid_ask_spread_pct': 5.0})
        mock_ytd.return_value = 0.15
        # Ensure get_latest returns None so today's skip check doesn't trigger
        iv_scraper.db.get_latest.return_value = None
        
        # Mock RV calculator
        iv_scraper.rv_calculator.get_rv_for_ticker.return_value = 0.20
        
        # Run scraper with small subset for testing
        original_universe = ETF_UNIVERSE[:]
        ETF_UNIVERSE.clear()
        ETF_UNIVERSE.extend([{"ticker": "SPY", "name": "SPDR S&P 500 Trust"}])
        
        try:
            result = iv_scraper.scrape_daily()
            
            # Verify results
            assert result['success'] == 1
            assert result['failed'] == 0
            assert result['total'] == 1
            assert result['failed_tickers'] == []
            
            # Verify database was called
            iv_scraper.db.upsert_daily.assert_called_once()
            call_args = iv_scraper.db.upsert_daily.call_args[1]
            
            assert call_args['ticker'] == 'SPY'
            assert call_args['close_price'] == 150.0
            assert call_args['iv_30d'] == 0.25
            assert call_args['rv_30d'] == 0.20
            assert abs(call_args['iv_premium'] - 25.0) < 1e-6  # ((0.25/0.20)-1)*100
            assert call_args['ytd_return'] == 0.15
            
        finally:
            # Restore original universe
            ETF_UNIVERSE.clear()
            ETF_UNIVERSE.extend(original_universe)

    @patch.object(IVScraper, '_get_current_price')
    def test_scrape_daily_failures(self, mock_price, iv_scraper):
        """Test scraping with failures."""
        # Mock failure
        mock_price.return_value = None
        
        # Run scraper with small subset
        original_universe = ETF_UNIVERSE[:]
        ETF_UNIVERSE.clear()
        ETF_UNIVERSE.extend([{"ticker": "TEST", "name": "Test ETF"}])
        
        try:
            result = iv_scraper.scrape_daily()
            
            # Verify failure handling
            assert result['success'] == 0
            assert result['failed'] == 1
            assert result['total'] == 1
            assert 'TEST' in result['failed_tickers']
            
            # Verify database was not called
            iv_scraper.db.upsert_daily.assert_not_called()
            
        finally:
            # Restore original universe
            ETF_UNIVERSE.clear()
            ETF_UNIVERSE.extend(original_universe)


@patch('data.iv_scraper.IVDatabase')
@patch('data.iv_scraper.IVScraper')
def test_run_scraper_function(mock_scraper_class, mock_db_class):
    """Test standalone run_scraper function."""
    # Mock the scraper instance and its scrape_daily method
    mock_scraper_instance = Mock()
    mock_scraper_instance.scrape_daily.return_value = {
        'success': 12,
        'failed': 2,
        'total': 14,
        'failed_tickers': ['TEST1', 'TEST2']
    }
    mock_scraper_class.return_value = mock_scraper_instance
    
    # Mock the database instance
    mock_db_instance = Mock()
    mock_db_class.return_value = mock_db_instance
    
    result = run_scraper()
    
    # Verify components were initialized
    mock_db_class.assert_called_once()
    mock_scraper_class.assert_called_once_with(mock_db_instance)
    
    # Verify scraping was called
    mock_scraper_instance.scrape_daily.assert_called_once()
    
    # Verify result
    assert result['success'] == 12
    assert result['failed'] == 2
    assert result['total'] == 14
    assert result['failed_tickers'] == ['TEST1', 'TEST2']


@patch('data.iv_scraper.IVScraper')
def test_run_scraper_exception(mock_scraper_class):
    """Test run_scraper with exception handling."""
    # Mock scraper to raise exception
    mock_scraper_class.side_effect = Exception("Database connection failed")
    
    result = run_scraper()
    
    # Should return empty result on failure
    assert result['success'] == 0
    assert result['failed'] == 0
    assert result['total'] == 0
    assert result['failed_tickers'] == []