"""
Macro Economic Indicators Dashboard

This application displays key macro economic indicators to help forecast
market conditions and economic trends.
"""
import data.numpy_compat  # noqa: F401 — before scipy/pandas may import NumPy APIs

import os
import asyncio
import logging
from datetime import date
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from ui.dashboard import create_dashboard, setup_page_config

from src.services import IndicatorService

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set up page config first, before any other Streamlit commands
setup_page_config()

# Load environment variables
load_dotenv()

# Add cached singletons for shared clients/resources
@st.cache_resource
def get_indicator_service():
    return IndicatorService()

@st.cache_data(ttl=300)  # Cache for 5 minutes
def check_volatility_data_freshness():
    """
    Check if volatility database has recent data.
    Returns info about data freshness for display.
    """
    try:
        from data.iv_db import IVDatabase
        from datetime import date
        
        db = IVDatabase()
        latest = db.get_all_latest()
        
        if latest.empty:
            return {
                'has_data': False,
                'message': "📊 Volatility data not available. Run the scraper to start collecting IV data.",
                'show_refresh': True
            }
        
        latest_date = pd.to_datetime(latest['date'].max()).date()
        days_old = (date.today() - latest_date).days
        
        if days_old == 0:
            return {'has_data': True, 'message': "✅ Volatility data is current", 'show_refresh': False}
        elif days_old == 1:
            return {'has_data': True, 'message': "⏰ Volatility data is 1 day old", 'show_refresh': True}
        elif days_old <= 3:
            return {'has_data': True, 'message': f"⚠️ Volatility data is {days_old} days old", 'show_refresh': True}
        else:
            return {'has_data': True, 'message': f"🚨 Volatility data is {days_old} days old", 'show_refresh': True}
            
    except Exception as e:
        logger.warning(f"Could not check volatility data freshness: {e}")
        return {
            'has_data': False, 
            'message': "❓ Could not check volatility data status",
            'show_refresh': False
        }

@st.cache_data(ttl=3600)
def _get_market_macro_csv() -> bytes:
    """Build CSV bytes for aligned daily ETF + macro export (3 years)."""
    from data.market_macro_export import market_macro_export_csv_bytes

    return market_macro_export_csv_bytes(years=3)


@st.cache_data(ttl=300)
def _get_iv_data_csv() -> bytes:
    """Build CSV bytes for all scraped IV/RV snapshots in the local database."""
    from data.iv_db import IVDatabase

    with IVDatabase() as db:
        df = db.get_all()
    if df.empty:
        return b""
    export = df.copy()
    export["date"] = pd.to_datetime(export["date"]).dt.strftime("%Y-%m-%d")
    return export.to_csv(index=False).encode("utf-8")


def reload_vol_table_from_db():
    """Clear vol table caches and rerun (no live Yahoo scrape)."""
    from ui.vol_table import reload_vol_table_caches

    reload_vol_table_caches()
    check_volatility_data_freshness.clear()
    _get_iv_data_csv.clear()
    st.rerun()


def refresh_volatility_data():
    """
    Manually trigger volatility data refresh.
    """
    try:
        from data.iv_scraper import IVScraper
        from data.iv_db import IVDatabase
        from ui.vol_table import reload_vol_table_caches
        
        with st.spinner("Refreshing volatility data... This may take 30-40 seconds."):
            db = IVDatabase()
            scraper = IVScraper(db)
            result = scraper.scrape_daily()
            
        if result['success'] > 0:
            st.success(f"✅ Successfully updated {result['success']} tickers. Failed: {result['failed']}")
            # Clear caches so fresh data is displayed
            check_volatility_data_freshness.clear()
            _get_iv_data_csv.clear()
            reload_vol_table_caches()
            get_indicator_service().invalidate_indicator_cache("implied_realized_vol")
            st.rerun()
        else:
            st.error(f"❌ Failed to update volatility data. Check logs for details.")
            
    except Exception as e:
        st.error(f"❌ Error refreshing volatility data: {str(e)}")
        logger.exception("Error in volatility data refresh")

# Check if FRED API key is available
if not os.getenv('FRED_API_KEY'):
    st.error("""
    ## FRED API Key Missing
    
    This dashboard requires a FRED API key to fetch economic data.
    
    1. Get a free API key from [FRED API](https://fred.stlouisfed.org/docs/api/api_key.html)
    2. Create a `.env` file in the project root with:
       ```
       FRED_API_KEY=
       ```
    3. Restart the application
    
    You can use the `.env.example` file as a template.
    """)
else:
    try:
        # Use service layer architecture
        logger.info("Using service layer architecture")
        indicator_service = get_indicator_service()

        # Fetch all indicators using service layer
        result = asyncio.run(indicator_service.get_all_indicators())

        if not result.success:
            raise ValueError(f"Service layer failed to fetch indicators: {result.error}")

        indicators = result.data
        fred_client = indicator_service.fred_client

        logger.info(f"Service layer fetched indicators in {result.execution_time:.2f}s")
        
        # Check volatility data freshness and provide refresh option
        vol_status = check_volatility_data_freshness()
        
        # Display volatility data status in sidebar
        with st.sidebar:
            st.markdown("### 📊 Volatility Data Status")
            st.info(vol_status['message'])

            if st.button(
                "↻ Reload Vol Table",
                help="Rebuild the IV/RV table from the local database (fast; fixes empty Yesterday/1W/1M columns)",
            ):
                reload_vol_table_from_db()

            if vol_status['show_refresh']:
                if st.button(
                    "🔄 Scrape Volatility Data",
                    help="Fetch today's implied vol from Yahoo options (~30–40s)",
                ):
                    refresh_volatility_data()

            if vol_status['has_data']:
                csv_bytes = _get_iv_data_csv()
                st.download_button(
                    label="⬇️ Export Options Data (CSV)",
                    data=csv_bytes,
                    file_name=f"iv_options_data_{date.today().isoformat()}.csv",
                    mime="text/csv",
                    help=(
                        "Download all daily IV/RV snapshots from the local database "
                        "(date, ticker, close, iv_30d, rv_30d, iv_premium, ytd_return)"
                    ),
                )

        # Create and display the dashboard (pass shared fred_client)
        create_dashboard(
            indicators,
            fred_client=fred_client,
            market_macro_csv=_get_market_macro_csv(),
        )
    except Exception as e:
        logger.exception("Error in dashboard initialization")
        st.error(f"An error occurred while initializing the dashboard: {str(e)}")
