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
        fred_client = FredClient()
        
        # Initialize indicator data handler
        indicator_data = IndicatorData(fred_client)
        
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
        
        # Create and display the dashboard (without calling setup_page_config again)
        create_dashboard(indicators)
    except Exception as e:
        logger.error(f"Error in dashboard initialization: {str(e)}")
        st.error(f"An error occurred while initializing the dashboard: {str(e)}")
