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
    
    # Check the last `count` pairwise moves, which requires `count + 1` points.
    start_idx = len(values) - (count + 1)
    result = all(values[i] < values[i+1] for i in range(start_idx, len(values)-1))
    
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
    
    # Check the last `count` pairwise moves, which requires `count + 1` points.
    start_idx = len(values) - (count + 1)
    result = all(values[i] > values[i+1] for i in range(start_idx, len(values)-1))
    
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


def blended_momentum_zscore(
    series: pd.Series,
    roc_periods: tuple[int, ...] = (20, 60, 120),
    zscore_window: int = 252
) -> pd.Series:
    """
    Blend multiple ROC-based z-score horizons into one momentum signal.

    Args:
        series: Input time series (price or ratio)
        roc_periods: ROC lookbacks to combine (in trading days)
        zscore_window: Rolling window for z-score normalization

    Returns:
        pd.Series: Blended z-score series
    """
    if series is None or len(series) == 0:
        return pd.Series(dtype=float)

    components = []
    for period in roc_periods:
        if period <= 0:
            continue
        z_component = calculate_roc_zscore(series, roc_period=period, zscore_window=zscore_window)
        components.append(z_component.rename(f"roc_{period}"))

    if not components:
        return pd.Series(index=series.index, dtype=float)

    blended = pd.concat(components, axis=1).mean(axis=1, skipna=True)
    blended.name = "blended_momentum_zscore"
    return blended


def build_composite_axis(proxy_zscores: dict[str, pd.Series], min_series: int = 1) -> pd.Series:
    """
    Build a composite axis by averaging aligned proxy z-score series.

    Args:
        proxy_zscores: Mapping of proxy name -> z-score series
        min_series: Minimum number of available proxies required per date

    Returns:
        pd.Series: Composite axis z-score
    """
    valid_series = []
    for name, series in proxy_zscores.items():
        if series is None or len(series) == 0:
            continue
        clean = pd.to_numeric(series, errors='coerce')
        valid_series.append(clean.rename(name))

    if not valid_series:
        return pd.Series(dtype=float)

    aligned = pd.concat(valid_series, axis=1, join='inner').dropna(how='all')
    if aligned.empty:
        return pd.Series(dtype=float)

    available_count = aligned.notna().sum(axis=1)
    composite = aligned.mean(axis=1, skipna=True)
    composite = composite.where(available_count >= max(1, min_series))
    composite.name = "composite_axis"
    return composite


def anchor_zscore(rolling_z: pd.Series, series: pd.Series, weight: float = 0.3, min_periods: int = 126) -> pd.Series:
    """
    Anchor rolling z-scores using an expanding baseline to reduce drift.

    Args:
        rolling_z: Rolling-window z-score series
        series: Raw underlying series used to compute expanding z-score
        weight: Blend weight for expanding z-score contribution
        min_periods: Minimum expanding window observations

    Returns:
        pd.Series: Anchored z-score series
    """
    if rolling_z is None or len(rolling_z) == 0:
        return pd.Series(dtype=float)

    weight = float(np.clip(weight, 0.0, 1.0))
    series = pd.to_numeric(series, errors='coerce')

    exp_mean = series.expanding(min_periods=min_periods).mean()
    exp_std = series.expanding(min_periods=min_periods).std()
    exp_std = exp_std.replace(0, np.nan)
    expanding_z = (series - exp_mean) / exp_std

    anchored = (1 - weight) * rolling_z + weight * expanding_z
    anchored = anchored.where(~rolling_z.isna(), np.nan)
    anchored = anchored.combine_first(rolling_z)
    anchored.name = rolling_z.name if rolling_z.name else "anchored_zscore"
    return anchored


def classify_regime(
    growth: float,
    inflation: float,
    neutral_band: float = 0.25,
    prev_regime: str | None = None
) -> str:
    """
    Classify growth/inflation point into regime with dead-zone and hysteresis.

    Args:
        growth: Growth axis value
        inflation: Inflation axis value
        neutral_band: Absolute dead-zone around each axis
        prev_regime: Previous regime label for hysteresis behavior

    Returns:
        str: Regime label
    """
    if pd.isna(growth) or pd.isna(inflation):
        return "Unknown"

    if abs(growth) < neutral_band or abs(inflation) < neutral_band:
        if prev_regime and prev_regime not in {"Unknown", "Transition"}:
            # Hold prior regime while signal is in the dead-zone.
            return prev_regime
        return "Transition"

    if growth >= 0 and inflation >= 0:
        return "Reflation"
    if growth >= 0 and inflation < 0:
        return "Goldilocks"
    if growth < 0 and inflation >= 0:
        return "Stagflation"
    return "Deflation"


