"""
Utility functions for data processing.
"""
import pandas as pd
import numpy as np
import logging

# Set up logging
logger = logging.getLogger(__name__)

def convert_dates(df):
    """
    Convert datetime index to numpy datetime64 array to avoid FutureWarning.

    Args:
        df (pd.DataFrame): DataFrame with datetime index or column

    Returns:
        pd.DataFrame: DataFrame with converted dates
    """
    if isinstance(df.index, pd.DatetimeIndex):
        df = df.copy()
        index_name = df.index.name
        df.index = df.index.to_numpy()
        df.index.name = index_name
    return df


def calculate_pct_change(df, column, periods=1, annualize=False, fill_method=None):
    """
    Calculate percentage change for a column in a DataFrame.
    
    Args:
        df (pd.DataFrame): DataFrame with data
        column (str): Column name to calculate percentage change for
        periods (int, optional): Number of periods to shift for calculation
        annualize (bool, optional): Whether to annualize the result (multiply by 12/periods)
        fill_method (str, optional): Method to fill NaN values before calculation
        
    Returns:
        pd.Series: Series with percentage change values
    """
    # Use the specified fill method before pct_change to avoid FutureWarning
    if fill_method:
        series = getattr(df[column], fill_method)().pct_change(periods=periods) * 100
    else:
        series = df[column].pct_change(periods=periods) * 100
    
    # Annualize if requested
    if annualize and periods > 0:
        series = series * (12 / periods)
    
    return series


def cap_outliers(series, lower_limit=-2, upper_limit=2):
    """
    Handle outliers by capping extreme values.
    
    Args:
        series (pd.Series): Series with data
        lower_limit (float, optional): Lower limit for capping
        upper_limit (float, optional): Upper limit for capping
        
    Returns:
        pd.Series: Series with capped values
    """
    return series.clip(lower=lower_limit, upper=upper_limit)


def check_consecutive_increase(values, count=3):
    """
    Check if values have been increasing for a specified number of periods.
    
    Args:
        values (array-like): Array of values to check
        count (int, optional): Number of consecutive increases to check for
        
    Returns:
        bool: True if values have been increasing for count periods, False otherwise
    """
    if len(values) < count + 1:
        return False
    
    # Check if each of the last 'count' values is greater than the previous
    result = all(values[i] < values[i+1] for i in range(len(values)-count, len(values)-1))
    
    return result


def check_consecutive_decrease(values, count=3):
    """
    Check if values have been decreasing for a specified number of periods.
    
    Args:
        values (array-like): Array of values to check
        count (int, optional): Number of consecutive decreases to check for
        
    Returns:
        bool: True if values have been decreasing for count periods, False otherwise
    """
    if len(values) < count + 1:
        return False
    
    # Check if each of the last 'count' values is less than the previous
    result = all(values[i] > values[i+1] for i in range(len(values)-count, len(values)-1))
    
    return result


def count_consecutive_changes(values, decreasing=True):
    """
    Count how many consecutive periods values have been changing in the specified direction.
    
    Args:
        values (array-like): Array of values to check
        decreasing (bool, optional): Whether to count decreases (True) or increases (False)
        
    Returns:
        int: Number of consecutive periods with the specified change direction
    """
    count = 0
    for i in range(len(values)-1, 0, -1):
        if decreasing and values[i-1] > values[i]:
            count += 1
        elif not decreasing and values[i-1] < values[i]:
            count += 1
        else:
            break
    return count

def validate_indicator_data(data: dict | None, config=None) -> bool:
    """
    Validate that indicator data contains required fields and valid values.
    
    Args:
        data (dict): Dictionary containing indicator data
        config: Optional IndicatorConfig for additional validation
        
    Returns:
        bool: True if data is valid, False otherwise
    """
    if not data or not isinstance(data, dict):
        return False
    
    # Check for error states
    if 'error' in data or 'status' in data and data['status'] == 'data_error':
        return False
    
    # Check for essential fields - at least one of these should exist and be valid
    essential_fields = [
        'latest_value', 'latest_ratio', 'latest_yield', 'latest_spread', 
        'latest_price', 'latest_claims', 'latest_pce', 'latest_cpi',  
        'latest_hours', 'latest_curve', 'pmi_score', 'latest_pmi', 'current_liquidity'
    ]
    
    # Check if at least one essential field exists and is not None or empty
    has_valid_data = False
    for field in essential_fields:
        if field in data:
            value = data[field]
            if value is not None and value != '' and (not isinstance(value, (int, float)) or not pd.isna(value)):
                has_valid_data = True
                break
    
    # Check for required DataFrame
    if 'data' in data:
        df = data['data']
        if isinstance(df, pd.DataFrame) and not df.empty:
            has_valid_data = True
    
    return has_valid_data


def calculate_roc_zscore(series: pd.Series, roc_period: int = 60, zscore_window: int = 252) -> pd.Series:
    """
    Calculate the Z-Score of the Rate of Change for a time series.
    
    This normalizes momentum into a comparable scale (roughly -3 to +3).
    Positive Z-Score = Accelerating. Negative Z-Score = Decelerating.
    
    Args:
        series: Price/ratio time series (daily frequency expected)
        roc_period: Lookback period for Rate of Change (default 60 ≈ 3 months of trading days)
        zscore_window: Rolling window for Z-Score normalization (default 252 ≈ 1 year of trading days)
    
    Returns:
        pd.Series: Z-Score of the ROC, same index as input (with leading NaNs)
    """
    # Step 1: Rate of Change (percentage)
    roc = series.pct_change(periods=roc_period) * 100
    
    # Step 2: Rolling Z-Score of the ROC
    rolling_mean = roc.rolling(window=zscore_window).mean()
    rolling_std = roc.rolling(window=zscore_window).std()
    
    zscore = (roc - rolling_mean) / rolling_std
    
    return zscore


def apply_ema_smoothing(series: pd.Series, span: int = 20) -> pd.Series:
    """
    Apply Exponential Moving Average smoothing to reduce noise in daily data.
    
    Args:
        series: Input time series
        span: EMA span (default 20 trading days ≈ 1 month)
    
    Returns:
        pd.Series: Smoothed series
    """
    return series.ewm(span=span, adjust=False).mean()