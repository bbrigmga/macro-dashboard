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


def display_hours_worked_card(hours_data):
    """
    Display the Average Weekly Hours as a card.
    
    Args:
        hours_data (dict): Dictionary with hours worked data
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


def display_core_cpi_card(core_cpi_data):
    """
    Display the Core CPI as a card.
    
    Args:
        core_cpi_data (dict): Dictionary with Core CPI data
    """
    # Calculate current value and status
    current_cpi_mom = core_cpi_data['current_cpi_mom']
    recent_cpi_mom = core_cpi_data['recent_cpi_mom']
    
    # Determine status based on consecutive increases/decreases
    cpi_increasing = all(recent_cpi_mom[i] < recent_cpi_mom[i+1] for i in range(len(recent_cpi_mom)-3, len(recent_cpi_mom)-1))
    cpi_decreasing = all(recent_cpi_mom[i] > recent_cpi_mom[i+1] for i in range(len(recent_cpi_mom)-3, len(recent_cpi_mom)-1))
    
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


def display_initial_claims_card(claims_data):
    """
    Display the Initial Jobless Claims as a card.
    
    Args:
        claims_data (dict): Dictionary with claims data
    """
    # Calculate current value and status
    current_claims = claims_data['data']['Claims'].iloc[-1]
    claims_increasing = claims_data['claims_increasing']
    claims_decreasing = claims_data['claims_decreasing']
    
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
        st.subheader("📈 Initial Jobless Claims")
        
        # Status below the title
        if status == "Bearish":
            st.markdown(f"<div style='color: #f44336; margin: 0; font-size: 1.1rem; font-weight: 600;'>↓ {status}</div>", unsafe_allow_html=True)
        elif status == "Bullish":
            st.markdown(f"<div style='color: #00c853; margin: 0; font-size: 1.1rem; font-weight: 600;'>↑ {status}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='color: #78909c; margin: 0; font-size: 1.1rem; font-weight: 600;'>→ {status}</div>", unsafe_allow_html=True)
        
        # Current value below the status in black text
        st.markdown(f"<div style='color: #000000; font-size: 0.9rem;'>{current_claims:,.0f}</div>", unsafe_allow_html=True)
        
        # Create and display the chart
        fig_claims = create_initial_claims_chart(claims_data)
        st.plotly_chart(fig_claims, use_container_width=True, height=250)
        
        # Expandable details section
        with st.expander("View Details"):
            st.write("Initial Jobless Claims show how many people filed for unemployment for the first time in a given week. Released every Thursday by the Department of Labor.")
            st.markdown(generate_initial_claims_warning(claims_data), unsafe_allow_html=True)
            st.markdown("[FRED Data: ICSA - Initial Claims for Unemployment Insurance](https://fred.stlouisfed.org/series/ICSA)")


def display_pce_card(pce_data):
    """
    Display the PCE as a card.
    
    Args:
        pce_data (dict): Dictionary with PCE data
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


