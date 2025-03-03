"""
Functions for creating the main dashboard layout with a modern finance-based UI.
"""
import streamlit as st
import datetime
from .indicators import (
    display_hours_worked_card,
    display_core_cpi_card,
    display_initial_claims_card,
    display_pce_card,
    display_pmi_card,
    display_usd_liquidity_card,
    display_defensive_playbook_card,
    display_core_principles_card
)


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
    # Setup page configuration
    setup_page_config()
    
    # Display header
    display_header()
    
    # First row - 3 indicators
    col1, col2, col3 = st.columns(3)
    
    with col1:
        display_hours_worked_card(indicators['hours_worked'])
    
    with col2:
        display_core_cpi_card(indicators['core_cpi'])
    
    with col3:
        display_initial_claims_card(indicators['claims'])
    
    # Second row - 3 indicators
    col1, col2, col3 = st.columns(3)
    
    with col1:
        display_pce_card(indicators['pce'])
    
    with col2:
        display_pmi_card(indicators['pmi'])
    
    with col3:
        display_usd_liquidity_card(indicators['usd_liquidity'])
    
    # Third row - Defensive playbook and core principles
    col1, col2 = st.columns(2)
    
    with col1:
        display_defensive_playbook_card()
    
    with col2:
        display_core_principles_card()
    
    # Display footer
    display_footer()
