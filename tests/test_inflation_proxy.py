"""Tests for standalone inflation proxy (Macro Dashboard)."""

import numpy as np
import pandas as pd
import pytest

from data.inflation_proxy import build_inflation_proxy, build_pair_zscore
from data.processing import log_ratio_delta_zscore
from src.config.inflation_proxy import INFLATION_PROXY_PAIRS, InflationProxyPair


def _synthetic_ticker_data(n: int = 400, seed: int = 0) -> dict[str, pd.Series]:
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2020-01-01", periods=n)
    return {
        "DBC": pd.Series(np.exp(rng.normal(0.001, 0.01, n).cumsum()), index=idx),
        "CPER": pd.Series(np.exp(rng.normal(0.0008, 0.009, n).cumsum()), index=idx),
        "XLV": pd.Series(np.exp(rng.normal(0.0006, 0.008, n).cumsum()), index=idx),
        "QQQ": pd.Series(np.exp(rng.normal(0.0012, 0.012, n).cumsum()), index=idx),
    }


class TestInflationProxy:
    def test_build_pair_zscore_returns_series(self):
        data = _synthetic_ticker_data()
        pair = InflationProxyPair("DBC", "CPER", 0.50)
        z = build_pair_zscore(data, pair)
        assert len(z) == 400
        assert z.name == "DBC_CPER"

    def test_composite_weights_sum_to_one(self):
        data = _synthetic_ticker_data()
        composite, pair_z = build_inflation_proxy(data)
        assert len(pair_z) == len(INFLATION_PROXY_PAIRS)
        assert composite.dropna().shape[0] > 0
        assert np.isclose(sum(p.weight for p in INFLATION_PROXY_PAIRS), 1.0)

    def test_missing_ticker_raises(self):
        data = _synthetic_ticker_data()
        del data["QQQ"]
        with pytest.raises(ValueError, match="Missing tickers"):
            build_inflation_proxy(data)

    def test_log_ratio_delta_zscore_matches_processing(self):
        data = _synthetic_ticker_data(n=300)
        z1 = build_pair_zscore(data, InflationProxyPair("XLV", "QQQ", 0.50))
        merged = pd.DataFrame({"XLV": data["XLV"], "QQQ": data["QQQ"]}).dropna()
        z2 = log_ratio_delta_zscore(merged["XLV"], merged["QQQ"])
        pd.testing.assert_series_equal(z1, z2.rename("XLV_QQQ"))
