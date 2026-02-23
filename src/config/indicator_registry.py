"""
Declarative indicator registry - the single source of truth for all indicator metadata.

This file consolidates indicator configuration that was previously scattered across
7+ different files. Adding a new indicator should only require updating this registry
and potentially adding custom chart/status functions.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class IndicatorConfig:
    """Configuration for a single economic indicator."""
    key: str                          # e.g. "initial_claims"
    display_name: str                 # e.g. "Initial Jobless Claims"
    emoji: str                        # e.g. "📋"
    fred_series: list[str]            # e.g. ["ICSA"]
    chart_type: str                   # "line" | "dual_axis" | "bar" | "custom"
    value_column: str                 # column name in the returned DataFrame
    periods: int                      # number of data points to fetch
    frequency: Optional[str]          # "d", "w", "m", "q", None
    bullish_condition: str            # "below_threshold" | "above_threshold" | "decreasing" | "custom"
    threshold: Optional[float]        # for threshold-based signals
    warning_description: str          # text shown in warning expander
    chart_color: str                  # hex color for the primary trace
    card_chart_height: int = 360
    fred_link: Optional[str] = None   # link for "View on FRED" button
    custom_chart_fn: Optional[str] = None  # dotted path to custom chart builder if chart_type == "custom"
    custom_status_fn: Optional[str] = None # dotted path to custom status logic
    cache_ttl: int = 3600
    yahoo_series: Optional[list[str]] = None  # for Yahoo Finance data (copper, gold, etc.)
    
    # Additional fields for complex indicators
    pmi_components: Optional[dict] = None      # PMI component series IDs and weights
    liquidity_components: Optional[dict] = None # USD Liquidity component series


# The main indicator registry - this is the single source of truth
INDICATOR_REGISTRY: dict[str, IndicatorConfig] = {
    
    "initial_claims": IndicatorConfig(
        key="initial_claims",
        display_name="Initial Jobless Claims",
        emoji="🏢",
        fred_series=["ICSA"],
        chart_type="line",
        value_column="Claims",
        periods=52,  # 52 weeks = 1 year
        frequency="W",  # Weekly
        bullish_condition="decreasing",
        threshold=None,  # Uses trend-based logic
        warning_description="This is your early warning system. The key pattern to watch is 3 consecutive weeks of rising claims, which often triggers before major market stress. Playbook for rising claims: Scale back aggressive positions, shift toward defensive sectors, and build cash reserves. 'Small moves early beat big moves late.'\n\n⚠️ **Danger Combination:** Claims rising 3 weeks + PMI below 50 + Hours worked dropping. When these align, protect capital first.",
        chart_color="#1a7fe0",
        fred_link="https://fred.stlouisfed.org/series/ICSA"
    ),
    
    "pce": IndicatorConfig(
        key="pce",
        display_name="Personal Consumption Expenditures",
        emoji="💰",
        fred_series=["PCE"],
        chart_type="line",
        value_column="PCE_YoY",
        periods=24,  # 2 years of monthly data
        frequency="M",
        bullish_condition="below_threshold",
        threshold=3.5,  # Above 3.5% YoY is concerning
        warning_description="Everyone watches CPI, but PCE guides Fed policy. Framework: PCE dropping + Stable jobs = Add risk. PCE rising + Rising claims = Get defensive. PCE is a window into rate trends, market conditions, and risk appetite.",
        chart_color="#00c853",
        fred_link="https://fred.stlouisfed.org/series/PCE"
    ),
    
    "core_cpi": IndicatorConfig(
        key="core_cpi",
        display_name="Core Consumer Price Index", 
        emoji="📊",
        fred_series=["CPILFESL"],
        chart_type="line",
        value_column="CPI_MoM",
        periods=24,  # 2 years of monthly data
        frequency="M",
        bullish_condition="decreasing",
        threshold=None,
        warning_description="Watch for 3 consecutive months of rising MoM core CPI — that's the inflation re-acceleration signal that forces the Fed's hand. Conversely, 3 consecutive months of declining MoM prints open the door to rate cuts and risk-on rotation. When it drops: Growth stocks outperform, bonds rally, and tech leads. When it rises: Value stocks win, real assets dominate, and tech struggles.",
        chart_color="#ff9800",
        fred_link="https://fred.stlouisfed.org/series/CPILFESL"
    ),
    
    "hours_worked": IndicatorConfig(
        key="hours_worked",
        display_name="Average Weekly Hours Worked",
        emoji="⏰",
        fred_series=["AWHAETP"],
        chart_type="line", 
        value_column="Hours",
        periods=24,  # 2 years of monthly data
        frequency="M",
        bullish_condition="above_threshold",
        threshold=34.0,  # Below 34 hours is concerning
        warning_description="Track hours worked for 3 consecutive months. When they drop consistently, big money gets defensive. This pattern tends to precede major market shifts and is a crucial early signal before actual job losses occur.\n\n⚠️ **Danger Combination:** Hours worked dropping + PMI below 50 + Claims rising 3 weeks. When these align, protect capital first.",
        chart_color="#78909c",
        fred_link="https://fred.stlouisfed.org/series/AWHAETP"
    ),
    
    "yield_curve": IndicatorConfig(
        key="yield_curve",
        display_name="2-10 Year Treasury Spread",
        emoji="📈", 
        fred_series=["T10Y2Y"],
        chart_type="line",
        value_column="T10Y2Y",
        periods=60,  # 5 years of monthly data
        frequency="M",
        bullish_condition="above_threshold",
        threshold=0.0,  # Negative spread (inversion) is bearish
        warning_description="Yield curve inversion (negative spread) has preceded every recession since 1950. Extended inversion (6+ months) increases recession probability significantly. Watch for re-steepening — it often marks the actual onset of downturn, not recovery.",
        chart_color="#f44336",
        fred_link="https://fred.stlouisfed.org/series/T10Y2Y"
    ),
    
    "credit_spread": IndicatorConfig(
        key="credit_spread", 
        display_name="High Yield Credit Spread",
        emoji="💎",
        fred_series=["BAMLH0A0HYM2"],
        chart_type="custom",
        value_column="value",
        periods=60,  # 5 years of monthly data
        frequency="M", 
        bullish_condition="below_threshold",
        threshold=5.0,  # Above 5% indicates credit stress
        warning_description="Credit spreads above 5% indicate market stress and potential liquidity concerns. Rapid widening often precedes equity corrections as institutional money prices in elevated default risk. Monitor for sudden jumps that can signal credit market seizure.",
        chart_color="#9c27b0",
        custom_chart_fn="visualization.charts.create_credit_spread_chart",
        fred_link="https://fred.stlouisfed.org/series/BAMLH0A0HYM2"
    ),
    
    "pscf_price": IndicatorConfig(
        key="pscf_price",
        display_name="Copper Price (PSCF)",
        emoji="🔩",
        fred_series=["PSCF"],
        chart_type="custom",
        value_column="value",
        periods=24,  # 2 years of monthly data
        frequency="M",
        bullish_condition="decreasing", 
        threshold=None,  # Uses trend-based logic - rising copper is typically bullish
        warning_description="Copper prices often lead global economic cycles due to deep industrial demand. Falling copper signals economic slowdown ahead. Rising copper signals expanding manufacturing and construction activity. Often called 'Dr. Copper' for its predictive track record.",
        chart_color="#ff5722",
        custom_chart_fn="visualization.charts.create_pscf_chart",
        fred_link="https://fred.stlouisfed.org/series/PSCF"
    ),
    
    "pmi_proxy": IndicatorConfig(
        key="pmi_proxy", 
        display_name="Manufacturing PMI Proxy",
        emoji="🏭",
        fred_series=["AMTMNO", "IPMAN", "MANEMP", "AMDMUS", "MNFCTRIMSA"],
        chart_type="custom",
        value_column="composite_pmi",
        periods=24,  # 2 years of monthly data
        frequency="M",
        bullish_condition="custom",
        threshold=50.0,  # PMI below 50 indicates contraction
        warning_description="Think of it as the economy's pulse. Above 50 = Growth, Below 50 = Contraction. Watch trends, not just levels. Danger combination: PMI below 50 + Claims rising 3 weeks + Hours worked dropping. When these align, protect capital first.",
        chart_color="#4caf50",
        custom_chart_fn="visualization.indicators.create_pmi_chart",
        custom_status_fn="visualization.warning_signals.generate_pmi_warning",
        fred_link=None,  # Multiple series, no single FRED link
        pmi_components={
            "series_ids": {
                'new_orders': 'AMTMNO',      # Manufacturing: New Orders
                'production': 'IPMAN',       # Industrial Production: Manufacturing
                'employment': 'MANEMP',      # Manufacturing Employment
                'supplier_deliveries': 'AMDMUS',  # Manufacturing: Supplier Deliveries
                'inventories': 'MNFCTRIMSA'  # Manufacturing Inventories (Seasonally Adjusted)
            },
            "weights": {
                'new_orders': 0.30,
                'production': 0.25,
                'employment': 0.20,
                'supplier_deliveries': 0.15,
                'inventories': 0.10
            }
        }
    ),
    
    "usd_liquidity": IndicatorConfig(
        key="usd_liquidity",
        display_name="USD Liquidity Conditions", 
        emoji="💧",
        fred_series=["WALCL", "RRPONTTLD", "B235RC1Q027SBEA", "CURRCIR", "GDP"],
        chart_type="custom",
        value_column="total_liquidity_pct_gdp",
        periods=60,  # 5 years of quarterly data (months → num_quarters = 60//3+1 = 21)
        frequency="Q",
        bullish_condition="custom",  # Complex multi-component logic
        threshold=None,
        warning_description="USD liquidity is a key driver of market direction. Rising liquidity + Stable inflation = Bullish for risk assets. Falling liquidity + Rising inflation = Bearish for risk assets. Watch for 3 consecutive months of directional change for high-confidence signals.",
        chart_color="#2196f3", 
        custom_chart_fn="visualization.indicators.create_usd_liquidity_chart",
        custom_status_fn="visualization.warning_signals.generate_usd_liquidity_warning",
        fred_link=None,  # Multiple series
        liquidity_components={
            "series_ids": ["WALCL", "RRPONTTLD", "B235RC1Q027SBEA", "CURRCIR"],
            "gdp_series": "GDP",
            "start_date": "2000-01-01"  # Need historical data for proper analysis
        }
    ),
    
    "new_orders": IndicatorConfig(
        key="new_orders",
        display_name="New Orders Index", 
        emoji="📦",
        fred_series=["NEWORDER"],
        chart_type="line",
        value_column="NEWORDER_MoM",
        periods=24,  # 2 years of monthly data
        frequency="M",
        bullish_condition="above_threshold",
        threshold=0.0,  # Positive MoM growth is bullish
        warning_description="New orders represent future production commitments. Consecutive monthly declines often foreshadow manufacturing weakness and can precede broader economic slowdowns by 2–3 months. A leading signal for ISM Manufacturing direction.",
        chart_color="#607d8b",
        fred_link="https://fred.stlouisfed.org/series/NEWORDER"
    ),
    
    "copper_gold_yield": IndicatorConfig(
        key="copper_gold_yield",
        display_name="Copper/Gold vs 10Y Treasury",
        emoji="🥇", 
        fred_series=["DGS10"],  # 10-Year Treasury
        yahoo_series=["HG=F", "GC=F"],  # Copper and Gold futures
        chart_type="dual_axis", 
        value_column="copper_gold_ratio",
        periods=252,  # 1 year of daily data
        frequency="D",
        bullish_condition="custom",  # Complex relationship analysis
        threshold=None,
        warning_description="Copper/Gold ratio vs Treasury yields helps identify risk-on/risk-off sentiment and inflation expectations. Copper is the economy's barometer — rising ratio signals growth expectations, falling ratio signals contraction. Divergence from yields often resolves with a sharp market re-pricing.",
        chart_color="#ff6f00",
        custom_chart_fn="visualization.indicators.create_copper_gold_yield_chart",
        fred_link="https://fred.stlouisfed.org/series/DGS10"
    )
}


def get_indicator_config(key: str) -> IndicatorConfig:
    """Get indicator configuration by key."""
    if key not in INDICATOR_REGISTRY:
        raise KeyError(f"Indicator '{key}' not found in registry")
    return INDICATOR_REGISTRY[key]


def list_indicators() -> list[str]:
    """Get list of all available indicator keys."""
    return list(INDICATOR_REGISTRY.keys())


def get_indicators_by_chart_type(chart_type: str) -> list[IndicatorConfig]:
    """Get all indicators of a specific chart type."""
    return [config for config in INDICATOR_REGISTRY.values() if config.chart_type == chart_type]


def get_fred_indicators() -> list[IndicatorConfig]:
    """Get all indicators that use FRED data."""
    return [config for config in INDICATOR_REGISTRY.values() if config.fred_series]


def get_yahoo_indicators() -> list[IndicatorConfig]:
    """Get all indicators that use Yahoo Finance data."""
    return [config for config in INDICATOR_REGISTRY.values() if config.yahoo_series]