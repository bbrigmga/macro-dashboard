"""Tests for regime LLM export (Macro Dashboard -> Moon Machine)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pandas as pd

from data.regime_llm_export import (
    SCHEMA_NAME,
    SCHEMA_VERSION,
    build_regime_llm_context,
    write_regime_context_json,
)


def _sample_regime_data() -> dict:
    dates = pd.bdate_range("2025-01-01", periods=130)
    trail = pd.DataFrame(
        {
            "Date": dates,
            "growth_zscore": [0.1 + (i * 0.002) for i in range(len(dates))],
            "inflation_zscore": [-0.2 + (i * 0.001) for i in range(len(dates))],
        }
    )
    return {
        "trail_data": trail,
        "current_regime": "Goldilocks",
        "current_growth": 0.35,
        "current_inflation": -0.15,
        "projected_growth": 0.28,
        "projected_inflation": -0.08,
        "regime_confidence": 0.62,
        "regime_description": "Growth above trend, inflation below trend.",
        "backtest_summary": {
            "hit_rate": {
                "overall_hit_rate": 0.55,
                "growth_hit_rate": 0.61,
                "inflation_hit_rate": 0.48,
                "n_obs": 120,
            },
            "forward_returns": {"Goldilocks": {"mean_63d": 0.02}},
        },
    }


class TestRegimeLlmExport:
    def test_build_regime_llm_context_schema(self) -> None:
        payload = build_regime_llm_context(_sample_regime_data())
        assert payload["schema_name"] == SCHEMA_NAME
        assert payload["schema_version"] == SCHEMA_VERSION
        assert payload["signal_type"] == "market_implied_regime_proxy"
        assert payload["current"]["regime_label"] == "Goldilocks"
        assert payload["current"]["growth_z"] == 0.35
        assert payload["ou_projection_63d"]["horizon_trading_days"] == 63
        assert payload["migration_63d"]["lookback_trading_days"] == 63
        assert payload["validation"]["vs_official_gdp_cpi_quadrant_monthly"]["exact_quadrant_match_pct"] == 0.44
        assert payload["scoring_policy"]["max_macro_overlay_weight"] == 0.15
        assert len(payload["caveats"]) >= 3

    def test_write_regime_context_json_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "regime_context.json"
            write_regime_context_json(out, _sample_regime_data())
            loaded = json.loads(out.read_text(encoding="utf-8"))
            expected_as_of = pd.to_datetime(_sample_regime_data()["trail_data"]["Date"].iloc[-1]).date().isoformat()
            assert loaded["current"]["as_of_date"] == expected_as_of
            assert loaded["proxy_definition"]["growth_pairs"]
            assert loaded["proxy_definition"]["inflation_pairs"]
