# Quadrant Regime Chart — Implementation Spec

> **Recommended Model:** Use **Claude Sonnet 4** in VS Code Copilot Chat (Agent mode). This codebase uses a declarative registry pattern with custom chart functions, Plotly for visualization, and async data fetching — Sonnet 4 handles this multi-file, pattern-following work efficiently and at lower cost than Opus. Feed the entire spec as a single prompt in Agent mode.
>
> **Alternative:** GPT-4.1 is also a strong choice here — fast at multi-file edits with good Plotly knowledge.

---

## Overview

Add a **Growth/Inflation Regime Quadrant Chart** (aka "Snail Trail") to the Macro Dashboard. This chart plots a trailing trajectory of smoothed (Growth Momentum, Inflation Momentum) coordinates across four macro regimes, using daily market-implied proxies instead of lagging government data.

The chart answers: **"What macro regime are we in right now, and where are we heading?"**

### The 4 Quadrants

| Quadrant | Growth | Inflation | Label | Favors |
|----------|--------|-----------|-------|--------|
| Top-Right | ↑ | ↑ | **Reflation** | Commodities, Energy, Value |
| Bottom-Right | ↑ | ↓ | **Goldilocks** | Tech, Equities, Risk-on |
| Top-Left | ↓ | ↑ | **Stagflation** | Gold, Cash, Defensive |
| Bottom-Left | ↓ | ↓ | **Deflation** | Long Bonds (TLT), Utilities |

---

## Architecture Alignment

This project follows a **declarative registry + service layer** pattern. Follow these conventions exactly.

### Key Files to Modify or Create

| File | Action | Purpose |
|------|--------|---------|
| `src/config/indicator_registry.py` | **MODIFY** | Add `regime_quadrant` entry to `INDICATOR_REGISTRY` |
| `src/services/indicator_service.py` | **MODIFY** | Add `_get_regime_quadrant_data()` method + wire into `get_all_indicators()` |
| `data/indicators.py` | **MODIFY** | Add `get_regime_quadrant_data()` method to `IndicatorData` class |
| `data/processing.py` | **MODIFY** | Add `calculate_roc_zscore()` and `apply_ema_smoothing()` helper functions |
| `visualization/charts.py` | **MODIFY** | Add `create_regime_quadrant_chart()` Plotly chart function |
| `ui/dashboard.py` | **MODIFY** | Add the quadrant chart to the dashboard layout |
| `tests/test_regime_quadrant.py` | **CREATE** | Unit tests for the new data processing and chart logic |

---

## Step 1: Data Processing Helpers — `data/processing.py`

Add two new functions to the existing `data/processing.py` file. These are generic utilities that follow the existing pattern of the file (pure functions, no side effects, well-documented).

### 1.1 `calculate_roc_zscore(series, roc_period=60, zscore_window=252)`

```python
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
```

### 1.2 `apply_ema_smoothing(series, span=20)`

```python
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
```

---

## Step 2: Data Fetching — `data/indicators.py`

Add a new method `get_regime_quadrant_data()` to the existing `IndicatorData` class. This method fetches Yahoo Finance data for the proxy ETFs and computes the regime coordinates.

### Method Signature

```python
def get_regime_quadrant_data(self, lookback_days: int = 504, trail_days: int = 60) -> dict:
```

### Parameters

| Param | Default | Description |
|-------|---------|-------------|
| `lookback_days` | 504 | Total days of Yahoo data to fetch (≈ 2 years, needed for 252-day Z-Score window warmup) |
| `trail_days` | 60 | Number of trailing days to plot in the snail trail |

### Yahoo Finance Tickers to Fetch

| Ticker | Purpose | Axis |
|--------|---------|------|
| `TIP` | iShares TIPS Bond ETF | Inflation numerator |
| `IEF` | iShares 7-10 Year Treasury ETF | Inflation denominator |
| `CPER` | United States Copper Index Fund | Growth numerator |
| `GLD` | SPDR Gold Shares | Growth denominator |

