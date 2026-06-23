"""
Build aligned daily export of ETF prices and FRED macro series for external analysis.
"""

from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING

import pandas as pd

from data.fred_client import FredClient
from data.processing import align_series_asof
from data.yahoo_client import YahooClient
from src.config.growth_proxy import GROWTH_PROXY_REQUIRED_TICKERS
from src.config.indicator_registry import INDICATOR_REGISTRY
from src.config.inflation_proxy import INFLATION_PROXY_REQUIRED_TICKERS

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Korea exports fallback series (same candidates as indicators.py)
_EXTRA_FRED_SERIES = ["XTEXVA01KRA667S", "CPIAUCSL"]

FRED_FREQUENCY_HINTS: dict[str, str] = {
    "ICSA": "W",
    "BAMLH0A0HYM2": "D",
    "DGS10": "D",
    "T10Y2Y": "D",
    "GDP": "Q",
    "B235RC1Q027SBEA": "Q",
    "WALCL": "W",
    "RRPONTTLD": "D",
    "CURRCIR": "W",
}


def collect_yahoo_tickers() -> list[str]:
    """All Yahoo tickers used by the dashboard and regime proxy configs."""
    tickers: set[str] = set()
    for config in INDICATOR_REGISTRY.values():
        if config.yahoo_series:
            tickers.update(config.yahoo_series)
    tickers.update(GROWTH_PROXY_REQUIRED_TICKERS)
    tickers.update(INFLATION_PROXY_REQUIRED_TICKERS)
    return sorted(tickers)


def collect_fred_series() -> list[str]:
    """All FRED series referenced by dashboard indicators plus export extras."""
    series: set[str] = set(_EXTRA_FRED_SERIES)
    for config in INDICATOR_REGISTRY.values():
        series.update(config.fred_series)
    return sorted(s for s in series if s)


def export_column_names(
    yahoo_tickers: list[str] | None = None,
    fred_series: list[str] | None = None,
) -> list[str]:
    """Expected CSV columns for a full export."""
    yahoo = yahoo_tickers or collect_yahoo_tickers()
    fred = fred_series or collect_fred_series()
    return ["Date", *yahoo, *fred]


def build_market_macro_export(
    years: int = 3,
    yahoo_client: YahooClient | None = None,
    fred_client: FredClient | None = None,
    yahoo_tickers: list[str] | None = None,
    fred_series: list[str] | None = None,
) -> pd.DataFrame:
    """
    Fetch ETF daily closes and FRED series, aligned to a single Date column.

    ETF columns hold the close on each trading day (outer-joined calendar).
    FRED columns use backward as-of alignment so each row shows the last published
    value on or before that date.
    """
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=int(years * 365.25) + 30)
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = (end_date + datetime.timedelta(days=1)).strftime("%Y-%m-%d")

    yahoo = yahoo_client or YahooClient()
    fred = fred_client or FredClient()
    tickers = yahoo_tickers or collect_yahoo_tickers()
    series_ids = fred_series or collect_fred_series()

    series_map: dict[str, pd.Series] = {}
    for ticker in tickers:
        try:
            df = yahoo.get_historical_prices(
                ticker=ticker,
                start_date=start_str,
                end_date=end_str,
                frequency="1d",
            )
            if df is None or df.empty:
                logger.warning("Skipping %s: no Yahoo data", ticker)
                continue
            s = df.set_index(pd.to_datetime(df["Date"]).dt.normalize())["value"]
            s = s[~s.index.duplicated(keep="last")]
            series_map[ticker] = s.rename(ticker)
        except Exception as exc:
            logger.warning("Skipping %s: %s", ticker, exc)

    if not series_map:
        return pd.DataFrame(columns=export_column_names(tickers, series_ids))

    merged = pd.DataFrame(series_map).sort_index()
    merged = merged[merged.index >= pd.Timestamp(start_date)].copy()
    merged = merged.reset_index().rename(columns={"index": "Date"})

    if merged.empty:
        return pd.DataFrame(columns=export_column_names(tickers, series_ids))

    for series_id in series_ids:
        freq = FRED_FREQUENCY_HINTS.get(series_id, "M")
        try:
            fred_df = fred.get_series(
                series_id,
                start_date=start_str,
                end_date=end_str,
                frequency=freq,
            )
            if fred_df is None or fred_df.empty:
                logger.warning("Skipping FRED %s: empty response", series_id)
                continue
            value_col = series_id if series_id in fred_df.columns else next(
                (c for c in fred_df.columns if c != "Date"), None
            )
            if value_col is None:
                logger.warning("Skipping FRED %s: no value column", series_id)
                continue
            macro = pd.to_numeric(
                fred_df.set_index("Date")[value_col],
                errors="coerce",
            )
            macro.index = pd.to_datetime(macro.index).tz_localize(None)
            merged[series_id] = align_series_asof(merged["Date"], macro, series_id)
        except Exception as exc:
            logger.warning("Skipping FRED %s: %s", series_id, exc)

    export_cols = ["Date"] + [t for t in tickers if t in merged.columns]
    export_cols += [s for s in series_ids if s in merged.columns]
    export = merged[export_cols].copy()
    export["Date"] = export["Date"].dt.strftime("%Y-%m-%d")
    return export


def market_macro_export_csv_bytes(
    years: int = 3,
    yahoo_client: YahooClient | None = None,
    fred_client: FredClient | None = None,
) -> bytes:
    """Return UTF-8 CSV bytes for the aligned market/macro export."""
    df = build_market_macro_export(
        years=years,
        yahoo_client=yahoo_client,
        fred_client=fred_client,
    )
    if df.empty:
        return b""
    return df.to_csv(index=False).encode("utf-8")
