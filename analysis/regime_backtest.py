"""Walk-forward backtest utilities for the regime quadrant model."""

from __future__ import annotations

import numpy as np
import pandas as pd

from data.processing import forecast_ou
from src.config.growth_proxy import FORECAST_HORIZON_DAYS


def _safe_float(value, default: float = 0.0) -> float:
    try:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return default
        return float(value)
    except Exception:
        return default


def walk_forward_directional_hit_rate(
    df: pd.DataFrame,
    horizon: int = FORECAST_HORIZON_DAYS,
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


def walk_forward_acceleration_hit_rate(
    df: pd.DataFrame,
    horizon: int = FORECAST_HORIZON_DAYS,
    min_train: int = 126
) -> dict:
    """
    Walk-forward hit-rate for predicted vs realized momentum acceleration.

    Compares the sign of (forward velocity - recent velocity) where velocity
    is the change in the raw proxy over ``horizon`` trading days.
    """
    empty = {
        "overall_hit_rate": 0.0,
        "growth_hit_rate": 0.0,
        "inflation_hit_rate": 0.0,
        "n_obs": 0,
    }
    required_cols = {"growth_raw", "inflation_raw"}
    if df is None or df.empty or not required_cols.issubset(df.columns):
        return empty

    data = df.dropna(subset=["growth_raw", "inflation_raw"]).reset_index(drop=True)
    max_idx = len(data) - horizon
    start_idx = max(min_train, horizon)
    if max_idx <= start_idx:
        return empty

    overall_hits = []
    growth_hits = []
    inflation_hits = []

    for i in range(start_idx, max_idx):
        hist = data.iloc[: i + 1]
        current_growth = _safe_float(hist["growth_raw"].iloc[-1])
        current_inflation = _safe_float(hist["inflation_raw"].iloc[-1])
        past_growth = _safe_float(data["growth_raw"].iloc[i - horizon], current_growth)
        past_inflation = _safe_float(data["inflation_raw"].iloc[i - horizon], current_inflation)

        growth_fc = forecast_ou(hist["growth_raw"], horizon=horizon)
        inflation_fc = forecast_ou(hist["inflation_raw"], horizon=horizon)
        proj_growth = _safe_float(growth_fc["projected"], current_growth)
        proj_inflation = _safe_float(inflation_fc["projected"], current_inflation)

        realized_growth = _safe_float(data["growth_raw"].iloc[i + horizon], current_growth)
        realized_inflation = _safe_float(data["inflation_raw"].iloc[i + horizon], current_inflation)

        past_vel_g = current_growth - past_growth
        past_vel_i = current_inflation - past_inflation
        pred_vel_g = proj_growth - current_growth
        pred_vel_i = proj_inflation - current_inflation
        real_vel_g = realized_growth - current_growth
        real_vel_i = realized_inflation - current_inflation

        pred_accel_g = pred_vel_g - past_vel_g
        pred_accel_i = pred_vel_i - past_vel_i
        real_accel_g = real_vel_g - past_vel_g
        real_accel_i = real_vel_i - past_vel_i

        g_hit = np.sign(pred_accel_g) == np.sign(real_accel_g)
        i_hit = np.sign(pred_accel_i) == np.sign(real_accel_i)
        growth_hits.append(bool(g_hit))
        inflation_hits.append(bool(i_hit))
        overall_hits.append(bool(g_hit and i_hit))

    n_obs = len(overall_hits)
    if n_obs == 0:
        return empty

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
    horizon: int = FORECAST_HORIZON_DAYS,
    min_train: int = 126
) -> dict:
    """Return a compact backtest summary for display and diagnostics."""
    empty_hit_rate = {
        "overall_hit_rate": 0.0,
        "growth_hit_rate": 0.0,
        "inflation_hit_rate": 0.0,
        "n_obs": 0,
    }
    if regime_df is None or regime_df.empty:
        return {
            "hit_rate": empty_hit_rate.copy(),
            "accel_hit_rate": empty_hit_rate.copy(),
            "flip_count": 0,
            "forward_returns": {},
        }

    summary = {
        "hit_rate": walk_forward_directional_hit_rate(regime_df, horizon=horizon, min_train=min_train),
        "accel_hit_rate": walk_forward_acceleration_hit_rate(
            regime_df, horizon=horizon, min_train=min_train
        ),
        "flip_count": count_regime_flips(regime_df.get("regime", pd.Series(dtype=str))),
        "forward_returns": {},
    }

    if asset_prices:
        summary["forward_returns"] = forward_returns_by_regime(regime_df, asset_prices)

    return summary


def enrich_regime_quadrant_data(regime_data: dict) -> dict:
    """
    Ensure backtest_summary includes accel_hit_rate for older cached payloads.
    """
    if not regime_data:
        return regime_data

    backtest_summary = dict(regime_data.get("backtest_summary") or {})
    if "accel_hit_rate" in backtest_summary:
        return regime_data

    growth_raw = regime_data.get("growth_raw")
    inflation_raw = regime_data.get("inflation_raw")
    if growth_raw is None or inflation_raw is None:
        return regime_data

    regime_df = pd.DataFrame({
        "growth_raw": pd.to_numeric(growth_raw, errors="coerce"),
        "inflation_raw": pd.to_numeric(inflation_raw, errors="coerce"),
    }).dropna()
    if regime_df.empty:
        return regime_data

    backtest_summary["accel_hit_rate"] = walk_forward_acceleration_hit_rate(regime_df)
    enriched = dict(regime_data)
    enriched["backtest_summary"] = backtest_summary

    hit_rate = (backtest_summary.get("hit_rate") or {}).get("overall_hit_rate")
    accel_hit_rate = backtest_summary["accel_hit_rate"].get("overall_hit_rate")
    hit_obs = (backtest_summary.get("hit_rate") or {}).get("n_obs", 0)
    description = str(enriched.get("regime_description") or "")
    if hit_obs > 0 and hit_rate is not None:
        base = description.split(" | Walk-forward")[0]
        note = f" | Walk-forward {FORECAST_HORIZON_DAYS}d dir: {hit_rate:.0%}"
        if accel_hit_rate is not None:
            note += f", accel: {accel_hit_rate:.0%}"
        note += f" ({hit_obs} obs)"
        enriched["regime_description"] = base + note

    return enriched
