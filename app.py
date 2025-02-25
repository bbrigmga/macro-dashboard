"""
Macro Economic Indicators Dashboard

This application displays key macro economic indicators to help forecast
market conditions and economic trends.
"""
import os
from dotenv import load_dotenv
from data.fred_client import FredClient
from data.indicators import IndicatorData
from ui.dashboard import create_dashboard

# Load environment variables
load_dotenv()

# Check if FRED API key is available
if not os.getenv('FRED_API_KEY'):
    import streamlit as st
    st.error("""
    ## FRED API Key Missing
    
    This dashboard requires a FRED API key to fetch economic data.
    
    1. Get a free API key from [FRED API](https://fred.stlouisfed.org/docs/api/api_key.html)
    2. Create a `.env` file in the project root with:
       ```
       FRED_API_KEY=your_api_key_here
       ```
    3. Restart the application
    
    You can use the `.env.example` file as a template.
    """)
else:
    # Initialize FRED client
    fred_client = FredClient()
    
    # Initialize indicator data handler
    indicator_data = IndicatorData(fred_client)
    
    # Fetch all indicators
    indicators = indicator_data.get_all_indicators()
    
    # Create and display the dashboard
    create_dashboard(indicators)
