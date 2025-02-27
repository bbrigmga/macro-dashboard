"""
Functions for creating the individual indicator sections of the dashboard.
"""
import streamlit as st
from visualization.indicators import (
    create_hours_worked_chart,
    create_core_cpi_chart,
    create_initial_claims_chart,
    create_pce_chart,
    create_pmi_chart,
    create_pmi_components_table
)
from visualization.charts import create_warning_indicator


def display_hours_worked_section(hours_data):
    """
    Display the Average Weekly Hours section.
    
    Args:
        hours_data (dict): Dictionary with hours worked data
    """
    st.header("1. Average Weekly Hours 🕒")
    st.markdown("""
    **Description:** Average weekly hours of all employees in the total private sector.
    A declining trend can signal reduced economic activity and potential job market weakness.
    """)
    
    # Create and display the chart
    fig_hours = create_hours_worked_chart(hours_data)
    st.plotly_chart(fig_hours, use_container_width=True)
    
    # Add FRED reference link
    st.markdown("[FRED Data Source: AWHAETP - Average Weekly Hours of All Employees: Total Private](https://fred.stlouisfed.org/series/AWHAETP)")
    
    # Warning signals for Hours Worked
    st.subheader("Warning Signals 🚨")
    st.markdown(f"""
    Current Status: {create_warning_indicator(hours_data['hours_weakening'], 0.5)} 
    Consecutive Months of Decline: {hours_data['consecutive_declines']}
    
    **Key Warning Signals to Watch:**
    - Three or more consecutive months of declining hours (current: {hours_data['consecutive_declines']})
    - Steep month-over-month drops (> 0.5%)
    """)


def display_core_cpi_section(core_cpi_data):
    """
    Display the Core CPI section.
    
    Args:
        core_cpi_data (dict): Dictionary with Core CPI data
    """
    st.header("2. Core CPI (Consumer Price Index Less Food and Energy) 📊")
    st.markdown("""
    **Description:** Core CPI measures inflation excluding volatile food and energy prices.
    This provides a clearer picture of underlying inflation trends.
    """)
    
    # Create and display the chart
    fig_cpi = create_core_cpi_chart(core_cpi_data)
    st.plotly_chart(fig_cpi, use_container_width=True)
    
    # Add FRED reference link
    st.markdown("[FRED Data Source: CPILFESL - Core Consumer Price Index](https://fred.stlouisfed.org/series/CPILFESL)")
    
    # Warning signals for Core CPI
    st.subheader("Warning Signals 🚨")
    st.markdown(f"""
    Current Status: {create_warning_indicator(core_cpi_data['cpi_accelerating'], 0.5)} 
    Current Core CPI MoM: {core_cpi_data['current_cpi_mom']:.2f}%
    {'⚠️ CPI has been accelerating for 3+ months - Inflation pressure building' if core_cpi_data['cpi_accelerating'] else '✅ CPI trend stable/decelerating - Inflation pressure easing'}
    
    **Key Warning Signals to Watch:**
    - Three consecutive months of accelerating MoM inflation
    - Monthly rate above 0.3% (annualizes to >3.6%)
    - Divergence from PCE trends
    """)


def display_initial_claims_section(claims_data):
    """
    Display the Initial Jobless Claims section.
    
    Args:
        claims_data (dict): Dictionary with claims data
    """
    st.header("3. Initial Jobless Claims 📈")
    st.markdown("""
    **Description:** Initial Jobless Claims show how many people filed for unemployment for the first time in a given week.
    Released every Thursday by the Department of Labor.
    """)
    
    # Create and display the chart
    fig_claims = create_initial_claims_chart(claims_data)
    st.plotly_chart(fig_claims, use_container_width=True)
    
    # Add FRED reference link
    st.markdown("[FRED Data Source: ICSA - Initial Claims for Unemployment Insurance](https://fred.stlouisfed.org/series/ICSA)")
    
    # Warning signals for Claims
    st.subheader("Warning Signals 🚨")
    st.markdown(f"""
    Current Status: {create_warning_indicator(claims_data['claims_increasing'], 0.5)} 
    {'⚠️ Claims have been rising for 3+ weeks - Consider defensive positioning' if claims_data['claims_increasing'] else '✅ Claims trend stable/decreasing - Market conditions normal'}
    
    **Key Warning Signals to Watch:**
    - Three consecutive weeks of rising claims
    - Claims rising while PCE is also rising
    - Sudden spike in claims (>10% week-over-week)
    
    **Playbook for Rising Claims:**
    - Scale back aggressive positions
    - Shift toward defensive sectors
    - Build cash reserves
    - "Small moves early beat big moves late"
    """)


