"""Build the inflation proxy composite for the regime quadrant."""

from __future__ import annotations

import pandas as pd

from data.processing import log_ratio_delta_zscore
from src.config.inflation_proxy import (
    DELTA_DAYS,
    INFLATION_PROXY_PAIRS,
    MIN_ZSCORE_PERIODS,
    ZSCORE_DAYS,
    InflationProxyPair,
)


def build_pair_zscore(
    ticker_data: dict[str, pd.Series],
    pair: InflationProxyPair,
) -> pd.Series:
    """Compute z(Δ63d log(num/denom)) for one configured pair."""
    if pair.num not in ticker_data or pair.denom not in ticker_data:
        raise ValueError(f"Missing tickers for pair {pair.num}/{pair.denom}")

    merged = pd.DataFrame({
        pair.num: ticker_data[pair.num],
        pair.denom: ticker_data[pair.denom],
    }).dropna()
    if merged.empty:
        raise ValueError(f"No overlapping data for pair {pair.num}/{pair.denom}")

    z = log_ratio_delta_zscore(
        merged[pair.num],
        merged[pair.denom],
        delta_days=DELTA_DAYS,
        zscore_window=ZSCORE_DAYS,
        min_zscore_periods=MIN_ZSCORE_PERIODS,
    )
    name = f"{pair.num}_{pair.denom}"
    return z.rename(name)


def build_inflation_proxy(
    ticker_data: dict[str, pd.Series],
    pairs: tuple[InflationProxyPair, ...] = INFLATION_PROXY_PAIRS,
) -> tuple[pd.Series, dict[str, pd.Series]]:
    """
    Weighted sum of pair z-scores. Returns (composite, individual pair z-scores).

    Any missing pair z-score on a date marks the composite NaN for that date.
    """
    pair_zscores: dict[str, pd.Series] = {}
    for pair in pairs:
        pair_zscores[f"{pair.num}_{pair.denom}"] = build_pair_zscore(ticker_data, pair)

    aligned = pd.concat(pair_zscores.values(), axis=1)
    weights = pd.Series({f"{p.num}_{p.denom}": p.weight for p in pairs})
    composite = aligned.mul(weights, axis=1).sum(axis=1, min_count=len(pairs))
    any_missing = aligned.isna().any(axis=1)
    composite = composite.where(~any_missing)
    composite.name = "inflation_proxy"
    return composite, pair_zscores
