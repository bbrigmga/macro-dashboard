"""
FRED API client for fetching economic data.
"""
from typing import List, Optional, Union
from fredapi import Fred
import os
import pandas as pd
import time
import logging
import urllib.error
from datetime import datetime, timedelta
from functools import wraps
import concurrent.futures

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def retry_with_backoff(max_retries: int = 3, initial_backoff: int = 1, backoff_factor: int = 2):
    """
    Retry decorator with exponential backoff for API calls.
    
    Args:
        max_retries (int): Maximum number of retry attempts
        initial_backoff (int): Initial backoff time in seconds
        backoff_factor (int): Factor to multiply backoff time by after each failure
        
    Returns:
        Function: Decorated function with retry logic
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            backoff = initial_backoff
            for retry in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except (urllib.error.HTTPError, urllib.error.URLError) as e:
                    if retry == max_retries:
                        logger.error(f"Failed after {max_retries} retries: {str(e)}")
                        raise
                    
                    if isinstance(e, urllib.error.HTTPError):
                        # Handle specific HTTP errors
                        if e.code == 504:  # Gateway Timeout
                            logger.warning(f"Gateway timeout, retrying in {backoff} seconds...")
                        elif e.code == 429:  # Too Many Requests
                            logger.warning(f"Rate limit exceeded, retrying in {backoff} seconds...")
                        else:
                            logger.warning(f"HTTP error {e.code}, retrying in {backoff} seconds...")
                    else:
                        logger.warning(f"URL error: {str(e)}, retrying in {backoff} seconds...")
                    
                    time.sleep(backoff)
                    backoff *= backoff_factor
        return wrapper
    return decorator


class FredClient:
    """Client for interacting with the FRED API with enhanced type hints and cache management."""
    
    def __init__(self, api_key: Optional[str] = None, cache_enabled: bool = True, max_cache_size: int = 100):
        """
        Initialize the FRED client.
        
        Args:
            api_key (str, optional): FRED API key. If None, will use FRED_API_KEY from environment.
            cache_enabled (bool): Whether to cache API responses
            max_cache_size (int): Maximum number of entries to keep in cache
        """
        if api_key is None:
            api_key = os.getenv('FRED_API_KEY')
            if api_key is None:
                raise ValueError("FRED_API_KEY environment variable not set")
        
        self.fred = Fred(api_key=api_key)
        self.cache_enabled = cache_enabled
        self.cache: dict = {}
        self.max_cache_size = max_cache_size
    
    def _manage_cache(self, cache_key: str, df: pd.DataFrame) -> None:
        """Manage cache size by removing oldest entries when limit is reached."""
        if len(self.cache) >= self.max_cache_size:
            # Remove the oldest entry
            oldest_key = min(self.cache, key=lambda k: self.cache[k].get('timestamp', 0))
            del self.cache[oldest_key]
        
        self.cache[cache_key] = {
            'data': df,
            'timestamp': time.time()
        }
    
    @retry_with_backoff(max_retries=3, initial_backoff=2, backoff_factor=2)
    def get_series(self, series_id: str, start_date: Optional[str] = None, 
                   end_date: Optional[str] = None, periods: Optional[int] = None, 
                   frequency: str = 'M') -> pd.DataFrame:
        """
        Get a time series from FRED with retry logic.
        
        Args:
            series_id (str): FRED series ID
            start_date (str, optional): Start date in format 'YYYY-MM-DD'
            end_date (str, optional): End date in format 'YYYY-MM-DD'
            periods (int, optional): Number of periods to fetch (will calculate start_date if not provided)
            frequency (str, optional): Data frequency ('D' for daily, 'W' for weekly, 'M' for monthly)
            
        Returns:
            pd.DataFrame: DataFrame with date index and value column
        """
        # Calculate start_date based on periods if not provided
        if start_date is None and periods is not None:
            end = datetime.now() if end_date is None else datetime.strptime(end_date, '%Y-%m-%d')
            
            if frequency == 'D':
                start = end - timedelta(days=periods + 10)  # Add buffer
            elif frequency == 'W':
                start = end - timedelta(weeks=periods + 2)  # Add buffer
            else:  # Monthly
                start = end - timedelta(days=(periods + 2) * 30)  # Add buffer
                
            start_date = start.strftime('%Y-%m-%d')
            logger.info(f"Calculated start_date {start_date} for {periods} {frequency} periods")
        
        # Check cache first if enabled
        cache_key = f"{series_id}_{start_date}_{end_date}"
        if self.cache_enabled and cache_key in self.cache:
            logger.info(f"Using cached data for {series_id}")
            return self.cache[cache_key]['data']
        
        try:
            logger.info(f"Fetching series {series_id} from FRED API (start_date: {start_date})")
            series = self.fred.get_series(
                series_id, 
                observation_start=start_date,
                observation_end=end_date
            )
            
            # Convert to DataFrame
            df = pd.DataFrame(series, columns=['Value']).reset_index()
            df.columns = ['Date', series_id]
            
            # Convert Date to numpy datetime64 to avoid FutureWarning
            df['Date'] = pd.to_datetime(df['Date']).to_numpy()
            
            # Cache the result if enabled
            if self.cache_enabled:
                self._manage_cache(cache_key, df)
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching {series_id}: {str(e)}")
            raise
    
    def get_multiple_series(self, series_ids: List[str], start_date: Optional[str] = None, 
                             end_date: Optional[str] = None, periods: Optional[int] = None, 
                             frequency: str = 'M', max_workers: int = 5) -> pd.DataFrame:
        """
        Get multiple time series from FRED and merge them using concurrent processing.
        
        Args:
            series_ids (list): List of FRED series IDs
            start_date (str, optional): Start date in format 'YYYY-MM-DD'
            end_date (str, optional): End date in format 'YYYY-MM-DD'
            periods (int, optional): Number of periods to fetch
            frequency (str, optional): Data frequency
            max_workers (int): Maximum number of concurrent API calls
        
        Returns:
            pd.DataFrame: DataFrame with date index and columns for each series
        """
        result = None
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all series fetch tasks
            future_to_series = {
                executor.submit(
                    self.get_series, 
                    series_id, 
                    start_date, 
                    end_date, 
                    periods, 
                    frequency
                ): series_id for series_id in series_ids
            }
            
            for future in concurrent.futures.as_completed(future_to_series):
                series_id = future_to_series[future]
                try:
                    df = future.result()
                    
                    if result is None:
                        result = df
                    else:
                        result = pd.merge(result, df, on='Date', how='outer')
                except Exception as e:
                    logger.error(f"Error in get_multiple_series for {series_id}: {str(e)}")
                    continue
        
        if result is None:
            raise ValueError("Failed to fetch any of the requested series")
            
        return result
