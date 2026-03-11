"""
Market utilities for handling trading days, holidays, and business day calculations.

This module provides functionality to:
- Detect US stock market holidays
- Calculate trading days vs calendar days  
- Find previous/next trading days
- Validate if markets are open on a given date
"""
import datetime as dt
import logging
from typing import List, Optional

from .volatility_logging import get_volatility_logger

# Set up enhanced logging
logger = get_volatility_logger(__name__)

# US Stock Market holidays for 2024-2027 (expandable as needed)
# These are the actual dates markets are closed
US_MARKET_HOLIDAYS_2024_2027 = [
    # 2024
    dt.date(2024, 1, 1),   # New Year's Day
    dt.date(2024, 1, 15),  # Martin Luther King Jr. Day
    dt.date(2024, 2, 19),  # Presidents Day
    dt.date(2024, 3, 29),  # Good Friday
    dt.date(2024, 5, 27),  # Memorial Day
    dt.date(2024, 6, 19),  # Juneteenth
    dt.date(2024, 7, 4),   # Independence Day
    dt.date(2024, 9, 2),   # Labor Day
    dt.date(2024, 11, 28), # Thanksgiving
    dt.date(2024, 12, 25), # Christmas Day
    
    # 2025
    dt.date(2025, 1, 1),   # New Year's Day
    dt.date(2025, 1, 20),  # Martin Luther King Jr. Day
    dt.date(2025, 2, 17),  # Presidents Day
    dt.date(2025, 4, 18),  # Good Friday
    dt.date(2025, 5, 26),  # Memorial Day
    dt.date(2025, 6, 19),  # Juneteenth
    dt.date(2025, 7, 4),   # Independence Day
    dt.date(2025, 9, 1),   # Labor Day
    dt.date(2025, 11, 27), # Thanksgiving
    dt.date(2025, 12, 25), # Christmas Day
    
    # 2026
    dt.date(2026, 1, 1),   # New Year's Day
    dt.date(2026, 1, 19),  # Martin Luther King Jr. Day
    dt.date(2026, 2, 16),  # Presidents Day
    dt.date(2026, 4, 3),   # Good Friday
    dt.date(2026, 5, 25),  # Memorial Day
    dt.date(2026, 6, 19),  # Juneteenth
    dt.date(2026, 7, 3),   # Independence Day (observed, 7/4 falls on Saturday)
    dt.date(2026, 9, 7),   # Labor Day
    dt.date(2026, 11, 26), # Thanksgiving
    dt.date(2026, 12, 25), # Christmas Day
    
    # 2027
    dt.date(2027, 1, 1),   # New Year's Day
    dt.date(2027, 1, 18),  # Martin Luther King Jr. Day
    dt.date(2027, 2, 15),  # Presidents Day
    dt.date(2027, 3, 26),  # Good Friday
    dt.date(2027, 5, 31),  # Memorial Day
    dt.date(2027, 6, 18),  # Juneteenth (observed, 6/19 falls on Saturday)
    dt.date(2027, 7, 5),   # Independence Day (observed, 7/4 falls on Sunday)
    dt.date(2027, 9, 6),   # Labor Day
    dt.date(2027, 11, 25), # Thanksgiving
    dt.date(2027, 12, 24), # Christmas Day (observed, 12/25 falls on Saturday)
]


def is_trading_day(date: dt.date) -> bool:
    """
    Check if a given date is a US stock market trading day.
    
    Args:
        date: Date to check
        
    Returns:
        True if markets are open, False if closed (weekend or holiday)
    """
    # Check if weekend (Saturday = 5, Sunday = 6)
    if date.weekday() >= 5:
        return False
    
    # Check if holiday
    if date in US_MARKET_HOLIDAYS_2024_2027:
        return False
    
    return True


