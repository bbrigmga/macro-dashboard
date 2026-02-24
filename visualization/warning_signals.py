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


def _coerce_scalar(value):
    """Coerce array-like inputs to a single scalar value."""
    if isinstance(value, pd.Series):
        if value.empty:
            return None
        return value.iloc[-1]

    if isinstance(value, np.ndarray):
        if value.size == 0:
            return None
        return value.reshape(-1)[-1]

    if isinstance(value, (list, tuple)):
        if not value:
            return None
        return value[-1]

    if isinstance(value, np.generic):
        return value.item()

    return value


def _is_missing(value) -> bool:
    """Return True for None/NaN-like values."""
    if value is None:
        return True
    return bool(pd.isna(value))


def _coerce_bool(value) -> bool:
    """Safely convert possibly array-like truthy values to bool."""
    scalar_value = _coerce_scalar(value)
    if _is_missing(scalar_value):
        return False
    return bool(scalar_value)


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


def generate_indicator_warning(data: dict, config) -> dict:
    """
    Generic warning signal generator driven by config.
    
    Args:
        data: Dictionary containing indicator data
        config: IndicatorConfig object with signal configuration
        
    Returns:
        dict: {"status": str, "details": str}
    """
    from src.config.indicator_registry import IndicatorConfig
    
    if not isinstance(config, IndicatorConfig):
        raise TypeError("config must be an IndicatorConfig object")
    
    # Handle custom status functions
    if config.bullish_condition == "custom" and config.custom_status_fn:
        # Import and call the custom function
        module_path, function_name = config.custom_status_fn.rsplit('.', 1)
        import importlib
        module = importlib.import_module(module_path)
        custom_function = getattr(module, function_name)
        
        # Custom functions return formatted warning messages, but we need dict format
        warning_message = custom_function(data)
        
        # Inject warning description if not already present
        if config.warning_description and config.warning_description not in warning_message:
            warning_message = f"<div style='margin-bottom: 1rem;'><strong>Signal Description:</strong><br/>{config.warning_description}</div>\n\n" + warning_message
            
        # Extract status from the message (simple heuristic based on content)
        if "Bearish" in warning_message:
            status = "Bearish"
        elif "Bullish" in warning_message:
            status = "Bullish"
        else:
            status = "Neutral"
            
        return {"status": status, "details": warning_message}
    
    # Get the latest value from data
    latest_value = None
    
    # Try different ways to get the latest value
    if 'current_value' in data:
        latest_value = data['current_value']
    elif config.value_column in data and hasattr(data[config.value_column], 'iloc'):
        # DataFrame case
        latest_value = data[config.value_column].iloc[-1]
    elif isinstance(data, dict) and 'latest_value' in data:
        latest_value = data['latest_value']
    elif f'current_{config.key}' in data:
        # Try current_<indicator_name> format
        latest_value = data[f'current_{config.key}']

    latest_value = _coerce_scalar(latest_value)
    
    # Final fallback: look inside the nested 'data' DataFrame using config.value_column
    if latest_value is None:
        nested_df = data.get('data')
        if isinstance(nested_df, pd.DataFrame) and not nested_df.empty:
            if config.value_column in nested_df.columns:
                vals = nested_df[config.value_column].dropna()
                if not vals.empty:
                    latest_value = _coerce_scalar(vals.iloc[-1])
    
    # Handle threshold-based conditions
    if config.bullish_condition == "below_threshold" and config.threshold is not None:
        if _is_missing(latest_value):
            status = "Neutral"
            status_emoji = create_warning_indicator(False, 0.5, neutral=True)
        elif latest_value < config.threshold:
            status = "Bullish"
            status_emoji = create_warning_indicator(False, 0.5)
        else:
            status = "Bearish" 
            status_emoji = create_warning_indicator(True, 0.5)
            
    elif config.bullish_condition == "above_threshold" and config.threshold is not None:
        if _is_missing(latest_value):
            status = "Neutral"
            status_emoji = create_warning_indicator(False, 0.5, neutral=True)
        elif latest_value > config.threshold:
            status = "Bullish"
            status_emoji = create_warning_indicator(False, 0.5)
        else:
            status = "Bearish"
            status_emoji = create_warning_indicator(True, 0.5)
            
    elif config.bullish_condition == "decreasing":
        # Check for consecutive increases/decreases
        increasing_key = f"{config.key}_increasing"
        decreasing_key = f"{config.key}_decreasing"
        
        is_increasing = _coerce_bool(data.get(increasing_key, False))
        is_decreasing = _coerce_bool(data.get(decreasing_key, False))
        
        if is_increasing:
            # For indicators where increasing is bearish (inflation, claims, etc.)
            # Exception: hours_worked, new_orders, pscf_price where increasing is bullish
            if config.key in ["hours_worked", "new_orders", "pscf_price"]:
                status = "Bullish"
                status_emoji = create_warning_indicator(False, 0.5)
            else:
                status = "Bearish" 
                status_emoji = create_warning_indicator(True, 0.5)
        elif is_decreasing:
            # For indicators where decreasing is bullish (inflation, claims, etc.)
            # Exception: hours_worked, new_orders, pscf_price where decreasing is bearish
            if config.key in ["hours_worked", "new_orders", "pscf_price"]:
                status = "Bearish"
                status_emoji = create_warning_indicator(True, 0.5)
            else:
                status = "Bullish"
                status_emoji = create_warning_indicator(False, 0.5)
        else:
            status = "Neutral"
            status_emoji = create_warning_indicator(False, 0.5, neutral=True)
    else:
        # Default fallback
        status = "Neutral"
        status_emoji = create_warning_indicator(False, 0.5, neutral=True)
    
    # Create details section
    if latest_value is not None:
        try:
            fv = float(latest_value)
            if abs(fv) < 0.01:
                _display_value = f"{fv:.5f}"
            elif abs(fv) < 10:
                _display_value = f"{fv:.2f}"
            elif abs(fv) < 1000:
                _display_value = f"{fv:.2f}"
            else:
                _display_value = f"{fv:,.0f}"
        except (TypeError, ValueError):
            _display_value = str(latest_value)
    else:
        _display_value = "N/A"

    details = f"""
<div class='financial-figure' style='font-size: 1.1rem; margin-bottom: 0.5rem;'>
Current {config.display_name}: {_display_value}
</div>

<div style='margin-top: 0.5rem;'>
<strong>Signal Description:</strong><br/>
{config.warning_description}
</div>
"""
    
    # Append indicator-specific extra context derived from the thread
    _per_indicator_notes = {
        "initial_claims": """
<div style='margin-top:0.75rem; padding:0.5rem; background:#f0f4ff; border-left:3px solid #1a7fe0;'>
<strong>Playbook for rising claims:</strong>
<ul style='margin:0.25rem 0 0 1.25rem;'>
  <li>Scale back aggressive positions</li>
  <li>Shift toward defensive sectors</li>
  <li>Build cash reserves</li>
</ul>
<em>"Small moves early beat big moves late."</em>
</div>""",
        "core_cpi": """
<div style='margin-top:0.75rem; padding:0.5rem; background:#fff8f0; border-left:3px solid #ff9800;'>
<strong>When services inflation drops:</strong> Growth stocks outperform · Bonds rally · Tech leads<br/>
<strong>When it rises:</strong> Value stocks win · Real assets dominate · Tech struggles
</div>""",
        "pce": """
<div style='margin-top:0.75rem; padding:0.5rem; background:#f0fff4; border-left:3px solid #00c853;'>
<strong>PCE framework:</strong>
<ul style='margin:0.25rem 0 0 1.25rem;'>
  <li>PCE dropping + Stable jobs = <strong>Add risk</strong></li>
  <li>PCE rising + Rising claims = <strong>Get defensive</strong></li>
</ul>
<em>PCE is the Fed's preferred inflation measure and guides policy decisions.</em>
</div>""",
        "hours_worked": """
<div style='margin-top:0.75rem; padding:0.5rem; background:#f5f5f5; border-left:3px solid #78909c;'>
<strong>Why hours matter before payrolls:</strong> Employers reduce hours before cutting headcount. Watching this leading signal gives you advance warning before the headlines catch up.
</div>""",
        "yield_curve": """
<div style='margin-top:0.75rem; padding:0.5rem; background:#fff0f0; border-left:3px solid #f44336;'>
<strong>Recession track record:</strong> Yield curve inversion has preceded every U.S. recession since 1950. Extended inversion (6+ months) significantly raises recession probability. Watch the re-steepening as it often marks the start of the downturn, not the recovery.
</div>""",
        "credit_spread": """
<div style='margin-top:0.75rem; padding:0.5rem; background:#f8f0ff; border-left:3px solid #9c27b0;'>
<strong>Why credit spreads matter:</strong> Rapidly widening high-yield spreads signal that institutional money is pricing in elevated default risk — a leading indicator for equity stress and liquidity crunches.
</div>""",
        "new_orders": """
<div style='margin-top:0.75rem; padding:0.5rem; background:#f0f7ff; border-left:3px solid #607d8b;'>
<strong>Forward-looking signal:</strong> New orders represent future production commitments. Consecutive monthly declines often foreshadow ISM Manufacturing weakness and can precede broader economic slowdowns by 2–3 months.
</div>""",
    }
    
    extra = _per_indicator_notes.get(config.key, "")
    if extra:
        details += extra
    
    # Format the final message
    formatted_message = format_warning_message(status_emoji, status, details)
    
    return {"status": status, "details": formatted_message}


