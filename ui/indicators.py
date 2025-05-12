"""
Functions for creating the individual indicator cards with a modern finance-based UI.
"""
import streamlit as st
from visualization.indicators import (
    create_hours_worked_chart,
    create_core_cpi_chart,
    create_initial_claims_chart,
    create_pce_chart,
    create_pmi_chart,
    create_pmi_components_table,
    create_usd_liquidity_chart,
    create_new_orders_chart,
    create_yield_curve_chart
)
from visualization.warning_signals import (
    generate_hours_worked_warning,
    generate_core_cpi_warning,
    generate_initial_claims_warning,
    generate_pce_warning,
    generate_pmi_warning,
    generate_usd_liquidity_warning,
    create_warning_indicator
)
from data.release_schedule import get_next_release_date, format_release_date
from data.fred_client import FredClient


def display_hours_worked_card(hours_data, fred_client=None):
    """
    Display the Average Weekly Hours as a card.
    
    Args:
        hours_data (dict): Dictionary with hours worked data
        fred_client (FredClient, optional): FRED API client for getting release dates
    """
    # Calculate current value and status
    current_hours = hours_data['recent_hours'][-1]
    consecutive_declines = hours_data['consecutive_declines']
    
    # Determine status
    if consecutive_declines >= 3:
        status = "Bearish"
        delta_color = "inverse"
    elif hours_data['consecutive_increases'] >= 3:
        status = "Bullish"
        delta_color = "normal"
    else:
        status = "Neutral"
        delta_color = "off"
    
    with st.container():
        # Title at the top
        st.subheader("🕒 Average Weekly Hours")
        
        # Add release date info
        next_release = get_next_release_date('hours', fred_client)
        st.caption(format_release_date(next_release))
        
        # Status below the title
        if status == "Bearish":
            st.markdown(f"<div style='color: #f44336; margin: 0; font-size: 1.1rem; font-weight: 600;'>↓ {status}</div>", unsafe_allow_html=True)
        elif status == "Bullish":
            st.markdown(f"<div style='color: #00c853; margin: 0; font-size: 1.1rem; font-weight: 600;'>↑ {status}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='color: #78909c; margin: 0; font-size: 1.1rem; font-weight: 600;'>→ {status}</div>", unsafe_allow_html=True)
        
        # Current value below the status in black text
        st.markdown(f"<div style='color: #000000; font-size: 0.9rem;'>{current_hours:.1f} hours</div>", unsafe_allow_html=True)
        
        # Create and display the chart
        fig_hours = create_hours_worked_chart(hours_data)
        st.plotly_chart(fig_hours, use_container_width=True, height=250)
        
        # Expandable details section
        with st.expander("View Details"):
            st.write("Average weekly hours of all employees in the private sector. Declining trend signals reduced economic activity.")
            st.markdown(generate_hours_worked_warning(hours_data), unsafe_allow_html=True)
            st.markdown("[FRED Data: AWHAETP - Average Weekly Hours](https://fred.stlouisfed.org/series/AWHAETP)")


def display_core_cpi_card(core_cpi_data, fred_client=None):
    """
    Display the Core CPI as a card.
    
    Args:
        core_cpi_data (dict): Dictionary with Core CPI data
        fred_client (FredClient, optional): FRED API client for getting release dates
    """
    # Calculate current value and status
    current_cpi_mom = core_cpi_data['current_cpi_mom']
    recent_cpi_mom = core_cpi_data['recent_cpi_mom']
    
    # Determine status based on cpi_increasing and cpi_decreasing flags
    cpi_increasing = core_cpi_data.get('cpi_increasing', False)
    cpi_decreasing = core_cpi_data.get('cpi_decreasing', False)
    
    if cpi_increasing:
        status = "Bearish"
        delta_color = "inverse"
    elif cpi_decreasing:
        status = "Bullish"
        delta_color = "normal"
    else:
        status = "Neutral"
        delta_color = "off"
    
    with st.container():
        # Title at the top
        st.subheader("📊 Core CPI")
        
        # Add release date info
        next_release = get_next_release_date('core_cpi', fred_client)
        st.caption(format_release_date(next_release))
        
        # Status below the title
        if status == "Bearish":
            st.markdown(f"<div style='color: #f44336; margin: 0; font-size: 1.1rem; font-weight: 600;'>↓ {status}</div>", unsafe_allow_html=True)
        elif status == "Bullish":
            st.markdown(f"<div style='color: #00c853; margin: 0; font-size: 1.1rem; font-weight: 600;'>↑ {status}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='color: #78909c; margin: 0; font-size: 1.1rem; font-weight: 600;'>→ {status}</div>", unsafe_allow_html=True)
        
        # Current value below the status in black text
        st.markdown(f"<div style='color: #000000; font-size: 0.9rem;'>{current_cpi_mom:.2f}%</div>", unsafe_allow_html=True)
        
        # Create and display the chart
        fig_cpi = create_core_cpi_chart(core_cpi_data)
        st.plotly_chart(fig_cpi, use_container_width=True, height=250)
        
        # Expandable details section
        with st.expander("View Details"):
            st.write("Core CPI measures inflation excluding volatile food and energy prices, providing a clearer picture of underlying inflation trends.")
            st.markdown(generate_core_cpi_warning(core_cpi_data), unsafe_allow_html=True)
            st.markdown("[FRED Data: CPILFESL - Core Consumer Price Index](https://fred.stlouisfed.org/series/CPILFESL)")


