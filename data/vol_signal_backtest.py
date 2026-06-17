"""
Historical validation for IV/RV contrarian signals.

Builds point-in-time features from stored daily_iv rows, computes forward returns
and volatility outcomes, and summarizes performance by signal bucket.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

import data.numpy_compat  # noqa: F401

from .iv_db import IVDatabase
from .vol_table_data import (
    ETF_UNIVERSE,
    _compute_contrarian_scores,
    _compute_vol_valuation,
    _contrarian_signal_label,
    _percentile_from_history,
    _premium_from_iv_rv,
    _safe_float,
    _zscore_from_history,
    _zscore_velocity_from_history,
)

logger = logging.getLogger(__name__)

UNIVERSE_TICKERS = [etf["ticker"] for etf in ETF_UNIVERSE]
FORWARD_HORIZONS = (5, 21, 63)
MIN_HISTORY_ROWS = 22
MIN_FORWARD_HORIZON = min(FORWARD_HORIZONS)
FORWARD_RV_WINDOW = 21
FORWARD_DD_WINDOW = 21

SIGNAL_BUCKETS = (
    "bull_strong",
    "bull_mild",
    "bear_strong",
    "bear_mild",
    "neutral",
    "high_premium",
    "low_premium",
)


def _combo_bucket(signal_bucket: str, extreme_bucket: Optional[str]) -> str:
    if extreme_bucket:
        return f"{signal_bucket}|{extreme_bucket}"
    return signal_bucket


def _ensemble_composite_score(net: int, pct_1y: Optional[float]) -> float:
    """Reinforce net score when 1Y premium percentile aligns with contrarian direction."""
    if pct_1y is None:
        return float(net)
    adj = 0.0
    if net > 0:
        adj = max(0.0, (pct_1y - 50.0) / 5.0)
    elif net < 0:
        adj = max(0.0, (50.0 - pct_1y) / 5.0)
    return round(float(net) + adj, 2)


def signal_bucket_from_net(net: int) -> str:
    if net >= 25:
        return "bull_strong"
    if net >= 10:
        return "bull_mild"
    if net <= -25:
        return "bear_strong"
    if net <= -10:
        return "bear_mild"
    return "neutral"


def _premium_at_row_offset(group: pd.DataFrame, idx: int, offset: int) -> Optional[float]:
    if idx - offset < 0:
        return None
    return _premium_from_iv_rv(group.iloc[idx - offset])


def _forward_return_pct(prices: pd.Series, start_idx: int, horizon: int) -> Optional[float]:
    end_idx = start_idx + horizon
    if end_idx >= len(prices):
        return None
    p0 = float(prices.iloc[start_idx])
    p1 = float(prices.iloc[end_idx])
    if p0 <= 0:
        return None
    return round((p1 / p0 - 1.0) * 100.0, 3)


def _forward_max_drawdown_pct(prices: pd.Series, start_idx: int, window: int) -> Optional[float]:
    end_idx = start_idx + window
    if end_idx >= len(prices):
        return None
    path = prices.iloc[start_idx : end_idx + 1].astype(float)
    if len(path) < 2:
        return None
    running_max = path.cummax()
    drawdowns = path / running_max - 1.0
    return round(float(drawdowns.min()) * 100.0, 3)


def _forward_realized_vol(prices: pd.Series, start_idx: int, window: int) -> Optional[float]:
    """Annualized realized vol over the next `window` trading-day returns."""
    end_idx = start_idx + window
    if end_idx >= len(prices):
        return None
    path = prices.iloc[start_idx : end_idx + 1].astype(float)
    if len(path) < window + 1:
        return None
    ratios = path / path.shift(1)
    rets = np.log(ratios.dropna().values)
    if len(rets) < window:
        return None
    rv = float(np.std(rets[-window:]) * np.sqrt(252))
    return round(rv, 4)


def _hit_rate_for_bucket(bucket: str, returns: pd.Series) -> Optional[float]:
    if returns.empty:
        return None
    if bucket.startswith("bull"):
        return float((returns > 0).mean())
    if bucket.startswith("bear"):
        return float((returns < 0).mean())
    return float((returns > 0).mean())


def _false_positive_rate(bucket: str, returns: pd.Series, threshold_pct: float = -3.0) -> Optional[float]:
    """Share of signals followed by a materially wrong move."""
    if returns.empty:
        return None
    if bucket.startswith("bull"):
        return float((returns < threshold_pct).mean())
    if bucket.startswith("bear"):
        return float((returns > abs(threshold_pct)).mean())
    return None


def build_signal_events(
    panel: pd.DataFrame,
    tickers: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Point-in-time signal rows with forward outcomes for each (ticker, date).

    Args:
        panel: Output of IVDatabase.get_panel_history (sorted by ticker, date).
        tickers: Optional subset of tickers to process.

    Returns:
        DataFrame of events with features and fwd_* columns.
    """
    if panel is None or panel.empty:
        return pd.DataFrame()

    work = panel.copy()
    if tickers:
        work = work[work["ticker"].isin(tickers)]
    if work.empty:
        return pd.DataFrame()

    work["premium"] = work.apply(_premium_from_iv_rv, axis=1)
    work = work.dropna(subset=["premium", "close_price"])
    work["cs_rank"] = work.groupby("date")["premium"].rank(ascending=False, method="min")
    work["cs_n"] = work.groupby("date")["ticker"].transform("count")

    events: List[dict] = []

    for ticker, group in work.groupby("ticker"):
        g = group.sort_values("date").reset_index(drop=True)
        prices = g["close_price"]
        n = len(g)
        # Require at least MIN_FORWARD_HORIZON ahead; longer horizons may be NaN
        last_idx = n - MIN_FORWARD_HORIZON - 1
        if last_idx < MIN_HISTORY_ROWS - 1:
            continue

        for i in range(MIN_HISTORY_ROWS - 1, last_idx + 1):
            row = g.iloc[i]
            hist_newest = g.iloc[: i + 1].iloc[::-1].reset_index(drop=True)

            current = _premium_from_iv_rv(row)
            prem_1d = _premium_at_row_offset(g, i, 1)
            prem_5d = _premium_at_row_offset(g, i, 5)
            prem_21d = _premium_at_row_offset(g, i, 21)
            pct_1y = _percentile_from_history(hist_newest, 252)
            ttm_z = _zscore_from_history(hist_newest, 252)
            prem_z_velocity = _zscore_velocity_from_history(hist_newest, 252, 5)
            ytd_pct = _safe_float(row.get("ytd_return"))
            if ytd_pct is not None:
                ytd_pct = ytd_pct * 100.0

            cs_rank = _safe_float(row.get("cs_rank"))
            cs_n = int(row.get("cs_n") or 1)
            bull, bear = _compute_contrarian_scores(
                pct_1y=pct_1y,
                ttm_z=ttm_z,
                ytd_pct=ytd_pct,
                current=current,
                week=prem_5d,
                month=prem_21d,
                cs_rank=cs_rank,
                n_tickers=cs_n,
            )
            label, net = _contrarian_signal_label(bull, bear)
            bucket = signal_bucket_from_net(net)

            iv = _safe_float(row.get("iv_30d"))
            fwd_rv_21 = _forward_realized_vol(prices, i, FORWARD_RV_WINDOW)
            ex_post_vrp = None
            if iv is not None and fwd_rv_21 is not None:
                ex_post_vrp = round((iv - fwd_rv_21) * 100.0, 2)

            event = {
                "date": row["date"],
                "ticker": ticker,
                "premium": current,
                "ivol_rvol_percentile_1y": pct_1y,
                "ttm_zscore": ttm_z,
                "prem_z_velocity": prem_z_velocity,
                "vol_valuation": _compute_vol_valuation(pct_1y, ttm_z),
                "contrarian_bull_score": bull,
                "contrarian_bear_score": bear,
                "contrarian_net_score": net,
                "contrarian_signal": label,
                "signal_bucket": bucket,
                "ytd_pct": ytd_pct,
                "premium_cs_rank": cs_rank,
                "ex_post_vrp": ex_post_vrp,
                "fwd_max_dd_21d": _forward_max_drawdown_pct(prices, i, FORWARD_DD_WINDOW),
            }

            for h in FORWARD_HORIZONS:
                event[f"fwd_return_{h}d"] = _forward_return_pct(prices, i, h)

            if pct_1y is not None and pct_1y >= 75:
                event["extreme_bucket"] = "high_premium"
            elif pct_1y is not None and pct_1y <= 25:
                event["extreme_bucket"] = "low_premium"
            else:
                event["extreme_bucket"] = None

            event["combo_bucket"] = _combo_bucket(bucket, event.get("extreme_bucket"))
            event["ensemble_score"] = _ensemble_composite_score(net, pct_1y)

            events.append(event)

    if not events:
        return pd.DataFrame()

    return pd.DataFrame(events)


