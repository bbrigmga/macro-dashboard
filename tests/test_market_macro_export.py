"""Tests for market macro export alignment and output shape."""
import datetime

import numpy as np
import pandas as pd

from data.market_macro_export import EXPORT_COLUMNS, build_market_macro_export
from data.processing import align_series_asof


class TestAlignSeriesAsOf:
    def test_quarterly_gdp_propagates_until_next_release(self):
        calendar = pd.bdate_range("2024-01-01", "2024-06-30")
        gdp_dates = pd.to_datetime(["2023-12-31", "2024-03-31"])
        gdp = pd.Series([25000.0, 25500.0], index=gdp_dates)

        aligned = align_series_asof(calendar, gdp, "GDP")

        before_q2 = aligned[calendar < "2024-04-01"]
        after_q2 = aligned[calendar >= "2024-04-01"]
        assert before_q2.iloc[-1] == 25000.0
        assert after_q2.iloc[0] == 25500.0

    def test_monthly_cpi_propagates_until_next_month(self):
        calendar = pd.date_range("2024-01-15", periods=20, freq="B")
        cpi_dates = pd.to_datetime(["2024-01-01", "2024-02-01"])
        cpi = pd.Series([310.0, 311.5], index=cpi_dates)

        aligned = align_series_asof(calendar, cpi, "CPI")

        assert aligned.iloc[0] == 310.0
        assert aligned.iloc[-1] == 311.5

    def test_rows_before_first_observation_are_nan(self):
        calendar = pd.date_range("2024-01-01", periods=5, freq="B")
        gdp_dates = pd.to_datetime(["2024-03-31"])
        gdp = pd.Series([25500.0], index=gdp_dates)

        aligned = align_series_asof(calendar, gdp, "GDP")

        assert aligned.isna().all()

    def test_empty_macro_series_returns_nan(self):
        calendar = pd.date_range("2024-01-01", periods=3, freq="B")
        aligned = align_series_asof(calendar, pd.Series(dtype=float), "GDP")
        assert aligned.isna().all()


class TestBuildMarketMacroExport:
    def test_inner_joined_etf_calendar_has_unique_dates(self):
        base = datetime.datetime.now() - datetime.timedelta(days=30)
        dates = pd.bdate_range(base, periods=5)
        yahoo_frames = {
            ticker: pd.DataFrame({
                "Date": dates,
                "value": np.arange(5) + i,
            })
            for i, ticker in enumerate(["CPER", "GLD", "IEF", "TIP"])
        }

        class FakeYahoo:
            def get_historical_prices(self, ticker, start_date=None, end_date=None, frequency="1d"):
                return yahoo_frames[ticker].copy()

        macro_start = dates.min() - pd.Timedelta(days=60)

        class FakeFred:
            def get_series(self, series_id, start_date=None, end_date=None, periods=None, frequency="M"):
                if series_id == "GDP":
                    return pd.DataFrame({
                        "Date": pd.to_datetime([macro_start]),
                        "GDP": [25000.0],
                    })
                return pd.DataFrame({
                    "Date": pd.to_datetime([macro_start, macro_start + pd.Timedelta(days=31)]),
                    "CPIAUCSL": [310.0, 311.0],
                })

        df = build_market_macro_export(
            years=1,
            yahoo_client=FakeYahoo(),
            fred_client=FakeFred(),
        )

        assert list(df.columns) == EXPORT_COLUMNS
        assert len(df) == 5
        assert df["Date"].duplicated().sum() == 0
        assert df["CPER"].notna().all()
        assert df["GDP"].notna().all()
        assert df["CPI"].notna().all()

    def test_export_columns_order(self):
        base = datetime.datetime.now() - datetime.timedelta(days=20)
        dates = pd.bdate_range(base, periods=3)
        yahoo_frames = {
            ticker: pd.DataFrame({"Date": dates, "value": [1.0, 2.0, 3.0]})
            for ticker in ["CPER", "GLD", "IEF", "TIP"]
        }

        class FakeYahoo:
            def get_historical_prices(self, ticker, start_date=None, end_date=None, frequency="1d"):
                return yahoo_frames[ticker].copy()

        macro_start = dates.min() - pd.Timedelta(days=60)

        class FakeFred:
            def get_series(self, series_id, start_date=None, end_date=None, periods=None, frequency="M"):
                if series_id == "GDP":
                    return pd.DataFrame({
                        "Date": pd.to_datetime([macro_start]),
                        "GDP": [25000.0],
                    })
                return pd.DataFrame({
                    "Date": pd.to_datetime([macro_start]),
                    "CPIAUCSL": [310.0],
                })

        df = build_market_macro_export(
            years=1,
            yahoo_client=FakeYahoo(),
            fred_client=FakeFred(),
        )

        assert list(df.columns) == ["Date", "CPER", "GLD", "IEF", "TIP", "GDP", "CPI"]
        assert df["Date"].iloc[0].count("-") == 2  # YYYY-MM-DD string
