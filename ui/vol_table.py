"""
Volatility Table UI Component
Renders the implied vs realized volatility heatmap table for Streamlit display
"""

import pandas as pd
import streamlit as st
from pandas.io.formats.style import Styler
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def clear_vol_table_cache() -> None:
    """Clear cached volatility table so UI reflects latest database state."""
    _get_cached_vol_table_data.clear()


def reload_vol_table_caches() -> None:
    """
    Clear all caches that can serve stale vol table rows (Streamlit + indicator service).
    """
    clear_vol_table_cache()
    try:
        from src.services.indicator_service import IndicatorService

        service = IndicatorService()
        cache_key = service._get_cache_key("implied_realized_vol")
        service.cache_manager.invalidate(cache_key)
        service.invalidate_indicator_cache("implied_realized_vol")
    except Exception as e:
        logger.warning("Could not invalidate implied_realized_vol indicator cache: %s", e)


def _historical_premium_columns_empty(data: pd.DataFrame) -> bool:
    """True when yesterday / 1W / 1M premium columns have no usable values."""
    hist_cols = ["ivol_prem_yesterday", "ivol_prem_1w", "ivol_prem_1m"]
    if not all(c in data.columns for c in hist_cols):
        return True
    subset = data[hist_cols]
    return subset.isna().all().all() or (subset.astype(str) == "None").all().all()


@st.cache_data(ttl=3600, show_spinner=False)  # Cache for 1 hour
def _get_cached_vol_table_data() -> Optional[pd.DataFrame]:
    """
    Get volatility table data with caching to improve performance.

    Returns:
        Cached DataFrame or None if error
    """
    try:
        from data.iv_db import IVDatabase
        from data.vol_table_data import VolTableDataAssembler

        db = IVDatabase()
        assembler = VolTableDataAssembler(db)
        return assembler.build_table()

    except Exception as e:
        logger.error(f"Error fetching volatility table data: {e}")
        return None


def render_vol_table(data: Optional[pd.DataFrame] = None) -> None:
    """
    Render the styled volatility heatmap table in Streamlit.

    Args:
        data: DataFrame from VolTableDataAssembler.build_table()
    """
    st.subheader("📊 Implied vs Realized Volatility")
    st.caption(
        "30-day ATM implied vol vs 30-day realized vol. "
        "**Vol Valuation** = options rich/cheap vs RV; "
        "**Contrarian Signal** = fear/complacency setup with trend filters (not a buy/sell model)."
    )

    if data is None:
        with st.spinner("Loading volatility data..."):
            data = _get_cached_vol_table_data()

    if data is not None and not data.empty and _historical_premium_columns_empty(data):
        st.warning(
            "Historical IV premium columns look empty — usually stale cached table data, "
            "not missing database rows."
        )
        if st.button(
            "Reload Vol Table from Database",
            key="reload_vol_table_from_db",
            help="Clears vol table caches and rebuilds from iv_data.db (does not scrape Yahoo)",
        ):
            reload_vol_table_caches()
            st.rerun()

    if data is None or data.empty:
        st.info(
            "🔄 No volatility data available. Run the daily scraper first:\n\n"
            "```bash\n"
            "python -m data.iv_scraper\n"
            "```"
        )
        return

    expected_tickers = 14
    if len(data) < expected_tickers:
        st.warning(
            f"⚠️ Showing partial data ({len(data)}/{expected_tickers} tickers). "
            "Some ETFs may be missing options data or have scraping issues."
        )

    try:
        styled_df = _format_and_style_table(data)

        st.dataframe(
            styled_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "ETF Name": st.column_config.TextColumn(width="medium"),
                "Ticker": st.column_config.TextColumn(width="small"),
                "Vol Valuation": st.column_config.TextColumn(
                    width="small",
                    help="Are options expensive or cheap vs recent realized vol? (percentile + z-score)",
                ),
                "Contrarian Signal": st.column_config.TextColumn(
                    width="medium",
                    help="Contrarian equity bias from IV/RV extremity, YTD trend, premium changes, "
                         "and cross-sectional rank. High fear + unwinding premium → bullish; "
                         "complacency + rising premium → bearish.",
                ),
                "YTD %": st.column_config.NumberColumn(width="small"),
                "IVOL/RVOL Current": st.column_config.NumberColumn(width="medium"),
                "IVOL Prem % Yesterday": st.column_config.NumberColumn(width="medium"),
                "IVOL Prem % 1W Ago": st.column_config.NumberColumn(width="medium"),
                "IVOL Prem % 1M Ago": st.column_config.NumberColumn(width="medium"),
                "TTM Z-Score": st.column_config.NumberColumn(width="small"),
                "3Yr Z-Score": st.column_config.NumberColumn(width="small"),
                "Prem %ile 1Y": st.column_config.NumberColumn(width="small"),
                "Prem %ile 3Y": st.column_config.NumberColumn(width="small"),
                "IV−RV Spread": st.column_config.NumberColumn(width="small"),
                "IV/RV Ratio": st.column_config.NumberColumn(width="small"),
                "Prem Δ 1W": st.column_config.NumberColumn(width="small"),
                "Prem Δ 1M": st.column_config.NumberColumn(width="small"),
                "CS Rank": st.column_config.NumberColumn(width="small"),
                "Bull Score": st.column_config.NumberColumn(width="small"),
                "Bear Score": st.column_config.NumberColumn(width="small"),
            },
        )

        _render_signal_backtest_panel()

        _render_data_freshness_info(data)

    except Exception as e:
        logger.error(f"Error rendering volatility table: {e}")
        st.error(f"Error rendering volatility table: {e}")


