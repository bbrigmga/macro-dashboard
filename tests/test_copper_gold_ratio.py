"""Regression tests for copper/gold ratio indicator."""

from unittest.mock import Mock

import pandas as pd

from data.indicators import IndicatorData


def test_get_copper_gold_ratio_builds_ratio_series():
    mock_fred = Mock()
    mock_yahoo = Mock()

    yield_dates = pd.date_range("2024-01-01", "2024-03-31", freq="D")
    yield_df = pd.DataFrame({"Date": yield_dates, "DGS10": [4.0 + (i * 0.001) for i in range(len(yield_dates))]})

    copper_df = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2024-01-01", "2024-02-01", "2024-03-01"]),
            "PCOPPUSDM": [8500.0, 8600.0, 8700.0],
        }
    )

    gold_df = pd.DataFrame({"Date": yield_dates, "value": [2000.0 + (i * 0.5) for i in range(len(yield_dates))]})

    def _get_series_side_effect(series_id, *args, **kwargs):
        if series_id == "DGS10":
            return yield_df
        if series_id == "PCOPPUSDM":
            return copper_df
        raise ValueError(f"Unexpected series id: {series_id}")

    mock_fred.get_series.side_effect = _get_series_side_effect
    mock_yahoo.get_historical_prices.return_value = gold_df

    indicator_data = IndicatorData(fred_client=mock_fred)
    indicator_data.yahoo_client = mock_yahoo

    result = indicator_data.get_copper_gold_ratio(periods=52)

    assert not result["data"].empty
    assert "ratio" in result["data"].columns
    assert result["current_value"] is not None
    assert result["current_value"] > 0