def summarize_bucket_performance(
    events: pd.DataFrame,
    horizon: int = 21,
    bucket_col: str = "signal_bucket",
) -> pd.DataFrame:
    """
    Aggregate forward-return stats by signal bucket for one horizon.

    Returns:
        DataFrame with bucket, n_obs, hit_rate, avg/median return, avg max DD, false_positive_rate.
    """
    ret_col = f"fwd_return_{horizon}d"
    if events is None or events.empty or ret_col not in events.columns:
        return pd.DataFrame()

    rows = []
    for bucket, grp in events.groupby(bucket_col):
        rets = grp[ret_col].dropna()
        if rets.empty:
            continue
        dd = grp["fwd_max_dd_21d"].dropna() if horizon == 21 else pd.Series(dtype=float)
        rows.append({
            "bucket": bucket,
            "horizon_days": horizon,
            "n_obs": int(len(rets)),
            "hit_rate": round(_hit_rate_for_bucket(str(bucket), rets) or 0.0, 3),
            "avg_fwd_return_pct": round(float(rets.mean()), 3),
            "median_fwd_return_pct": round(float(rets.median()), 3),
            "avg_max_dd_21d_pct": round(float(dd.mean()), 3) if not dd.empty else None,
            "false_positive_rate": round(
                _false_positive_rate(str(bucket), rets) or 0.0, 3
            ),
        })

    if not rows:
        return pd.DataFrame(
            columns=[
                "bucket", "horizon_days", "n_obs", "hit_rate",
                "avg_fwd_return_pct", "median_fwd_return_pct",
                "avg_max_dd_21d_pct", "false_positive_rate",
            ]
        )
    return pd.DataFrame(rows).sort_values("n_obs", ascending=False)


