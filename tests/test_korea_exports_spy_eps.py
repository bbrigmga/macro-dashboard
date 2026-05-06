"""Tests for Korea exports vs SPY EPS indicator behavior."""

import pandas as pd
from unittest.mock import Mock

from data.indicators import IndicatorData
from visualization.indicators import create_korea_exports_spy_eps_chart


def _monthly_df(series_id: str, start: str, periods: int, values):
    dates = pd.date_range(start=start, periods=periods, freq='M')
    return pd.DataFrame({"Date": dates, series_id: values})


def _quarterly_df(series_id: str, start: str, periods: int, values):
    dates = pd.date_range(start=start, periods=periods, freq='Q')
    return pd.DataFrame({"Date": dates, series_id: values})


def test_exports_only_mode_when_eps_missing():
    mock_fred = Mock()

    exports_values = [100 + i for i in range(48)]

    def _get_series_side_effect(series_id, *args, **kwargs):
        if series_id == "XTEXVA01KRM667S":
            return _monthly_df("XTEXVA01KRM667S", "2022-01-31", 48, exports_values)
        raise ValueError("Series unavailable")

    mock_fred.get_series.side_effect = _get_series_side_effect

    indicator_data = IndicatorData(fred_client=mock_fred)
    result = indicator_data.get_korea_exports_vs_spy_eps(periods=24)

    assert result["mode"] == "exports_only"
    assert result["forward_eps_available"] is False
    assert "korea_exports_yoy" in result["data"].columns
    assert not result["data"]["korea_exports_yoy"].dropna().empty


def test_eps_proxy_mode_when_eps_available():
    mock_fred = Mock()

    exports_values = [100 + i for i in range(72)]
    eps_values = [50 + i for i in range(24)]

    def _get_series_side_effect(series_id, *args, **kwargs):
        if series_id == "XTEXVA01KRM667S":
            return _monthly_df("XTEXVA01KRM667S", "2020-01-31", 72, exports_values)
        if series_id == "SP500EARN":
            return _quarterly_df("SP500EARN", "2020-03-31", 24, eps_values)
        raise ValueError("Series unavailable")

    mock_fred.get_series.side_effect = _get_series_side_effect

    indicator_data = IndicatorData(fred_client=mock_fred)
    result = indicator_data.get_korea_exports_vs_spy_eps(periods=36)

    assert result["mode"] == "eps_proxy"
    assert result["forward_eps_available"] is True
    assert "spy_ntm_eps_yoy" in result["data"].columns
    assert not result["data"]["spy_ntm_eps_yoy"].dropna().empty


def test_chart_renders_exports_only_mode():
    df = pd.DataFrame(
        {
            "Date": pd.date_range("2024-01-31", periods=12, freq="M"),
            "korea_exports_yoy": [i * 0.5 for i in range(12)],
        }
    )

    fig = create_korea_exports_spy_eps_chart(
        {
            "data": df,
            "mode": "exports_only",
            "correlation_full": None,
        },
        periods=12,
    )

    assert len(fig.data) == 1


def test_chart_renders_paired_mode():
    df = pd.DataFrame(
        {
            "Date": pd.date_range("2024-01-31", periods=12, freq="M"),
            "korea_exports_yoy": [i * 0.5 for i in range(12)],
            "spy_ntm_eps_yoy": [i * 0.4 for i in range(12)],
        }
    )

    fig = create_korea_exports_spy_eps_chart(
        {
            "data": df,
            "mode": "eps_proxy",
            "correlation_full": 0.88,
        },
        periods=12,
    )

    assert len(fig.data) == 2
