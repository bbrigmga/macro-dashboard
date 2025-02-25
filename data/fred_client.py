"""
FRED API client for fetching economic data.
"""
from fredapi import Fred
import os
import pandas as pd
from datetime import datetime, timedelta


class FredClient:
    """Client for interacting with the FRED API."""
    
    def __init__(self, api_key=None):
        """
        Initialize the FRED client.
        
        Args:
            api_key (str, optional): FRED API key. If None, will use FRED_API_KEY from environment.
        """
        if api_key is None:
            api_key = os.getenv('FRED_API_KEY')
            if api_key is None:
                raise ValueError("FRED_API_KEY environment variable not set")
        
        self.fred = Fred(api_key=api_key)
    
    def get_series(self, series_id, start_date=None, end_date=None):
        """
        Get a time series from FRED.
        
        Args:
            series_id (str): FRED series ID
            start_date (str, optional): Start date in format 'YYYY-MM-DD'
            end_date (str, optional): End date in format 'YYYY-MM-DD'
            
        Returns:
            pd.DataFrame: DataFrame with date index and value column
        """
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
        
        return df
    
    def get_multiple_series(self, series_ids, start_date=None, end_date=None):
        """
        Get multiple time series from FRED and merge them.
        
        Args:
            series_ids (list): List of FRED series IDs
            start_date (str, optional): Start date in format 'YYYY-MM-DD'
            end_date (str, optional): End date in format 'YYYY-MM-DD'
            
        Returns:
            pd.DataFrame: DataFrame with date index and columns for each series
        """
        result = None
        
        for series_id in series_ids:
            df = self.get_series(series_id, start_date, end_date)
            
            if result is None:
                result = df
            else:
                result = pd.merge(result, df, on='Date', how='outer')
        
        return result