def _format_and_style_table(data: pd.DataFrame) -> Styler:
    """
    Format and apply conditional styling to the volatility table.

    Args:
        data: Raw DataFrame from VolTableDataAssembler

    Returns:
        Styled DataFrame ready for Streamlit display
    """
    df = data.copy()

    column_map = {
        "etf_name": "ETF Name",
        "ticker_display": "Ticker",
        "vol_valuation": "Vol Valuation",
        "contrarian_signal": "Contrarian Signal",
        "ytd_pct": "YTD %",
        "ivol_rvol_current": "IVOL/RVOL Current",
        "ivol_prem_yesterday": "IVOL Prem % Yesterday",
        "ivol_prem_1w": "IVOL Prem % 1W Ago",
        "ivol_prem_1m": "IVOL Prem % 1M Ago",
        "ttm_zscore": "TTM Z-Score",
        "three_yr_zscore": "3Yr Z-Score",
        "ivol_rvol_percentile_1y": "Prem %ile 1Y",
        "ivol_rvol_percentile_3y": "Prem %ile 3Y",
        "iv_rv_spread": "IV−RV Spread",
        "iv_rv_ratio": "IV/RV Ratio",
        "prem_change_1w": "Prem Δ 1W",
        "prem_change_1m": "Prem Δ 1M",
        "premium_cs_rank": "CS Rank",
        "contrarian_bull_score": "Bull Score",
        "contrarian_bear_score": "Bear Score",
    }

    df = df.rename(columns=column_map)

    main_display = [
        "ETF Name", "Ticker", "Vol Valuation", "Contrarian Signal",
        "YTD %", "IVOL/RVOL Current",
        "IVOL Prem % Yesterday", "IVOL Prem % 1W Ago", "IVOL Prem % 1M Ago",
        "TTM Z-Score", "3Yr Z-Score",
    ]
    detail_display = [
        "Prem %ile 1Y", "Prem %ile 3Y", "IV−RV Spread", "IV/RV Ratio",
        "Prem Δ 1W", "Prem Δ 1M", "CS Rank", "Bull Score", "Bear Score",
    ]

    cols = [c for c in main_display + detail_display if c in df.columns]
    df = df[cols]

    percentage_cols = [
        "YTD %", "IVOL/RVOL Current",
        "IVOL Prem % Yesterday", "IVOL Prem % 1W Ago", "IVOL Prem % 1M Ago",
        "Prem Δ 1W", "Prem Δ 1M",
    ]
    percentage_cols = [c for c in percentage_cols if c in df.columns]
    zscore_cols = [c for c in ["TTM Z-Score", "3Yr Z-Score"] if c in df.columns]
    percentile_cols = [c for c in ["Prem %ile 1Y", "Prem %ile 3Y"] if c in df.columns]
    score_cols = [c for c in ["Bull Score", "Bear Score"] if c in df.columns]

    def rdylgn_css(val, vmin, vmax):
        try:
            v = float(val)
        except (TypeError, ValueError):
            return ""
        if vmax == vmin:
            return ""
        t = max(0.0, min(1.0, (v - vmin) / (vmax - vmin)))
        if t < 0.5:
            r, g = 220, int(220 * (t / 0.5))
        else:
            r, g = int(220 * (1.0 - (t - 0.5) / 0.5)), 200
        return f"background-color: rgb({r},{g},0); color: #000"

    def pct_color(col):
        return [rdylgn_css(v, -30, 50) for v in col]

    def zscore_color(col):
        return [rdylgn_css(v, -2, 2) for v in col]

    def percentile_color(col):
        return [rdylgn_css(v, 0, 100) for v in col]

    def contrarian_signal_color(col):
        styles = []
        for val in col:
            s = str(val)
            if "Bullish" in s:
                styles.append("background-color: #1e4d1e; color: #b6ffb6; font-weight: bold")
            elif "Bearish" in s:
                styles.append("background-color: #4d1e1e; color: #ffb6b6; font-weight: bold")
            else:
                styles.append("background-color: #4a4a00; color: #ffffb6; font-weight: bold")
        return styles

    def vol_valuation_color(col):
        styles = []
        for val in col:
            s = str(val)
            if s == "Expensive":
                styles.append("background-color: #4d2e1e; color: #ffd4b6")
            elif s == "Cheap":
                styles.append("background-color: #1e3d4d; color: #b6e6ff")
            else:
                styles.append("background-color: #333; color: #ddd")
        return styles

    styled = df.style
    for col in percentage_cols:
        styled = styled.apply(pct_color, subset=[col])
    for col in zscore_cols:
        styled = styled.apply(zscore_color, subset=[col])
    for col in percentile_cols:
        styled = styled.apply(percentile_color, subset=[col])
    if "Contrarian Signal" in df.columns:
        styled = styled.apply(contrarian_signal_color, subset=["Contrarian Signal"])
    if "Vol Valuation" in df.columns:
        styled = styled.apply(vol_valuation_color, subset=["Vol Valuation"])

    fmt = {col: "{:.1f}%" for col in percentage_cols}
    fmt.update({col: "{:.2f}" for col in zscore_cols})
    fmt.update({col: "{:.1f}" for col in percentile_cols})
    fmt.update({col: "{:.0f}" for col in score_cols if col in df.columns})
    if "IV−RV Spread" in df.columns:
        fmt["IV−RV Spread"] = "{:.2f}"
    if "IV/RV Ratio" in df.columns:
        fmt["IV/RV Ratio"] = "{:.3f}"
    if "CS Rank" in df.columns:
        fmt["CS Rank"] = "{:.0f}"

    styled = styled.format(fmt)
    styled = styled.format(na_rep="N/A")

    return styled