def display_initial_claims_card(claims_data, fred_client=None):
    """
    Display the Initial Claims as a card.
    
    Args:
        claims_data (dict): Dictionary with claims data
        fred_client (FredClient, optional): FRED API client for getting release dates
    """
    # Calculate current value and status
    current_claims = claims_data['current_value']
    
    # Determine status based on consecutive increases/decreases
    claims_increasing = claims_data.get('claims_increasing', False)
    claims_decreasing = claims_data.get('claims_decreasing', False)
    
    if claims_increasing:
        status = "Bearish"
        delta_color = "inverse"
    elif claims_decreasing:
        status = "Bullish"
        delta_color = "normal"
    else:
        status = "Neutral"
        delta_color = "off"
    
    with st.container():
        # Title at the top
        st.subheader("🏢 Initial Claims")
        
        # Add release date info
        next_release = get_next_release_date('claims', fred_client)
        st.caption(format_release_date(next_release))
        
        # Status below the title
        if status == "Bearish":
            st.markdown(f"<div style='color: #f44336; margin: 0; font-size: 1.1rem; font-weight: 600;'>↓ {status}</div>", unsafe_allow_html=True)
        elif status == "Bullish":
            st.markdown(f"<div style='color: #00c853; margin: 0; font-size: 1.1rem; font-weight: 600;'>↑ {status}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='color: #78909c; margin: 0; font-size: 1.1rem; font-weight: 600;'>→ {status}</div>", unsafe_allow_html=True)
        
        # Current value below the status in black text
        st.markdown(f"<div style='color: #000000; font-size: 0.9rem;'>{int(current_claims):,}</div>", unsafe_allow_html=True)
        
        # Create and display the chart
        fig_claims = create_initial_claims_chart(claims_data)
        st.plotly_chart(fig_claims, use_container_width=True, height=250)
        
        # Expandable details section
        with st.expander("View Details"):
            st.write("Initial Claims measures the number of people filing for unemployment benefits for the first time. Rising claims can signal a weakening job market.")
            st.markdown(generate_initial_claims_warning(claims_data), unsafe_allow_html=True)
            st.markdown("[FRED Data: ICSA - Initial Claims](https://fred.stlouisfed.org/series/ICSA)")


