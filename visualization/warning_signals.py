"""
Functions for generating and displaying warning signals for economic indicators with a modern finance-based theme.
"""
import pandas as pd
import numpy as np
from data.processing import check_consecutive_increase, check_consecutive_decrease


# Define theme colors for warning signals
WARNING_COLORS = {
    'bearish': '#f44336',  # Red
    'bullish': '#00c853',  # Green
    'neutral': '#78909c'   # Grey
}


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
    Format a warning message with consistent styling for the modern theme.
    
    Args:
        status: Status indicator emoji
        message: Main warning message
        details: Optional details to include
        
    Returns:
        str: Formatted warning message
    """
    # Determine color class based on message
    color_class = ""
    if message == "Bearish":
        color_class = f"<span style='color: {WARNING_COLORS['bearish']};'>"
    elif message == "Bullish":
        color_class = f"<span style='color: {WARNING_COLORS['bullish']};'>"
    else:
        color_class = f"<span style='color: {WARNING_COLORS['neutral']};'>"
    
    # Format the message with HTML styling
    formatted_message = f"{status} {color_class}{message}</span>"
    
    if details:
        formatted_message += f"\n\n{details}"
    
    return formatted_message


# Indicator-specific warning functions

def generate_hours_worked_warning(hours_data):
    """
    Generate warning signals for hours worked data with modern styling.
    
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
<div class='financial-figure' style='font-size: 1.1rem; margin-bottom: 0.5rem;'>
Current Avg Weekly Hours: {current_hours:.1f}
</div>

<div style='margin-top: 0.5rem;'>
<strong>Key Signals to Watch:</strong>
<ul style='margin-top: 0.25rem; padding-left: 1.5rem;'>
    <li>Three or more consecutive months of declining hours (Bearish)</li>
    <li>Three or more consecutive months of increasing hours (Bullish)</li>
</ul>
</div>
"""
    
    return format_warning_message(status, message, details)


def generate_core_cpi_warning(core_cpi_data):
    """
    Generate warning signals for Core CPI data with modern styling.
    
    Args:
        core_cpi_data (dict): Dictionary with Core CPI data
        
    Returns:
        str: Formatted warning message
    """
    recent_cpi_mom = core_cpi_data['recent_cpi_mom']
    current_cpi_mom = core_cpi_data['current_cpi_mom']
    
    # Check for consecutive increases and decreases
    cpi_increasing = core_cpi_data.get('cpi_increasing', False)
    cpi_decreasing = core_cpi_data.get('cpi_decreasing', False)
    
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
<div class='financial-figure' style='font-size: 1.1rem; margin-bottom: 0.5rem;'>
Current Core CPI MoM: {current_cpi_mom:.2f}%
</div>

<div style='margin-top: 0.5rem;'>
<strong>Key Signals to Watch:</strong>
<ul style='margin-top: 0.25rem; padding-left: 1.5rem;'>
    <li>Four consecutive months of increasing MoM inflation (Bearish)</li>
    <li>Four consecutive months of decreasing MoM inflation (Bullish)</li>
</ul>
</div>
"""
    
    return format_warning_message(status, message, details)


def generate_initial_claims_warning(claims_data):
    """
    Generate warning signals for initial claims data with modern styling.
    
    Args:
        claims_data (dict): Dictionary with claims data
        
    Returns:
        str: Formatted warning message
    """
    claims_increasing = claims_data.get('claims_increasing', False)
    claims_decreasing = claims_data.get('claims_decreasing', False)
    
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
<div style='margin-top: 0.5rem;'>
<strong>Key Warning Signals to Watch:</strong>
<ul style='margin-top: 0.25rem; padding-left: 1.5rem;'>
    <li>Four consecutive weeks of rising claims (Bearish)</li>
    <li>Four consecutive weeks of falling claims (Bullish)</li>
    <li>Sudden spike in claims (>10% week-over-week)</li>
</ul>
</div>

<div style='margin-top: 0.5rem;'>
<strong>Playbook for Rising Claims:</strong>
<ul style='margin-top: 0.25rem; padding-left: 1.5rem;'>
    <li>Scale back aggressive positions</li>
    <li>Shift toward defensive sectors</li>
    <li>Build cash reserves</li>
</ul>
</div>

<div style='font-style: italic; margin-top: 0.5rem;'>
"Small moves early beat big moves late"
</div>
"""
    
    return format_warning_message(status, message, details)


def generate_pce_warning(pce_data):
    """
    Generate warning signals for PCE data with modern styling.
    
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
<div class='financial-figure' style='font-size: 1.1rem; margin-bottom: 0.5rem;'>
Current PCE MoM: {current_pce_mom:.2f}%
</div>

<div style='margin-top: 0.5rem;'>
<strong>Key Signals to Watch:</strong>
<ul style='margin-top: 0.25rem; padding-left: 1.5rem;'>
    <li>Four consecutive months of increasing MoM inflation (Bearish)</li>
    <li>Four consecutive months of decreasing MoM inflation (Bullish)</li>
</ul>
</div>

