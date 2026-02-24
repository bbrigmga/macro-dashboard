"""
Functions for creating the main dashboard layout with a modern finance-based UI.
"""
import os
import datetime
import streamlit as st
import pandas as pd
from .indicators import (
    display_indicator_card,
    display_core_principles_card
)
from src.config.indicator_registry import INDICATOR_REGISTRY
from visualization.warning_signals import generate_indicator_warning
from data.fred_client import FredClient


def setup_page_config():
    """
    Configure the Streamlit page settings with modern theme.
    """
    st.set_page_config(
        page_title="Macro Dashboard",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="collapsed"
    )


def display_header():
    """
    Display the dashboard header with modern styling.
    """
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.title("📊 Macro Economic Indicators")
    
    with col2:
        current_date = datetime.datetime.now().strftime("%b %d, %Y")
        st.caption(f"Last updated: {current_date}")
    
    # Add tweet link
    st.markdown("[View Original Tweet Thread by @a_vroenne](https://x.com/a_vroenne/status/1867241557658829130)")
    st.divider()


def display_footer():
    """
    Display the dashboard footer with modern styling.
    """
    st.divider()
    st.caption("Data sourced from FRED (Federal Reserve Economic Data). Updated automatically with each release.")


def create_dashboard(indicators, fred_client):
    """
    Create the complete dashboard layout with a modern grid-based design.
    
    Args:
        indicators (dict): Dictionary with all indicator data
        fred_client (FredClient): Shared FRED client instance
    """
    # Initialize FRED client for release dates
    # fred_client is provided by the caller; do not instantiate here
    # Display header
    display_header()
    
    # Add CSS to remove scrollbars from all dataframes
    st.markdown("""
    <style>
    [data-testid="stDataFrame"] div[data-testid="stVerticalBlock"] {
        overflow: visible !important;
    }
    [data-testid="stDataFrame"] [data-testid="stVerticalBlock"] > div:nth-child(3) {
        overflow: visible !important;
    }
    [data-testid="stDataFrame"] [data-testid="stVerticalBlock"] > div:nth-child(3) > div {
        overflow: visible !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Create two columns for the tables with headers
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📊 Indicator Status")
    
    with col2:
        st.markdown("### 📈 Positioning")
    
    # Compute statuses using the same logic as the chart indicators
    pmi_status = generate_indicator_warning(indicators['pmi'], INDICATOR_REGISTRY['pmi_proxy'])['status']
    initial_claims_status = generate_indicator_warning(indicators['claims'], INDICATOR_REGISTRY['initial_claims'])['status']
    hours_status = generate_indicator_warning(indicators['hours_worked'], INDICATOR_REGISTRY['hours_worked'])['status']
    pce_status = generate_indicator_warning(indicators['pce'], INDICATOR_REGISTRY['pce'])['status']

    status_data = [
        ["Manufacturing PMI", pmi_status],
        ["Initial Claims", initial_claims_status],
        ["Hours Worked", hours_status],
    ]
    
    # Determine positioning based on PCE and Initial Claims
    if pce_status == "Bullish" and (initial_claims_status == "Bullish" or initial_claims_status == "Neutral"):
        positioning = "Risk On"
    elif pce_status == "Bearish" and initial_claims_status == "Bearish":
        positioning = "Risk Off"
    else:
        positioning = "Risk Neutral"
    
    # Create two columns for the tables content (same as above)
    table_col1, table_col2 = st.columns(2)
    
    with table_col1:
        # Use Streamlit's native table rendering for indicator status
        status_df = pd.DataFrame(status_data, columns=['Indicator', 'Status'])
        
        # Custom styling for status
        def color_status(val):
            color = {
                'Bullish': 'green',
                'Bearish': 'red',
                'Neutral': 'gray'
            }.get(val, 'black')
            return f'color: {color}'
        
        styled_status_df = status_df.style.map(color_status, subset=['Status'])
        
        # Set a taller height to ensure all content is visible without scrolling
        st.dataframe(styled_status_df, use_container_width=True, height=150, hide_index=True)
    
    with table_col2:
        # Create a DataFrame with just the data we need - no empty rows
        positioning_data = {
            'PCE': [pce_status],
            'Initial Claims': [initial_claims_status],
            'Positioning': [positioning]
        }
        
        positioning_df = pd.DataFrame(positioning_data)
        
        # Custom styling for positioning
        def color_positioning(val):
            color = {
                'Bullish': 'green',
                'Bearish': 'red',
                'Neutral': 'gray',
                'Risk On': 'green',
                'Risk Off': 'red',
                'Risk Neutral': 'gray'
            }.get(val, 'black')
            return f'color: {color}'
        
        # Apply styling to all columns
        styled_positioning_df = positioning_df.style.map(color_positioning)
        
        # Match height with the indicator status table
        st.dataframe(styled_positioning_df, use_container_width=True, height=150, hide_index=True)
    
    # First row - 3 indicators
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if 'hours_worked' in indicators:
            display_indicator_card('hours_worked', indicators['hours_worked'], fred_client)
    
    with col2:
        if 'core_cpi' in indicators:
            display_indicator_card('core_cpi', indicators['core_cpi'], fred_client)
    
    with col3:
        if 'claims' in indicators:  # Note: data key is 'claims' but registry key is 'initial_claims'
            display_indicator_card('initial_claims', indicators['claims'], fred_client)
    
    # Second row - 3 indicators
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if 'pce' in indicators:
            display_indicator_card('pce', indicators['pce'], fred_client)
    
    with col2:
        if 'pmi' in indicators:  # Note: data key is 'pmi' but registry key is 'pmi_proxy'
            display_indicator_card('pmi_proxy', indicators['pmi'], fred_client)
    
    with col3:
        if 'new_orders' in indicators:
            display_indicator_card('new_orders', indicators['new_orders'], fred_client)
    
    # Third row - USD liquidity, Copper/Gold vs 10Y yield, PSCF small cap financials
    col1, col2, col3 = st.columns(3)

    with col1:
        if 'usd_liquidity' in indicators:
            display_indicator_card('usd_liquidity', indicators['usd_liquidity'], fred_client)

    with col2:
        if 'copper_gold_ratio' in indicators:  # Note: data key matches registry key 'copper_gold_yield'
            display_indicator_card('copper_gold_yield', indicators['copper_gold_ratio'], fred_client)

    with col3:
        if 'pscf' in indicators:  # Note: data key matches registry key 'pscf_price'
            display_indicator_card('pscf_price', indicators['pscf'], fred_client)

    # Fourth row - 2-10Y spread, High Yield Credit Spread, XLP/XLY Ratio
    st.divider()
    col1, col2, col3 = st.columns(3)

    with col1:
        if 'yield_curve' in indicators:
            display_indicator_card('yield_curve', indicators['yield_curve'], fred_client)

    with col2:
        if 'credit_spread' in indicators:
            display_indicator_card('credit_spread', indicators['credit_spread'], fred_client)

    with col3:
        if 'xlp_xly_ratio' in indicators:
            display_indicator_card('xlp_xly_ratio', indicators['xlp_xly_ratio'], fred_client)

    # Display footer
    display_footer()
