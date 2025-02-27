"""
Functions for generating and displaying warning signals for economic indicators.
"""
import pandas as pd
import numpy as np
from data.processing import check_consecutive_increase, check_consecutive_decrease


def create_warning_indicator(value, threshold, higher_is_bad=True, neutral=False):
    """
    Create a warning signal indicator.
    
    Args:
        value: Value to check
        threshold: Threshold for warning
        higher_is_bad (bool, optional): Whether higher values are bad
        neutral (bool, optional): Whether to return a neutral indicator
        
    Returns:
        str: Warning indicator emoji
    """
    if neutral:
        return "⚪"  # Grey dot for neutral state
    if higher_is_bad:
        color = "red" if value > threshold else "green"
    else:
        color = "red" if value < threshold else "green"
    return f"🔴" if color == "red" else "🟢"


def create_warning_status(value, thresholds, labels=None, higher_is_bad=True):
    """
    Generate a status label based on multiple thresholds.
    
    Args:
        value: Value to check
        thresholds: List of threshold values in ascending order
        labels: List of labels corresponding to thresholds (should be len(thresholds) + 1)
        higher_is_bad (bool, optional): Whether higher values are bad
        
    Returns:
        str: Status label
    """
    if labels is None:
        labels = ["Normal", "Warning", "Alert", "Critical"]
    
    # Ensure we have enough labels
    if len(labels) != len(thresholds) + 1:
        raise ValueError("Number of labels should be one more than number of thresholds")
    
    # Determine which threshold range the value falls into
    if higher_is_bad:
        for i, threshold in enumerate(thresholds):
            if value <= threshold:
                return labels[i]
        return labels[-1]
    else:
        for i, threshold in enumerate(thresholds):
            if value >= threshold:
                return labels[i]
        return labels[-1]


def create_trend_indicator(values, periods=3):
    """
    Generate a trend indicator (up/down/flat) based on recent values.
    
    Args:
        values: Array-like of values
        periods: Number of periods to consider for trend
        
    Returns:
        str: Trend indicator emoji and description
    """
    if len(values) < periods:
        return "⚪ Insufficient data"
    
    # Get the last 'periods' values
    recent_values = values[-periods:]
    
    # Calculate the trend
    if all(recent_values[i] < recent_values[i+1] for i in range(len(recent_values)-1)):
        return "📈 Increasing"
    elif all(recent_values[i] > recent_values[i+1] for i in range(len(recent_values)-1)):
        return "📉 Decreasing"
    else:
        # Check if the overall trend is up or down
        if recent_values[-1] > recent_values[0]:
            return "↗️ Mixed (upward bias)"
        elif recent_values[-1] < recent_values[0]:
            return "↘️ Mixed (downward bias)"
        else:
            return "➡️ Flat"


def format_warning_message(status, message, details=None):
    """
    Format a warning message with consistent styling.
    
    Args:
        status: Status indicator emoji
        message: Main warning message
        details: Optional details to include
        
    Returns:
        str: Formatted warning message
    """
    formatted_message = f"{status} {message}"
    if details:
        formatted_message += f"\n\n{details}"
    return formatted_message


# Indicator-specific warning functions

def generate_hours_worked_warning(hours_data):
    """
    Generate warning signals for hours worked data.
    
    Args:
        hours_data (dict): Dictionary with hours worked data
        
    Returns:
        str: Formatted warning message
    """
    consecutive_declines = hours_data['consecutive_declines']
    consecutive_increases = hours_data['consecutive_increases']
    
    # Determine warning status
    if consecutive_declines >= 3:
        status = create_warning_indicator(True, 0.5)  # Red indicator
        message = "Bearish"
    elif consecutive_increases >= 3:
        status = create_warning_indicator(False, 0.5)  # Green indicator
        message = "Bullish"
    else:
        status = create_warning_indicator(False, 0.5, neutral=True)  # Grey indicator
        message = "No Trend"
    
    # Add details
    current_hours = hours_data['recent_hours'][-1]
    
    details = f"""
    Current Avg Weekly Hours: {current_hours:.1f}
    
    **Key Signals to Watch:**
    - Three or more consecutive months of declining hours (Bearish)
    - Three or more consecutive months of increasing hours (Bullish)
    """
    
    return format_warning_message(status, message, details)