def display_pce_card(pce_data, fred_client=None):
    """
    Display the PCE as a card.
    
    Args:
        pce_data (dict): Dictionary with PCE data
        fred_client (FredClient, optional): FRED API client for getting release dates
    """
    # Calculate current value and status
    current_pce_mom = pce_data['current_pce_mom']
    pce_increasing = pce_data['pce_increasing']
    pce_decreasing = pce_data['pce_decreasing']
    
    if pce_increasing:
        status = "Bearish"
        delta_color = "inverse"
    elif pce_decreasing:
        status = "Bullish"
        delta_color = "normal"
    else:
        status = "Neutral"
        delta_color = "off"
    
    with st.container():
        # Title at the top
        st.subheader("💵 PCE")
        
        # Add release date info
        next_release = get_next_release_date('pce', fred_client)
        st.caption(format_release_date(next_release))
        
        # Status below the title
        if status == "Bearish":
            st.markdown(f"<div style='color: #f44336; margin: 0; font-size: 1.1rem; font-weight: 600;'>↓ {status}</div>", unsafe_allow_html=True)
        elif status == "Bullish":
            st.markdown(f"<div style='color: #00c853; margin: 0; font-size: 1.1rem; font-weight: 600;'>↑ {status}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='color: #78909c; margin: 0; font-size: 1.1rem; font-weight: 600;'>→ {status}</div>", unsafe_allow_html=True)
        
        # Current value below the status in black text
        st.markdown(f"<div style='color: #000000; font-size: 0.9rem;'>{current_pce_mom:.2f}%</div>", unsafe_allow_html=True)
        
        # Create and display the chart
        fig_pce = create_pce_chart(pce_data)
        st.plotly_chart(fig_pce, use_container_width=True, height=250)
        
        # Expandable details section
        with st.expander("View Details"):
            st.write("PCE is the Fed's preferred measure of inflation, tracking all spending across consumer, business, and government sectors.")
            st.markdown(generate_pce_warning(pce_data), unsafe_allow_html=True)
            st.markdown("[FRED Data: PCE - Personal Consumption Expenditures](https://fred.stlouisfed.org/series/PCE)")


def display_pmi_card(pmi_data, fred_client=None):
    """
    Display the Manufacturing PMI Proxy as a card.
    
    Args:
        pmi_data (dict): Dictionary with PMI data
        fred_client (FredClient, optional): FRED API client for getting release dates
    """
    # Calculate current value and status
    latest_pmi = pmi_data['latest_pmi']
    
    if latest_pmi < 50:
        status = "Bearish"
        delta_color = "inverse"
    else:
        status = "Bullish"
        delta_color = "normal"
    
    with st.container():
        # Title at the top
        st.subheader("🏭 Manufacturing PMI Proxy")
        
        # Add release date info
        next_release = get_next_release_date('pmi', fred_client)
        st.caption(format_release_date(next_release))
        
        # Status below the title
        if status == "Bearish":
            st.markdown(f"<div style='color: #f44336; margin: 0; font-size: 1.1rem; font-weight: 600;'>↓ {status}</div>", unsafe_allow_html=True)
        elif status == "Bullish":
            st.markdown(f"<div style='color: #00c853; margin: 0; font-size: 1.1rem; font-weight: 600;'>↑ {status}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='color: #78909c; margin: 0; font-size: 1.1rem; font-weight: 600;'>→ {status}</div>", unsafe_allow_html=True)
        
        # Current value below the status in black text
        st.markdown(f"<div style='color: #000000; font-size: 0.9rem;'>{latest_pmi:.1f}</div>", unsafe_allow_html=True)
        
        # Create and display the chart
        fig_pmi = create_pmi_chart(pmi_data)
        st.plotly_chart(fig_pmi, use_container_width=True, height=250)
        
        # Expandable details section
        with st.expander("View Details"):
            st.write("A proxy for the ISM Manufacturing PMI using FRED data. PMI values above 50 indicate expansion, below 50 indicate contraction.")
            st.markdown(generate_pmi_warning(pmi_data), unsafe_allow_html=True)
            
            # Display PMI components in a compact table
            st.subheader("PMI Components")
            component_df = create_pmi_components_table(pmi_data)
            st.write(component_df)
            
            st.markdown("""
            FRED Data Sources: 
            - [AMTMNO - Manufacturing: New Orders](https://fred.stlouisfed.org/series/AMTMNO)
            - [IPMAN - Industrial Production: Manufacturing](https://fred.stlouisfed.org/series/IPMAN)
            - [MANEMP - Manufacturing Employment](https://fred.stlouisfed.org/series/MANEMP)
            - [AMDMUS - Manufacturing: Supplier Deliveries](https://fred.stlouisfed.org/series/AMDMUS)
            - [MNFCTRIMSA - Manufacturing Inventories (Seasonally Adjusted)](https://fred.stlouisfed.org/series/MNFCTRIMSA)
            """)