def get_previous_trading_day(date: Optional[dt.date] = None, days_back: int = 1) -> dt.date:
    """
    Get the Nth previous trading day from a given date.
    
    Args:
        date: Starting date (defaults to today)
        days_back: Number of trading days to go back (default 1)
        
    Returns:
        The previous trading day
    """
    if date is None:
        date = dt.date.today()
    
    current_date = date
    trading_days_found = 0
    
    while trading_days_found < days_back:
        current_date -= dt.timedelta(days=1)
        if is_trading_day(current_date):
            trading_days_found += 1
    
    return current_date


def get_next_trading_day(date: Optional[dt.date] = None) -> dt.date:
    """
    Get the next trading day after a given date.
    
    Args:
        date: Starting date (defaults to today)
        
    Returns:
        The next trading day
    """
    if date is None:
        date = dt.date.today()
    
    current_date = date + dt.timedelta(days=1)
    
    while not is_trading_day(current_date):
        current_date += dt.timedelta(days=1)
    
    return current_date


def get_trading_days_between(start_date: dt.date, end_date: dt.date) -> List[dt.date]:
    """
    Get all trading days between two dates (inclusive).
    
    Args:
        start_date: Start date
        end_date: End date
        
    Returns:
        List of trading days between the dates
    """
    trading_days = []
    current_date = start_date
    
    while current_date <= end_date:
        if is_trading_day(current_date):
            trading_days.append(current_date)
        current_date += dt.timedelta(days=1)
    
    return trading_days


def should_skip_scraping(date: Optional[dt.date] = None) -> tuple[bool, str]:
    """
    Determine if IV scraping should be skipped for a given date.
    
    Args:
        date: Date to check (defaults to today)
        
    Returns:
        Tuple of (should_skip, reason_message)
    """
    if date is None:
        date = dt.date.today()
    
    if not is_trading_day(date):
        if date.weekday() >= 5:
            return True, f"Skipping scrape - {date} is a weekend"
        else:
            return True, f"Skipping scrape - {date} is a market holiday"
    
    return False, f"Market is open on {date}"


def get_approximate_trading_day(date: dt.date, days_back: int) -> dt.date:
    """
    Get an approximate trading day N business days back, with buffer for holidays.
    
    This is used for historical lookups where we want to find data from approximately
    N trading days ago, but don't need exact precision.
    
    Args:
        date: Starting date
        days_back: Approximate number of trading days to go back
        
    Returns:
        Approximate date for database lookup
    """
    # Add buffer for weekends (multiply by 1.4) and potential holidays
    calendar_days_back = int(days_back * 1.4) + 2
    
    # Simple calendar math - not precise but good enough for database lookups
    target_date = date - dt.timedelta(days=calendar_days_back)
    
    # If we landed on a weekend, go to the previous Friday
    while target_date.weekday() >= 5:
        target_date -= dt.timedelta(days=1)
    
    return target_date


def is_market_hours_et(hour: int | None = None) -> bool:
    """
    Check if current time is within market hours (9:30 AM - 4:00 PM ET).
    
    Args:
        hour: Hour to check in ET (0-23), defaults to current ET hour
        
    Returns:
        True if within market hours
        
    Note:
        This is a simplified check - doesn't account for early closes or holidays.
        For production use, consider more sophisticated market hours libraries.
    """
    if hour is None:
        # Get current ET hour (approximate - doesn't handle DST transitions perfectly)
        utc_now = dt.datetime.utcnow()
        # Assume EST (UTC-5) during winter, EDT (UTC-4) during summer
        # This is approximate - for exact timing, use pytz
        et_hour = (utc_now.hour - 5) % 24  # Rough EST conversion
        hour = et_hour
    
    return 9 <= hour <= 16  # 9:30 AM to 4:00 PM ET (allowing some buffer)


# Module-level cache for performance
_holiday_set = set(US_MARKET_HOLIDAYS_2024_2027)

def is_trading_day_fast(date: dt.date) -> bool:
    """
    Fast version of is_trading_day using cached holiday set.
    
    Args:
        date: Date to check
        
    Returns:
        True if trading day, False otherwise
    """
    return date.weekday() < 5 and date not in _holiday_set