@st.cache_data(ttl=3600, show_spinner=False)
def _get_cached_backtest_result():
    """Cached backtest summary (rebuilt hourly)."""
    from data.vol_signal_backtest import run_vol_signal_backtest

    return run_vol_signal_backtest()


def _render_signal_backtest_panel() -> None:
    """
    Historical validation: forward returns after contrarian signal buckets.
    """
    with st.expander("Historical signal validation (backtest)"):
        st.caption(
            "Point-in-time contrarian scores vs forward 5D / 21D / 63D ETF returns from stored "
            "close prices. **Hit rate**: bull buckets → positive forward return; bear buckets → negative. "
            "Not investment advice — sample size and regime matter."
        )
        horizon = st.selectbox(
            "Forward horizon (trading days)",
            options=[5, 21, 63],
            index=1,
            key="vol_backtest_horizon",
        )
        ticker_filter = st.selectbox(
            "Ticker filter",
            options=["All universe"] + sorted(
                [
                    "SPY", "QQQ", "IWM", "XLF", "XLE", "XLK", "XLV", "XLB",
                    "XLI", "XLY", "XLP", "XLU", "XLC", "XLRE",
                ]
            ),
            key="vol_backtest_ticker",
        )

        try:
            with st.spinner("Running backtest on stored history..."):
                if ticker_filter == "All universe":
                    result = _get_cached_backtest_result()
                else:
                    from data.vol_signal_backtest import run_vol_signal_backtest

                    result = run_vol_signal_backtest(tickers=[ticker_filter])

            meta = result.get("metadata", {})
            n_events = meta.get("n_events", 0)
            if n_events == 0:
                st.info(
                    "Not enough history for backtest yet. Need ~27+ trading days per ticker "
                    "(22 for signals + 5 for forward returns). Longer horizons need more history."
                )
                return

            ic = result.get("ic_by_horizon", {}).get(horizon)
            c1, c2, c3 = st.columns(3)
            c1.metric("Backtest events", f"{n_events:,}")
            c2.metric("History", f"{meta.get('date_start')} → {meta.get('date_end')}")
            c3.metric(
                f"IC (score vs {horizon}D return)",
                f"{ic:.3f}" if ic is not None else "N/A",
                help="Correlation of contrarian net score with forward return",
            )

            from data.vol_signal_backtest import format_backtest_summary_table

            table = format_backtest_summary_table(result, horizon=horizon)
            if table.empty:
                st.warning("No summary rows for this horizon.")
                return

            display = table.rename(columns={
                "bucket": "Bucket",
                "horizon_days": "Horizon",
                "n_obs": "N",
                "hit_rate": "Hit rate",
                "avg_fwd_return_pct": "Avg fwd %",
                "median_fwd_return_pct": "Median fwd %",
                "avg_max_dd_21d_pct": "Avg max DD 21D %",
                "false_positive_rate": "False positive rate",
                "category": "Category",
            })
            st.dataframe(display, use_container_width=True, hide_index=True)

            st.caption(
                "CLI: `python scripts/vol_signal_backtest.py --horizon 21` · "
                "Premium extremes use 1Y IV/RV percentile ≥75 or ≤25."
            )
        except Exception as e:
            logger.warning("Vol signal backtest failed: %s", e)
            st.warning(f"Backtest unavailable: {e}")


