"""
Functions for creating the summary section of the dashboard.
"""
import streamlit as st
import pandas as pd
from visualization.charts import create_warning_indicator


def create_summary_table(indicators):
    """
    Create a summary table with all indicators.
    
    Args:
        indicators (dict): Dictionary with all indicator data
    """
    # Extract data from indicators
    hours_data = indicators['hours_worked']
    core_cpi_data = indicators['core_cpi']
    claims_data = indicators['claims']
    pce_data = indicators['pce']
    pmi_data = indicators['pmi']
    
    # Create summary table with numbered indicators
    summary_data = {
        'Indicator': [
            '1. Average Weekly Hours',
            '2. Core CPI',
            '3. Initial Jobless Claims',
            '4. PCE (Inflation)',
            '5. Manufacturing PMI Proxy'
        ],
        'Status': [
            create_warning_indicator(hours_data['hours_weakening'], 0.5),
            create_warning_indicator(core_cpi_data['cpi_accelerating'], 0.5),
            create_warning_indicator(claims_data['claims_increasing'], 0.5),
            create_warning_indicator(pce_data['current_pce'], 2.0),
            create_warning_indicator(pmi_data['latest_pmi'] < 50, 0.5)
        ],
        'Current Value': [
            f"{hours_data['consecutive_declines']} consecutive months of decline",
            f"{core_cpi_data['current_cpi_mom']:.2f}% MoM",
            f"{claims_data['current_value']:,.0f} claims",
            f"{pce_data['current_pce']:.1f}% YoY",
            f"{pmi_data['latest_pmi']:.1f}"
        ],
        'Interpretation': [
            'Weakening' if hours_data['hours_weakening'] else 'Strong',
            'Accelerating' if core_cpi_data['cpi_accelerating'] else 'Stable/Decelerating',
            'Rising' if claims_data['claims_increasing'] else 'Stable/Decreasing',
            'Rising' if pce_data['pce_rising'] else 'Falling',
            'Contraction' if pmi_data['pmi_below_50'] else 'Expansion'
        ]
    }
    
    st.header("Current Market Signals Summary")
    summary_df = pd.DataFrame(summary_data)
    # Use st.dataframe instead of st.table with hide_index=True to properly hide the index
    st.dataframe(summary_df, hide_index=True)


def create_danger_combination_section(indicators):
    """
    Create the danger combination visualization section.
    
    Args:
        indicators (dict): Dictionary with all indicator data
    """
    # Extract data from indicators
    hours_data = indicators['hours_worked']
    claims_data = indicators['claims']
    pmi_data = indicators['pmi']
    danger_combination = indicators['danger_combination']
    
    st.subheader("Danger Combination Status")
    # Create columns for the visualization
    col1, col2 = st.columns([3, 2])
    
    with col1:
        # Create a DataFrame for the danger combination
        danger_data = {
            'Indicator': [
                'Manufacturing PMI < 50',
                'Initial Claims Rising',
                'Avg Weekly Hours Dropping'
            ],
            'Status': [
                create_warning_indicator(pmi_data['pmi_below_50'], 0.5, higher_is_bad=True),
                create_warning_indicator(claims_data['claims_increasing'], 0.5, higher_is_bad=True),
                create_warning_indicator(hours_data['hours_weakening'], 0.5, higher_is_bad=True)
            ],
            'Current Value': [
                f"{pmi_data['latest_pmi']:.1f}",
                f"{'Rising' if claims_data['claims_increasing'] else 'Stable/Falling'}",
                f"{hours_data['consecutive_declines']} consecutive months of decline"
            ]
        }
        danger_df = pd.DataFrame(danger_data)
        st.dataframe(danger_df, hide_index=True)
    
    with col2:
        # Create a gauge or indicator for the danger combination
        if danger_combination:
            st.error("⚠️ DANGER COMBINATION ACTIVE")
            st.markdown("**All three warning signals are active!**")
        else:
            active_count = sum([
                pmi_data['pmi_below_50'], 
                claims_data['claims_increasing'], 
                hours_data['hours_weakening']
            ])
            if active_count == 0:
                st.success("✅ No warning signals active")
            elif active_count == 1:
                st.info("ℹ️ 1 of 3 warning signals active")
            elif active_count == 2:
                st.warning("⚠️ 2 of 3 warning signals active")


def create_market_signal_section(indicators):
    """
    Create the overall market signal section.
    
    Args:
        indicators (dict): Dictionary with all indicator data
    """
    # Extract data
    danger_combination = indicators['danger_combination']
    risk_on_opportunity = indicators['risk_on_opportunity']
    claims_increasing = indicators['claims']['claims_increasing']
    pce_rising = indicators['pce']['pce_rising']
    
    st.subheader("Overall Market Signal")
    if danger_combination:
        st.error("⚠️ DANGER COMBINATION DETECTED: Manufacturing PMI below 50 + Claims rising + Average weekly hours dropping")
        st.markdown("**Recommended Action:** Protect capital first. Scale back aggressive positions.")
    elif claims_increasing and pce_rising:
        st.warning("⚠️ WARNING: PCE rising + Rising claims = Get defensive")
        st.markdown("**Recommended Action:** Shift toward defensive sectors, build cash reserves.")
    elif risk_on_opportunity:
        st.success("✅ OPPORTUNITY: PCE dropping + Stable jobs = Add risk")
        st.markdown("**Recommended Action:** Consider adding risk to portfolio.")
    else:
        st.info("📊 Mixed signals - Monitor closely and wait for confirmation")
        st.markdown("**Recommended Action:** Make gradual moves based on trend changes.")
    
    st.markdown("""
    🔴 = Warning Signal / Needs Attention
    🟢 = Normal / Healthy Range
    """)


def display_summary_section(indicators):
    """
    Display the complete summary section.
    
    Args:
        indicators (dict): Dictionary with all indicator data
    """
    create_summary_table(indicators)
    create_danger_combination_section(indicators)
    create_market_signal_section(indicators)
