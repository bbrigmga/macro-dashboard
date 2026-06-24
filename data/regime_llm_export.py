"""
Build versioned regime context JSON for external consumers (e.g. Moon Machine LLM scoring).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from data.processing import classify_regime
from src.config.growth_proxy import (
    DELTA_DAYS,
    FORECAST_HORIZON_DAYS,
    GROWTH_PROXY_PAIRS,
    ZSCORE_DAYS,
)
from src.config.inflation_proxy import INFLATION_PROXY_PAIRS

SCHEMA_NAME = "macro_dashboard.regime_context"
SCHEMA_VERSION = "2.0.0"

# Static calibration from walk-forward vs official GDP/CPI quadrants (~10y monthly sample).
VALIDATION_VS_OFFICIAL_MACRO = {
    "exact_quadrant_match_pct": 0.44,
    "growth_axis_match_pct": 0.69,
    "inflation_axis_match_pct": 0.57,
    "note": "Proxy vs GDPC1 QoQ + core CPI YoY median-split axes; not a live backtest field.",
}

SCORING_POLICY = {
    "max_macro_overlay_weight": 0.15,
    "ignore_if_transition": True,
    "ignore_if_confidence_below": 0.35,
    "do_not_equate_with_official_cpi_gdp": True,
}

CAVEATS = [
    "Market-implied contemporaneous momentum from ETF ratio pairs, not official GDP/CPI prints.",
    "Current dot reflects ~63 trading days of ratio change z-scored over ~252 days.",
    "Inflation proxy often diverges from CPI YoY during disinflation.",
    "GDP is quarterly with publication lag; do not treat regime label as BEA/BLS ground truth.",
    "OU projection is mean-reversion on proxy z-scores, not a macro release forecast.",
]


def _axis_direction(z: float | None) -> str | None:
    if z is None or pd.isna(z):
        return None
    return "up" if float(z) >= 0 else "down"


def _regime_at_z(growth_z: float, inflation_z: float) -> str:
    return classify_regime(float(growth_z), float(inflation_z), neutral_band=0.25, prev_regime=None)


def _pair_labels(pairs: tuple) -> list[str]:
    return [f"{p.num}/{p.denom}" for p in pairs]


def build_regime_llm_context(regime_data: dict[str, Any]) -> dict[str, Any]:
    """
    Transform get_regime_quadrant_data() output into Moon Machine / LLM-ready JSON.
    """
    trail = regime_data.get("trail_data")
    if trail is None or (hasattr(trail, "empty") and trail.empty):
        as_of = datetime.now(timezone.utc).date().isoformat()
    else:
        as_of = pd.to_datetime(trail["Date"].iloc[-1]).date().isoformat()

    current_growth = float(regime_data.get("current_growth") or 0.0)
    current_inflation = float(regime_data.get("current_inflation") or 0.0)
    projected_growth = float(regime_data.get("projected_growth") or current_growth)
    projected_inflation = float(regime_data.get("projected_inflation") or current_inflation)
    confidence = float(regime_data.get("regime_confidence") or 0.0)
    current_regime = str(regime_data.get("current_regime") or "Unknown")

    migration: dict[str, Any] = {}
    if trail is not None and not (hasattr(trail, "empty") and trail.empty) and len(trail) > 1:
        lookback = min(FORECAST_HORIZON_DAYS, len(trail) - 1)
        past = trail.iloc[-1 - lookback]
        g_delta = current_growth - float(past["growth_zscore"])
        i_delta = current_inflation - float(past["inflation_zscore"])
        past_regime = _regime_at_z(float(past["growth_zscore"]), float(past["inflation_zscore"]))
        migration = {
            "lookback_trading_days": lookback,
            "regime_label": past_regime,
            "growth_z_delta": round(g_delta, 4),
            "inflation_z_delta": round(i_delta, 4),
            "summary": (
                f"over {lookback}d: growth_z {'+' if g_delta >= 0 else ''}{g_delta:.2f}, "
                f"inflation_z {'+' if i_delta >= 0 else ''}{i_delta:.2f}"
            ),
        }

    backtest_summary = regime_data.get("backtest_summary") or {}
    hit_rate = backtest_summary.get("hit_rate") or {}
    accel_hit_rate = backtest_summary.get("accel_hit_rate") or {}
    forward_returns = (regime_data.get("backtest_summary") or {}).get("forward_returns") or {}

    return {
        "schema_name": SCHEMA_NAME,
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "source": "macro_dashboard",
        "signal_type": "market_implied_regime_proxy",
        "current": {
            "as_of_date": as_of,
            "regime_label": current_regime,
            "growth_z": round(current_growth, 4),
            "inflation_z": round(current_inflation, 4),
            "growth_axis": _axis_direction(current_growth),
            "inflation_axis": _axis_direction(current_inflation),
            "confidence": round(confidence, 4),
        },
        "migration_63d": migration,
        "ou_projection_63d": {
            "horizon_trading_days": FORECAST_HORIZON_DAYS,
            "projected_growth_z": round(projected_growth, 4),
            "projected_inflation_z": round(projected_inflation, 4),
            "projected_regime_label": _regime_at_z(projected_growth, projected_inflation),
            "note": "Mean-reverting AR(1)/OU on proxy z-scores; not a GDP/CPI forecast.",
        },
        "proxy_definition": {
            "growth_pairs": _pair_labels(GROWTH_PROXY_PAIRS),
            "inflation_pairs": _pair_labels(INFLATION_PROXY_PAIRS),
            "delta_days": DELTA_DAYS,
            "zscore_window": ZSCORE_DAYS,
            "ema_span": 20,
        },
        "validation": {
            "vs_official_gdp_cpi_quadrant_monthly": VALIDATION_VS_OFFICIAL_MACRO,
            "ou_directional_hit_rate_63d": {
                "overall": hit_rate.get("overall_hit_rate"),
                "growth": hit_rate.get("growth_hit_rate"),
                "inflation": hit_rate.get("inflation_hit_rate"),
                "n_obs": hit_rate.get("n_obs"),
            },
            "ou_acceleration_hit_rate_63d": {
                "overall": accel_hit_rate.get("overall_hit_rate"),
                "growth": accel_hit_rate.get("growth_hit_rate"),
                "inflation": accel_hit_rate.get("inflation_hit_rate"),
                "n_obs": accel_hit_rate.get("n_obs"),
            },
            "forward_returns_by_regime": forward_returns,
        },
        "scoring_policy": SCORING_POLICY,
        "caveats": CAVEATS,
        "regime_description": regime_data.get("regime_description"),
    }


def write_regime_context_json(
    output_path: Path | str,
    regime_data: dict[str, Any],
) -> Path:
    """Write regime LLM context JSON to disk."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_regime_llm_context(regime_data)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