def forecast_ou(series: pd.Series, horizon: int | None = None) -> dict:
    """
    Forecast a mean-reverting series using an AR(1) / OU discretization.

    Args:
        series: Input series to model
        horizon: Forecast horizon in trading days (default matches proxy DELTA_DAYS)

    Returns:
        dict: projected, variance, beta, intercept, residual_std
    """
    if horizon is None:
        from src.config.growth_proxy import FORECAST_HORIZON_DAYS
        horizon = FORECAST_HORIZON_DAYS
    clean = pd.to_numeric(series, errors='coerce').dropna()
    if clean.empty:
        return {
            "projected": 0.0,
            "variance": 0.0,
            "beta": 0.0,
            "intercept": 0.0,
            "residual_std": 0.0,
        }

    if len(clean) < 20:
        last_val = float(clean.iloc[-1])
        return {
            "projected": last_val,
            "variance": 0.0,
            "beta": 0.0,
            "intercept": last_val,
            "residual_std": 0.0,
        }

    x_prev = clean.iloc[:-1]
    x_next = clean.iloc[1:]
    x_var = float(x_prev.var(ddof=1))

    if x_var <= 0 or np.isnan(x_var):
        last_val = float(clean.iloc[-1])
        return {
            "projected": last_val,
            "variance": 0.0,
            "beta": 0.0,
            "intercept": float(x_next.mean()),
            "residual_std": 0.0,
        }

    cov = float(np.cov(x_prev, x_next, ddof=1)[0, 1])
    beta = cov / x_var
    beta = float(np.clip(beta, -0.999, 0.999))
    intercept = float(x_next.mean() - beta * x_prev.mean())

    current = float(clean.iloc[-1])
    projected = current
    for _ in range(max(1, int(horizon))):
        projected = intercept + beta * projected

    residuals = x_next - (intercept + beta * x_prev)
    sigma2 = float(residuals.var(ddof=1)) if len(residuals) > 1 else 0.0
    sigma2 = max(0.0, sigma2)

    steps = max(1, int(horizon))
    denom = 1.0 - (beta ** 2)
    if abs(denom) < 1e-6:
        variance = sigma2 * steps
    else:
        variance = sigma2 * (1.0 - beta ** (2 * steps)) / denom

    return {
        "projected": float(projected),
        "variance": float(max(0.0, variance)),
        "beta": beta,
        "intercept": intercept,
        "residual_std": float(np.sqrt(sigma2)),
    }


def align_series_asof(
    calendar: pd.DatetimeIndex | pd.Series,
    series: pd.Series,
    column_name: str,
) -> pd.Series:
    """
    Backward as-of join: each calendar date gets the last known observation on or before that date.

    Rows before the first macro observation receive NaN (no forward-fill before first release).
    """
    cal_normalized = pd.to_datetime(calendar)
    if isinstance(cal_normalized, pd.DatetimeIndex):
        cal_normalized = cal_normalized.normalize()
    else:
        cal_normalized = cal_normalized.dt.normalize()
    cal_series = pd.Series(cal_normalized)
    cal_df = pd.DataFrame({
        'Date': cal_series.values,
        '_ord': np.arange(len(cal_series)),
    })

    if series.empty:
        return pd.Series(np.nan, index=cal_series.index, name=column_name)

    aligned = series.copy()
    aligned.index = pd.to_datetime(aligned.index).tz_localize(None).normalize()
    aligned = aligned.sort_index()
    aligned = aligned[~aligned.index.duplicated(keep='last')]
    right = aligned.rename(column_name).reset_index()
    right.columns = ['Date', column_name]

    cal_sorted = cal_df.sort_values('Date')
    merged = pd.merge_asof(cal_sorted, right, on='Date', direction='backward')
    merged = merged.sort_values('_ord')
    return pd.Series(merged[column_name].values, index=cal_series.index, name=column_name)


def log_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """Natural log of price ratio, dropping non-positive values."""
    ratio = numerator / denominator
    ratio = ratio.where(ratio > 0)
    return np.log(ratio)


def log_delta(series: pd.Series, periods: int = 63) -> pd.Series:
    """Change in log series over N periods (trading days)."""
    return series.diff(periods)


def rolling_zscore(
    series: pd.Series,
    window: int = 252,
    min_periods: int | None = None,
) -> pd.Series:
    """Rolling z-score normalization."""
    if min_periods is None:
        min_periods = max(1, window // 2)

    rolling_mean = series.rolling(window=window, min_periods=min_periods).mean()
    rolling_std = series.rolling(window=window, min_periods=min_periods).std()
    return (series - rolling_mean) / rolling_std


def log_ratio_delta_zscore(
    numerator: pd.Series,
    denominator: pd.Series,
    delta_days: int = 63,
    zscore_window: int = 252,
    min_zscore_periods: int = 126,
) -> pd.Series:
    """z(ΔN log(numerator/denominator)) — GDP growth proxy pair signal."""
    lr = log_ratio(numerator, denominator)
    delta = log_delta(lr, periods=delta_days)
    return rolling_zscore(delta, window=zscore_window, min_periods=min_zscore_periods)