Use the existing `YahooClient` class (`data/yahoo_client.py`) to fetch data — it already has caching built in. The ETFs above are preferred over futures tickers (`HG=F`, `GC=F`) because they have cleaner daily data on Yahoo Finance and no rollover gaps.

### Processing Pipeline

```
1. Fetch daily adjusted close prices for TIP, IEF, CPER, GLD
2. Calculate ratios:
   - inflation_ratio = TIP / IEF
   - growth_ratio = CPER / GLD
3. For each ratio:
   a. Calculate ROC Z-Score (roc_period=60, zscore_window=252)  
   b. Apply EMA smoothing (span=20)
4. Build output DataFrame with columns:
   - Date, growth_zscore, inflation_zscore
5. Calculate trajectory slope for the projected arrow:
   - slope_x = mean of last 5 days' daily change in growth_zscore
   - slope_y = mean of last 5 days' daily change in inflation_zscore
   - projected_x = current_x + slope_x * 10
   - projected_y = current_y + slope_y * 10
6. Determine current regime label from the quadrant of the latest point
```

### Return Value

Return a `dict` matching the existing indicator data pattern:

```python
{
    "data": pd.DataFrame,            # columns: Date, growth_zscore, inflation_zscore
    "trail_data": pd.DataFrame,      # last `trail_days` rows of the above
    "current_regime": str,            # "Reflation" | "Goldilocks" | "Stagflation" | "Deflation"
    "current_growth": float,          # latest smoothed growth Z-Score
    "current_inflation": float,       # latest smoothed inflation Z-Score  
    "projected_growth": float,        # projected growth Z-Score (5-day slope extrapolation)
    "projected_inflation": float,     # projected inflation Z-Score (5-day slope extrapolation)
    "regime_description": str,        # Human-readable description of current regime positioning
}
```

### Important Notes

- Align dates across all 4 tickers using an inner join before computing ratios (drop any dates where one ticker is missing).
- If `YahooClient` returns an empty DataFrame for any ticker, fall back gracefully and return a dict with `"data": pd.DataFrame()` and populate a `"regime_description"` explaining the data gap.
- The existing `YahooClient.get_historical_prices()` returns a DataFrame with columns `['Date', 'value']`. You'll need to rename the `value` column per-ticker before merging.

---

## Step 3: Indicator Registry — `src/config/indicator_registry.py`

Add a new entry to `INDICATOR_REGISTRY`:

```python
"regime_quadrant": IndicatorConfig(
    key="regime_quadrant",
    display_name="Growth/Inflation Regime",
    emoji="🧭",
    fred_series=[],                    # No FRED data needed
    yahoo_series=["TIP", "IEF", "CPER", "GLD"],
    chart_type="custom",
    value_column="growth_zscore",      # Primary display column
    periods=504,                       # 2 years of daily data for warmup
    frequency="D",
    bullish_condition="custom",
    threshold=None,
    warning_description=(
        "This chart shows the current macroeconomic regime using market-implied proxies. "
        "The X-axis measures Growth Momentum (CPER/GLD ratio Z-Score) and the Y-axis measures "
        "Inflation Momentum (TIP/IEF ratio Z-Score). The trailing 60-day path shows regime "
        "migration. A dotted arrow projects the near-term trajectory based on the 5-day slope.\n\n"
        "**Quadrants:**\n"
        "- 🟥 **Top-Right (Reflation):** Growth ↑, Inflation ↑ → Commodities, Energy, Value\n"
        "- 🟩 **Bottom-Right (Goldilocks):** Growth ↑, Inflation ↓ → Tech, Equities, Risk-on\n"
        "- 🟧 **Top-Left (Stagflation):** Growth ↓, Inflation ↑ → Gold, Cash, Defensive\n"
        "- 🟦 **Bottom-Left (Deflation):** Growth ↓, Inflation ↓ → Long Bonds (TLT), Utilities"
    ),
    chart_color="#ff6f00",
    card_chart_height=500,             # Taller to accommodate square aspect ratio
    custom_chart_fn="visualization.charts.create_regime_quadrant_chart",
    custom_status_fn="visualization.warning_signals.generate_regime_quadrant_warning",
    fred_link=None,
    cache_ttl=3600,
),
```

