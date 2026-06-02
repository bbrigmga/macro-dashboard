"""Walk-forward backtest utilities for the regime quadrant model."""

from __future__ import annotations

import numpy as np
import pandas as pd

from data.processing import forecast_ou


def _safe_float(value, default: float = 0.0) -> float:
    try:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return default
        return float(value)
    except Exception:
        return default


def walk_forward_directional_hit_rate(
    df: pd.DataFrame,
    horizon: int = 10,
    min_train: int = 126
) -> dict:
    """
    Calculate walk-forward directional hit-rate for growth/inflation forecasts.

    Args:
        df: DataFrame with Date, growth_raw, inflation_raw columns
        horizon: Forward horizon in trading days
        min_train: Minimum training observations before first forecast

    Returns:
        dict: Hit-rate metrics
    """
    required_cols = {"growth_raw", "inflation_raw"}
    if df is None or df.empty or not required_cols.issubset(df.columns):
        return {"overall_hit_rate": 0.0, "growth_hit_rate": 0.0, "inflation_hit_rate": 0.0, "n_obs": 0}

    data = df.dropna(subset=["growth_raw", "inflation_raw"]).reset_index(drop=True)
    max_idx = len(data) - horizon
    if max_idx <= min_train:
        return {"overall_hit_rate": 0.0, "growth_hit_rate": 0.0, "inflation_hit_rate": 0.0, "n_obs": 0}

    overall_hits = []
    growth_hits = []
    inflation_hits = []

    for i in range(min_train, max_idx):
        hist = data.iloc[: i + 1]
        current_growth = _safe_float(hist["growth_raw"].iloc[-1])
        current_inflation = _safe_float(hist["inflation_raw"].iloc[-1])

        growth_fc = forecast_ou(hist["growth_raw"], horizon=horizon)
        inflation_fc = forecast_ou(hist["inflation_raw"], horizon=horizon)
        proj_growth = _safe_float(growth_fc["projected"], current_growth)
        proj_inflation = _safe_float(inflation_fc["projected"], current_inflation)

        realized_growth = _safe_float(data["growth_raw"].iloc[i + horizon], current_growth)
        realized_inflation = _safe_float(data["inflation_raw"].iloc[i + horizon], current_inflation)

        pred_move_g = proj_growth - current_growth
        pred_move_i = proj_inflation - current_inflation
        real_move_g = realized_growth - current_growth
        real_move_i = realized_inflation - current_inflation

        g_hit = np.sign(pred_move_g) == np.sign(real_move_g)
        i_hit = np.sign(pred_move_i) == np.sign(real_move_i)
        growth_hits.append(bool(g_hit))
        inflation_hits.append(bool(i_hit))
        overall_hits.append(bool(g_hit and i_hit))

    n_obs = len(overall_hits)
    if n_obs == 0:
        return {"overall_hit_rate": 0.0, "growth_hit_rate": 0.0, "inflation_hit_rate": 0.0, "n_obs": 0}

    return {
        "overall_hit_rate": float(np.mean(overall_hits)),
        "growth_hit_rate": float(np.mean(growth_hits)),
        "inflation_hit_rate": float(np.mean(inflation_hits)),
        "n_obs": int(n_obs),
    }


def count_regime_flips(regimes: pd.Series) -> int:
    """Count transitions between adjacent non-null regime labels."""
    if regimes is None or len(regimes) <= 1:
        return 0
    clean = regimes.dropna().astype(str)
    if len(clean) <= 1:
        return 0
    return int((clean != clean.shift(1)).sum() - 1)


def forward_returns_by_regime(
    regime_df: pd.DataFrame,
    asset_prices: dict[str, pd.Series],
    horizons: tuple[int, ...] = (21, 63, 126)
) -> dict:
    """
    Compute average forward returns of favored assets conditioned on regime labels.

    Regime -> favored asset mapping:
    - Goldilocks -> SPY
    - Reflation -> XLE
    - Stagflation -> GLD
    - Deflation -> TLT
    """
    if regime_df is None or regime_df.empty or "regime" not in regime_df.columns:
        return {}

    favored_assets = {
        "Goldilocks": "SPY",
        "Reflation": "XLE",
        "Stagflation": "GLD",
        "Deflation": "TLT",
    }

    if "Date" in regime_df.columns:
        base = regime_df.set_index("Date")[["regime"]].copy()
    else:
        base = regime_df[["regime"]].copy()
    base.index = pd.to_datetime(base.index)
    base = base.sort_index()

    output: dict[str, dict[str, float]] = {}
    for regime, ticker in favored_assets.items():
        px = asset_prices.get(ticker)
        if px is None or len(px) == 0:
            continue
        px = pd.to_numeric(px, errors="coerce").dropna().sort_index()
        if px.empty:
            continue

        merged = base.join(px.rename("price"), how="inner").dropna()
        merged = merged[merged["regime"] == regime]
        if merged.empty:
            continue

        regime_stats: dict[str, float] = {}
        for h in horizons:
            fwd = (px.shift(-h) / px - 1.0) * 100.0
            fwd_merged = merged.join(fwd.rename(f"fwd_{h}"), how="inner")
            metric = fwd_merged[f"fwd_{h}"].dropna()
            if len(metric) == 0:
                continue
            regime_stats[f"fwd_{h}d_avg_pct"] = float(metric.mean())
            regime_stats[f"fwd_{h}d_obs"] = int(len(metric))
        if regime_stats:
            output[regime] = regime_stats

    return output


def summarize_regime_backtest(
    regime_df: pd.DataFrame,
    asset_prices: dict[str, pd.Series] | None = None,
    horizon: int = 10,
    min_train: int = 126
) -> dict:
    """Return a compact backtest summary for display and diagnostics."""
    if regime_df is None or regime_df.empty:
        return {
            "hit_rate": {"overall_hit_rate": 0.0, "growth_hit_rate": 0.0, "inflation_hit_rate": 0.0, "n_obs": 0},
            "flip_count": 0,
            "forward_returns": {},
        }

    summary = {
        "hit_rate": walk_forward_directional_hit_rate(regime_df, horizon=horizon, min_train=min_train),
        "flip_count": count_regime_flips(regime_df.get("regime", pd.Series(dtype=str))),
        "forward_returns": {},
    }

    if asset_prices:
        summary["forward_returns"] = forward_returns_by_regime(regime_df, asset_prices)

    return summary
