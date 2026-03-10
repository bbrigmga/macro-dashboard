"""
Realized Volatility Calculator for computing annualized volatility from price history.
"""
import pandas as pd
import numpy as np
import logging
from typing import Optional, Dict, List
from data.yahoo_client import YahooClient

# Set up logging
logger = logging.getLogger(__name__)

class RealizedVolCalculator:
    """Calculator for realized volatility metrics using historical price data."""
    
    def __init__(self, yahoo_client: YahooClient):
        """
        Initialize the calculator with a YahooClient instance.
        
        Args:
            yahoo_client (YahooClient): Client for fetching price data
        """
        self.yahoo_client = yahoo_client
        logger.info("RealizedVolCalculator initialized")
    
    def calculate_rv(self, prices: pd.Series, window: int = 30) -> float:
        """
        Calculate annualized realized volatility from a price series.
        
        Args:
            prices (pd.Series): Series of closing prices
            window (int): Number of periods to calculate volatility over (default: 30)
        
        Returns:
            float: Annualized realized volatility as decimal (e.g., 0.18 = 18%)
        """
        if len(prices) < window + 1:
            logger.warning(f"Insufficient price data: {len(prices)} prices for window {window}")
            return np.nan
        
        # Calculate daily log returns
        daily_returns = np.log(prices / prices.shift(1))
        
        # Take the last 'window' returns and calculate volatility
        recent_returns = daily_returns.tail(window)
        
        # Annualize using sqrt(252) for trading days
        rv = recent_returns.std() * np.sqrt(252)
        
        logger.debug(f"Calculated RV: {rv:.4f} from {len(recent_returns)} returns")
        return rv
    
    def get_rv_for_ticker(self, ticker: str, window: int = 30) -> Optional[float]:
        """
        Get realized volatility for a single ticker.
        
        Args:
            ticker (str): Yahoo Finance ticker symbol
            window (int): Number of days for RV calculation (default: 30)
        
        Returns:
            float | None: Annualized realized volatility, or None if calculation fails
        """
        try:
            # Fetch additional days to ensure we have enough data after weekends/holidays
            periods = window + 10  # Buffer for weekends/holidays
            
            df = self.yahoo_client.get_historical_prices(
                ticker=ticker, 
                periods=periods,
                frequency='1d'
            )
            
            if df is None or df.empty:
                logger.warning(f"No price data returned for {ticker}")
                return None
            
            if len(df) < window + 1:
                logger.warning(f"Insufficient price history for {ticker}: {len(df)} days")
                return None
            
            # Extract prices (YahooClient returns 'value' column with Close prices)
            prices = df['value']
            
            rv = self.calculate_rv(prices, window)
            
            if np.isnan(rv):
                logger.warning(f"Failed to calculate RV for {ticker}")
                return None
            
            logger.info(f"Calculated RV for {ticker}: {rv:.4f} ({rv*100:.2f}%)")
            return rv
            
        except Exception as e:
            logger.error(f"Error calculating RV for {ticker}: {str(e)}")
            return None
    
    def get_rv_batch(self, tickers: List[str], window: int = 30) -> Dict[str, Optional[float]]:
        """
        Calculate realized volatility for multiple tickers.
        
        Args:
            tickers (List[str]): List of Yahoo Finance ticker symbols
            window (int): Number of days for RV calculation (default: 30)
        
        Returns:
            Dict[str, float | None]: Dictionary mapping ticker to RV value (None for failures)
        """
        logger.info(f"Calculating RV for {len(tickers)} tickers with {window}-day window")
        
        results = {}
        success_count = 0
        
        for ticker in tickers:
            rv = self.get_rv_for_ticker(ticker, window)
            results[ticker] = rv
            
            if rv is not None:
                success_count += 1
        
        logger.info(f"RV batch calculation complete: {success_count}/{len(tickers)} successful")
        return results