---

## Step 4: Service Layer — `src/services/indicator_service.py`

### 4.1 Add to `_load_indicators_config()`

```python
'regime_quadrant': {
    'source': 'yahoo',
    'tickers': ['TIP', 'IEF', 'CPER', 'GLD'],
    'frequency': 'D',
    'cache_ttl': self.settings.cache.yahoo_ttl,
    'default_lookback_days': 504
}
```

### 4.2 Add `_get_regime_quadrant_data()` method

```python
def _get_regime_quadrant_data(self, **kwargs) -> IndicatorResult:
    """Get regime quadrant data from Yahoo Finance proxies."""
    try:
        result = self.indicator_data.get_regime_quadrant_data(
            lookback_days=kwargs.get('lookback_days', 504),
            trail_days=kwargs.get('trail_days', 60)
        )
        return IndicatorResult(success=True, data=result)
    except Exception as e:
        return IndicatorResult(success=False, error=str(e))
```

### 4.3 Wire into `get_indicator()` dispatch

Add to the `if/elif` chain in `get_indicator()`:

```python
elif indicator_name == 'regime_quadrant':
    result = await asyncio.to_thread(self._get_regime_quadrant_data, **kwargs)
```

### 4.4 Add to `get_all_indicators()`

Add `'regime_quadrant'` to the `indicators` list in `get_all_indicators()`.

---

## Step 5: Visualization — `visualization/charts.py`

Add `create_regime_quadrant_chart(data: dict)` function. This is the core visual component.

### Chart Requirements

Use `plotly.graph_objects` (already imported in this file). The chart must render correctly in Streamlit's dark and light themes.

#### Layout

- **Square aspect ratio** — set `width=500, height=500` (or let the card stretch with `height=500`).
- **Axis range:** Dynamically set to at minimum `[-3, 3]` on both axes, or wider if data exceeds that range. Use `range=[min(data_min, -3), max(data_max, 3)]`.
- **Zero lines** — draw solid horizontal and vertical lines at `x=0` and `y=0` to define the four quadrants.
- **Quadrant background shading** — use `fig.add_shape(type="rect", ...)` with low-opacity fill colors:
  - Top-Right: `rgba(255, 152, 0, 0.08)` (warm orange — Reflation)
  - Bottom-Right: `rgba(76, 175, 80, 0.08)` (green — Goldilocks)
  - Top-Left: `rgba(244, 67, 54, 0.08)` (red — Stagflation)
  - Bottom-Left: `rgba(33, 150, 243, 0.08)` (blue — Deflation)
- **Quadrant labels** — add `fig.add_annotation()` in each corner with the regime name + brief descriptor (e.g., "Reflation\nCommodities, Energy"). Use `xref="paper", yref="paper"` positioning so labels stay in place regardless of data range.
- **Axis titles:** X = "Growth Momentum (CPER/GLD Z-Score)", Y = "Inflation Momentum (TIP/IEF Z-Score)"

#### The Snail Trail

Plot the trailing `trail_days` (60) data points as a connected scatter path:

```python
fig.add_trace(go.Scatter(
    x=trail_df['growth_zscore'],
    y=trail_df['inflation_zscore'],
    mode='lines+markers',
    marker=dict(
        size=trail_sizes,       # Array: 3 → 14, growing toward the present
        color=trail_colors,     # Array: fading opacity, most recent = brightest
        colorscale=[[0, 'rgba(255,111,0,0.15)'], [1, 'rgba(255,111,0,1.0)']],
        showscale=False,
    ),
    line=dict(
        color='rgba(255,111,0,0.4)',
        width=1.5,
    ),
    hovertemplate='Date: %{text}<br>Growth: %{x:.2f}<br>Inflation: %{y:.2f}<extra></extra>',
    text=trail_df['Date'].dt.strftime('%b %d, %Y'),
    name='Regime Trail',
    showlegend=False,
))
```

