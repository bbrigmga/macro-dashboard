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


def calculate_pct_change(df, column, periods=1, annualize=False, fill_method='ffill'):
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
