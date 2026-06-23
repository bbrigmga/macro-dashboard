"""Tests for standalone GDP growth proxy (Macro Dashboard)."""

import numpy as np
import pandas as pd
import pytest

from data.growth_proxy import build_gdp_growth_proxy, build_pair_zscore
from data.processing import log_ratio_delta_zscore
from src.config.growth_proxy import GROWTH_PROXY_PAIRS, GrowthProxyPair, DELTA_DAYS, FORECAST_HORIZON_DAYS


def _synthetic_ticker_data(n: int = 400, seed: int = 0) -> dict[str, pd.Series]:
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2020-01-01", periods=n)
    return {
        "CPER": pd.Series(np.exp(rng.normal(0.001, 0.01, n).cumsum()), index=idx),
        "GLD": pd.Series(np.exp(rng.normal(0.0005, 0.008, n).cumsum()), index=idx),
        "XHB": pd.Series(np.exp(rng.normal(0.0012, 0.012, n).cumsum()), index=idx),
        "IWM": pd.Series(np.exp(rng.normal(0.0008, 0.01, n).cumsum()), index=idx),
        "EFA": pd.Series(np.exp(rng.normal(0.0007, 0.009, n).cumsum()), index=idx),
        "SLV": pd.Series(np.exp(rng.normal(0.0006, 0.011, n).cumsum()), index=idx),
        "FXI": pd.Series(np.exp(rng.normal(0.0009, 0.013, n).cumsum()), index=idx),
    }


class TestGdpGrowthProxy:
    def test_build_pair_zscore_returns_series(self):
        data = _synthetic_ticker_data()
        pair = GrowthProxyPair("CPER", "GLD", 0.25)
        z = build_pair_zscore(data, pair)
        assert len(z) == 400
        assert z.name == "CPER_GLD"

    def test_composite_weights_sum_to_one(self):
        data = _synthetic_ticker_data()
        composite, pair_z = build_gdp_growth_proxy(data)
        assert len(pair_z) == len(GROWTH_PROXY_PAIRS)
        assert composite.dropna().shape[0] > 0
        assert np.isclose(sum(p.weight for p in GROWTH_PROXY_PAIRS), 1.0)

    def test_missing_ticker_raises(self):
        data = _synthetic_ticker_data()
        del data["FXI"]
        with pytest.raises(ValueError, match="Missing tickers"):
            build_gdp_growth_proxy(data)

    def test_log_ratio_delta_zscore_matches_processing(self):
        data = _synthetic_ticker_data(n=300)
        z1 = build_pair_zscore(data, GrowthProxyPair("CPER", "GLD", 0.25))
        merged = pd.DataFrame({"CPER": data["CPER"], "GLD": data["GLD"]}).dropna()
        z2 = log_ratio_delta_zscore(merged["CPER"], merged["GLD"])
        pd.testing.assert_series_equal(z1, z2.rename("CPER_GLD"))


def test_forecast_horizon_matches_proxy_delta():
    assert FORECAST_HORIZON_DAYS == DELTA_DAYS == 63