- **Marker sizing:** Create an array from `3` to `14` linearly across the trail points so the most recent point is the largest.
- **Color/opacity gradient:** Use a normalized `[0, 1]` array mapped to the colorscale, so older points are nearly transparent and the current point is fully opaque.

#### The Current Point

Overlay the most recent point as a large, distinct marker:

```python
fig.add_trace(go.Scatter(
    x=[current_growth],
    y=[current_inflation],
    mode='markers+text',
    marker=dict(size=18, color='#ff6f00', line=dict(color='white', width=2)),
    text=[current_regime],
    textposition='top center',
    textfont=dict(size=12, color='#ff6f00'),
    name='Current Regime',
    showlegend=False,
))
```

#### The Projected Arrow

Draw a dotted line from the current point to the projected future point:

```python
fig.add_annotation(
    x=projected_growth,
    y=projected_inflation,
    ax=current_growth,
    ay=current_inflation,
    xref='x', yref='y',
    axref='x', ayref='y',
    showarrow=True,
    arrowhead=3,
    arrowsize=1.5,
    arrowwidth=2,
    arrowcolor='rgba(255,111,0,0.6)',
    standoff=10,
)
```

#### Final Theme

Apply `apply_dark_theme(fig)` (already exists in this file), then override:

```python
fig.update_layout(
    height=500,
    xaxis=dict(
        title="Growth Momentum (CPER/GLD Z-Score)",
        zeroline=True, zerolinewidth=2, zerolinecolor='rgba(128,128,128,0.5)',
        range=[x_min, x_max],
    ),
    yaxis=dict(
        title="Inflation Momentum (TIP/IEF Z-Score)",
        zeroline=True, zerolinewidth=2, zerolinecolor='rgba(128,128,128,0.5)',
        range=[y_min, y_max],
        scaleanchor="x",  # Force square aspect ratio
        scaleratio=1,
    ),
    margin=dict(l=60, r=60, t=40, b=60),
)
```

---

## Step 6: Warning Signal — `visualization/warning_signals.py`

Add `generate_regime_quadrant_warning(data: dict, config=None) -> dict`:

```python
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
```

---

## Step 7: Dashboard Layout — `ui/dashboard.py`