<div style='margin-top: 0.5rem;'>
<strong>Key Framework:</strong>
<ul style='margin-top: 0.25rem; padding-left: 1.5rem;'>
    <li>PCE dropping + Stable jobs = Add risk</li>
    <li>PCE rising + Rising claims = Get defensive</li>
</ul>
</div>

<div style='font-style: italic; margin-top: 0.5rem;'>
"Everyone watches CPI, but PCE guides policy."
</div>
"""
    
    return format_warning_message(status, message, details)


def generate_usd_liquidity_warning(usd_liquidity_data):
    """
    Generate warning signals for USD Liquidity data with modern styling.
    
    Args:
        usd_liquidity_data (dict): Dictionary with USD Liquidity data
        
    Returns:
        str: Formatted warning message
    """
    current_liquidity = usd_liquidity_data['current_liquidity']
    liquidity_increasing = usd_liquidity_data['liquidity_increasing']
    liquidity_decreasing = usd_liquidity_data['liquidity_decreasing']
    
    # For USD Liquidity, increasing is generally bullish for markets
    if liquidity_increasing:
        status = create_warning_indicator(False, 0.5)  # Green indicator
        message = "Bullish"
    elif liquidity_decreasing:
        status = create_warning_indicator(True, 0.5)  # Red indicator
        message = "Bearish"
    else:
        status = create_warning_indicator(False, 0.5, neutral=True)  # Grey indicator
        message = "No Trend"
    
    # Format the current liquidity value for display in trillions
    formatted_value = f"{current_liquidity/1000000:.2f}T"  # Convert from millions to trillions
    
    # Add details
    details = f"""
<div class='financial-figure' style='font-size: 1.1rem; margin-bottom: 0.5rem;'>
Current USD Liquidity: {formatted_value}
</div>

<div style='margin-top: 0.5rem;'>
<strong>Key Signals to Watch:</strong>
<ul style='margin-top: 0.25rem; padding-left: 1.5rem;'>
    <li>Three consecutive months of increasing liquidity (Bullish)</li>
    <li>Three consecutive months of decreasing liquidity (Bearish)</li>
</ul>
</div>

<div style='margin-top: 0.5rem;'>
<strong>Key Framework:</strong>
<ul style='margin-top: 0.25rem; padding-left: 1.5rem;'>
    <li>Rising liquidity + Stable inflation = Bullish for risk assets</li>
    <li>Falling liquidity + Rising inflation = Bearish for risk assets</li>
</ul>
</div>

<div style='margin-top: 0.5rem;'>
<strong>Formula:</strong>
<ul style='margin-top: 0.25rem; padding-left: 1.5rem;'>
    <li>USD Liquidity = WALCL - (RRPONTTLD × 1000) - (WTREGEN × 1000)</li>
    <li><small>WALCL (millions) - Fed Balance Sheet</small></li>
    <li><small>RRPONTTLD (billions, converted to millions) - Reverse Repo</small></li>
    <li><small>WTREGEN (billions, converted to millions) - Treasury General Account</small></li>
</ul>
</div>

<div style='font-style: italic; margin-top: 0.5rem;'>
"Liquidity drives markets in the short term, fundamentals matter in the long term."
</div>
"""
    
    return format_warning_message(status, message, details)


def generate_pmi_warning(pmi_data):
    """
    Generate a warning or description for the Manufacturing PMI.
    
    Args:
        pmi_data (dict): Dictionary with PMI data
        
    Returns:
        str: Formatted warning or description text
    """
    latest_pmi = pmi_data['latest_pmi']
    status = create_warning_indicator(latest_pmi < 50, 0.5)
    
    # Detailed explanation of the new PMI calculation methodology
    methodology_description = """
    **PMI Calculation Methodology:**
    - **Data Sources:** Uses 5 key manufacturing indicators from FRED
      1. New Orders (30% weight)
      2. Production (25% weight)
      3. Employment (20% weight)
      4. Supplier Deliveries (15% weight)
      5. Inventories (10% weight)
    
    - **Calculation Steps:**
      1. Calculate month-over-month percentage changes
      2. Compute standard deviation over a 10-year historical period
      3. Transform to Diffusion Indices using: 50 + (Percentage Change / Standard Deviation * 10)
      4. Cap index values between 0 and 100
      5. Compute weighted average of component indices
    """
    
    if latest_pmi < 50:
        warning_text = f"""
        **Manufacturing Sector Alert** {status}
        
        The Manufacturing PMI Proxy is currently **{latest_pmi:.1f}**, indicating the manufacturing sector is **contracting**.
        
        {methodology_description}
        
        **Interpretation:** 
        - PMI below 50 suggests economic contraction in the manufacturing sector
        - Potential indicators of economic slowdown
        - May signal reduced industrial activity and economic challenges
        """
    else:
        description_text = f"""
        **Manufacturing Sector Overview** {status}
        
        The Manufacturing PMI Proxy is currently **{latest_pmi:.1f}**, indicating the manufacturing sector is **expanding**.
        
        {methodology_description}
        
        **Interpretation:**
        - PMI above 50 suggests economic expansion in the manufacturing sector
        - Indicates positive industrial activity and economic growth
        - Potential signs of increasing production and demand
        """
    
    return description_text if latest_pmi >= 50 else warning_text