def display_pce_section(pce_data):
    """
    Display the PCE section.
    
    Args:
        pce_data (dict): Dictionary with PCE data
    """
    st.header("4. Personal Consumption Expenditures (PCE) 💵")
    st.markdown("""
    **Description:** PCE is the Fed's preferred measure of inflation, tracking all spending across consumer, business, and government sectors.
    Released monthly by the Bureau of Economic Analysis.
    
    PCE tracks ALL spending:
    - Consumer spending
    - Business spending
    - Government spending
    - Includes healthcare costs insurance covers
    - Shows how people adapt to price changes
    """)
    
    # Create and display the chart
    fig_pce = create_pce_chart(pce_data)
    st.plotly_chart(fig_pce, use_container_width=True)
    
    # Add FRED reference link
    st.markdown("[FRED Data Source: PCEPI - Personal Consumption Expenditures Price Index](https://fred.stlouisfed.org/series/PCEPI)")
    
    # Warning signals for PCE
    st.subheader("Warning Signals 🚨")
    st.markdown(f"""
    Current Status: {create_warning_indicator(pce_data['current_pce'], 2.0)} 
    Current PCE YoY: {pce_data['current_pce']:.1f}%
    Current PCE MoM: {pce_data['current_pce_mom']:.2f}%
    Trend: {'Rising' if pce_data['pce_rising'] else 'Falling'}
    
    **Key Framework:**
    - PCE dropping + Stable jobs = Add risk
    - PCE rising + Rising claims = Get defensive
    
    **What PCE Tells Us:**
    - Rate trends
    - Market conditions
    - Risk appetite
    
    **Remember:** "Everyone watches CPI, but PCE guides policy."
    """)


def display_pmi_section(pmi_data):
    """
    Display the Manufacturing PMI Proxy section.
    
    Args:
        pmi_data (dict): Dictionary with PMI data
    """
    st.header("5. Manufacturing PMI Proxy 🏭")
    st.markdown("""
    **Description:** A proxy for the ISM Manufacturing PMI using FRED data.
    This index approximates manufacturing sector activity using a weighted average of key economic indicators.
    
    PMI values above 50 indicate expansion, while values below 50 indicate contraction.
    """)
    
    # Create and display the chart
    fig_pmi = create_pmi_chart(pmi_data)
    st.plotly_chart(fig_pmi, use_container_width=True)
    
    # Display PMI components
    st.subheader("PMI Components")
    component_df = create_pmi_components_table(pmi_data)
    st.dataframe(component_df, hide_index=True)
    
    # Add FRED reference links
    st.markdown("""
    **FRED Data Sources used in this proxy:**
    - [DGORDER - Manufacturers' New Orders: Durable Goods](https://fred.stlouisfed.org/series/DGORDER)
    - [INDPRO - Industrial Production Index](https://fred.stlouisfed.org/series/INDPRO)
    - [MANEMP - All Employees, Manufacturing](https://fred.stlouisfed.org/series/MANEMP)
    - [AMTMUO - Manufacturers: Unfilled Orders for All Manufacturing Industries](https://fred.stlouisfed.org/series/AMTMUO)
    - [BUSINV - Total Business Inventories](https://fred.stlouisfed.org/series/BUSINV)
    """)
    
    # Warning signals for PMI
    st.subheader("Warning Signals 🚨")
    st.markdown(f"""
    Current Status: {create_warning_indicator(pmi_data['latest_pmi'] < 50, 0.5)} 
    Current PMI Proxy Value: {pmi_data['latest_pmi']:.1f}
    
    **Key Warning Signals to Watch:**
    - PMI below 50 (indicating contraction)
    - Declining trend over multiple months
    
    **Key Insight:** "PMI is a leading indicator of manufacturing health."
    """)


def display_defensive_playbook_section():
    """
    Display the Defensive Playbook section.
    """
    st.header("Defensive Playbook 🛡️")
    st.markdown("""
    When warning signals align, consider this defensive strategy:
    
    1. **Review Tech Holdings**
       - Evaluate position sizes
       - Consider trimming high-beta names
    
    2. **Shift to Quality Stocks**
       - Focus on strong balance sheets
       - Prefer profitable companies
       - Consider defensive sectors
    
    3. **Keep Dry Powder Ready**
       - Build cash reserves
       - Wait for signals to clear
       - Prepare for opportunities
    
    4. **Risk Management**
       - Scale back aggressive positions
       - Make gradual moves
       - Stay disciplined
    
    Then return to growth when trends improve.
    """)


def display_core_principles_section():
    """
    Display the Core Principles section.
    """
    st.header("Core Principles 📋")
    st.markdown("""
    **Remember:**
    - Never trade on one signal alone
    - Wait for confirmation
    - Make gradual moves
    - Stay disciplined
    - It's not about being right - it's about being profitable
    
    **Market Dynamics:**
    - Markets are driven by simple forces: Jobs, Spending, Business activity
    - Like weather forecasting, you can't predict every storm
    - But you can spot conditions that make storms likely
    - That's what these 5 indicators do
    """)


def display_all_indicator_sections(indicators):
    """
    Display all individual indicator sections.
    
    Args:
        indicators (dict): Dictionary with all indicator data
    """
    display_hours_worked_section(indicators['hours_worked'])
    display_core_cpi_section(indicators['core_cpi'])
    display_initial_claims_section(indicators['claims'])
    display_pce_section(indicators['pce'])
    display_pmi_section(indicators['pmi'])
    display_defensive_playbook_section()
    display_core_principles_section()