def summarize_extreme_premium_performance(
    events: pd.DataFrame,
    horizon: int = 21,
) -> pd.DataFrame:
    """Stats for high/low premium percentile extremes (non-signal buckets)."""
    if events is None or events.empty or "extreme_bucket" not in events.columns:
        return pd.DataFrame()
    subset = events.dropna(subset=["extreme_bucket"])
    return summarize_bucket_performance(
        subset, horizon=horizon, bucket_col="extreme_bucket"
    )


def _spearman_corr(a: pd.Series, b: pd.Series) -> Optional[float]:
    """
    Spearman rank correlation without scipy.

    Pandas' ``Series.corr(method='spearman')`` imports scipy, which breaks on
    NumPy 2.4+ where ``np.in1d`` was removed.
    """
    aligned = pd.concat([a, b], axis=1).dropna()
    if len(aligned) < 10:
        return None
    x = aligned.iloc[:, 0]
    y = aligned.iloc[:, 1]
    if x.std() == 0 or y.std() == 0:
        return None
    return float(x.rank(method="average").corr(y.rank(method="average")))


def information_coefficient(
    events: pd.DataFrame,
    horizon: int = 21,
    score_col: str = "contrarian_net_score",
) -> Optional[float]:
    """Spearman rank correlation between signal score and forward return."""
    ret_col = f"fwd_return_{horizon}d"
    if events is None or events.empty or score_col not in events.columns:
        return None
    df = events[[score_col, ret_col]].dropna()
    if len(df) < 10:
        return None
    if df[ret_col].std() == 0 or df[score_col].std() == 0:
        return None
    ic = _spearman_corr(df[score_col], df[ret_col])
    if ic is None:
        return None
    return round(ic, 4)


