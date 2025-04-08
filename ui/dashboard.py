"""
Functions for creating the main dashboard layout with a modern finance-based UI.
"""
import os
import datetime
import streamlit as st
import pandas as pd
from .indicators import (
    display_hours_worked_card,
    display_core_cpi_card,
    display_initial_claims_card,
    display_pce_card,
    display_pmi_card,
    display_usd_liquidity_card,
    display_core_principles_card,
    display_new_orders_card,
    display_yield_curve_card
)
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


def create_dashboard(indicators):
    """
    Create the complete dashboard layout with a modern grid-based design.
    
    Args:
        indicators (dict): Dictionary with all indicator data
    """
    # Initialize FRED client for release dates
    fred_client = FredClient()
    
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
    
    # Determine status for each indicator
    def get_indicator_status(data, key_func):
        if key_func(data):
            return "Bullish"
        elif key_func(data, inverse=True):
            return "Bearish"
        else:
            return "Neutral"
    
    status_data = [
        ["Manufacturing PMI", 
         "Bullish" if indicators['pmi']['latest_pmi'] >= 50 else "Bearish"],
        ["Initial Claims", get_indicator_status(indicators['claims'], 
            lambda d, inverse=False: d.get('claims_decreasing', False) if not inverse else d.get('claims_increasing', False))],
        ["Hours Worked", get_indicator_status(indicators['hours_worked'], 
            lambda d, inverse=False: d.get('consecutive_increases', 0) >= 3 if not inverse else d.get('consecutive_declines', 0) >= 3)]
    ]
    
    # Get PCE and Initial Claims status
    pce_status = "Bullish" if indicators['pce'].get('pce_decreasing', False) else (
        "Bearish" if indicators['pce'].get('pce_increasing', False) else "Neutral"
    )
    
    initial_claims_status = get_indicator_status(indicators['claims'], 
        lambda d, inverse=False: d.get('claims_decreasing', False) if not inverse else d.get('claims_increasing', False))
    
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
        styled_positioning_df = positioning_df.style.applymap(color_positioning)
        
        # Match height with the indicator status table
        st.dataframe(styled_positioning_df, use_container_width=True, height=150, hide_index=True)
    
    # First row - 3 indicators
    col1, col2, col3 = st.columns(3)
    
    with col1:
        display_hours_worked_card(indicators['hours_worked'], fred_client)
    
    with col2:
        display_core_cpi_card(indicators['core_cpi'], fred_client)
    
    with col3:
        display_initial_claims_card(indicators['claims'], fred_client)
    
    # Second row - 3 indicators
    col1, col2, col3 = st.columns(3)
    
    with col1:
        display_pce_card(indicators['pce'], fred_client)
    
    with col2:
        display_pmi_card(indicators['pmi'], fred_client)
    
    with col3:
        display_usd_liquidity_card(indicators['usd_liquidity'], fred_client)
    
    # Third row - New Orders and Yield Curve
    col1, col2 = st.columns(2)
    
    with col1:
        display_new_orders_card(indicators['new_orders'], fred_client)
    
    with col2:
        display_yield_curve_card(indicators['yield_curve'], fred_client)
    
    # Display footer
    display_footer()
