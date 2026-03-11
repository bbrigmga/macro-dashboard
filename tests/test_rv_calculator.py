"""
Tests for the RealizedVolCalculator class.
"""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, MagicMock
from data.rv_calculator import RealizedVolCalculator
from data.yahoo_client import YahooClient

class TestRealizedVolCalculator:
    """Test suite for RealizedVolCalculator."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.mock_yahoo_client = Mock(spec=YahooClient)
        self.calculator = RealizedVolCalculator(self.mock_yahoo_client)
    
    def test_calculate_rv_constant_prices(self):
        """Test RV calculation with constant prices (should return 0)."""
        # Create price series with constant values
        constant_prices = pd.Series([100.0] * 50)
        
        rv = self.calculator.calculate_rv(constant_prices, window=30)
        
        # Constant prices should yield zero volatility
        assert rv == 0.0
    
    def test_calculate_rv_synthetic_data(self):
        """Test RV calculation with synthetic data of known volatility."""
        # Create synthetic price path with known daily volatility
        np.random.seed(42)  # For reproducible tests
        n_days = 100
        daily_vol = 0.02  # 2% daily volatility
        
        # Generate log returns with known volatility
        returns = np.random.normal(0, daily_vol, n_days)
        
        # Convert to price series starting at 100
        log_prices = np.cumsum(returns) + np.log(100)
        prices = pd.Series(np.exp(log_prices))
        
        rv = self.calculator.calculate_rv(prices, window=30)
        
        # Check that calculated RV is close to expected annualized volatility
        # Expected: daily_vol * sqrt(252) = 0.02 * ~15.87 ≈ 0.317
        expected = daily_vol * np.sqrt(252)
        
        # Allow for sampling variance in random data
        assert abs(rv - expected) < 0.1, f"RV {rv:.4f} too far from expected {expected:.4f}"
    
    def test_calculate_rv_annualization_factor(self):
        """Test that annualization factor is correct (sqrt(252))."""
        # Create simple price series with known daily standard deviation
        # Prices: [100, 102, 98, 101, 99, ...] alternating pattern
        prices = pd.Series([100 + 2 * ((-1) ** i) for i in range(50)])
        
        # Calculate daily returns manually
        price_ratios = (prices / prices.shift(1))
        daily_returns = pd.Series(np.log(price_ratios)).dropna()
        
        # Manual calculation
        manual_daily_std = daily_returns.tail(30).std()
        manual_annualized = manual_daily_std * np.sqrt(252)
        
        # Calculator result
        rv = self.calculator.calculate_rv(prices, window=30)
        
        # Should match manual calculation
        assert abs(rv - manual_annualized) < 1e-10
    
    def test_calculate_rv_insufficient_data(self):
        """Test handling of insufficient price data."""
        # Only 20 prices for a 30-day window
        insufficient_prices = pd.Series(range(100, 120))
        
        rv = self.calculator.calculate_rv(insufficient_prices, window=30)
        
        assert np.isnan(rv)
    
    def test_get_rv_for_ticker_success(self):
        """Test successful RV calculation for a single ticker."""
        # Mock YahooClient to return sample price data
        sample_data = pd.DataFrame({
            'Date': pd.date_range('2024-01-01', periods=50, freq='D'),
            'value': [100 + i + np.random.normal(0, 2) for i in range(50)]
        })
        self.mock_yahoo_client.get_historical_prices.return_value = sample_data
        
        rv = self.calculator.get_rv_for_ticker('SPY', window=30)
        
        # Should return a valid float
        assert isinstance(rv, float)
        assert not np.isnan(rv)
        assert rv > 0  # Volatility should be positive
        
        # Verify YahooClient was called correctly
        self.mock_yahoo_client.get_historical_prices.assert_called_once_with(
            ticker='SPY',
            periods=40,  # window + 10 buffer
            frequency='1d'
        )
    
    def test_get_rv_for_ticker_no_data(self):
        """Test handling when YahooClient returns no data."""
        self.mock_yahoo_client.get_historical_prices.return_value = pd.DataFrame()
        
        rv = self.calculator.get_rv_for_ticker('INVALID', window=30)
        
        assert rv is None
    
    def test_get_rv_for_ticker_insufficient_history(self):
        """Test handling when price history is too short."""
        # Return only 20 days of data for 30-day window
        short_data = pd.DataFrame({
            'Date': pd.date_range('2024-01-01', periods=20, freq='D'),
            'value': range(100, 120)
        })
        self.mock_yahoo_client.get_historical_prices.return_value = short_data
        
        rv = self.calculator.get_rv_for_ticker('SPY', window=30)
        
        assert rv is None
    
    def test_get_rv_for_ticker_exception(self):
        """Test handling of exceptions during data retrieval."""
        self.mock_yahoo_client.get_historical_prices.side_effect = Exception("Network error")
        
        rv = self.calculator.get_rv_for_ticker('SPY', window=30)
        
        assert rv is None
    
    def test_get_rv_batch_mixed_results(self):
        """Test batch RV calculation with mixed success/failure."""
        tickers = ['SPY', 'QQQ', 'INVALID', 'VIX']
        
        def mock_get_historical_prices(ticker, periods, frequency):
            if ticker == 'SPY':
                return pd.DataFrame({
                    'Date': pd.date_range('2024-01-01', periods=50, freq='D'),
                    'value': [100 + i * 0.1 for i in range(50)]
                })
            elif ticker == 'QQQ':
                return pd.DataFrame({
                    'Date': pd.date_range('2024-01-01', periods=50, freq='D'),
                    'value': [300 + i * 0.5 for i in range(50)]
                })
            elif ticker == 'INVALID':
                return pd.DataFrame()  # No data
            elif ticker == 'VIX':
                raise Exception("API Error")  # Exception
        
        self.mock_yahoo_client.get_historical_prices.side_effect = mock_get_historical_prices
        
        results = self.calculator.get_rv_batch(tickers, window=30)
        
        # Check results structure
        assert len(results) == 4
        assert set(results.keys()) == set(tickers)
        
        # SPY and QQQ should succeed
        assert results['SPY'] is not None
        assert results['QQQ'] is not None
        assert isinstance(results['SPY'], float)
        assert isinstance(results['QQQ'], float)
        
        # INVALID and VIX should fail
        assert results['INVALID'] is None
        assert results['VIX'] is None
    
    def test_get_rv_batch_empty_list(self):
        """Test batch calculation with empty ticker list."""
        results = self.calculator.get_rv_batch([])
        
        assert results == {}
    
    def test_get_rv_batch_all_success(self):
        """Test batch calculation where all tickers succeed."""
        tickers = ['SPY', 'QQQ']
        
        # Mock all tickers to return valid data
        sample_data = pd.DataFrame({
            'Date': pd.date_range('2024-01-01', periods=50, freq='D'),
            'value': [100 + i * 0.1 for i in range(50)]
        })
        self.mock_yahoo_client.get_historical_prices.return_value = sample_data
        
        results = self.calculator.get_rv_batch(tickers, window=30)
        
        # All should succeed
        assert len(results) == 2
        assert all(results[ticker] is not None for ticker in tickers)
        assert all(isinstance(results[ticker], float) for ticker in tickers)
    
    def test_different_window_sizes(self):
        """Test RV calculation with different window sizes."""
        # Create price series with consistent returns pattern
        prices = pd.Series([100 * (1.01 ** i) for i in range(100)])  # 1% daily growth
        
        rv_10 = self.calculator.calculate_rv(prices, window=10)
        rv_30 = self.calculator.calculate_rv(prices, window=30)
        rv_60 = self.calculator.calculate_rv(prices, window=60)
        
        # All should be valid numbers
        assert not np.isnan(rv_10)
        assert not np.isnan(rv_30)
        assert not np.isnan(rv_60)
        
        # Longer windows typically give different (often lower) volatility estimates
        assert rv_10 > 0
        assert rv_30 > 0
        assert rv_60 > 0