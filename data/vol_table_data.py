"""
Volatility Table Data Assembly

Combines database data into display-ready DataFrame matching the spec's column layout.
This module assembles IV/RV data from the database and calculates Z-scores for the
volatility table display component.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
from typing import Optional
import logging

from .iv_db import IVDatabase
from .market_utils import get_previous_trading_day, get_approximate_trading_day
from .volatility_logging import get_volatility_logger, log_performance_metric

# Set up enhanced logging
logger = get_volatility_logger(__name__)

# ETF Universe constant from Phase 3
ETF_UNIVERSE = [
    {"ticker": "XLRE", "name": "Real Estate Sector SPDR ETF"},
    {"ticker": "XLF",  "name": "Financials Sector SPDR ETF"},
    {"ticker": "XLE",  "name": "Energy Sector SPDR ETF"},
    {"ticker": "XLC",  "name": "Communication Services SPDR ETF"},
    {"ticker": "XLK",  "name": "Technology Sector SPDR ETF"},
    {"ticker": "QQQ",  "name": "Power Shares QQQ Trust ETF"},
    {"ticker": "SPY",  "name": "SPDR S&P 500 Trust"},
    {"ticker": "XLV",  "name": "Health Care Sector SPDR ETF"},
    {"ticker": "XLB",  "name": "Materials Sector SPDR ETF"},
    {"ticker": "XLI",  "name": "Industrials Sector SPDR ETF"},
    {"ticker": "XLY",  "name": "Consumer Discretionary SPDR ETF"},
    {"ticker": "IWM",  "name": "I-Shares Russell 2000"},
    {"ticker": "XLU",  "name": "Utilities Sector SPDR ETF"},
    {"ticker": "XLP",  "name": "Consumer Staples Sector SPDR ETF"},
]

# Create lookup dict for ETF names
ETF_NAME_LOOKUP = {etf["ticker"]: etf["name"] for etf in ETF_UNIVERSE}


class VolTableDataAssembler:
    """
    Assembles volatility table data from the database into a display-ready format.
    
    Produces DataFrame with columns:
    - etf_name: ETF display name
    - ticker_display: Formatted ticker (e.g., "SPY US EQUITY")
    - ytd_pct: Year-to-date return percentage
    - ivol_rvol_current: Current IV premium percentage
    - ivol_prem_yesterday: IV premium from previous trading day  
    - ivol_prem_1w: IV premium from 1 week ago
    - ivol_prem_1m: IV premium from 1 month ago
    - ttm_zscore: Z-score over trailing 252 trading days
    - three_yr_zscore: Z-score over trailing 756 trading days
    """
    
    def __init__(self, db: IVDatabase):
        """
        Initialize with database connection.
        
        Args:
            db: IVDatabase instance for data retrieval
        """
        self.db = db
    
    def build_table(self) -> pd.DataFrame:
        """
        Build the complete volatility table DataFrame.
        
        Returns:
            DataFrame with all required columns, sorted by ytd_pct descending
        """
        import time
        start_time = time.time()
        logger.info("Building volatility table data")
        
        # Get all universe tickers for batch operations
        universe_tickers = [etf["ticker"] for etf in ETF_UNIVERSE]
        
        # Use batch method to get latest data for all tickers at once
        latest_data = self.db.get_multiple_latest(universe_tickers)
        
        if latest_data.empty:
            logger.warning("No data available in database")
            # Return empty DataFrame with correct schema
            return pd.DataFrame(columns=[
                'etf_name', 'ticker_display', 'ytd_pct', 'ivol_rvol_current',
                'ivol_prem_yesterday', 'ivol_prem_1w', 'ivol_prem_1m',
                'ttm_zscore', 'three_yr_zscore'
            ])
        
        # Batch fetch historical data for all tickers at once (3 years max)
        # This is much more efficient than individual queries per ticker
        batch_start = time.time()
        all_history = self.db.get_multiple_history(universe_tickers, lookback_days=756)
        batch_duration = time.time() - batch_start
        
        log_performance_metric(
            "vol_table_batch_fetch", 
            batch_duration, 
            "seconds",
            context={'tickers': len(universe_tickers), 'history_records': len(all_history)}
        )
        
        # Group historical data by ticker for fast lookup
        history_by_ticker = {}
        if not all_history.empty:
            history_grouped = all_history.groupby('ticker')
            for ticker, group in history_grouped:
                # Sort by date descending (newest first) for consistent access patterns
                history_by_ticker[ticker] = group.sort_values('date', ascending=False).reset_index(drop=True)
        
        # Build the table rows using pre-fetched data
        rows = []
        for _, row in latest_data.iterrows():
            ticker = row['ticker']
            ticker_history = history_by_ticker.get(ticker, pd.DataFrame())
            table_row = self._build_ticker_row_optimized(row, ticker_history)
            if table_row is not None:
                rows.append(table_row)
        
        if not rows:
            logger.warning("No valid rows could be built")
            return pd.DataFrame(columns=[
                'etf_name', 'ticker_display', 'ytd_pct', 'ivol_rvol_current',
                'ivol_prem_yesterday', 'ivol_prem_1w', 'ivol_prem_1m',
                'ttm_zscore', 'three_yr_zscore'
            ])
        
        # Create DataFrame and sort
        df = pd.DataFrame(rows)
        df = df.sort_values('ytd_pct', ascending=False).reset_index(drop=True)
        
        # Log overall performance
        total_duration = time.time() - start_time
        log_performance_metric(
            "vol_table_build_total", 
            total_duration, 
            "seconds",
            context={'rows_built': len(df), 'tickers_available': len(latest_data)}
        )
        
        logger.info(f"Built volatility table with {len(df)} rows using optimized batch queries in {total_duration:.2f}s")
        return df
    
    def _build_ticker_row_optimized(self, latest_row: pd.Series, history: pd.DataFrame) -> Optional[dict]:
        """
        Build a single row for the volatility table using pre-fetched historical data.
        
        Args:
            latest_row: Latest data row from database for this ticker
            history: Historical data DataFrame for this ticker (newest first)
            
        Returns:
            Dict with table columns, or None if ticker not in universe
        """
        ticker = latest_row['ticker']
        
        # Skip if not in our universe
        if ticker not in ETF_NAME_LOOKUP:
            return None
        
        # Build the row using pre-fetched history
        row = {
            'etf_name': ETF_NAME_LOOKUP[ticker],
            'ticker_display': f"{ticker} US EQUITY",
            'ytd_pct': latest_row.get('ytd_return', 0.0) * 100,  # Convert to percentage
            'ivol_rvol_current': latest_row.get('iv_premium', 0.0),
            'ivol_prem_yesterday': self._get_historical_premium_from_data(history, 1),
            'ivol_prem_1w': self._get_historical_premium_from_data(history, 5),
            'ivol_prem_1m': self._get_historical_premium_from_data(history, 21),
            'ttm_zscore': self._calculate_zscore_from_history(history, 252),
            'three_yr_zscore': self._calculate_zscore_from_history(history, 756),
        }
        
        return row
    
    def _get_historical_premium_from_data(self, history_df: pd.DataFrame, days_ago: int) -> Optional[float]:
        """
        Get IV premium from N trading days ago using pre-fetched historical data.
        
        Args:
            history_df: Historical data DataFrame (newest first)
            days_ago: Number of trading days to look back
            
        Returns:
            IV premium percentage, or None if insufficient history
        """
        try:
            # Check if we have enough data
            if len(history_df) <= days_ago:
                return None
            
            # Get the row that's days_ago back (0-indexed, so days_ago row is what we want)
            target_row = history_df.iloc[days_ago]
            iv_premium = target_row.get('iv_premium')
            
            if pd.isna(iv_premium):
                return None
                
            return iv_premium
            
        except (IndexError, Exception) as e:
            logger.debug(f"Could not get historical premium -{days_ago}d: {e}")
            return None
            
    def _build_ticker_row(self, latest_row: pd.Series) -> Optional[dict]:
        """
        Build a single row for the volatility table.
        
        Args:
            latest_row: Latest data row from database for this ticker
            
        Returns:
            Dict with table columns, or None if ticker not in universe
        """
        ticker = latest_row['ticker']
        
        # Skip if not in our universe
        if ticker not in ETF_NAME_LOOKUP:
            return None
        
        # Get historical data for Z-score calculations
        history = self.db.get_history(ticker, lookback_days=756)  # 3 years max
        
        # Build the row
        row = {
            'etf_name': ETF_NAME_LOOKUP[ticker],
            'ticker_display': f"{ticker} US EQUITY",
            'ytd_pct': latest_row.get('ytd_return', 0.0) * 100,  # Convert to percentage
            'ivol_rvol_current': latest_row.get('iv_premium', 0.0),
            'ivol_prem_yesterday': self._get_historical_premium(ticker, 1),
            'ivol_prem_1w': self._get_historical_premium(ticker, 5),
            'ivol_prem_1m': self._get_historical_premium(ticker, 21),
            'ttm_zscore': self._calculate_zscore_from_history(history, 252),
            'three_yr_zscore': self._calculate_zscore_from_history(history, 756),
        }
        
        return row
    
    def _get_historical_premium(self, ticker: str, days_ago: int) -> Optional[float]:
        """
        Get IV premium from N trading days ago.
        
        Args:
            ticker: Stock ticker
            days_ago: Number of trading days to look back
            
        Returns:
            IV premium percentage, or None if insufficient history
        """
        try:
            # Use trading day calculation to find the target date
            today = date.today()
            target_date = get_previous_trading_day(today, days_ago)
            
            # First try exact date match
            snapshot = self.db.get_snapshot(target_date.isoformat(), ticker)
            if snapshot:
                return snapshot.get('iv_premium')
            
            # If no exact match, try approximate trading day with buffer
            approximate_date = get_approximate_trading_day(today, days_ago)
            snapshot = self.db.get_snapshot(approximate_date.isoformat(), ticker)
            if snapshot:
                return snapshot.get('iv_premium')
            
            # If still no match, try to find closest within reasonable range
            history = self.db.get_history(ticker, lookback_days=days_ago + 10)  # More buffer for trading days
            if len(history) > days_ago:
                # Take the row that's approximately days_ago back
                target_idx = min(days_ago - 1, len(history) - 1)
                return history.iloc[-(target_idx + 1)]['iv_premium']
            elif len(history) > 0 and days_ago == 1:
                # For yesterday, if we only have today's data, return None
                return None
            
            return None
            
        except Exception as e:
            logger.debug(f"Could not get historical premium for {ticker} -{days_ago}d: {e}")
            return None
    
    def _calculate_zscore_from_history(self, history: pd.DataFrame, window: int) -> Optional[float]:
        """
        Calculate Z-score of current IV premium relative to historical window.
        
        Args:
            history: Historical data DataFrame (newest first)
            window: Lookback window in trading days
            
        Returns:
            Z-score, or None if insufficient data
        """
        try:
            if len(history) < 5:  # Need at least 5 data points
                return None
            
            # Get IV premium series (newest first, so reverse for calculation)
            iv_premiums = history['iv_premium'].dropna()
            
            if len(iv_premiums) < 5:
                return None
            
            # Calculate Z-score using available data (not requiring full window)
            current_premium = iv_premiums.iloc[0]  # Most recent
            # Use all available historical data, but limit to window size
            historical_window = iv_premiums.iloc[1:min(window + 1, len(iv_premiums))]
            
            if len(historical_window) < 4:  # Need at least 4 historical points
                return None
                
            mean = historical_window.mean()
            std = historical_window.std()
            
            if std == 0 or pd.isna(std) or std < 0.01:  # Avoid division by near-zero
                return 0.0
            
            zscore = (current_premium - mean) / std
            return round(zscore, 2)
            
        except Exception as e:
            logger.debug(f"Could not calculate Z-score for window {window}: {e}")
            return None
    
    def get_data_freshness_info(self) -> dict:
        """
        Get information about data freshness and availability.
        
        Returns:
            Dict with freshness metrics
        """
        latest_data = self.db.get_all_latest()
        
        if latest_data.empty:
            return {
                'has_data': False,
                'ticker_count': 0,
                'latest_date': None,
                'days_old': None
            }
        
        latest_date_str = latest_data['date'].max()
        # Handle both string and Timestamp types
        if hasattr(latest_date_str, 'date'):
            latest_date = latest_date_str.date()
        else:
            latest_date = datetime.strptime(str(latest_date_str), '%Y-%m-%d').date()
        days_old = (datetime.now().date() - latest_date).days
        
        universe_tickers = [etf["ticker"] for etf in ETF_UNIVERSE]
        available_tickers = latest_data[latest_data['ticker'].isin(universe_tickers)]
        
        return {
            'has_data': True,
            'ticker_count': len(available_tickers),
            'universe_size': len(universe_tickers),
            'latest_date': latest_date_str,
            'days_old': days_old,
            'coverage_pct': len(available_tickers) / len(universe_tickers) * 100
        }