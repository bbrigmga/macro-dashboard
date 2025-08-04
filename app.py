"""
Macro Economic Indicators Dashboard

This application displays key macro economic indicators to help forecast
market conditions and economic trends.
"""
import os
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
    # Enable internal client cache and increase max cache size
    return FredClient(cache_enabled=True, max_cache_size=512)

@st.cache_resource
def get_indicator_data():
    return IndicatorData(get_fred_client())

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
        # Initialize FRED client (singleton) and indicator data handler (singleton)
        fred_client = get_fred_client()
        indicator_data = get_indicator_data()
        # Fetch all indicators with caching
        claims_data = indicator_data.get_initial_claims()
        pce_data = indicator_data.get_pce()
        core_cpi_data = indicator_data.get_core_cpi()
        hours_data = indicator_data.get_hours_worked()
        pmi_data = indicator_data.calculate_pmi_proxy(periods=36)
        usd_liquidity_data = indicator_data.get_usd_liquidity()
        new_orders_data = indicator_data.get_new_orders()
        yield_curve_data = indicator_data.get_yield_curve(periods=36, frequency='D')
        # Combine all indicators
        indicators = {
            'claims': claims_data,
            'pce': pce_data,
            'core_cpi': core_cpi_data,
            'hours_worked': hours_data,
            'pmi': pmi_data,
            'usd_liquidity': usd_liquidity_data,
            'new_orders': new_orders_data,
            'yield_curve': yield_curve_data
        }
        # Create and display the dashboard (pass shared fred_client)
        create_dashboard(indicators, fred_client=fred_client)
    except Exception as e:
        logger.error(f"Error in dashboard initialization: {str(e)}")
        st.error(f"An error occurred while initializing the dashboard: {str(e)}")
