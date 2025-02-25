"""
Functions for creating the main dashboard layout.
"""
import streamlit as st
from ui.summary import display_summary_section
from ui.indicators import display_all_indicator_sections


def setup_page_config():
    """
    Configure the Streamlit page settings.
    """
    st.set_page_config(
        page_title="Macro Dashboard",
        page_icon="📊",
        layout="wide"
    )


def display_header():
    """
    Display the dashboard header and introduction.
    """
    st.title("📊 Macro Economic Indicators Dashboard")
    
    # Add tweet link button
    st.link_button("View Original Tweet Thread by @a_vroenne", "https://x.com/a_vroenne/status/1867241557658829130")
    
    st.markdown("""
    This dashboard tracks key macro economic indicators that help forecast market conditions and economic trends.
    Each indicator includes detailed explanations and warning signals to watch for.
    """)


def display_footer():
    """
    Display the dashboard footer.
    """
    st.markdown("""
    ---
    *Data sourced from FRED (Federal Reserve Economic Data). Updated automatically with each release.*
    """)


def create_dashboard(indicators):
    """
    Create the complete dashboard layout.
    
    Args:
        indicators (dict): Dictionary with all indicator data
    """
    # Setup page configuration
    setup_page_config()
    
    # Display header
    display_header()
    
    # Display summary section
    display_summary_section(indicators)
    
    # Display individual indicator sections
    display_all_indicator_sections(indicators)
    
    # Display footer
    display_footer()
