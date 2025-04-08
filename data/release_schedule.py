"""
Functions for managing economic indicator release schedules.
"""
import datetime
from datetime import timedelta
import calendar
from typing import Dict, Optional

# Mapping of indicators to their FRED series IDs and release IDs
INDICATOR_SERIES_MAP = {
    'pce': {
        'series_id': 'PCE',  # Personal Consumption Expenditures
        'release_id': 149  # Monthly Personal Income and Outlays
    },
    'core_cpi': {
        'series_id': 'CPILFESL',  # Core Consumer Price Index
        'release_id': 53,  # Consumer Price Index (Monthly)
        'release_name': 'Consumer Price Index'  # Adding name for clarity
    },
    'claims': {
        'series_id': 'ICSA',  # Initial Claims
        'release_id': 59  # Weekly Initial Claims
    },
    'hours': {
        'series_id': 'AWHNONAG',  # Average Weekly Hours
        'release_id': 11  # Employment Situation
    },
    'pmi': {  # PMI components
        'new_orders': 'AMTMNO',
        'production': 'IPMAN',
        'employment': 'MANEMP',
        'deliveries': 'AMDMUS',
        'inventories': 'MNFCTRIMSA',
        'release_id': 13  # G.17 Industrial Production and Capacity Utilization
    },
    'new_orders': {
        'series_id': 'DGORDER',  # Durable Goods Orders
        'release_id': 85  # Manufacturers' Shipments, Inventories, and Orders
    },
    'yield_curve': {
        'series_ids': ['DGS10', 'DGS2'],  # 10Y and 2Y Treasury yields
        'release_id': 20  # H.15 Selected Interest Rates
    }
}

def get_next_release_date(indicator_type: str, fred_client=None, current_date=None) -> Optional[datetime.datetime]:
    """
    Get the next release date for a given economic indicator using FRED API if available,
    otherwise fallback to estimated dates.
    
    Args:
        indicator_type (str): Type of indicator
        fred_client (FredClient, optional): FRED API client instance
        current_date (datetime, optional): Current date for calculation
        
    Returns:
        datetime: Next expected release date
    """
    if current_date is None:
        current_date = datetime.datetime.now()
    
    # If we have a FRED client, try to get the actual release date
    if fred_client is not None:
        indicator_info = INDICATOR_SERIES_MAP.get(indicator_type)
        if indicator_info:
            # Try using series IDs first as this is more reliable
            if 'series_id' in indicator_info:
                release_date = fred_client.get_series_release_date(indicator_info['series_id'])
                if release_date:
                    return release_date
            elif 'series_ids' in indicator_info:
                # For indicators that use multiple series
                release_dates = fred_client.get_multiple_release_dates(indicator_info['series_ids'])
                if release_dates:
                    return min(release_dates.values())
            elif isinstance(indicator_info, dict) and 'release_id' not in indicator_info:
                # For PMI-like indicators with multiple component series
                release_dates = fred_client.get_multiple_release_dates(list(
                    v for k, v in indicator_info.items() if k != 'release_id'
                ))
                if release_dates:
                    return min(release_dates.values())
            
            # If series approach fails, try release ID as fallback
            if 'release_id' in indicator_info:
                release_date = fred_client.get_next_release_date_from_release(indicator_info['release_id'])
                if release_date:
                    return release_date
    
    # Fallback to estimated dates if FRED API is not available or doesn't return dates
    # Get the first day of next month
    first_of_next_month = (current_date.replace(day=1) + timedelta(days=32)).replace(day=1)
    
    # Release schedules for each indicator (fallback estimates)
    schedules = {
        'claims': {
            'weekday': 3,  # Thursday
            'offset': 1,  # 1 week lag
            'frequency': 'weekly'
        },
        'pce': {
            'day': 'last_business_day',  # Last business day of month
            'offset': 1,  # 1 month lag
            'frequency': 'monthly'
        },
        'core_cpi': {
            'day': 12,  # Usually around 12th of each month
            'offset': 1,  # 1 month lag
            'frequency': 'monthly'
        },
        'hours': {
            'day': 1,  # First Friday of month
            'weekday': 4,  # Friday
            'offset': 1,  # 1 month lag
            'frequency': 'monthly'
        },
        'pmi': {
            'day': 1,  # First business day of month
            'offset': 0,  # Current month
            'frequency': 'monthly'
        },
        'new_orders': {
            'day': 25,  # Around 25th of each month
            'offset': 1,  # 1 month lag
            'frequency': 'monthly'
        },
        'yield_curve': {
            'frequency': 'daily'  # Updated daily
        }
    }
    
    schedule = schedules.get(indicator_type)
    if not schedule:
        return None
        
    if schedule['frequency'] == 'weekly':
        # For weekly releases (like Initial Claims)
        next_date = current_date + timedelta(days=(schedule['weekday'] - current_date.weekday() + 7) % 7)
        if next_date <= current_date:
            next_date += timedelta(weeks=1)
        return next_date
        
    elif schedule['frequency'] == 'daily':
        # For daily releases (like Yield Curve)
        next_date = current_date + timedelta(days=1)
        # Skip weekends
        while next_date.weekday() > 4:  # Saturday = 5, Sunday = 6
            next_date += timedelta(days=1)
        return next_date
        
    else:  # Monthly releases
        target_month = first_of_next_month
        if schedule.get('offset', 0) > 0:
            target_month = target_month + timedelta(days=32)
            target_month = target_month.replace(day=1)
            
        if schedule.get('day') == 'last_business_day':
            # Find last business day of the month
            last_day = calendar.monthrange(target_month.year, target_month.month)[1]
            next_date = target_month.replace(day=last_day)
            while next_date.weekday() > 4:  # Skip weekends
                next_date -= timedelta(days=1)
            return next_date
            
        elif schedule.get('weekday') is not None:
            # Find first occurrence of weekday in month
            next_date = target_month
            while next_date.weekday() != schedule['weekday']:
                next_date += timedelta(days=1)
            return next_date
            
        else:
            # Use specific day of month
            next_date = target_month.replace(day=schedule['day'])
            # If it falls on weekend, move to next business day
            while next_date.weekday() > 4:
                next_date += timedelta(days=1)
            return next_date

def format_release_date(date):
    """
    Format the release date in a human-readable format.
    
    Args:
        date (datetime): Release date
        
    Returns:
        str: Formatted date string
    """
    if date is None:
        return "Next release date not available"
        
    today = datetime.datetime.now()
    days_until = (date - today).days
    
    if days_until < 0:
        return "Next release date not available"
    elif days_until == 0:
        return "Next release: Today"
    elif days_until == 1:
        return "Next release: Tomorrow"
    else:
        return f"Next release: {date.strftime('%B %d, %Y')} ({days_until} days)"
