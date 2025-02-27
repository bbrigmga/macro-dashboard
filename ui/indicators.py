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
from visualization.warning_signals import (
    generate_hours_worked_warning,
    generate_core_cpi_warning,
    generate_initial_claims_warning,
    generate_pce_warning,
    generate_pmi_warning
)


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
    st.markdown(generate_hours_worked_warning(hours_data))


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
    st.markdown(generate_core_cpi_warning(core_cpi_data))


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
    st.markdown(generate_initial_claims_warning(claims_data))


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
    st.markdown(generate_pce_warning(pce_data))


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
    st.markdown(generate_pmi_warning(pmi_data))


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
