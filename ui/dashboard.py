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
    
    # Load custom CSS
    with open('ui/custom.css') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)


def display_header():
    """
    Display the dashboard header with modern styling.
    """
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown("<h1 style='margin-bottom: 0px;'>📊 Macro Economic Indicators</h1>", unsafe_allow_html=True)
    
    with col2:
        current_date = datetime.datetime.now().strftime("%b %d, %Y")
        st.markdown(f"<p style='text-align: right; color: var(--neutral-color);'>Last updated: {current_date}</p>", 
                   unsafe_allow_html=True)
    
    # Add tweet link button with custom styling
    st.markdown(
        """
        <div style='margin-bottom: 1rem;'>
            <a href='https://x.com/a_vroenne/status/1867241557658829130' 
               style='color: var(--primary-color); text-decoration: none; font-size: 0.9rem;' 
               target='_blank'>
                View Original Tweet Thread by @a_vroenne
            </a>
        </div>
        """, 
        unsafe_allow_html=True
    )



def display_footer():
    """
    Display the dashboard footer with modern styling.
    """
    st.markdown(
        """
        <footer>
            Data sourced from FRED (Federal Reserve Economic Data). Updated automatically with each release.
        </footer>
        """, 
        unsafe_allow_html=True
    )


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
    
    # Second row - 2 indicators and defensive playbook
    col1, col2, col3 = st.columns(3)
    
    with col1:
        display_pce_card(indicators['pce'])
    
    with col2:
        display_pmi_card(indicators['pmi'])
    
    with col3:
        display_defensive_playbook_card()
        display_core_principles_card()
    
    # Display footer
    display_footer()