def _render_data_freshness_info(data: pd.DataFrame) -> None:
    """
    Display a rich collection-health status panel below the volatility table.
    Shows days collected, gaps detected, and per-ticker staleness.
    """
    try:
        from data.iv_db import IVDatabase
        with IVDatabase() as db:
            stats = db.get_collection_stats()
    except Exception as e:
        logger.warning(f"Could not load collection stats: {e}")
        return

    total       = stats['total_days']
    latest      = stats['latest_date']
    first       = stats['first_date']
    days_since  = stats['days_since_latest']
    missing     = stats['missing_days']
    per_ticker  = stats['tickers_latest_date']

    if total == 0:
        st.caption("No data collected yet.")
        return

    if days_since == 0:
        badge = "🟢 Up to date"
    elif days_since == 1:
        badge = "🟡 1 day old"
    elif days_since <= 3:
        badge = f"🟠 {days_since} days old"
    else:
        badge = f"🔴 {days_since} days old — scheduler may have missed runs"

    c1, c2, c3 = st.columns(3)
    c1.metric("Days Collected", total,
              help="Distinct trading days stored in the database (anchor: SPY).")
    c2.metric("Latest Data", latest.strftime("%b %d, %Y") if latest else "—")
    c3.metric("Gaps Detected", len(missing),
              delta=None if not missing else f"{len(missing)} missing",
              delta_color="inverse")

    st.caption(badge)

    if missing:
        with st.expander(f"⚠️ {len(missing)} missing trading day(s) — click to see details"):
            st.markdown(
                "These business days are within the collected date range but have "
                "no data in the database, which usually means the scheduler didn't "
                "run on those days."
            )
            gap_df = pd.DataFrame({'Missing Date': missing})
            gap_df['Day'] = pd.to_datetime(gap_df['Missing Date']).dt.strftime('%A')
            st.dataframe(gap_df, hide_index=True, use_container_width=False)
    else:
        st.caption(f"✅ No gaps detected across {total} trading day(s) "
                   f"({first.strftime('%b %d') if first else ''}–"
                   f"{latest.strftime('%b %d, %Y') if latest else ''})")

    if per_ticker:
        latest_str = latest.isoformat() if latest else ""
        stale = {
            t: d for t, d in per_ticker.items() if d != latest_str
        }
        if stale:
            with st.expander(f"⚠️ {len(stale)} ticker(s) behind latest date"):
                st.markdown(
                    "These tickers did not collect data on the most recent scraped date, "
                    "which may indicate scraping errors for those specific tickers."
                )
                rows = [{"Ticker": t, "Latest Date": d} for t, d in sorted(stale.items())]
                st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=False)


def render_vol_table_with_data_fetch() -> None:
    """
    Convenience function that fetches volatility data and renders the table.
    Uses the indicator service to get formatted data.
    """
    try:
        import asyncio
        from src.services.indicator_service import IndicatorService

        service = IndicatorService()
        result = asyncio.run(service.get_indicator("implied_realized_vol"))

        if result and result.data is not None:
            inner = result.data
            if isinstance(inner, dict) and "data" in inner:
                render_vol_table(inner["data"])
            else:
                render_vol_table(inner)
        else:
            render_vol_table(None)

    except ImportError as e:
        logger.error(f"Cannot import indicator service: {e}")
        st.error(f"Service import error: {e}")
    except Exception as e:
        logger.error(f"Error fetching volatility data: {e}")
        st.error(f"Error fetching data: {e}")