def signal_calibration(events: pd.DataFrame, horizon: int = 21) -> dict:
    """
    Spearman IC diagnostics for net score, negated net score, and per-bucket IC.
    """
    ret_col = f"fwd_return_{horizon}d"
    empty = {
        "horizon_days": horizon,
        "ic_net_score": None,
        "ic_negated_net_score": None,
        "ic_ensemble_score": None,
        "ic_prem_z_velocity": None,
        "ic_by_bucket": {},
    }
    if events is None or events.empty or ret_col not in events.columns:
        return empty

    ic_net = information_coefficient(events, horizon=horizon)
    ic_negated = information_coefficient(
        events.assign(_negated_net=-events["contrarian_net_score"]),
        horizon=horizon,
        score_col="_negated_net",
    )
    ic_ensemble = information_coefficient(
        events, horizon=horizon, score_col="ensemble_score"
    )
    ic_prem_z_velocity = information_coefficient(
        events, horizon=horizon, score_col="prem_z_velocity"
    )

    ic_by_bucket: Dict[str, float] = {}
    subset = events[["signal_bucket", "contrarian_net_score", ret_col]].dropna(subset=[ret_col])
    for bucket, grp in subset.groupby("signal_bucket"):
        if len(grp) < 10:
            continue
        if grp[ret_col].std() == 0 or grp["contrarian_net_score"].std() == 0:
            continue
        ic = _spearman_corr(grp["contrarian_net_score"], grp[ret_col])
        if ic is None:
            continue
        ic_by_bucket[str(bucket)] = round(ic, 4)

    return {
        "horizon_days": horizon,
        "ic_net_score": ic_net,
        "ic_negated_net_score": ic_negated,
        "ic_ensemble_score": ic_ensemble,
        "ic_prem_z_velocity": ic_prem_z_velocity,
        "ic_by_bucket": ic_by_bucket,
    }


def run_vol_signal_backtest(
    db: Optional[IVDatabase] = None,
    tickers: Optional[List[str]] = None,
    close_db: bool = True,
) -> Dict:
    """
    Full backtest pipeline: load panel, build events, summarize by bucket/horizon.

    Returns:
        dict with keys: events, summary_by_horizon, extreme_summary, metadata, ic_by_horizon
    """
    own_db = db is None
    if own_db:
        db = IVDatabase()

    try:
        universe = tickers or UNIVERSE_TICKERS
        panel = db.get_panel_history(universe)
        events = build_signal_events(panel, tickers=universe)

        summary_by_horizon = {}
        extreme_by_horizon = {}
        combo_summary_by_horizon = {}
        ic_by_horizon = {}
        ic_ensemble_by_horizon = {}
        calibration_by_horizon = {}
        for h in FORWARD_HORIZONS:
            summary_by_horizon[h] = summarize_bucket_performance(events, horizon=h)
            extreme_by_horizon[h] = summarize_extreme_premium_performance(events, horizon=h)
            combo_summary_by_horizon[h] = summarize_bucket_performance(
                events, horizon=h, bucket_col="combo_bucket"
            )
            ic_by_horizon[h] = information_coefficient(events, horizon=h)
            ic_ensemble_by_horizon[h] = information_coefficient(
                events, horizon=h, score_col="ensemble_score"
            )
            calibration_by_horizon[h] = signal_calibration(events, horizon=h)

        date_min = events["date"].min() if not events.empty else None
        date_max = events["date"].max() if not events.empty else None

        return {
            "events": events,
            "summary_by_horizon": summary_by_horizon,
            "extreme_summary_by_horizon": extreme_by_horizon,
            "combo_summary_by_horizon": combo_summary_by_horizon,
            "ic_by_horizon": ic_by_horizon,
            "ic_ensemble_by_horizon": ic_ensemble_by_horizon,
            "calibration_by_horizon": calibration_by_horizon,
            "metadata": {
                "n_events": len(events),
                "tickers": sorted(events["ticker"].unique().tolist()) if not events.empty else [],
                "date_start": str(date_min)[:10] if date_min is not None else None,
                "date_end": str(date_max)[:10] if date_max is not None else None,
            },
        }
    finally:
        if own_db and close_db and db is not None:
            db.close()


def format_backtest_summary_table(result: Dict, horizon: int = 21) -> pd.DataFrame:
    """Single display table merging signal buckets and premium extremes for one horizon."""
    parts = []
    summ = result.get("summary_by_horizon", {}).get(horizon)
    if summ is not None and not summ.empty:
        parts.append(summ.assign(category="contrarian_signal"))
    extreme = result.get("extreme_summary_by_horizon", {}).get(horizon)
    if extreme is not None and not extreme.empty:
        parts.append(extreme.assign(category="premium_extreme"))
    combo = result.get("combo_summary_by_horizon", {}).get(horizon)
    if combo is not None and not combo.empty:
        parts.append(combo.assign(category="combo_signal"))
    if not parts:
        return pd.DataFrame()
    return pd.concat(parts, ignore_index=True)
