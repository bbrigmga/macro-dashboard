"""Tests for the Growth/Inflation Regime Quadrant feature."""
import numpy as np
import pandas as pd
import pytest

from data.processing import (
    apply_ema_smoothing,
    anchor_zscore,
    blended_momentum_zscore,
    build_composite_axis,
    calculate_roc_zscore,
    classify_regime,
    forecast_ou,
)


class TestCalculateRocZscore:
    def test_returns_series_same_length(self):
        series = pd.Series(np.random.randn(400).cumsum() + 100)
        result = calculate_roc_zscore(series, roc_period=60, zscore_window=252)
        assert len(result) == len(series)

    def test_empty_series(self):
        series = pd.Series(dtype=float)
        result = calculate_roc_zscore(series)
        assert len(result) == 0


class TestApplyEmaSmoothing:
    def test_reduces_noise(self):
        np.random.seed(42)
        noisy = pd.Series(np.random.randn(200))
        smoothed = apply_ema_smoothing(noisy, span=20)
        assert smoothed.std() < noisy.std()


class TestCompositeHelpers:
    def test_blended_momentum_zscore_shape(self):
        np.random.seed(42)
        series = pd.Series(np.random.randn(700).cumsum() + 100)
        result = blended_momentum_zscore(series, roc_periods=(20, 60, 120), zscore_window=252)
        assert len(result) == len(series)
        assert result.dropna().shape[0] > 0

    def test_build_composite_axis(self):
        idx = pd.date_range("2024-01-01", periods=6, freq="D")
        s1 = pd.Series([1, 2, 3, 4, 5, 6], index=idx)
        s2 = pd.Series([2, 3, 4, 5, 6, 7], index=idx)
        comp = build_composite_axis({"a": s1, "b": s2}, min_series=1)
        assert len(comp) == 6
        assert np.isclose(comp.iloc[0], 1.5)
        assert np.isclose(comp.iloc[-1], 6.5)

    def test_anchor_zscore_keeps_index(self):
        idx = pd.date_range("2023-01-01", periods=300, freq="D")
        base = pd.Series(np.linspace(10, 20, 300), index=idx)
        rolling = calculate_roc_zscore(base, roc_period=20, zscore_window=60)
        anchored = anchor_zscore(rolling, base, weight=0.3)
        assert len(anchored) == len(rolling)
        assert anchored.index.equals(rolling.index)


class TestRegimeClassification:
    def test_all_quadrants_covered(self):
        assert classify_regime(1.5, 1.5, neutral_band=0.25) == "Reflation"
        assert classify_regime(1.5, -1.5, neutral_band=0.25) == "Goldilocks"
        assert classify_regime(-1.5, 1.5, neutral_band=0.25) == "Stagflation"
        assert classify_regime(-1.5, -1.5, neutral_band=0.25) == "Deflation"

    def test_neutral_band_returns_transition_without_history(self):
        assert classify_regime(0.1, 0.8, neutral_band=0.25, prev_regime=None) == "Transition"
        assert classify_regime(-0.1, -0.1, neutral_band=0.25, prev_regime=None) == "Transition"

    def test_hysteresis_holds_previous_regime_inside_band(self):
        held = classify_regime(0.1, 0.05, neutral_band=0.25, prev_regime="Goldilocks")
        assert held == "Goldilocks"


class TestForecastOu:
    def test_forecast_mean_reverts_for_stationary_series(self):
        np.random.seed(42)
        n = 500
        x = np.zeros(n)
        for i in range(1, n):
            x[i] = 0.85 * x[i - 1] + np.random.normal(scale=0.25)
        x[-1] = 2.5  # force an extreme endpoint
        series = pd.Series(x)
        fc = forecast_ou(series, horizon=10)
        assert fc["projected"] < series.iloc[-1]
        assert fc["variance"] >= 0.0

    def test_forecast_covariance_input_is_numeric(self):
        series = pd.Series(np.random.randn(300).cumsum())
        fc = forecast_ou(series, horizon=10)
        assert isinstance(fc["projected"], float)
        assert isinstance(fc["variance"], float)


class TestRegimeQuadrantChart:
    def test_chart_backfills_accel_hit_rate_from_raw_series(self):
        from visualization.charts import create_regime_quadrant_chart

        n = 400
        trail = pd.DataFrame({
            "Date": pd.date_range("2024-01-01", periods=10),
            "growth_zscore": [0.1] * 10,
            "inflation_zscore": [0.2] * 10,
        })
        mock_data = {
            "trail_data": trail,
            "current_growth": 0.5,
            "current_inflation": 0.6,
            "projected_growth": 0.6,
            "projected_inflation": 0.7,
            "growth_raw": pd.Series(range(n), dtype=float),
            "inflation_raw": pd.Series(range(n), dtype=float),
            "backtest_summary": {
                "hit_rate": {"overall_hit_rate": 0.55, "n_obs": 100},
            },
        }

        fig = create_regime_quadrant_chart(mock_data)
        badge = next(
            (
                ann.text
                for ann in fig.layout.annotations
                if ann.text and ann.text.startswith("Forecast: OU")
            ),
            "",
        )
        assert "Accel:" in badge
        assert fig is not None


class TestRegimeQuadrantPayloadStructure:
    def test_return_dict_structure(self):
        mock_data = {
            'data': pd.DataFrame({
                'Date': pd.date_range('2024-01-01', periods=5),
                'growth_zscore': [0.1, 0.2, 0.3, 0.4, 0.5],
                'inflation_zscore': [0.2, 0.3, 0.4, 0.5, 0.6]
            }),
            'trail_data': pd.DataFrame(),
            'current_regime': 'Goldilocks',
            'current_growth': 0.5,
            'current_inflation': 0.6,
            'projected_growth': 0.6,
            'projected_inflation': 0.7,
            'forecast_cov': [[0.05, 0.01], [0.01, 0.06]],
            'regime_confidence': 0.8,
            'backtest_summary': {'hit_rate': {'overall_hit_rate': 0.55}},
            'regime_description': 'Test description'
        }

        required_keys = [
            'data', 'trail_data', 'current_regime',
            'current_growth', 'current_inflation',
            'projected_growth', 'projected_inflation',
            'forecast_cov', 'regime_confidence', 'backtest_summary',
            'regime_description'
        ]
        for key in required_keys:
            assert key in mock_data, f"Missing required key: {key}"

        assert isinstance(mock_data['data'], pd.DataFrame)
        assert isinstance(mock_data['trail_data'], pd.DataFrame)
        assert isinstance(mock_data['current_regime'], str)
        assert isinstance(mock_data['forecast_cov'], list)
        assert isinstance(mock_data['regime_confidence'], (int, float))


if __name__ == "__main__":
    pytest.main([__file__])