"""
Macro Economic Indicators Dashboard

This application displays key macro economic indicators to help forecast
market conditions and economic trends.
"""
import os
import asyncio
import logging
import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from data.fred_client import FredClient
from data.indicators import IndicatorData
from ui.dashboard import create_dashboard, setup_page_config
from src.config.settings import get_settings

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
def get_fred_client():
    # Get configuration settings
    settings = get_settings()

    # Use configuration for cache settings
    return FredClient(
        cache_enabled=settings.cache.enabled,
        max_cache_size=settings.cache.max_memory_size
    )

@st.cache_resource
def get_indicator_data():
    return IndicatorData(get_fred_client())

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

def refresh_volatility_data():
    """
    Manually trigger volatility data refresh.
    """
    try:
        from data.iv_scraper import IVScraper
        from data.iv_db import IVDatabase
        
        with st.spinner("Refreshing volatility data... This may take 30-40 seconds."):
            db = IVDatabase()
            scraper = IVScraper(db)
            result = scraper.scrape_daily()
            
        if result['success'] > 0:
            st.success(f"✅ Successfully updated {result['success']} tickers. Failed: {result['failed']}")
            # Clear the cache so fresh data is displayed
            check_volatility_data_freshness.clear()
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
        settings = get_settings()
        indicator_service = IndicatorService(settings)

        # Fetch all indicators using service layer
        result = asyncio.run(indicator_service.get_all_indicators())

        if not result.success:
            raise ValueError(f"Service layer failed to fetch indicators: {result.error}")

        indicators = result.data
        fred_client = get_fred_client()  # Still needed for dashboard creation

        logger.info(f"Service layer fetched indicators in {result.execution_time:.2f}s")
        
        # Check volatility data freshness and provide refresh option
        vol_status = check_volatility_data_freshness()
        
        # Display volatility data status in sidebar
        with st.sidebar:
            st.markdown("### 📊 Volatility Data Status")
            st.info(vol_status['message'])
            
            if vol_status['show_refresh']:
                if st.button("🔄 Refresh Volatility Data", help="Manually update implied volatility data from options markets"):
                    refresh_volatility_data()

        # Create and display the dashboard (pass shared fred_client)
        create_dashboard(indicators, fred_client=fred_client)
    except Exception as e:
        logger.exception("Error in dashboard initialization")
        st.error(f"An error occurred while initializing the dashboard: {str(e)}")
