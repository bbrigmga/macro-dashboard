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
import requests

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create a module-level session for HTTP reuse
_session = requests.Session()

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
    
    def __init__(self, api_key: Optional[str] = None, cache_enabled: bool = False, max_cache_size: int = 100):
        """
        Initialize the FRED client.
        
        Args:
            api_key (str, optional): FRED API key. If None, will use FRED_API_KEY from environment.
            cache_enabled (bool): Whether to cache API responses (default: False)
            max_cache_size (int): Maximum number of entries to keep in cache
        """
        if api_key is None:
            logger.info("Attempting to get FRED_API_KEY from environment")
            api_key = os.getenv('FRED_API_KEY')
            if api_key is None:
                raise ValueError("FRED_API_KEY environment variable not set")
            else:
                logger.info("Successfully retrieved FRED_API_KEY from environment")
        
        self.fred = Fred(api_key=api_key)
        self.cache_enabled = cache_enabled  # Explicitly set to False by default
        self.cache: dict = {}
        self.max_cache_size = max_cache_size
        # Reuse HTTP session
        self._session = _session
        
        # Add logging for API key validation
        logger.info("FRED API Client initialized with cache_enabled: %s", cache_enabled)

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

    def _get_cache_file_path(self, series_id: str) -> str:
        """Get the cache file path for a FRED series."""
        # Replace invalid filename characters
        safe_id = series_id.replace('/', '_').replace('\\', '_').replace(':', '_')
        return os.path.join('data', 'cache', f'{safe_id}.csv')

    def _load_cached_data(self, series_id: str) -> pd.DataFrame:
        """Load cached data for a FRED series if it exists."""
        cache_file = self._get_cache_file_path(series_id)
        if os.path.exists(cache_file):
            try:
                df = pd.read_csv(cache_file)
                df['Date'] = pd.to_datetime(df['Date'])
                logger.info(f"Loaded {len(df)} cached records for {series_id}")
                return df
            except Exception as e:
                logger.warning(f"Failed to load cache for {series_id}: {e}")
        return pd.DataFrame()

    def _save_cached_data(self, series_id: str, df: pd.DataFrame) -> None:
        """Save data to cache file."""
        cache_file = self._get_cache_file_path(series_id)
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        df.to_csv(cache_file, index=False)
        logger.info(f"Saved {len(df)} records to cache for {series_id}")

    def _is_cache_fresh(self, series_id: str, max_age_hours: int = 24) -> bool:
        """Check if the cached data for a series is fresh (within max_age_hours)."""
        cache_file = self._get_cache_file_path(series_id)
        if not os.path.exists(cache_file):
            return False
        file_age_hours = (time.time() - os.path.getmtime(cache_file)) / 3600
        return file_age_hours < max_age_hours
    
    @retry_with_backoff(max_retries=3, initial_backoff=2, backoff_factor=2)
    def get_series(self, series_id: str, start_date: Optional[str] = None, 
                   end_date: Optional[str] = None, periods: Optional[int] = None, 
                   frequency: str = 'M') -> pd.DataFrame:
        """
        Get a time series from FRED with enhanced error handling and logging.
        
        Args:
            series_id (str): FRED series ID
            start_date (str, optional): Start date in format 'YYYY-MM-DD'
            end_date (str, optional): End date in format 'YYYY-MM-DD'
            periods (int, optional): Number of periods to fetch (will calculate start_date if not provided)
            frequency (str, optional): Data frequency ('D' for daily, 'W' for weekly, 'M' for monthly)
            
        Returns:
            pd.DataFrame: DataFrame with date index and value column
        """
        # Validate series_id
        if not series_id or not isinstance(series_id, str):
            raise ValueError(f"Invalid series_id: {series_id}")
        
        # Calculate start_date based on periods if not provided
        if start_date is None and periods is not None:
            end = datetime.now() if end_date is None else datetime.strptime(end_date, '%Y-%m-%d')

            if frequency == 'D':
                start = end - timedelta(days=periods + 10)  # Add buffer
            elif frequency == 'W':
                start = end - timedelta(weeks=periods + 2)  # Add buffer
            elif frequency == 'M':
                start = end - timedelta(days=(periods + 2) * 30)  # Add buffer
            elif frequency == 'Q':
                start = end - timedelta(days=(periods + 2) * 91)  # Add buffer, ~91 days per quarter
            else:  # Default to monthly
                start = end - timedelta(days=(periods + 2) * 30)  # Add buffer

            start_date = start.strftime('%Y-%m-%d')

        # Check persistent cache
        if self.cache_enabled and self._is_cache_fresh(series_id):
            cached_df = self._load_cached_data(series_id)
            if not cached_df.empty:
                cached_start = cached_df['Date'].min()
                cached_end = cached_df['Date'].max()
                requested_start = pd.to_datetime(start_date) if start_date else cached_start
                requested_end = pd.to_datetime(end_date) if end_date else datetime.now()

                # If cache covers the requested period
                if cached_start <= requested_start and cached_end >= requested_end:
                    logger.info(f"Using cached data for {series_id}")
                    # Filter to requested period
                    filtered_df = cached_df[(cached_df['Date'] >= requested_start) & (cached_df['Date'] <= requested_end)].copy()
                    # Ensure correct column names
                    if len(filtered_df.columns) == 2:
                        filtered_df.columns = ['Date', series_id]
                    # Manage in-memory cache
                    cache_key = f"series:{series_id}:{start_date}:{end_date}:{periods}:{frequency}"
                    if self.cache_enabled:
                        self._manage_cache(cache_key, filtered_df.copy())
                    return filtered_df

                # If cache is missing recent data, fetch incremental
                # Only do incremental if the cache also covers the requested start date;
                # otherwise fall through and do a full FRED refetch.
                elif cached_end < requested_end and cached_start <= requested_start:
                    logger.info(f"Fetching incremental data for {series_id} from {(cached_end + timedelta(days=1)).date()} to {requested_end.date()}")
                    try:
                        new_start_date = (cached_end + timedelta(days=1)).strftime('%Y-%m-%d')
                        new_series = self.fred.get_series(
                            series_id,
                            observation_start=new_start_date,
                            observation_end=end_date
                        )
                        if not new_series.empty:
                            new_df = pd.DataFrame(new_series, columns=['Value']).reset_index()
                            new_df.columns = ['Date', series_id]
                            new_df['Date'] = pd.to_datetime(new_df['Date'])
                            # Merge with cached
                            combined_df = pd.concat([cached_df, new_df], ignore_index=True)
                            combined_df = combined_df.drop_duplicates(subset='Date', keep='last')
                            combined_df = combined_df.sort_values('Date').reset_index(drop=True)
                            # Save updated cache
                            self._save_cached_data(series_id, combined_df)
                            # Filter to requested period
                            filtered_df = combined_df[(combined_df['Date'] >= requested_start) & (combined_df['Date'] <= requested_end)].copy()
                            # Manage in-memory cache
                            cache_key = f"series:{series_id}:{start_date}:{end_date}:{periods}:{frequency}"
                            if self.cache_enabled:
                                self._manage_cache(cache_key, filtered_df.copy())
                            return filtered_df
                    except Exception as e:
                        logger.warning(f"Failed to fetch incremental data for {series_id}: {e}")
                        # Fall back to using available cached data
                        if cached_start <= requested_start:
                            filtered_df = cached_df[(cached_df['Date'] >= requested_start)].copy()
                            if len(filtered_df.columns) == 2:
                                filtered_df.columns = ['Date', series_id]
                            cache_key = f"series:{series_id}:{start_date}:{end_date}:{periods}:{frequency}"
                            if self.cache_enabled:
                                self._manage_cache(cache_key, filtered_df.copy())
                            return filtered_df

        # Deterministic cache key
        cache_key = f"series:{series_id}:{start_date}:{end_date}:{periods}:{frequency}"
        if self.cache_enabled and cache_key in self.cache:
            cached = self.cache[cache_key]['data']
            # Return a copy to avoid accidental mutation of cache
            return cached.copy()
        try:
            # Fetch series with detailed error handling
            try:
                series = self.fred.get_series(
                    series_id, 
                    observation_start=start_date,
                    observation_end=end_date
                )
            except Exception as e:
                logger.error(f"FRED API Error for series {series_id}: {str(e)}")
                # Additional diagnostic information
                try:
                    # Check series information
                    series_info = self.fred.get_series_info(series_id)
                    logger.error(f"Series Info for {series_id}: {series_info}")
                except Exception as info_error:
                    logger.error(f"Could not retrieve series info: {str(info_error)}")
                
                raise
            
            # Validate series data
            if series is None or len(series) == 0:
                logger.warning(f"No data found for series {series_id}")
                raise ValueError(f"No data found for series {series_id}")
            
            # Convert to DataFrame
            df = pd.DataFrame(series, columns=['Value']).reset_index()
            df.columns = ['Date', series_id]
            # Normalize Date to pandas datetime
            df['Date'] = pd.to_datetime(df['Date'])
            # Write to cache
            if self.cache_enabled:
                self._manage_cache(cache_key, df.copy())
                self._save_cached_data(series_id, df.copy())
            return df
            
        except Exception as e:
            logger.error(f"Comprehensive error fetching {series_id}: {str(e)}")
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
        # Optional: cap workers to reduce rate-limit risk
        max_workers = min(max_workers, 3)
        result = None
        series_fetch_results = {}
        # Deduplicate incoming IDs to avoid redundant fetches
        unique_series_ids = list(dict.fromkeys(series_ids))
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
                ): series_id for series_id in unique_series_ids
            }
            
            # Handle completed tasks
            for future in concurrent.futures.as_completed(future_to_series):
                series_id = future_to_series[future]
                try:
                    df = future.result()
                    
                    series_fetch_results[series_id] = df
                    
                    if result is None:
                        result = df
                    else:
                        result = pd.merge(result, df, on='Date', how='outer')
                except Exception as e:
                    logger.error(f"Error in get_multiple_series for {series_id}: {str(e)}")
                    series_fetch_results[series_id] = None
                    continue
        
        # Raise error if no series were successfully fetched
        if result is None or len(result) == 0:
            logger.error("Failed to fetch any of the requested series")
            raise ValueError("Failed to fetch any of the requested series")
        
        # Ensure Date normalized once
        result['Date'] = pd.to_datetime(result['Date'])
        return result

    @retry_with_backoff()
    def get_series_release_id(self, series_id: str) -> Optional[int]:
        """
        Get the release ID for a FRED series.
        
        Args:
            series_id (str): FRED series ID
            
        Returns:
            int: Release ID if available, None otherwise
        """
        try:
            # Use shared session
            response = self._session.get(f"https://api.stlouisfed.org/fred/series/release?series_id={series_id}&api_key={self.fred.api_key}&file_type=json")
            response.raise_for_status()
            release_info = response.json()
            if release_info and 'releases' in release_info and release_info['releases']:
                release_id = release_info['releases'][0]['id']
                return release_id
            else:
                logger.warning(f"No release ID found for series {series_id}")
            return None
        except Exception as e:
            logger.warning(f"Failed to get release ID for series {series_id}: {str(e)}")
            return None

    @retry_with_backoff()
    def get_next_release_date_from_release(self, release_id: int) -> Optional[datetime]:
        """
        Get the next release date for a specific FRED release.
        
        Args:
            release_id (int): FRED release ID
            
        Returns:
            datetime: Next release date if available, None otherwise
        """
        try:
            # First try the release/dates endpoint
            params = {
                'release_id': release_id,
                'realtime_start': (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
                'realtime_end': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
                'include_release_dates_with_no_data': 'true',
                'api_key': self.fred.api_key,
                'file_type': 'json'
            }
            response = self._session.get("https://api.stlouisfed.org/fred/release/dates", params=params)
            response.raise_for_status()
            release_dates = response.json()
            
            if release_dates and 'release_dates' in release_dates:
                release_dates = release_dates['release_dates']
                current_time = datetime.now()
                future_releases = [date['date'] for date in release_dates if pd.to_datetime(date['date']) > current_time]
                if future_releases:
                    next_date = pd.to_datetime(min(future_releases))
                    return next_date
                
            logger.warning(f"No future release dates found for release ID {release_id}")
            return None
            
        except Exception as e:
            logger.warning(f"Failed to get release dates for release {release_id}: {str(e)}")
            return None

    @retry_with_backoff()
    def get_series_release_date(self, series_id: str) -> Optional[datetime]:
        """
        Get the next release date for a FRED series.
        
        Args:
            series_id (str): FRED series ID
            
        Returns:
            datetime: Next release date if available, None otherwise
        """
        try:
            # First try to get the release ID for the series
            release_id = self.get_series_release_id(series_id)
            if release_id:
                # Get next release date from the release schedule
                next_date = self.get_next_release_date_from_release(release_id)
                if next_date:
                    return next_date
            
            logger.info(f"Falling back to vintage dates for series {series_id}")
            # If that fails, try the vintage dates approach as fallback
            response = self._session.get(f"https://api.stlouisfed.org/fred/series/vintagedates?series_id={series_id}&api_key={self.fred.api_key}&file_type=json")
            response.raise_for_status()
            vintage_dates = response.json()
            
            if vintage_dates and 'vintage_dates' in vintage_dates:
                vintage_dates = vintage_dates['vintage_dates']
                current_time = datetime.now()
                future_releases = [date for date in vintage_dates if pd.to_datetime(date) > current_time]
                if future_releases:
                    next_date = pd.to_datetime(min(future_releases))
                    return next_date
                else:
                    logger.warning(f"No future vintage dates found for series {series_id}")
            else:
                logger.warning(f"No vintage dates found for series {series_id}")
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to get release date for series {series_id}: {str(e)}")
            return None

    @retry_with_backoff()
    def get_multiple_release_dates(self, series_ids: List[str], max_workers: int = 5) -> dict:
        """
        Get release dates for multiple series concurrently.
        
        Args:
            series_ids (list): List of FRED series IDs
            max_workers (int): Maximum number of concurrent API calls
            
        Returns:
            dict: Dictionary mapping series IDs to their next release dates
        """
        release_dates = {}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_series = {executor.submit(self.get_series_release_date, series_id): series_id 
                              for series_id in series_ids}
            
            for future in concurrent.futures.as_completed(future_to_series):
                series_id = future_to_series[future]
                try:
                    release_date = future.result()
                    if release_date:
                        release_dates[series_id] = release_date
                except Exception as e:
                    logger.error(f"Error getting release date for {series_id}: {str(e)}")
        
        return release_dates