def display_usd_liquidity_card(usd_liquidity_data, fred_client=None):
    """
    Display the USD Liquidity as a card.
    
    Args:
        usd_liquidity_data (dict): Dictionary with USD Liquidity data
        fred_client (FredClient, optional): FRED API client for getting release dates
    """
    # Calculate current value
    current_liquidity = usd_liquidity_data['current_liquidity']
    
    with st.container():
        # Title at the top
        st.subheader("💵 USD Liquidity")
        
        # Current value below the title in black text
        # Format large number with commas and B for billions or T for trillions
        if current_liquidity >= 1000000:
            formatted_value = f"{current_liquidity/1000000:.2f}T"  # Trillions
        elif current_liquidity >= 1000:
            formatted_value = f"{current_liquidity/1000:.2f}B"  # Billions
        else:
            formatted_value = f"{current_liquidity:,.0f}M"  # Millions
        st.markdown(f"<div style='color: #000000; font-size: 0.9rem;'>{formatted_value}</div>", unsafe_allow_html=True)
        
        # Create and display the chart
        fig_liquidity = create_usd_liquidity_chart(usd_liquidity_data)
        st.plotly_chart(fig_liquidity, use_container_width=True, height=250)
        
        # Expandable details section
        with st.expander("View Details"):
            st.write("USD Liquidity is calculated as: Fed Balance Sheet - Reverse Repo - Treasury General Account")
            
            # Display the actual values used in the calculation
            if 'details' in usd_liquidity_data:
                # Get the values from the details dictionary
                walcl = usd_liquidity_data['details'].get('WALCL', 0)
                rrponttld = usd_liquidity_data['details'].get('RRPONTTLD', 0)
                wtregen = usd_liquidity_data['details'].get('WTREGEN', 0)
                
                # Check for NaN values and replace with zeros
                import numpy as np
                walcl = 0 if np.isnan(walcl) else walcl
                rrponttld = 0 if np.isnan(rrponttld) else rrponttld
                wtregen = 0 if np.isnan(wtregen) else wtregen
                
                # Format the values for display
                if walcl >= 1000000:
                    walcl_formatted = f"{walcl/1000000:.2f}T"  # Convert millions to trillions
                elif walcl >= 1000:
                    walcl_formatted = f"{walcl/1000:.2f}B"  # Billions
                else:
                    walcl_formatted = f"{walcl:,.0f}M"  # Millions
                
                # RRPONTTLD and WTREGEN are already in billions, but we'll convert to display format
                rrponttld_formatted = f"{rrponttld:.2f}B"  # Billions
                wtregen_formatted = f"{wtregen:.2f}B"  # Billions
                
                # Calculate the result (should match current_liquidity)
                # WALCL is in millions, RRPONTTLD and WTREGEN are in billions
                result = walcl - (rrponttld * 1000) - (wtregen * 1000)
                if result >= 1000000:
                    result_formatted = f"{result/1000000:.2f}T"  # Trillions
                elif result >= 1000:
                    result_formatted = f"{result/1000:.2f}B"  # Billions
                else:
                    result_formatted = f"{result:,.0f}M"  # Millions
                
                # Format WALCL (which is in millions) to trillions for display
                walcl_formatted = f"{walcl/1000000:.2f}T"  # Convert millions to trillions
                
                # Display the calculation with actual values
                st.markdown("""
                <div style='background-color: #f5f5f5; padding: 10px; border-radius: 5px;'>
                <b>Latest Data Point Calculation:</b><br>
                Fed Balance Sheet: {} <br>
                - Reverse Repo: {} <br>
                - Treasury General Account: {} <br>
                = USD Liquidity: {}
                </div>
                """.format(walcl_formatted, rrponttld_formatted, wtregen_formatted, result_formatted), 
                unsafe_allow_html=True)
            
            st.markdown("""
            FRED Data Sources:
            [WALCL](https://fred.stlouisfed.org/series/WALCL) - Fed Balance Sheet (millions),
            [RRPONTTLD](https://fred.stlouisfed.org/series/RRPONTTLD) - Reverse Repo (billions),
            [WTREGEN](https://fred.stlouisfed.org/series/WTREGEN) - Treasury General Account (billions),
            [SP500](https://fred.stlouisfed.org/series/SP500) - S&P 500 Index
            """)
            
            st.write("The chart displays USD Liquidity (left axis) alongside the S&P 500 Index (right axis) to visualize the relationship between market liquidity and equity market performance.")


