"""
Volatility Table Data Assembly

Combines database data into display-ready DataFrame matching the spec's column layout.
This module assembles IV/RV data from the database and calculates Z-scores, percentiles,
and contrarian signal scores for the volatility table display component.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
from typing import Optional, List, Tuple
import logging

from .iv_db import IVDatabase
from .market_utils import get_previous_trading_day, get_approximate_trading_day
from .volatility_logging import get_volatility_logger, log_performance_metric

# Set up enhanced logging
logger = get_volatility_logger(__name__)

# ETF Universe constant from Phase 3
ETF_UNIVERSE = [
    {"ticker": "XLRE", "name": "Real Estate Sector SPDR ETF"},
    {"ticker": "XLF",  "name": "Financials Sector SPDR ETF"},
    {"ticker": "XLE",  "name": "Energy Sector SPDR ETF"},
    {"ticker": "XLC",  "name": "Communication Services SPDR ETF"},
    {"ticker": "XLK",  "name": "Technology Sector SPDR ETF"},
    {"ticker": "QQQ",  "name": "Power Shares QQQ Trust ETF"},
    {"ticker": "SPY",  "name": "SPDR S&P 500 Trust"},
    {"ticker": "XLV",  "name": "Health Care Sector SPDR ETF"},
    {"ticker": "XLB",  "name": "Materials Sector SPDR ETF"},
    {"ticker": "XLI",  "name": "Industrials Sector SPDR ETF"},
    {"ticker": "XLY",  "name": "Consumer Discretionary SPDR ETF"},
    {"ticker": "IWM",  "name": "I-Shares Russell 2000"},
    {"ticker": "XLU",  "name": "Utilities Sector SPDR ETF"},
    {"ticker": "XLP",  "name": "Consumer Staples Sector SPDR ETF"},
]

# Create lookup dict for ETF names
ETF_NAME_LOOKUP = {etf["ticker"]: etf["name"] for etf in ETF_UNIVERSE}

# Output schema for build_table()
TABLE_COLUMNS: List[str] = [
    'etf_name', 'ticker_display',
    'vol_valuation', 'contrarian_signal', 'contrarian_net_score',
    'contrarian_bull_score', 'contrarian_bear_score',
    'ytd_pct', 'ivol_rvol_current',
    'ivol_rvol_percentile_1y', 'ivol_rvol_percentile_3y',
    'iv_rv_spread', 'iv_rv_ratio',
    'prem_change_1w', 'prem_change_1m', 'premium_cs_rank',
    'ivol_prem_yesterday', 'ivol_prem_1w', 'ivol_prem_1m',
    'ttm_zscore', 'three_yr_zscore',
]


def _premium_from_iv_rv(row: pd.Series) -> Optional[float]:
    """Return IV/RV premium from valid IV and RV inputs, otherwise None."""
    try:
        iv = row.get('iv_30d')
        rv = row.get('rv_30d')
        if pd.isna(iv) or pd.isna(rv):
            return None

        iv = float(iv)
        rv = float(rv)
        if iv < 0.02 or iv > 3.0 or rv <= 0:
            return None

        return ((iv / rv) - 1.0) * 100.0
    except (TypeError, ValueError):
        return None


def _iv_rv_spread_and_ratio(row: pd.Series) -> Tuple[Optional[float], Optional[float]]:
    """Annualized IV minus RV in percentage points; IV/RV ratio."""
    try:
        iv = row.get('iv_30d')
        rv = row.get('rv_30d')
        if pd.isna(iv) or pd.isna(rv):
            return None, None
        iv, rv = float(iv), float(rv)
        if iv < 0.02 or iv > 3.0 or rv <= 0:
            return None, None
        spread = (iv - rv) * 100.0
        ratio = iv / rv
        return round(spread, 2), round(ratio, 3)
    except (TypeError, ValueError):
        return None, None


def _safe_float(val) -> Optional[float]:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _percentile_from_history(history: pd.DataFrame, window: int) -> Optional[float]:
    """
    Percentile rank (0-100) of current IV premium within trailing window.
    Higher = current premium is more extreme vs history.
    """
    try:
        if history is None or len(history) < 5:
            return None
        iv_premiums = history.apply(_premium_from_iv_rv, axis=1).dropna()
        if len(iv_premiums) < 5 or pd.isna(iv_premiums.iloc[0]):
            return None
        current = float(iv_premiums.iloc[0])
        hist = iv_premiums.iloc[1:min(window + 1, len(iv_premiums))].dropna()
        if len(hist) < 4:
            return None
        # Percentile: share of historical values strictly below current
        below = (hist < current).sum()
        pct = 100.0 * below / len(hist)
        return round(pct, 1)
    except Exception as e:
        logger.debug(f"Percentile calculation failed: {e}")
        return None


def _premium_change(current: Optional[float], past: Optional[float]) -> Optional[float]:
    c, p = _safe_float(current), _safe_float(past)
    if c is None or p is None:
        return None
    return round(c - p, 2)


def _score_high_percentile(pct: Optional[float]) -> float:
    """0-100: rewards high IV/RV percentile (fear / expensive options)."""
    if pct is None:
        return 0.0
    return float(min(100.0, max(0.0, (pct - 50.0) * 2.0)))


def _score_low_percentile(pct: Optional[float]) -> float:
    """0-100: rewards low IV/RV percentile (complacency)."""
    if pct is None:
        return 0.0
    return float(min(100.0, max(0.0, (50.0 - pct) * 2.0)))


def _score_high_zscore(z: Optional[float]) -> float:
    """0-100: extreme positive z-score (fear premium)."""
    z = _safe_float(z)
    if z is None or z <= 0:
        return 0.0
    return float(min(100.0, z * 50.0))


def _score_low_zscore(z: Optional[float]) -> float:
    """0-100: extreme negative z-score (complacency)."""
    z = _safe_float(z)
    if z is None or z >= 0:
        return 0.0
    return float(min(100.0, abs(z) * 50.0))


def _score_weak_ytd(ytd_pct: Optional[float]) -> float:
    """0-100: weak YTD as drawdown proxy for contrarian bullish."""
    y = _safe_float(ytd_pct)
    if y is None:
        return 0.0
    if y < -15:
        return 100.0
    if y < -5:
        return 70.0
    if y < 0:
        return 40.0
    return 0.0


def _score_strong_ytd(ytd_pct: Optional[float]) -> float:
    """0-100: extended uptrend for contrarian bearish."""
    y = _safe_float(ytd_pct)
    if y is None:
        return 0.0
    if y > 25:
        return 100.0
    if y > 15:
        return 70.0
    if y > 8:
        return 40.0
    return 0.0


def _score_premium_compression(
    current: Optional[float],
    week: Optional[float],
    month: Optional[float],
) -> float:
    """0-100: fear premium unwinding (falling premium)."""
    score = 0.0
    c, w, m = _safe_float(current), _safe_float(week), _safe_float(month)
    if c is not None and w is not None:
        if c < w - 5:
            score += 50.0
        elif c < w:
            score += 25.0
    if w is not None and m is not None:
        if w < m - 10:
            score += 50.0
        elif w < m:
            score += 25.0
    return min(100.0, score)


def _score_premium_expansion(
    current: Optional[float],
    week: Optional[float],
    month: Optional[float],
) -> float:
    """0-100: fear building (rising premium) — avoid early bottom-fishing."""
    score = 0.0
    c, w, m = _safe_float(current), _safe_float(week), _safe_float(month)
    if c is not None and w is not None:
        if c > w + 5:
            score += 50.0
        elif c > w:
            score += 25.0
    if w is not None and m is not None:
        if w > m + 10:
            score += 50.0
        elif w > m:
            score += 25.0
    return min(100.0, score)


def _score_cs_rank_bull(cs_rank: Optional[float], n_tickers: int) -> float:
    """0-100: highest cross-sectional premium ranks (panic relative to peers)."""
    if cs_rank is None or n_tickers <= 1:
        return 0.0
    # rank 1 = highest premium
    if cs_rank <= 3:
        return 100.0
    if cs_rank <= max(3, n_tickers * 0.25):
        return 60.0
    return 0.0


def _score_cs_rank_bear(cs_rank: Optional[float], n_tickers: int) -> float:
    """0-100: lowest cross-sectional premium (complacency vs peers)."""
    if cs_rank is None or n_tickers <= 1:
        return 0.0
    if cs_rank >= n_tickers - 2:
        return 100.0
    if cs_rank >= n_tickers * 0.75:
        return 60.0
    return 0.0


def _compute_vol_valuation(
    pct_1y: Optional[float],
    ttm_z: Optional[float],
) -> str:
    """Options expensive/cheap vs realized — independent of equity contrarian signal."""
    pct = _safe_float(pct_1y)
    z = _safe_float(ttm_z)
    expensive = (pct is not None and pct >= 75) or (z is not None and z >= 1.5)
    cheap = (pct is not None and pct <= 25) or (z is not None and z <= -1.5)
    if expensive and not cheap:
        return "Expensive"
    if cheap and not expensive:
        return "Cheap"
    return "Fair"


def _compute_contrarian_scores(
    pct_1y: Optional[float],
    ttm_z: Optional[float],
    ytd_pct: Optional[float],
    current: Optional[float],
    week: Optional[float],
    month: Optional[float],
    cs_rank: Optional[float],
    n_tickers: int,
) -> Tuple[float, float]:
    """
    Weighted contrarian bull/bear scores (0-100 each).
    Separates vol valuation context from equity contrarian bias.
    """
    bull = (
        0.30 * _score_high_percentile(pct_1y)
        + 0.20 * _score_high_zscore(ttm_z)
        + 0.15 * _score_weak_ytd(ytd_pct)
        + 0.15 * _score_premium_compression(current, week, month)
        + 0.10 * _score_cs_rank_bull(cs_rank, n_tickers)
        + 0.10 * _score_premium_compression(current, _safe_float(week), None)
    )
    bear = (
        0.30 * _score_low_percentile(pct_1y)
        + 0.20 * _score_low_zscore(ttm_z)
        + 0.15 * _score_strong_ytd(ytd_pct)
        + 0.15 * _score_premium_expansion(current, week, month)
        + 0.10 * _score_cs_rank_bear(cs_rank, n_tickers)
        + 0.10 * _score_premium_expansion(_safe_float(current), _safe_float(week), None)
    )
    return round(bull, 1), round(bear, 1)


def _contrarian_signal_label(bull: float, bear: float) -> Tuple[str, int]:
    """Net score and human-readable contrarian label."""
    net = int(round(bull - bear))
    if net >= 25:
        label = f"Contrarian Bullish ({net:+d})"
    elif net >= 10:
        label = f"Mild Bullish ({net:+d})"
    elif net <= -25:
        label = f"Contrarian Bearish ({net:+d})"
    elif net <= -10:
        label = f"Mild Bearish ({net:+d})"
    else:
        label = f"Neutral ({net:+d})"
    return label, net


class VolTableDataAssembler:
    """
    Assembles volatility table data from the database into a display-ready format.

    Produces DataFrame with vol valuation, contrarian scores, percentiles,
    spreads, premium changes, cross-sectional ranks, and historical z-scores.
    """

    def __init__(self, db: IVDatabase):
        """
        Initialize with database connection.

        Args:
            db: IVDatabase instance for data retrieval
        """
        self.db = db

    def build_table(self) -> pd.DataFrame:
        """
        Build the complete volatility table DataFrame.

        Returns:
            DataFrame with all required columns, sorted by contrarian_net_score desc
        """
        import time
        start_time = time.time()
        logger.info("Building volatility table data")

        universe_tickers = [etf["ticker"] for etf in ETF_UNIVERSE]
        latest_data = self.db.get_multiple_latest(universe_tickers)

        if latest_data.empty:
            logger.warning("No data available in database")
            return pd.DataFrame(columns=TABLE_COLUMNS)

        batch_start = time.time()
        all_history = self.db.get_multiple_history(universe_tickers, lookback_days=756)
        batch_duration = time.time() - batch_start

        log_performance_metric(
            "vol_table_batch_fetch",
            batch_duration,
            "seconds",
            context={'tickers': len(universe_tickers), 'history_records': len(all_history)},
        )

        history_by_ticker = {}
        if not all_history.empty:
            history_grouped = all_history.groupby('ticker')
            for ticker, group in history_grouped:
                history_by_ticker[ticker] = group.sort_values('date', ascending=False).reset_index(drop=True)

        rows = []
        for _, row in latest_data.iterrows():
            ticker = row['ticker']
            ticker_history = history_by_ticker.get(ticker, pd.DataFrame())
            table_row = self._build_ticker_row_optimized(row, ticker_history)
            if table_row is not None:
                rows.append(table_row)

        if not rows:
            logger.warning("No valid rows could be built")
            return pd.DataFrame(columns=TABLE_COLUMNS)

        df = pd.DataFrame(rows)
        df = self._apply_cross_sectional_ranks_and_scores(df)

        df = df.sort_values(
            ['contrarian_net_score', 'contrarian_bull_score', 'ytd_pct'],
            ascending=[False, False, False],
        ).reset_index(drop=True)

        total_duration = time.time() - start_time
        log_performance_metric(
            "vol_table_build_total",
            total_duration,
            "seconds",
            context={'rows_built': len(df), 'tickers_available': len(latest_data)},
        )

        logger.info(
            f"Built volatility table with {len(df)} rows in {total_duration:.2f}s"
        )
        return df

    def _apply_cross_sectional_ranks_and_scores(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add cross-sectional premium rank and finalize contrarian scores."""
        n = len(df)
        if n == 0:
            return df

        # Rank 1 = highest IV/RV premium today
        valid = df['ivol_rvol_current'].notna()
        df['premium_cs_rank'] = np.nan
        if valid.any():
            df.loc[valid, 'premium_cs_rank'] = (
                df.loc[valid, 'ivol_rvol_current']
                .rank(ascending=False, method='min')
                .astype(float)
            )

        bull_scores = []
        bear_scores = []
        signals = []
        nets = []
        valuations = []

        for _, row in df.iterrows():
            cs_rank = _safe_float(row.get('premium_cs_rank'))
            bull, bear = _compute_contrarian_scores(
                pct_1y=row.get('ivol_rvol_percentile_1y'),
                ttm_z=row.get('ttm_zscore'),
                ytd_pct=row.get('ytd_pct'),
                current=row.get('ivol_rvol_current'),
                week=row.get('ivol_prem_1w'),
                month=row.get('ivol_prem_1m'),
                cs_rank=cs_rank,
                n_tickers=n,
            )
            label, net = _contrarian_signal_label(bull, bear)
            bull_scores.append(bull)
            bear_scores.append(bear)
            signals.append(label)
            nets.append(net)
            valuations.append(
                _compute_vol_valuation(
                    row.get('ivol_rvol_percentile_1y'),
                    row.get('ttm_zscore'),
                )
            )

        df['contrarian_bull_score'] = bull_scores
        df['contrarian_bear_score'] = bear_scores
        df['contrarian_signal'] = signals
        df['contrarian_net_score'] = nets
        df['vol_valuation'] = valuations
        return df

    def _build_ticker_row_optimized(
        self, latest_row: pd.Series, history: pd.DataFrame
    ) -> Optional[dict]:
        """
        Build a single row for the volatility table using pre-fetched historical data.
        Contrarian scores are finalized in _apply_cross_sectional_ranks_and_scores.
        """
        ticker = latest_row['ticker']

        if ticker not in ETF_NAME_LOOKUP:
            return None

        current = _premium_from_iv_rv(latest_row)
        yesterday = self._get_historical_premium_from_data(history, 1)
        week = self._get_historical_premium_from_data(history, 5)
        month = self._get_historical_premium_from_data(history, 21)
        spread, ratio = _iv_rv_spread_and_ratio(latest_row)
        pct_1y = _percentile_from_history(history, 252)
        pct_3y = _percentile_from_history(history, 756)
        ttm_z = self._calculate_zscore_from_history(history, 252)
        three_yr_z = self._calculate_zscore_from_history(history, 756)
        ytd_pct = latest_row.get('ytd_return', 0.0) * 100

        return {
            'etf_name': ETF_NAME_LOOKUP[ticker],
            'ticker_display': ticker,
            'vol_valuation': _compute_vol_valuation(pct_1y, ttm_z),
            'contrarian_signal': 'Neutral (+0)',
            'contrarian_net_score': 0,
            'contrarian_bull_score': 0.0,
            'contrarian_bear_score': 0.0,
            'ytd_pct': ytd_pct,
            'ivol_rvol_current': current,
            'ivol_rvol_percentile_1y': pct_1y,
            'ivol_rvol_percentile_3y': pct_3y,
            'iv_rv_spread': spread,
            'iv_rv_ratio': ratio,
            'prem_change_1w': _premium_change(current, week),
            'prem_change_1m': _premium_change(current, month),
            'premium_cs_rank': None,
            'ivol_prem_yesterday': yesterday,
            'ivol_prem_1w': week,
            'ivol_prem_1m': month,
            'ttm_zscore': ttm_z,
            'three_yr_zscore': three_yr_z,
        }

    def _get_historical_premium_from_data(
        self, history_df: pd.DataFrame, days_ago: int
    ) -> Optional[float]:
        """
        Get IV premium from N trading days ago using pre-fetched historical data.

        Uses calendar trading-day targets (not raw row offsets) so DB gaps do not
        shift "yesterday" / "1W" / "1M" columns.
        """
        try:
            if history_df is None or history_df.empty:
                return None

            target_date = get_previous_trading_day(date.today(), days_ago)
            hist = history_df.copy()
            hist['date'] = pd.to_datetime(hist['date']).dt.date

            exact = hist[hist['date'] == target_date]
            if not exact.empty:
                return _premium_from_iv_rv(exact.iloc[0])

            prior = hist[hist['date'] <= target_date]
            if prior.empty:
                return None
            return _premium_from_iv_rv(prior.iloc[0])

        except Exception as e:
            logger.debug(f"Could not get historical premium -{days_ago}d: {e}")
            return None

    def _build_ticker_row(self, latest_row: pd.Series) -> Optional[dict]:
        """Build a single row (legacy path with per-ticker DB fetch)."""
        ticker = latest_row['ticker']

        if ticker not in ETF_NAME_LOOKUP:
            return None

        history = self.db.get_history(ticker, lookback_days=756)
        return self._build_ticker_row_optimized(latest_row, history.sort_values('date', ascending=False))

    def _get_historical_premium(self, ticker: str, days_ago: int) -> Optional[float]:
        """Get IV premium from N trading days ago."""
        try:
            today = date.today()
            target_date = get_previous_trading_day(today, days_ago)

            snapshot = self.db.get_snapshot(target_date.isoformat(), ticker)
            if snapshot:
                return _premium_from_iv_rv(pd.Series(snapshot))

            approximate_date = get_approximate_trading_day(today, days_ago)
            snapshot = self.db.get_snapshot(approximate_date.isoformat(), ticker)
            if snapshot:
                return _premium_from_iv_rv(pd.Series(snapshot))

            history = self.db.get_history(ticker, lookback_days=days_ago + 10)
            if len(history) > days_ago:
                target_idx = min(days_ago - 1, len(history) - 1)
                return _premium_from_iv_rv(history.iloc[-(target_idx + 1)])
            elif len(history) > 0 and days_ago == 1:
                return None

            return None

        except Exception as e:
            logger.debug(f"Could not get historical premium for {ticker} -{days_ago}d: {e}")
            return None

    def _calculate_zscore_from_history(
        self, history: pd.DataFrame, window: int
    ) -> Optional[float]:
        """Calculate Z-score of current IV premium relative to historical window."""
        try:
            if len(history) < 5:
                return None

            iv_premiums = history.apply(_premium_from_iv_rv, axis=1)
            if iv_premiums.empty or pd.isna(iv_premiums.iloc[0]):
                return None

            valid_premiums = iv_premiums.dropna()
            if len(valid_premiums) < 5:
                return None

            current_premium = iv_premiums.iloc[0]
            historical_window = iv_premiums.iloc[1:min(window + 1, len(iv_premiums))].dropna()

            if len(historical_window) < 4:
                return None

            mean = historical_window.mean()
            std = historical_window.std()

            if std == 0 or pd.isna(std) or std < 0.01:
                return 0.0

            zscore = (current_premium - mean) / std
            return round(zscore, 2)

        except Exception as e:
            logger.debug(f"Could not calculate Z-score for window {window}: {e}")
            return None

    def get_data_freshness_info(self) -> dict:
        """Get information about data freshness and availability."""
        latest_data = self.db.get_all_latest()

        if latest_data.empty:
            return {
                'has_data': False,
                'ticker_count': 0,
                'latest_date': None,
                'days_old': None,
            }

        latest_date_str = latest_data['date'].max()
        if hasattr(latest_date_str, 'date'):
            latest_date = latest_date_str.date()
        else:
            latest_date = datetime.strptime(str(latest_date_str), '%Y-%m-%d').date()
        days_old = (datetime.now().date() - latest_date).days

        universe_tickers = [etf["ticker"] for etf in ETF_UNIVERSE]
        available_tickers = latest_data[latest_data['ticker'].isin(universe_tickers)]

        return {
            'has_data': True,
            'ticker_count': len(available_tickers),
            'universe_size': len(universe_tickers),
            'latest_date': latest_date_str,
            'days_old': days_old,
            'coverage_pct': len(available_tickers) / len(universe_tickers) * 100,
        }