# Indicator-specific warning functions

def generate_usd_liquidity_warning(usd_liquidity_data):
    """
    Generate warning signals for USD Liquidity data with modern styling.
    
    Args:
        usd_liquidity_data (dict): Dictionary with USD Liquidity data
        
    Returns:
        str: Formatted warning message
    """
    current_liquidity = _coerce_scalar(usd_liquidity_data.get('current_liquidity'))
    liquidity_increasing = _coerce_bool(usd_liquidity_data.get('liquidity_increasing', False))
    liquidity_decreasing = _coerce_bool(usd_liquidity_data.get('liquidity_decreasing', False))
    
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
    
    # Format the current liquidity value for display (value is already a ratio = Liquidity/GDP)
    if _is_missing(current_liquidity):
        formatted_value = "N/A"
    else:
        formatted_value = f"{current_liquidity * 100:.1f}% of GDP"
    
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
        **Manufacturing Sector Alert — Bearish** {status}
        
        The Manufacturing PMI Proxy is currently **{latest_pmi:.1f}**, indicating the manufacturing sector is **contracting**.
        
        {methodology_description}
        
        **Interpretation:** 
        - PMI below 50 suggests economic contraction in the manufacturing sector
        - Watch trends, not just levels
        - ⚠️ **Danger Combination:** PMI below 50 + Claims rising 3 weeks + Hours worked dropping. "When these align, protect capital first."
        """
    else:
        description_text = f"""
        **Manufacturing Sector Overview — Bullish** {status}
        
        The Manufacturing PMI Proxy is currently **{latest_pmi:.1f}**, indicating the manufacturing sector is **expanding**.
        
        {methodology_description}
        
        **Interpretation:**
        - PMI above 50 suggests economic expansion in the manufacturing sector
        - Watch trends, not just levels
        - ⚠️ **Danger Combination:** PMI below 50 + Claims rising 3 weeks + Hours worked dropping. "When these align, protect capital first."
        """
    
    return description_text if latest_pmi >= 50 else warning_text


def generate_regime_quadrant_warning(data: dict, config=None) -> dict:
    """Generate warning signal for the regime quadrant indicator."""
    regime = data.get('current_regime', 'Unknown')
    
    status_map = {
        'Goldilocks': 'Bullish',
        'Reflation': 'Neutral',
        'Stagflation': 'Bearish',
        'Deflation': 'Bearish',
    }
    
    return {
        'status': status_map.get(regime, 'Neutral'),
        'description': data.get('regime_description', f'Current regime: {regime}'),
        'indicator': '🟢' if regime == 'Goldilocks' else ('🔴' if regime in ('Stagflation', 'Deflation') else '🟡'),
    }
