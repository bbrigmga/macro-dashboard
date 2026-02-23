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

        # Create and display the dashboard (pass shared fred_client)
        create_dashboard(indicators, fred_client=fred_client)
    except Exception as e:
        logger.exception("Error in dashboard initialization")
        st.error(f"An error occurred while initializing the dashboard: {str(e)}")