def generate_core_cpi_warning(core_cpi_data):
    """
    Generate warning signals for Core CPI data.
    
    Args:
        core_cpi_data (dict): Dictionary with Core CPI data
        
    Returns:
        str: Formatted warning message
    """
    recent_cpi_mom = core_cpi_data['recent_cpi_mom']
    current_cpi_mom = core_cpi_data['current_cpi_mom']
    
    # Check for consecutive increases and decreases
    cpi_increasing = check_consecutive_increase(recent_cpi_mom, 3)
    cpi_decreasing = check_consecutive_decrease(recent_cpi_mom, 3)
    
    # Determine warning status
    if cpi_increasing:
        status = create_warning_indicator(True, 0.5)  # Red indicator
        message = "Bearish"
    elif cpi_decreasing:
        status = create_warning_indicator(False, 0.5)  # Green indicator
        message = "Bullish"
    else:
        status = create_warning_indicator(False, 0.5, neutral=True)  # Grey indicator
        message = "No Trend"
    
    # Add details
    details = f"""
    Current Core CPI MoM: {current_cpi_mom:.2f}%
    
    **Key Signals to Watch:**
    - Three consecutive months of increasing MoM inflation (Bearish)
    - Three consecutive months of decreasing MoM inflation (Bullish)
    """
    
    return format_warning_message(status, message, details)


def generate_initial_claims_warning(claims_data):
    """
    Generate warning signals for initial claims data.
    
    Args:
        claims_data (dict): Dictionary with claims data
        
    Returns:
        str: Formatted warning message
    """
    claims_increasing = claims_data['claims_increasing']
    claims_decreasing = claims_data['claims_decreasing']
    
    # Determine warning status
    if claims_increasing:
        status = create_warning_indicator(True, 0.5)  # Red indicator
        message = "Bearish"
    elif claims_decreasing:
        status = create_warning_indicator(False, 0.5)  # Green indicator
        message = "Bullish"
    else:
        status = create_warning_indicator(False, 0.5, neutral=True)  # Grey indicator
        message = "No Trend"
    
    # Add details
    details = f"""
    **Key Warning Signals to Watch:**
    - Three consecutive weeks of rising claims
    - Claims rising while PCE is also rising
    - Sudden spike in claims (>10% week-over-week)
    
    **Playbook for Rising Claims:**
    - Scale back aggressive positions
    - Shift toward defensive sectors
    - Build cash reserves
    - "Small moves early beat big moves late"
    """
    
    return format_warning_message(status, message, details)


def generate_pce_warning(pce_data):
    """
    Generate warning signals for PCE data.
    
    Args:
        pce_data (dict): Dictionary with PCE data
        
    Returns:
        str: Formatted warning message
    """
    current_pce = pce_data['current_pce']
    current_pce_mom = pce_data['current_pce_mom']
    pce_increasing = pce_data['pce_increasing']
    pce_decreasing = pce_data['pce_decreasing']
    
    # Determine warning status
    if pce_increasing:
        status = create_warning_indicator(True, 0.5)  # Red indicator
        message = "Bearish"
    elif pce_decreasing:
        status = create_warning_indicator(False, 0.5)  # Green indicator
        message = "Bullish"
    else:
        status = create_warning_indicator(False, 0.5, neutral=True)  # Grey indicator
        message = "No Trend"
    
    # Add details
    details = f"""
    Current PCE MoM: {current_pce_mom:.2f}%
    
    **Key Signals to Watch:**
    - Three consecutive months of increasing MoM inflation (Bearish)
    - Three consecutive months of decreasing MoM inflation (Bullish)
    
    **Key Framework:**
    - PCE dropping + Stable jobs = Add risk
    - PCE rising + Rising claims = Get defensive
    
    **What PCE Tells Us:**
    - Rate trends
    - Market conditions
    - Risk appetite
    
    **Remember:** "Everyone watches CPI, but PCE guides policy."
    """
    
    return format_warning_message(status, message, details)


def generate_pmi_warning(pmi_data):
    """
    Generate warning signals for PMI data.
    
    Args:
        pmi_data (dict): Dictionary with PMI data
        
    Returns:
        str: Formatted warning message
    """
    latest_pmi = pmi_data['latest_pmi']
    
    # Determine warning status - this will give green for PMI >= 50
    status = create_warning_indicator(latest_pmi < 50, 0.5)
    
    # Create message based on PMI value
    if latest_pmi < 50:
        message = "Bearish"
    else:  # This includes PMI == 50
        message = "Bullish"
    
    # Add details
    sector_status = "Manufacturing sector contracting" if latest_pmi < 50 else "Manufacturing sector expanding"
    details = f"""
    Current PMI Proxy Value: {latest_pmi:.1f}
    {sector_status}
    
    **Key Warning Signals to Watch:**
    - PMI below 50 (indicating contraction)
    - Declining trend over multiple months
    
    **Key Insight:** "PMI is a leading indicator of manufacturing health."
    """
    
    return format_warning_message(status, message, details)
