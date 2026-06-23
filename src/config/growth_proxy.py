"""
GDP growth proxy definition for the regime quadrant X-axis.

Standalone copy — edit here without touching GDP_Inflation_Proxy-Backtester.
If you re-run pair discovery in the backtester, update these pairs/weights manually.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GrowthProxyPair:
    num: str
    denom: str
    weight: float


# Greedy composite from backtester discovery (equal-weight, holdout-validated).
GROWTH_PROXY_PAIRS: tuple[GrowthProxyPair, ...] = (
    GrowthProxyPair("CPER", "GLD", 0.25),
    GrowthProxyPair("XHB", "IWM", 0.25),
    GrowthProxyPair("EFA", "SLV", 0.25),
    GrowthProxyPair("CPER", "FXI", 0.25),
)

DELTA_DAYS = 63
ZSCORE_DAYS = 252
MIN_ZSCORE_PERIODS = 126

# OU regime projection horizon — aligned with proxy momentum window (~3 months).
FORECAST_HORIZON_DAYS = DELTA_DAYS

GROWTH_PROXY_REQUIRED_TICKERS: frozenset[str] = frozenset(
    ticker for pair in GROWTH_PROXY_PAIRS for ticker in (pair.num, pair.denom)
)

GROWTH_AXIS_LABEL = "GDP Growth Proxy (4-pair Z-Score)"
GROWTH_PROXY_DESCRIPTION = (
    "Equal-weight blend of z(Δ63d log ratio) for CPER/GLD, XHB/IWM, EFA/SLV, and CPER/FXI "
    "(252d rolling z-score). Tuned via GDP backtester pair discovery; config lives in this repo only."
)
