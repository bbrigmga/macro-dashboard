"""
Inflation proxy definition for the regime quadrant Y-axis.

Standalone copy — edit here without touching GDP_Inflation_Proxy-Backtester.
If you re-run pair discovery in the backtester, update these pairs/weights manually.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InflationProxyPair:
    num: str
    denom: str
    weight: float


# Greedy composite from backtester discovery (DBC/CPER anchor + XLV/QQQ).
INFLATION_PROXY_PAIRS: tuple[InflationProxyPair, ...] = (
    InflationProxyPair("DBC", "CPER", 0.50),
    InflationProxyPair("XLV", "QQQ", 0.50),
)

DELTA_DAYS = 63
ZSCORE_DAYS = 252
MIN_ZSCORE_PERIODS = 126

INFLATION_PROXY_REQUIRED_TICKERS: frozenset[str] = frozenset(
    ticker for pair in INFLATION_PROXY_PAIRS for ticker in (pair.num, pair.denom)
)

INFLATION_AXIS_LABEL = "Inflation Proxy (DBC/CPER + XLV/QQQ Z-Score)"
INFLATION_PROXY_DESCRIPTION = (
    "Equal-weight blend of z(Δ63d log ratio) for DBC/CPER and XLV/QQQ "
    "(252d rolling z-score). Tuned via inflation backtester pair discovery; config lives in this repo only."
)
