"""Tests for the Growth/Inflation Regime Quadrant feature."""
import numpy as np
import pandas as pd
import pytest

from data.processing import (
    apply_ema_smoothing,
    build_composite_axis,
    classify_regime,
    forecast_ou,
)


class TestApplyEmaSmoothing:
    def test_reduces_noise(self):
        np.random.seed(42)
        noisy = pd.Series(np.random.randn(200))
        smoothed = apply_ema_smoothing(noisy, span=20)
        assert smoothed.std() < noisy.std()


class TestCompositeHelpers:
    def test_build_composite_axis(self):
        idx = pd.date_range("2024-01-01", periods=6, freq="D")
        s1 = pd.Series([1, 2, 3, 4, 5, 6], index=idx)
        s2 = pd.Series([2, 3, 4, 5, 6, 7], index=idx)
        comp = build_composite_axis({"a": s1, "b": s2}, min_series=1)
        assert len(comp) == 6
        assert np.isclose(comp.iloc[0], 1.5)
        assert np.isclose(comp.iloc[-1], 6.5)


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

    def test_current_marker_visible_on_light_theme(self):
        from visualization.charts import create_regime_quadrant_chart

        trail = pd.DataFrame({
            "Date": pd.date_range("2024-01-01", periods=5),
            "growth_zscore": [0.1, 0.2, 0.3, 0.4, 0.5],
            "inflation_zscore": [0.2, 0.3, 0.4, 0.5, 0.6],
        })
        fig = create_regime_quadrant_chart({
            "trail_data": trail,
            "current_regime": "Goldilocks",
            "current_growth": 0.5,
            "current_inflation": 0.6,
            "projected_growth": 0.5,
            "projected_inflation": 0.6,
            "backtest_summary": {},
        })
        current_trace = fig.data[1]
        assert str(current_trace.marker.color).lower() not in {"#ffffff", "#fff", "white"}

    def test_axis_zooms_to_trail_not_fixed_three(self):
        from visualization.charts import create_regime_quadrant_chart

        trail = pd.DataFrame({
            "Date": pd.date_range("2024-01-01", periods=20),
            "growth_zscore": np.linspace(-0.4, 0.5, 20),
            "inflation_zscore": np.linspace(0.2, 1.0, 20),
        })
        fig = create_regime_quadrant_chart({
            "trail_data": trail,
            "current_regime": "Reflation",
            "current_growth": 0.5,
            "current_inflation": 1.0,
            "projected_growth": 0.45,
            "projected_inflation": 0.95,
            "backtest_summary": {},
        })
        assert fig.layout.xaxis.range[1] <= 1.5
        assert fig.layout.yaxis.range[1] <= 1.5
        assert fig.layout.xaxis.range == fig.layout.yaxis.range
        assert fig.layout.xaxis.range[0] <= 0 <= fig.layout.xaxis.range[1]

    def test_regime_margins_preserved_after_theme(self):
        from visualization.charts import create_regime_quadrant_chart

        trail = pd.DataFrame({
            "Date": pd.date_range("2024-01-01", periods=5),
            "growth_zscore": [0.1] * 5,
            "inflation_zscore": [0.2] * 5,
        })
        fig = create_regime_quadrant_chart({
            "trail_data": trail,
            "current_regime": "Reflation",
            "current_growth": 0.5,
            "current_inflation": 0.6,
            "projected_growth": 0.55,
            "projected_inflation": 0.65,
            "backtest_summary": {},
        })
        assert fig.layout.margin.l >= 60
        assert fig.layout.margin.b >= 60

    def test_arrow_endpoints_match_current_and_projected(self):
        from src.config.growth_proxy import FORECAST_HORIZON_DAYS
        from visualization.charts import create_regime_quadrant_chart

        np.random.seed(0)
        n = 300
        growth_smooth = pd.Series(np.sin(np.linspace(0, 8, n)) + np.random.randn(n) * 0.05)
        inflation_smooth = pd.Series(np.cos(np.linspace(0, 8, n)))
        g_fc = forecast_ou(growth_smooth, horizon=FORECAST_HORIZON_DAYS)
        i_fc = forecast_ou(inflation_smooth, horizon=FORECAST_HORIZON_DAYS)
        current_g = float(growth_smooth.iloc[-1])
        current_i = float(inflation_smooth.iloc[-1])

        trail = pd.DataFrame({
            "Date": pd.date_range("2024-01-01", periods=10),
            "growth_zscore": [float(growth_smooth.iloc[-1])] * 10,
            "inflation_zscore": [float(inflation_smooth.iloc[-1])] * 10,
        })
        fig = create_regime_quadrant_chart({
            "trail_data": trail,
            "current_regime": "Transition",
            "current_growth": current_g,
            "current_inflation": current_i,
            "projected_growth": g_fc["projected"],
            "projected_inflation": i_fc["projected"],
            "forecast_cov": [[0.05, 0.0], [0.0, 0.05]],
            "backtest_summary": {},
        })
        arrow = next(a for a in fig.layout.annotations if a.showarrow)
        assert np.isclose(arrow.ax, current_g)
        assert np.isclose(arrow.ay, current_i)
        assert np.isclose(arrow.x, g_fc["projected"])
        assert np.isclose(arrow.y, i_fc["projected"])


class TestRegimeQuadrantForecastAlignment:
    def test_get_regime_projected_matches_ou_on_smoothed_series(self):
        from data.indicators import IndicatorData
        from src.config.growth_proxy import FORECAST_HORIZON_DAYS

        class FakeYahoo:
            def get_historical_prices(self, ticker, start_date=None, end_date=None, frequency="1d", periods=None):
                path = f"data/cache/{ticker.replace('=', '_').replace('/', '_')}.csv"
                df = pd.read_csv(path)
                df["Date"] = pd.to_datetime(df["Date"])
                if start_date:
                    df = df[df["Date"] >= pd.Timestamp(start_date)]
                if end_date:
                    df = df[df["Date"] < pd.Timestamp(end_date)]
                return df.reset_index(drop=True)

        ind = IndicatorData.__new__(IndicatorData)
        ind.fred_client = None
        ind.yahoo_client = FakeYahoo()
        result = ind.get_regime_quadrant_data(lookback_days=1260, trail_days=252)

        g_smooth = result["growth_smooth"]
        i_smooth = result["inflation_smooth"]
        expected_g = forecast_ou(g_smooth, horizon=FORECAST_HORIZON_DAYS)["projected"]
        expected_i = forecast_ou(i_smooth, horizon=FORECAST_HORIZON_DAYS)["projected"]
        assert np.isclose(result["projected_growth"], expected_g)
        assert np.isclose(result["projected_inflation"], expected_i)
        assert np.isclose(result["current_growth"], float(g_smooth.iloc[-1]))
        assert np.isclose(result["current_inflation"], float(i_smooth.iloc[-1]))


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