def display_core_principles_card():
    """
    Display the Core Principles as a card.
    """
    with st.container():
        st.subheader("📋 Core Principles")
        
        st.markdown("**Remember:**")
        st.markdown("- Never trade on one signal alone")
        st.markdown("- Wait for confirmation")
        st.markdown("- Make gradual moves")
        st.markdown("- Stay disciplined")
        
        st.markdown("**Market Dynamics:**")
        st.markdown("- Markets are driven by simple forces: Jobs, Spending, Business activity")
        st.markdown("- Like weather forecasting, you can't predict every storm")
        st.markdown("- But you can spot conditions that make storms likely")


def display_new_orders_card(new_orders_data, fred_client=None):
    """
    Display a card with Non-Defense Durable Goods Orders data and chart.
    
    Args:
        new_orders_data (dict): Dictionary with New Orders data
        fred_client (FredClient, optional): FRED API client for getting release dates
    """
    with st.container():
        # Title at the top
        st.subheader("📦 Non-Defense Durable Goods Orders")
        
        # Add release date info
        next_release = get_next_release_date('new_orders', fred_client)
        st.caption(format_release_date(next_release))
        
        # Get latest value and determine status
        latest_value = new_orders_data['latest_value']
        previous_period = new_orders_data['recent_mom_values'][-2] if len(new_orders_data['recent_mom_values']) > 1 else 0
        delta = latest_value - previous_period
        
        # Determine status based on latest value and trend
        if latest_value > 0 and new_orders_data.get('mom_increasing', False):
            status = "Bullish"
            delta_color = "normal"
        elif latest_value < 0 and new_orders_data.get('mom_decreasing', False):
            status = "Bearish"
            delta_color = "inverse"
        else:
            status = "Neutral"
            delta_color = "off"
        
        # Status below the title
        if status == "Bearish":
            st.markdown(f"<div style='color: #f44336; margin: 0; font-size: 1.1rem; font-weight: 600;'>↓ {status}</div>", unsafe_allow_html=True)
        elif status == "Bullish":
            st.markdown(f"<div style='color: #00c853; margin: 0; font-size: 1.1rem; font-weight: 600;'>↑ {status}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='color: #78909c; margin: 0; font-size: 1.1rem; font-weight: 600;'>→ {status}</div>", unsafe_allow_html=True)
        
        # Current value below the status in black text
        st.markdown(f"<div style='color: #000000; font-size: 0.9rem;'>{latest_value:.1f}%</div>", unsafe_allow_html=True)
        
        # Add chart
        fig = create_new_orders_chart(new_orders_data)
        st.plotly_chart(fig, use_container_width=True, height=250)
        
        # Expandable details section
        with st.expander("View Details"):
            st.write("Non-Defense Durable Goods Orders represents new orders placed with domestic manufacturers for delivery of non-defense capital goods. It's a leading indicator of manufacturing activity and business investment.")
            st.markdown("[FRED Data: NEWORDER - Manufacturers' New Orders: Durable Goods](https://fred.stlouisfed.org/series/NEWORDER)")


def display_yield_curve_card(yield_curve_data, fred_client=None):
    """
    Display a card with the 2-10 Year Treasury Yield Spread.
    
    Args:
        yield_curve_data (dict): Dictionary with yield curve data
        fred_client (FredClient, optional): FRED API client for getting release dates
    """
    # Global chart height constant for the entire row
    CHART_HEIGHT = 250  # Same height as USD Liquidity chart
    
    # Calculate current value
    if 'data' in yield_curve_data and not yield_curve_data['data'].empty:
        current_spread = yield_curve_data['data']['T10Y2Y'].iloc[-1]
    else:
        current_spread = 0
    
    with st.container():
        # Title at the top - use subheader like USD Liquidity
        st.subheader("📈 2-10 Year Spread")
        
        # Current value - use same styling as USD Liquidity
        st.markdown(f"<div style='color: #000000; font-size: 0.9rem;'>{current_spread:.2f}%</div>", unsafe_allow_html=True)
        
        # Create and display chart
        fig = create_yield_curve_chart(yield_curve_data)
        st.plotly_chart(fig, use_container_width=True, height=CHART_HEIGHT)
        
        # Expandable details section - use same label as USD Liquidity
        with st.expander("View Details"):
            st.markdown("<small>10Y-2Y Treasury yield spread</small>", unsafe_allow_html=True)
