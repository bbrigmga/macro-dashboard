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
              If None, will fetch data with caching for better performance.
              Expected columns: etf_name, ticker_display, ytd_pct, 
              ivol_rvol_current, ivol_prem_yesterday, ivol_prem_1w, 
              ivol_prem_1m, ttm_zscore, three_yr_zscore
    """
    # Add section header and description
    st.subheader("📊 Implied vs Realized Volatility")
    st.caption("30-day ATM implied vol vs 30-day realized vol across US equity sector ETFs")
    
    # Fetch data with caching if not provided
    if data is None:
        with st.spinner("Loading volatility data..."):
            data = _get_cached_vol_table_data()
    
    # Handle empty/sparse data cases
    if data is None or data.empty:
        st.info(
            "🔄 No volatility data available. Run the daily scraper first:\n\n"
            "```bash\n"
            "python -m data.iv_scraper\n"
            "```"
        )
        return
    
    # Check if we have partial data
    expected_tickers = 14  # Full ETF universe
    if len(data) < expected_tickers:
        st.warning(
            f"⚠️ Showing partial data ({len(data)}/{expected_tickers} tickers). "
            "Some ETFs may be missing options data or have scraping issues."
        )
    
    try:
        # Format and style the data
        styled_df = _format_and_style_table(data)
        
        # Render the table
        st.dataframe(
            styled_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "ETF Name": st.column_config.TextColumn(width="medium"),
                "Ticker": st.column_config.TextColumn(width="small"),
                "Bias": st.column_config.TextColumn(
                    width="medium",
                    help="Hedgeye IVOL/RVOL contrarian bias. Score −3 (most bearish) to +3 (most bullish). "
                         "Based on: premium level, short-term trend (yesterday vs 1W), "
                         "and medium-term trend (1W vs 1M)."
                ),
                "YTD %": st.column_config.NumberColumn(width="small"),
                "IVOL/RVOL Current": st.column_config.NumberColumn(width="medium"),
                "IVOL Prem % Yesterday": st.column_config.NumberColumn(width="medium"),
                "IVOL Prem % 1W Ago": st.column_config.NumberColumn(width="medium"),
                "IVOL Prem % 1M Ago": st.column_config.NumberColumn(width="medium"),
                "TTM Z-Score": st.column_config.NumberColumn(width="small"),
                "3Yr Z-Score": st.column_config.NumberColumn(width="small"),
            }
        )
        
        # Add data freshness info
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
    # Create a copy to avoid modifying original data
    df = data.copy()
    
    # Rename columns for display
    column_map = {
        "etf_name": "ETF Name",
        "ticker_display": "Ticker",
        "bias_label": "Bias",
        "ytd_pct": "YTD %",
        "ivol_rvol_current": "IVOL/RVOL Current",
        "ivol_prem_yesterday": "IVOL Prem % Yesterday",
        "ivol_prem_1w": "IVOL Prem % 1W Ago",
        "ivol_prem_1m": "IVOL Prem % 1M Ago",
        "ttm_zscore": "TTM Z-Score",
        "three_yr_zscore": "3Yr Z-Score",
    }

    # Keep bias_score for styling, then drop it from display
    df = df.rename(columns=column_map)
    # bias_score column remains (not renamed) — used for coloring, excluded at render time
    
    # Define column groups for styling
    percentage_cols = ["YTD %", "IVOL/RVOL Current", "IVOL Prem % Yesterday",
                       "IVOL Prem % 1W Ago", "IVOL Prem % 1M Ago"]
    zscore_cols = ["TTM Z-Score", "3Yr Z-Score"]
    
    # Apply conditional formatting using custom CSS (no matplotlib needed)
    def rdylgn_css(val, vmin, vmax):
        """Map a scalar value to a RdYlGn background CSS string."""
        try:
            v = float(val)
        except (TypeError, ValueError):
            return ""
        t = max(0.0, min(1.0, (v - vmin) / (vmax - vmin)))
        # Red (0) -> Yellow (0.5) -> Green (1)
        if t < 0.5:
            r, g = 220, int(220 * (t / 0.5))
            b = 0
        else:
            r, g = int(220 * (1.0 - (t - 0.5) / 0.5)), 200
            b = 0
        return f"background-color: rgb({r},{g},{b}); color: #000"

    def pct_color(col):
        return [rdylgn_css(v, -30, 50) for v in col]

    def zscore_color(col):
        return [rdylgn_css(v, -2, 2) for v in col]

    def bias_color(col):
        """Color the Bias label column: green=bullish, red=bearish, yellow=neutral."""
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

    # Drop bias_score before building the Styler (it was only needed for sorting)
    display_cols = [c for c in df.columns if c != 'bias_score']
    df = df[display_cols]

    styled = df.style
    if percentage_cols:
        styling = styled
        for col in percentage_cols:
            styling = styling.apply(pct_color, subset=[col])
        styled = styling
    if zscore_cols:
        styling = styled
        for col in zscore_cols:
            styling = styling.apply(zscore_color, subset=[col])
        styled = styling
    if "Bias" in df.columns:
        styled = styled.apply(bias_color, subset=["Bias"])
    
    # Format numeric displays
    styled = styled.format({
        col: "{:.1f}%" for col in percentage_cols
    })
    
    styled = styled.format({
        col: "{:.2f}" for col in zscore_cols  
    })
    
    # Handle N/A values gracefully
    styled = styled.format(na_rep="N/A")
    
    return styled


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

    # --- Freshness badge ---
    if days_since == 0:
        badge = "🟢 Up to date"
    elif days_since == 1:
        badge = "🟡 1 day old"
    elif days_since <= 3:
        badge = f"🟠 {days_since} days old"
    else:
        badge = f"🔴 {days_since} days old — scheduler may have missed runs"

    # --- Top summary row ---
    c1, c2, c3 = st.columns(3)
    c1.metric("Days Collected", total,
              help="Distinct trading days stored in the database (anchor: SPY).")
    c2.metric("Latest Data", latest.strftime("%b %d, %Y") if latest else "—")
    c3.metric("Gaps Detected", len(missing),
              delta=None if not missing else f"{len(missing)} missing",
              delta_color="inverse")

    st.caption(badge)

    # --- Gap detail (only shown if there are gaps) ---
    if missing:
        with st.expander(f"⚠️ {len(missing)} missing trading day(s) — click to see details"):
            st.markdown(
                "These business days are within the collected date range but have "
                "no data in the database, which usually means the scheduler didn't "
                "run on those days."
            )
            # Show in a compact table
            gap_df = pd.DataFrame({'Missing Date': missing})
            gap_df['Day'] = pd.to_datetime(gap_df['Missing Date']).dt.strftime('%A')
            st.dataframe(gap_df, hide_index=True, use_container_width=False)
    else:
        st.caption(f"✅ No gaps detected across {total} trading day(s) "
                   f"({first.strftime('%b %d') if first else ''}–"
                   f"{latest.strftime('%b %d, %Y') if latest else ''})")

    # --- Per-ticker staleness (collapsed by default) ---
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
            render_vol_table(result.data)
        else:
            render_vol_table(None)
            
    except ImportError as e:
        logger.error(f"Cannot import indicator service: {e}")
        st.error(f"Service import error: {e}")
    except Exception as e:
        logger.error(f"Error fetching volatility data: {e}")
        st.error(f"Error fetching data: {e}")