Add the quadrant chart to the dashboard. Place it in a **full-width row** above or below the existing indicator grid (it's a wide chart that benefits from full width). Suggested placement: **below the header tables and above the indicator cards**, or as a new dedicated section with a divider.

### Implementation

```python
# --- Regime Quadrant Chart (full-width) ---
if 'regime_quadrant' in indicators:
    st.divider()
    st.markdown("### 🧭 Growth/Inflation Regime")
    display_indicator_card('regime_quadrant', indicators['regime_quadrant'], fred_client)
```

Alternatively, for a cleaner layout you could render it directly without the card wrapper:

```python
if 'regime_quadrant' in indicators:
    st.divider()
    col1, col2 = st.columns([2, 1])
    with col1:
        from visualization.charts import create_regime_quadrant_chart
        fig = create_regime_quadrant_chart(indicators['regime_quadrant'])
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        regime = indicators['regime_quadrant'].get('current_regime', 'Unknown')
        st.markdown(f"### 🧭 Current Regime: **{regime}**")
        st.markdown(indicators['regime_quadrant'].get('regime_description', ''))
        # Show the warning description from registry
        from src.config.indicator_registry import INDICATOR_REGISTRY
        config = INDICATOR_REGISTRY['regime_quadrant']
        with st.expander("📖 How to read this chart"):
            st.markdown(config.warning_description)
```

**Pick whichever layout looks better** — both approaches work with the existing architecture. The second option (side-by-side chart + info panel) is recommended for this particular chart since it's visually dense and benefits from adjacent context.

---

## Step 8: Tests — `tests/test_regime_quadrant.py`

Create a new test file following the existing test patterns (see `tests/test_processing.py`, `tests/test_indicator_registry.py`).

### Test Cases

```python
"""Tests for the Growth/Inflation Regime Quadrant feature."""
import pytest
import pandas as pd
import numpy as np
from data.processing import calculate_roc_zscore, apply_ema_smoothing


class TestCalculateRocZscore:
    """Tests for calculate_roc_zscore()."""
    
    def test_returns_series_same_length(self):
        """Output series should have same length as input."""
        series = pd.Series(np.random.randn(400).cumsum() + 100)
        result = calculate_roc_zscore(series, roc_period=60, zscore_window=252)
        assert len(result) == len(series)
    
    def test_leading_nans(self):
        """Should have NaN values at the start due to rolling windows."""
        series = pd.Series(np.random.randn(400).cumsum() + 100)
        result = calculate_roc_zscore(series, roc_period=60, zscore_window=252)
        # First roc_period + zscore_window - 1 values should be NaN
        assert result.iloc[:60].isna().all()
    
    def test_zscore_bounded(self):
        """Z-Scores should typically be within [-4, 4] for normal data."""
        np.random.seed(42)
        series = pd.Series(np.random.randn(600).cumsum() + 100)
        result = calculate_roc_zscore(series, roc_period=60, zscore_window=252)
        valid = result.dropna()
        assert valid.between(-5, 5).all()
    
    def test_empty_series(self):
        """Should handle empty series gracefully."""
        series = pd.Series(dtype=float)
        result = calculate_roc_zscore(series)
        assert len(result) == 0
    
    def test_constant_series(self):
        """A constant series should produce ROC of 0 (and NaN Z-Scores due to 0 std)."""
        series = pd.Series([100.0] * 400)
        result = calculate_roc_zscore(series, roc_period=60, zscore_window=252)
        # All NaN because std deviation is 0
        valid = result.dropna()
        # Either empty or all NaN/zero
        assert len(valid) == 0 or (valid == 0).all() or valid.isna().all()


class TestApplyEmaSmoothing:
    """Tests for apply_ema_smoothing()."""
    
    def test_reduces_noise(self):
        """EMA should reduce the standard deviation of noisy data."""
        np.random.seed(42)
        noisy = pd.Series(np.random.randn(200))
        smoothed = apply_ema_smoothing(noisy, span=20)
        assert smoothed.std() < noisy.std()
    
    def test_same_length(self):
        """Output should be same length as input."""
        series = pd.Series(np.random.randn(100))
        result = apply_ema_smoothing(series, span=10)
        assert len(result) == len(series)
    
    def test_span_parameter(self):
        """Larger span should produce smoother output."""
        np.random.seed(42)
        series = pd.Series(np.random.randn(200))
        smooth_10 = apply_ema_smoothing(series, span=10)
        smooth_50 = apply_ema_smoothing(series, span=50)
        assert smooth_50.std() < smooth_10.std()


class TestRegimeQuadrantData:
    """Tests for the regime quadrant data pipeline (integration-level)."""
    
    def test_regime_labels(self):
        """Verify regime label assignment from coordinates."""
        # These are the expected mappings
        assert _get_regime(1.0, 1.0) == "Reflation"
        assert _get_regime(1.0, -1.0) == "Goldilocks"
        assert _get_regime(-1.0, 1.0) == "Stagflation"
        assert _get_regime(-1.0, -1.0) == "Deflation"
    
    def test_return_dict_structure(self):
        """Verify the returned dict has all expected keys."""
        # Mock or construct sample data and verify structure
        required_keys = [
            'data', 'trail_data', 'current_regime',
            'current_growth', 'current_inflation',
            'projected_growth', 'projected_inflation',
            'regime_description'
        ]
        # This test should be implemented with mock Yahoo data
        pass


def _get_regime(growth: float, inflation: float) -> str:
    """Helper to test regime classification logic."""
    if growth >= 0 and inflation >= 0:
        return "Reflation"
    elif growth >= 0 and inflation < 0:
        return "Goldilocks"
    elif growth < 0 and inflation >= 0:
        return "Stagflation"
    else:
        return "Deflation"
```

---

## Data Flow Summary

```
Yahoo Finance (TIP, IEF, CPER, GLD daily close prices)
        │
        ▼
IndicatorData.get_regime_quadrant_data()     ← data/indicators.py
        │
        ├── calculate ratios: TIP/IEF, CPER/GLD
        ├── calculate_roc_zscore()            ← data/processing.py
        ├── apply_ema_smoothing()             ← data/processing.py
        ├── classify regime quadrant
        ├── compute projected trajectory (5-day slope)
        │
        ▼
IndicatorService._get_regime_quadrant_data() ← src/services/indicator_service.py
        │
        ▼
get_all_indicators() → indicators dict
        │
        ▼
create_dashboard(indicators)                 ← ui/dashboard.py
        │
        ▼
create_regime_quadrant_chart(data)           ← visualization/charts.py
        │
        ▼
Plotly figure rendered in Streamlit
```

---

## Configurable Parameters (Sensible Defaults)

These should be constants at the top of the data-fetching method or in the registry config, easy to tune later:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `ROC_PERIOD` | 60 | Rate of Change lookback (trading days) |
| `ZSCORE_WINDOW` | 252 | Rolling Z-Score normalization window (≈ 1 year) |
| `EMA_SPAN` | 20 | Exponential Moving Average smoothing span |
| `TRAIL_DAYS` | 60 | Number of trailing days to show in the snail trail |
| `PROJECTION_DAYS` | 5 | Days of slope used for trajectory projection |
| `PROJECTION_EXTEND` | 10 | How many days forward to extend the projected arrow |
| `LOOKBACK_DAYS` | 504 | Total historical data to fetch (≈ 2 trading years) |

---

## Edge Cases to Handle

1. **Weekend/holiday gaps in Yahoo data:** Use inner join when merging the 4 tickers — don't forward-fill across large gaps.
2. **Ticker data unavailable:** If any of the 4 tickers returns empty data, show a placeholder chart with an explanatory message (use the same pattern as `generic_chart.py`'s "No Data Available" fallback).
3. **Insufficient data for Z-Score:** If fewer than `roc_period + zscore_window` data points are available, show whatever partial trail is available and note it in the regime description.
4. **All Z-Scores are NaN:** Can happen with very short history or stale data. Return `current_regime = "Unknown"` and display accordingly.
5. **Extreme Z-Score values:** The chart axis range should dynamically expand if Z-Scores exceed ±3 (use `max(abs(data), 3)` for symmetric axis limits).

---

## Checklist for the Implementing Model

- [ ] Add `calculate_roc_zscore()` and `apply_ema_smoothing()` to `data/processing.py`
- [ ] Add `get_regime_quadrant_data()` to `data/indicators.py` (using existing `YahooClient`)
- [ ] Add `"regime_quadrant"` entry to `INDICATOR_REGISTRY` in `src/config/indicator_registry.py`
- [ ] Add `_get_regime_quadrant_data()` to `IndicatorService` in `src/services/indicator_service.py`
- [ ] Add `'regime_quadrant'` to the indicators list in `get_all_indicators()`
- [ ] Wire `regime_quadrant` into the `get_indicator()` dispatch in `indicator_service.py`
- [ ] Add `create_regime_quadrant_chart()` to `visualization/charts.py`
- [ ] Add `generate_regime_quadrant_warning()` to `visualization/warning_signals.py`
- [ ] Add the quadrant chart section to `ui/dashboard.py`
- [ ] Create `tests/test_regime_quadrant.py` with unit tests
- [ ] Run `pytest` and fix any failures
- [ ] Run the Streamlit app and visually verify the chart renders correctly
- [ ] Verify the snail trail, current dot, projected arrow, quadrant shading, and labels all display

---

## Example Prompt for the Implementing Model

> Implement the Growth/Inflation Regime Quadrant Chart as specified in `QUADRANT_CHART_SPEC.md`. Follow the existing codebase patterns exactly — declarative registry, service layer, custom chart function. Work through the checklist in order. Run tests after implementation.
