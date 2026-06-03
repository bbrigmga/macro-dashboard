"""Tests for IV backfill helpers."""
from datetime import date

import pandas as pd
import pytest

from data.iv_scraper import IVScraper


class _FakeDB:
    def __init__(self, history: pd.DataFrame):
        self._history = history

    def get_history(self, ticker: str, lookback_days: int = 900) -> pd.DataFrame:
        return self._history

    def get_snapshot(self, date: str, ticker: str):
        return None

    def upsert_daily(self, **kwargs):
        pass


def test_estimate_iv_interpolated_between_neighbors():
    history = pd.DataFrame({
        "date": ["2026-06-01", "2026-06-03"],
        "iv_30d": [0.20, 0.30],
        "ticker": ["SPY", "SPY"],
    })
    scraper = IVScraper(_FakeDB(history))
    iv, method = scraper._estimate_iv_from_neighbors("SPY", date(2026, 6, 2))
    assert method == "interpolated"
    assert iv == pytest.approx(0.25)


def test_estimate_iv_uses_prior_when_no_later_neighbor():
    history = pd.DataFrame({
        "date": ["2026-06-01"],
        "iv_30d": [0.18],
        "ticker": ["SPY"],
    })
    scraper = IVScraper(_FakeDB(history))
    iv, method = scraper._estimate_iv_from_neighbors("SPY", date(2026, 6, 2))
    assert method == "prior_day"
    assert iv == pytest.approx(0.18)
