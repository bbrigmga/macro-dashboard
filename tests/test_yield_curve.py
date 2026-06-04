"""Tests for 10Y-2Y yield curve data preparation."""

import pandas as pd

from data.indicators import IndicatorData


def _daily_spread_frame():
    dates = pd.date_range("2019-01-02", periods=1600, freq="B")
    values = [0.5 + (i % 40) * 0.01 for i in range(len(dates))]
    return pd.DataFrame({"Date": dates, "T10Y2Y": values})


def test_yield_curve_monthly_resample_returns_one_row_per_month(monkeypatch):
    """Monthly display must not pass raw daily rows to the chart builder."""
    daily = _daily_spread_frame()

    class FakeFred:
        def get_series(self, series_id, start_date=None, periods=None, frequency='M'):
            assert series_id == "T10Y2Y"
            assert start_date is not None
            return daily.copy()

    indicator = IndicatorData(fred_client=FakeFred())
    result = indicator.get_yield_curve(periods=60, frequency="M")
    chart_df = result["data"]

    assert len(chart_df) == 60
    chart_df["Date"] = pd.to_datetime(chart_df["Date"])
    labels = chart_df["Date"].dt.strftime("%b %Y")
    assert labels.nunique() == len(chart_df)
    assert result["latest_value"] == float(daily["T10Y2Y"].iloc[-1])
