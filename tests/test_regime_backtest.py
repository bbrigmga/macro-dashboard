"""Tests for regime quadrant walk-forward backtest metrics."""

from __future__ import annotations

import pandas as pd
import pytest

from analysis.regime_backtest import (
    enrich_regime_quadrant_data,
    summarize_regime_backtest,
    walk_forward_acceleration_hit_rate,
    walk_forward_directional_hit_rate,
)


def _linear_series(n: int) -> pd.Series:
    return pd.Series(range(n), dtype=float)


def test_walk_forward_acceleration_hit_rate_constant_velocity(monkeypatch):
    n = 400
    df = pd.DataFrame({
        "growth_raw": _linear_series(n),
        "inflation_raw": _linear_series(n),
    })

    def mock_forecast(series, horizon=63):
        last = float(series.iloc[-1])
        return {"projected": last + horizon}

    monkeypatch.setattr("analysis.regime_backtest.forecast_ou", mock_forecast)

    result = walk_forward_acceleration_hit_rate(df, horizon=63, min_train=126)

    assert result["n_obs"] > 0
    assert result["overall_hit_rate"] == pytest.approx(1.0)
    assert result["growth_hit_rate"] == pytest.approx(1.0)
    assert result["inflation_hit_rate"] == pytest.approx(1.0)


def test_walk_forward_acceleration_hit_rate_detects_mismatch(monkeypatch):
    n = 400
    df = pd.DataFrame({
        "growth_raw": _linear_series(n),
        "inflation_raw": _linear_series(n),
    })

    def mock_forecast(series, horizon=63):
        last = float(series.iloc[-1])
        return {"projected": last + (2 * horizon)}

    monkeypatch.setattr("analysis.regime_backtest.forecast_ou", mock_forecast)

    result = walk_forward_acceleration_hit_rate(df, horizon=63, min_train=126)

    assert result["n_obs"] > 0
    assert result["overall_hit_rate"] == pytest.approx(0.0)


def test_summarize_regime_backtest_includes_accel_hit_rate(monkeypatch):
    n = 400
    regime_df = pd.DataFrame({
        "Date": pd.date_range("2020-01-01", periods=n, freq="B"),
        "growth_raw": _linear_series(n),
        "inflation_raw": _linear_series(n),
        "regime": ["Goldilocks"] * n,
    })

    def mock_forecast(series, horizon=63):
        last = float(series.iloc[-1])
        return {"projected": last + horizon}

    monkeypatch.setattr("analysis.regime_backtest.forecast_ou", mock_forecast)

    summary = summarize_regime_backtest(regime_df, horizon=63, min_train=126)

    assert "hit_rate" in summary
    assert "accel_hit_rate" in summary
    assert summary["hit_rate"]["n_obs"] == summary["accel_hit_rate"]["n_obs"]
    assert summary["hit_rate"]["overall_hit_rate"] == pytest.approx(1.0)
    assert summary["accel_hit_rate"]["overall_hit_rate"] == pytest.approx(1.0)


def test_enrich_regime_quadrant_data_backfills_accel_hit_rate():
    n = 400
    regime_data = {
        "backtest_summary": {
            "hit_rate": {
                "overall_hit_rate": 0.55,
                "growth_hit_rate": 0.61,
                "inflation_hit_rate": 0.48,
                "n_obs": 120,
            },
        },
        "regime_description": "Growth up, inflation down.",
        "growth_raw": _linear_series(n),
        "inflation_raw": _linear_series(n),
    }

    enriched = enrich_regime_quadrant_data(regime_data)

    assert "accel_hit_rate" in enriched["backtest_summary"]
    assert enriched["backtest_summary"]["accel_hit_rate"]["n_obs"] > 0
    assert "accel_hit_rate" not in regime_data["backtest_summary"]
    assert "accel:" in enriched["regime_description"]


def test_enrich_regime_quadrant_data_leaves_complete_payload_unchanged():
    regime_data = {
        "backtest_summary": {
            "hit_rate": {"overall_hit_rate": 0.5, "n_obs": 10},
            "accel_hit_rate": {"overall_hit_rate": 0.4, "n_obs": 10},
        },
        "regime_description": "Goldilocks | Walk-forward 63d dir: 50%, accel: 40% (10 obs)",
    }

    assert enrich_regime_quadrant_data(regime_data) is regime_data


def test_walk_forward_directional_hit_rate_linear_trend(monkeypatch):
    n = 400
    df = pd.DataFrame({
        "growth_raw": _linear_series(n),
        "inflation_raw": _linear_series(n),
    })

    def mock_forecast(series, horizon=63):
        last = float(series.iloc[-1])
        return {"projected": last + horizon}

    monkeypatch.setattr("analysis.regime_backtest.forecast_ou", mock_forecast)

    result = walk_forward_directional_hit_rate(df, horizon=63, min_train=126)

    assert result["overall_hit_rate"] == pytest.approx(1.0)
