"""
Macro Economic Indicators Dashboard

This application displays key macro economic indicators to help forecast
market conditions and economic trends.
"""
import os
import logging
import streamlit as st
from dotenv import load_dotenv
from data.fred_client import FredClient
from data.indicators import IndicatorData
from ui.dashboard import create_dashboard, setup_page_config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set up page config first, before any other Streamlit commands
setup_page_config()

# Load environment variables
load_dotenv()

# Define caching functions
@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_claims_data(_indicator_data):
    logger.info("Fetching claims data (cached)")
    return _indicator_data.get_initial_claims()
    
@st.cache_data(ttl=3600*24)  # Cache for 24 hours
def fetch_pce_data(_indicator_data):
    logger.info("Fetching PCE data (cached)")
    return _indicator_data.get_pce()
    
@st.cache_data(ttl=3600*24)  # Cache for 24 hours
def fetch_core_cpi_data(_indicator_data):
    logger.info("Fetching Core CPI data (cached)")
    return _indicator_data.get_core_cpi()
    
@st.cache_data(ttl=3600*24)  # Cache for 24 hours
def fetch_hours_data(_indicator_data):
    logger.info("Fetching hours worked data (cached)")
    return _indicator_data.get_hours_worked()
    
@st.cache_data(ttl=3600*24)  # Cache for 24 hours
def fetch_pmi_data(_indicator_data):
    logger.info("Fetching PMI data (cached)")
    return _indicator_data.calculate_pmi_proxy(periods=36)
    
@st.cache_data(ttl=3600*24)  # Cache for 24 hours
def fetch_usd_liquidity_data(_indicator_data):
    logger.info("Fetching USD liquidity data (cached)")
    return _indicator_data.get_usd_liquidity()

@st.cache_data(ttl=3600*24)  # Cache for 24 hours
def fetch_new_orders_data(_indicator_data):
    logger.info("Fetching manufacturers' new orders data (cached)")
    return _indicator_data.get_new_orders()

@st.cache_data(ttl=3600*24)  # Cache for 24 hours
def fetch_yield_curve_data(_indicator_data):
    logger.info("Fetching 10Y-2Y Treasury yield spread data (cached)")
    return _indicator_data.get_yield_curve(periods=36, frequency='D')

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
        # Initialize FRED client
        logger.info("Initializing FRED client")
        fred_client = FredClient()
        
        # Initialize indicator data handler
        logger.info("Initializing indicator data handler")
        indicator_data = IndicatorData(fred_client)
        
        # Fetch all indicators with caching
        logger.info("Fetching all indicators with caching")
        claims_data = fetch_claims_data(indicator_data)
        pce_data = fetch_pce_data(indicator_data)
        core_cpi_data = fetch_core_cpi_data(indicator_data)
        hours_data = fetch_hours_data(indicator_data)
        pmi_data = fetch_pmi_data(indicator_data)
        usd_liquidity_data = fetch_usd_liquidity_data(indicator_data)
        new_orders_data = fetch_new_orders_data(indicator_data)
        yield_curve_data = fetch_yield_curve_data(indicator_data)
        
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
        
        # Create and display the dashboard (without calling setup_page_config again)
        logger.info("Creating and displaying dashboard")
        create_dashboard(indicators)
    except Exception as e:
        logger.error(f"Error in dashboard initialization: {str(e)}")
        st.error(f"An error occurred while initializing the dashboard: {str(e)}")
