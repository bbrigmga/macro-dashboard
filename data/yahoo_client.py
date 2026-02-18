"""
Yahoo Finance client for fetching historical price data.
"""
import yfinance as yf
import pandas as pd
import logging
import os
from datetime import datetime, timedelta
from data.processing import convert_dates

# Set up logging
logger = logging.getLogger(__name__)

class YahooClient:
    """Client for interacting with Yahoo Finance API."""

    def __init__(self):
        """Initialize the Yahoo Finance client."""
        logger.info("Yahoo Finance Client initialized")

    def _get_cache_file_path(self, ticker: str) -> str:
        """Get the cache file path for a ticker."""
        # Replace invalid filename characters
        safe_ticker = ticker.replace('=', '_').replace('/', '_')
        return os.path.join('data', 'cache', f'{safe_ticker}.csv')

    def _load_cached_data(self, ticker: str) -> pd.DataFrame:
        """Load cached data for a ticker if it exists."""
        cache_file = self._get_cache_file_path(ticker)
        if os.path.exists(cache_file):
            try:
                df = pd.read_csv(cache_file)
                # Parse dates with utc=True to handle any tz-aware strings, then strip tz
                df['Date'] = pd.to_datetime(df['Date'], utc=True).dt.tz_localize(None).dt.normalize()
                logger.info(f"Loaded {len(df)} cached records for {ticker}")
                return df
            except Exception as e:
                logger.warning(f"Failed to load cache for {ticker}: {e}")
        return pd.DataFrame()

    def _save_cached_data(self, ticker: str, df: pd.DataFrame) -> None:
        """Save data to cache file."""
        cache_file = self._get_cache_file_path(ticker)
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        df.to_csv(cache_file, index=False)
        logger.info(f"Saved {len(df)} records to cache for {ticker}")

    def get_historical_prices(self, ticker: str, start_date: str = None,
                               end_date: str = None, periods: int = None,
                               frequency: str = '1d') -> pd.DataFrame:
        """
        Get historical price data from Yahoo Finance with file-based caching.

        Args:
            ticker (str): Yahoo Finance ticker symbol (e.g., 'HG=F')
            start_date (str, optional): Start date in format 'YYYY-MM-DD'
            end_date (str, optional): End date in format 'YYYY-MM-DD'
            periods (int, optional): Number of periods to fetch (will calculate start_date if not provided)
            frequency (str, optional): Data frequency ('1d' for daily, '1wk' for weekly, '1mo' for monthly)

        Returns:
            pd.DataFrame: DataFrame with 'Date' and 'value' columns
        """
        # Validate ticker
        if not ticker or not isinstance(ticker, str):
            raise ValueError(f"Invalid ticker: {ticker}")

        # Load cached data
        cached_df = self._load_cached_data(ticker)
        today = datetime.now().date()

        # Check if we have recent data (within last 2 days to account for weekends/holidays)
        has_recent_data = False
        if not cached_df.empty:
            latest_date = cached_df['Date'].max().date()
            days_since_latest = (today - latest_date).days
            has_recent_data = days_since_latest <= 2  # Consider data recent if within 2 days

        # If we have recent cached data and periods is specified, check if we have enough data
        if has_recent_data and periods is not None and not cached_df.empty:
            # Sort cached data by date
            cached_df = cached_df.sort_values('Date').reset_index(drop=True)
            if len(cached_df) >= periods:
                # Return the most recent periods from cache
                result_df = cached_df.tail(periods).copy()
                logger.info(f"Using cached data for {ticker} - {len(result_df)} records")
                return result_df

        # Calculate start_date based on periods if not provided
        if start_date is None and periods is not None:
            end = datetime.now() if end_date is None else datetime.strptime(end_date, '%Y-%m-%d')

            if frequency == '1d':
                start = end - timedelta(days=periods + 10)  # Add buffer
            elif frequency == '1wk':
                start = end - timedelta(weeks=periods + 2)  # Add buffer
            else:  # Monthly
                start = end - timedelta(days=(periods + 2) * 30)  # Add buffer

            start_date = start.strftime('%Y-%m-%d')

        # Determine what data to fetch
        fetch_start_date = start_date
        if not cached_df.empty and has_recent_data:
            # We have recent data, but might need more historical data
            cached_start = cached_df['Date'].min().date()
            requested_start = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else today - timedelta(days=periods)
            if cached_start <= requested_start:
                # Cache covers the requested period, return from cache
                cached_df = cached_df.sort_values('Date').reset_index(drop=True)
                # cached_df['Date'] is datetime64; compare against a Timestamp to avoid dtype/date comparison errors
                requested_start_dt = pd.Timestamp(requested_start) if start_date else None
                result_df = cached_df[cached_df['Date'] >= requested_start_dt].copy() if start_date else cached_df.tail(periods).copy()
                logger.info(f"Using cached data for {ticker} - {len(result_df)} records")
                return result_df
            else:
                # Need to fetch older data
                fetch_start_date = start_date
        elif not cached_df.empty:
            # Have cached data but not recent, fetch from day after latest cached date
            latest_cached_date = cached_df['Date'].max()
            fetch_start_date = (latest_cached_date + timedelta(days=1)).strftime('%Y-%m-%d')
            logger.info(f"Fetching new data for {ticker} from {fetch_start_date}")
        else:
            # No cache, fetch all
            logger.info(f"No cached data for {ticker}, fetching all data")

        try:
            # Fetch data from Yahoo Finance
            ticker_obj = yf.Ticker(ticker)
            df = ticker_obj.history(start=fetch_start_date, end=end_date, interval=frequency)

            # Validate data
            if df is None or df.empty:
                if not cached_df.empty:
                    logger.warning(f"No new data found for {ticker}, using cached data")
                    cached_df = cached_df.sort_values('Date').reset_index(drop=True)
                    result_df = cached_df.tail(periods).copy() if periods else cached_df
                    return result_df
                else:
                    logger.warning(f"No data found for ticker {ticker}")
                    raise ValueError(f"No data found for ticker {ticker}")

            # Select Close price as value
            df = df[['Close']].reset_index()
            df.columns = ['Date', 'value']

            # Ensure Date is tz-naive datetime (Yahoo returns tz-aware dates)
            df['Date'] = pd.to_datetime(df['Date'], utc=True).dt.tz_localize(None).dt.normalize()

            # Use processing utility to convert dates
            df = convert_dates(df.set_index('Date')).reset_index()

            # Merge with cached data if we fetched incremental data
            if not cached_df.empty and fetch_start_date != start_date:
                # Combine cached and new data
                combined_df = pd.concat([cached_df, df], ignore_index=True)
                # Remove duplicates based on Date
                combined_df = combined_df.drop_duplicates(subset='Date', keep='last')
                combined_df = combined_df.sort_values('Date').reset_index(drop=True)
                # Save updated cache
                self._save_cached_data(ticker, combined_df)
                result_df = combined_df.tail(periods).copy() if periods else combined_df
            else:
                # Full fetch, save to cache
                self._save_cached_data(ticker, df)
                result_df = df

            logger.info(f"Successfully fetched/updated {len(df)} records for {ticker}")
            return result_df

        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {str(e)}")
            # If fetch failed and we have cache, return cached data
            if not cached_df.empty:
                logger.info(f"Using cached data due to fetch error for {ticker}")
                cached_df = cached_df.sort_values('Date').reset_index(drop=True)
                return cached_df.tail(periods).copy() if periods else cached_df
            raise