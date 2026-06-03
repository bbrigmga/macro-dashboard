"""
Tests for IV/RV contrarian signal backtest module.
"""

import pytest
import pandas as pd
import numpy as np
from data.iv_db import IVDatabase
from data.vol_signal_backtest import (
    build_signal_events,
    summarize_bucket_performance,
    summarize_extreme_premium_performance,
    signal_bucket_from_net,
    information_coefficient,
    run_vol_signal_backtest,
    format_backtest_summary_table,
    _forward_return_pct,
    _forward_max_drawdown_pct,
    _forward_realized_vol,
)


@pytest.fixture
def memory_db():
    db = IVDatabase(":memory:")
    yield db
    db.close()


def _seed_ticker_history(
    db: IVDatabase,
    ticker: str,
    n_trading_days: int = 120,
    base_iv: float = 0.18,
):
    """Insert synthetic business-day rows (enough for 63D forward horizon)."""
    dates = pd.bdate_range(start="2024-06-01", periods=n_trading_days)
    for i, d in enumerate(dates):
        iv = base_iv + 0.04 * np.sin(i * 0.15)
        rv = 0.14 + 0.02 * np.sin(i * 0.1)
        price = 100.0 + i * 0.2 + np.random.default_rng(i).normal(0, 0.5)
        prem = ((iv / rv) - 1.0) * 100.0
        db.upsert_daily(
            date=d.date().isoformat(),
            ticker=ticker,
            close_price=float(price),
            iv_30d=float(iv),
            rv_30d=float(rv),
            iv_premium=float(prem),
            ytd_return=float(0.02 + i * 0.001),
        )


@pytest.fixture
def seeded_db(memory_db):
    for ticker in ["SPY", "QQQ", "XLF"]:
        _seed_ticker_history(memory_db, ticker, n_trading_days=120)
    return memory_db


class TestSignalBucket:
    def test_signal_bucket_thresholds(self):
        assert signal_bucket_from_net(30) == "bull_strong"
        assert signal_bucket_from_net(15) == "bull_mild"
        assert signal_bucket_from_net(-30) == "bear_strong"
        assert signal_bucket_from_net(-12) == "bear_mild"
        assert signal_bucket_from_net(0) == "neutral"


class TestForwardMetrics:
    def test_forward_return(self):
        prices = pd.Series([100.0, 101.0, 102.0, 103.0, 104.0, 105.0])
        assert _forward_return_pct(prices, 0, 5) == pytest.approx(5.0, rel=0.01)

    def test_forward_max_drawdown(self):
        prices = pd.Series([100.0, 105.0, 90.0, 95.0])
        dd = _forward_max_drawdown_pct(prices, 0, 3)
        assert dd is not None
        assert dd < 0

    def test_forward_realized_vol(self):
        prices = pd.Series(100.0 + np.cumsum(np.random.default_rng(0).normal(0, 0.5, 30)))
        rv = _forward_realized_vol(prices, 0, 21)
        assert rv is not None
        assert rv > 0


class TestBuildSignalEvents:
    def test_build_events_from_panel(self, seeded_db):
        panel = seeded_db.get_panel_history(["SPY", "QQQ", "XLF"])
        events = build_signal_events(panel)
        assert not events.empty
        assert "fwd_return_21d" in events.columns
        assert "contrarian_net_score" in events.columns
        assert "signal_bucket" in events.columns
        assert events["ticker"].isin(["SPY", "QQQ", "XLF"]).all()

    def test_forward_columns_populated(self, seeded_db):
        panel = seeded_db.get_panel_history(["SPY"])
        events = build_signal_events(panel, tickers=["SPY"])
        valid = events["fwd_return_21d"].dropna()
        assert len(valid) > 0


class TestSummarize:
    def test_summarize_by_bucket(self, seeded_db):
        result = run_vol_signal_backtest(db=seeded_db, close_db=False)
        events = result["events"]
        assert not events.empty
        summary = summarize_bucket_performance(events, horizon=21)
        assert not summary.empty
        assert "hit_rate" in summary.columns
        assert "n_obs" in summary.columns
        assert summary["n_obs"].sum() > 0

    def test_extreme_premium_summary(self, seeded_db):
        result = run_vol_signal_backtest(db=seeded_db, close_db=False)
        extreme = summarize_extreme_premium_performance(result["events"], horizon=21)
        # May be empty if no extremes in synthetic data — at least should not crash
        assert isinstance(extreme, pd.DataFrame)

    def test_information_coefficient(self, seeded_db):
        result = run_vol_signal_backtest(db=seeded_db, close_db=False)
        ic = information_coefficient(result["events"], horizon=21)
        # May be None with short/random data; just ensure callable
        assert ic is None or isinstance(ic, float)

    def test_format_summary_table(self, seeded_db):
        result = run_vol_signal_backtest(db=seeded_db, close_db=False)
        table = format_backtest_summary_table(result, horizon=21)
        assert isinstance(table, pd.DataFrame)


class TestRunPipeline:
    def test_run_vol_signal_backtest_metadata(self, seeded_db):
        result = run_vol_signal_backtest(db=seeded_db, close_db=False)
        meta = result["metadata"]
        assert meta["n_events"] > 0
        assert meta["date_start"] is not None
        assert "SPY" in meta["tickers"]

    def test_empty_panel(self, memory_db):
        result = run_vol_signal_backtest(db=memory_db, close_db=False)
        assert result["metadata"]["n_events"] == 0

    def test_single_ticker_filter(self, seeded_db):
        result = run_vol_signal_backtest(db=seeded_db, tickers=["SPY"], close_db=False)
        assert set(result["events"]["ticker"].unique()) == {"SPY"}
