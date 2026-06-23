"""Tests for market macro export alignment and output shape."""
import datetime

import numpy as np
import pandas as pd

from data.market_macro_export import (
    build_market_macro_export,
    collect_fred_series,
    collect_yahoo_tickers,
    export_column_names,
)
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


class TestExportCollections:
    def test_yahoo_tickers_include_regime_proxies(self):
        tickers = collect_yahoo_tickers()
        assert "DBC" in tickers
        assert "CPER" in tickers
        assert "XLV" in tickers
        assert "QQQ" in tickers

    def test_fred_series_include_gdp_and_cpi(self):
        series = collect_fred_series()
        assert "GDP" in series
        assert "CPIAUCSL" in series


class TestBuildMarketMacroExport:
    def test_outer_joined_etf_calendar_and_fred_columns(self):
        base = datetime.datetime.now() - datetime.timedelta(days=30)
        dates = pd.bdate_range(base, periods=5)
        yahoo_frames = {
            "CPER": pd.DataFrame({"Date": dates, "value": [1.0, 2.0, 3.0, 4.0, 5.0]}),
            "DBC": pd.DataFrame({"Date": dates[1:], "value": [2.0, 3.0, 4.0, 5.0]}),
        }

        class FakeYahoo:
            def get_historical_prices(self, ticker, start_date=None, end_date=None, frequency="1d"):
                if ticker not in yahoo_frames:
                    raise ValueError(f"no data for {ticker}")
                return yahoo_frames[ticker].copy()

        macro_start = dates.min() - pd.Timedelta(days=60)

        class FakeFred:
            def get_series(self, series_id, start_date=None, end_date=None, periods=None, frequency="M"):
                if series_id == "GDP":
                    return pd.DataFrame({
                        "Date": pd.to_datetime([macro_start]),
                        "GDP": [25000.0],
                    })
                if series_id == "CPIAUCSL":
                    return pd.DataFrame({
                        "Date": pd.to_datetime([macro_start, macro_start + pd.Timedelta(days=31)]),
                        "CPIAUCSL": [310.0, 311.0],
                    })
                return pd.DataFrame(columns=["Date", series_id])

        df = build_market_macro_export(
            years=1,
            yahoo_client=FakeYahoo(),
            fred_client=FakeFred(),
            yahoo_tickers=["CPER", "DBC"],
            fred_series=["GDP", "CPIAUCSL"],
        )

        assert list(df.columns) == export_column_names(["CPER", "DBC"], ["GDP", "CPIAUCSL"])
        assert len(df) == 5
        assert df["Date"].duplicated().sum() == 0
        assert df["CPER"].notna().all()
        assert pd.isna(df["DBC"].iloc[0])
        assert df["GDP"].notna().all()

    def test_date_column_is_iso_string(self):
        base = datetime.datetime.now() - datetime.timedelta(days=20)
        dates = pd.bdate_range(base, periods=3)
        yahoo_frames = {
            "CPER": pd.DataFrame({"Date": dates, "value": [1.0, 2.0, 3.0]}),
        }

        class FakeYahoo:
            def get_historical_prices(self, ticker, start_date=None, end_date=None, frequency="1d"):
                return yahoo_frames[ticker].copy()

        class FakeFred:
            def get_series(self, series_id, start_date=None, end_date=None, periods=None, frequency="M"):
                return pd.DataFrame({
                    "Date": pd.to_datetime([dates.min() - pd.Timedelta(days=60)]),
                    series_id: [1.0],
                })

        df = build_market_macro_export(
            years=1,
            yahoo_client=FakeYahoo(),
            fred_client=FakeFred(),
            yahoo_tickers=["CPER"],
            fred_series=["GDP"],
        )

        assert df["Date"].iloc[0].count("-") == 2