def display_pmi_card(pmi_data):
    """
    Display the Manufacturing PMI Proxy as a card.
    
    Args:
        pmi_data (dict): Dictionary with PMI data
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


def display_usd_liquidity_card(usd_liquidity_data):
    """
    Display the USD Liquidity as a card.
    
    Args:
        usd_liquidity_data (dict): Dictionary with USD Liquidity data
    """
    # Calculate current value and status
    current_liquidity = usd_liquidity_data['current_liquidity']
    liquidity_increasing = usd_liquidity_data['liquidity_increasing']
    liquidity_decreasing = usd_liquidity_data['liquidity_decreasing']
    
    # Determine status based on trend
    # For USD Liquidity, increasing is generally bullish for markets
    if liquidity_increasing:
        status = "Bullish"
        delta_color = "normal"
    elif liquidity_decreasing:
        status = "Bearish"
        delta_color = "inverse"
    else:
        status = "Neutral"
        delta_color = "off"
    
    with st.container():
        # Title at the top
        st.subheader("💵 USD Liquidity")
        
        # Status below the title
        if status == "Bearish":
            st.markdown(f"<div style='color: #f44336; margin: 0; font-size: 1.1rem; font-weight: 600;'>↓ {status}</div>", unsafe_allow_html=True)
        elif status == "Bullish":
            st.markdown(f"<div style='color: #00c853; margin: 0; font-size: 1.1rem; font-weight: 600;'>↑ {status}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='color: #78909c; margin: 0; font-size: 1.1rem; font-weight: 600;'>→ {status}</div>", unsafe_allow_html=True)
        
        # Current value below the status in black text
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
                    walcl_formatted = f"{walcl/1000000:.2f}T"  # Trillions
                elif walcl >= 1000:
                    walcl_formatted = f"{walcl/1000:.2f}B"  # Billions
                else:
                    walcl_formatted = f"{walcl:,.0f}M"  # Millions
                
                # RRPONTTLD and WTREGEN are already in billions, but we'll convert to display format
                rrponttld_formatted = f"{rrponttld:.2f}B"  # Billions
                wtregen_formatted = f"{wtregen:.2f}B"  # Billions
                
                # Calculate the result (should match current_liquidity)
                # Convert RRPONTTLD and WTREGEN from billions to millions for calculation
                result = walcl - (rrponttld * 1000) - (wtregen * 1000)
                if result >= 1000000:
                    result_formatted = f"{result/1000000:.2f}T"  # Trillions
                elif result >= 1000:
                    result_formatted = f"{result/1000:.2f}B"  # Billions
                else:
                    result_formatted = f"{result:,.0f}M"  # Millions
                
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
            
            st.markdown(generate_usd_liquidity_warning(usd_liquidity_data), unsafe_allow_html=True)
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


def display_new_orders_card(new_orders_data):
    """
    Display a card with Non-Defense Durable Goods Orders data and chart.
    
    Args:
        new_orders_data (dict): Dictionary with New Orders data
    """
    st.subheader("📦 Non-Defense Durable Goods Orders")
    
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
    
    # Display status
    if status == "Bearish":
        st.markdown(f"<div style='color: #f44336; margin: 0; font-size: 1.1rem; font-weight: 600;'>↓ {status}</div>", unsafe_allow_html=True)
    elif status == "Bullish":
        st.markdown(f"<div style='color: #00c853; margin: 0; font-size: 1.1rem; font-weight: 600;'>↑ {status}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div style='color: #78909c; margin: 0; font-size: 1.1rem; font-weight: 600;'>→ {status}</div>", unsafe_allow_html=True)
    
    # Display metric with delta
    st.metric(
        label="MoM % Change",
        value=f"{latest_value:.1f}%",
        delta=f"{delta:.1f}%",
        delta_color=delta_color
    )
    
    # Add chart
    fig = create_new_orders_chart(new_orders_data)
    st.plotly_chart(fig, use_container_width=True)
    
    # Expandable details section
    with st.expander("View Details"):
        st.write("Non-Defense Durable Goods Orders represents new orders placed with domestic manufacturers for delivery of non-defense capital goods. It's a leading indicator of manufacturing activity and business investment.")
        st.markdown("[FRED Data: NEWORDER - Manufacturers' New Orders: Durable Goods](https://fred.stlouisfed.org/series/NEWORDER)")


def display_yield_curve_card(yield_curve_data):
    """
    Display a card with 10Y-2Y Treasury Yield Spread data and chart.
    
    Args:
        yield_curve_data (dict): Dictionary with yield curve data
    """
    st.subheader("📊 10Y-2Y Treasury Yield Spread")
    
    # Get latest value and determine status
    latest_value = yield_curve_data['latest_value']
    previous_value = yield_curve_data['recent_values'][-2] if len(yield_curve_data['recent_values']) > 1 else 0
    delta = latest_value - previous_value
    
    # Determine status based on inversion (negative spread is bearish)
    if latest_value < 0:
        status = "Bearish"
        delta_color = "inverse"
    elif latest_value > 0.5:  # Healthy spread
        status = "Bullish"
        delta_color = "normal"
    else:  # Low but positive spread
        status = "Neutral"
        delta_color = "off"
    
    # Display status
    if status == "Bearish":
        st.markdown(f"<div style='color: #f44336; margin: 0; font-size: 1.1rem; font-weight: 600;'>↓ {status}</div>", unsafe_allow_html=True)
    elif status == "Bullish":
        st.markdown(f"<div style='color: #00c853; margin: 0; font-size: 1.1rem; font-weight: 600;'>↑ {status}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div style='color: #78909c; margin: 0; font-size: 1.1rem; font-weight: 600;'>→ {status}</div>", unsafe_allow_html=True)
    
    # Display metric with delta
    st.metric(
        label="Spread (%)",
        value=f"{latest_value:.2f}%",
        delta=f"{delta:.2f}%",
        delta_color=delta_color
    )
    
    # Add chart
    fig = create_yield_curve_chart(yield_curve_data)
    st.plotly_chart(fig, use_container_width=True)
    
    # Expandable details section
    with st.expander("View Details"):
        st.write("The 10Y-2Y Treasury Yield Spread is the difference between 10-year and 2-year Treasury yields. A negative spread (yield curve inversion) has historically preceded recessions.")
        st.markdown("[FRED Data: T10Y2Y - 10-Year Treasury Minus 2-Year Treasury](https://fred.stlouisfed.org/series/T10Y2Y)")
