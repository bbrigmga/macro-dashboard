"""
Enhanced USD Liquidity indicator display function.
This file provides an improved version of the display_usd_liquidity_card function
with more detailed information in the dropdown menu.
"""
import streamlit as st
import pandas as pd
import numpy as np
from data.release_schedule import get_next_release_date, format_release_date

def enhanced_display_usd_liquidity_card(usd_liquidity_data, fred_client=None):
    """
    Display the USD Liquidity as a card with enhanced details.
    
    Args:
        usd_liquidity_data (dict): Dictionary with USD Liquidity data
        fred_client (FredClient, optional): FRED API client for getting release dates
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
        
        # Add release date info
        next_release = get_next_release_date('liquidity', fred_client)
        st.caption(format_release_date(next_release))
        
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
        
        # Import the chart creation function
        from visualization.indicators import create_usd_liquidity_chart
        
        # Create and display the chart
        fig_liquidity = create_usd_liquidity_chart(usd_liquidity_data)
        st.plotly_chart(fig_liquidity, use_container_width=True, height=250)
        
        # Expandable details section with enhanced content
        with st.expander("View Details"):
            st.write("USD Liquidity is calculated as: Fed Balance Sheet - Reverse Repo - Treasury General Account")
            
            # Display the actual values used in the calculation
            if 'details' in usd_liquidity_data:
                # Get the values from the details dictionary
                walcl = usd_liquidity_data['details'].get('WALCL', 0)
                rrponttld = usd_liquidity_data['details'].get('RRPONTTLD', 0)
                wtregen = usd_liquidity_data['details'].get('WTREGEN', 0)
                
                # Check for NaN values and replace with zeros
                walcl = 0 if np.isnan(walcl) else walcl
                rrponttld = 0 if np.isnan(rrponttld) else rrponttld
                wtregen = 0 if np.isnan(wtregen) else wtregen
                
                # Format WALCL (which is in millions) to trillions for display
                walcl_formatted = f"{walcl/1000000:.2f}T"  # Convert millions to trillions
                
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
            
            # Import the warning generation function
            from ui.indicators import generate_usd_liquidity_warning
            st.markdown(generate_usd_liquidity_warning(usd_liquidity_data), unsafe_allow_html=True)
            
            # Add detailed explanation of USD Liquidity
            st.subheader("What is USD Liquidity?")
            st.markdown("""
            USD Liquidity represents the amount of dollars available in the financial system that can be used to purchase assets. 
            It's a key driver of asset prices across markets, particularly equities and risk assets.
            
            **Components Explained:**
            """)
            
            # Create a components explanation table
            components_data = {
                'Component': ['Fed Balance Sheet (WALCL)', 'Reverse Repo (RRPONTTLD)', 'Treasury General Account (WTREGEN)'],
                'Description': [
                    'Total assets held by the Federal Reserve, including bonds, mortgage-backed securities, and other financial instruments.',
                    'Amount of money that financial institutions park at the Fed overnight, temporarily removing it from the system.',
                    'The U.S. Treasury\'s checking account at the Fed. When the Treasury receives tax payments or issues bonds, the money sits here before being spent.'
                ],
                'Impact': [
                    'INCREASES liquidity when it grows (Fed buying assets = adding money to system)',
                    'DECREASES liquidity when it grows (money parked at Fed = not in financial system)',
                    'DECREASES liquidity when it grows (money sitting idle = not in financial system)'
                ]
            }
            
            components_df = pd.DataFrame(components_data)
            st.table(components_df)
            
            st.subheader("Market Interpretation")
            st.markdown("""
            **Rising USD Liquidity (Bullish):**
            - Typically supports higher asset prices, especially equities and risk assets
            - Often leads to increased market risk appetite and lower volatility
            - Historically associated with higher P/E ratios and tighter credit spreads
            
            **Falling USD Liquidity (Bearish):**
            - May lead to market stress, lower asset prices, and increased volatility
            - Often precedes economic slowdowns or market corrections
            - Can trigger risk-off sentiment and flight to quality assets
            
            **Important Notes:**
            - Changes in USD Liquidity often lead market movements by 1-3 months
            - The relationship is strongest during periods of stress or significant policy changes
            - Local liquidity conditions can sometimes override global liquidity trends
            """)
            
            st.markdown("""
            FRED Data Sources:
            - [WALCL](https://fred.stlouisfed.org/series/WALCL) - Fed Balance Sheet (millions)
            - [RRPONTTLD](https://fred.stlouisfed.org/series/RRPONTTLD) - Reverse Repo (billions)
            - [WTREGEN](https://fred.stlouisfed.org/series/WTREGEN) - Treasury General Account (billions)
            - [SP500](https://fred.stlouisfed.org/series/SP500) - S&P 500 Index
            """)
            
            st.write("The chart displays USD Liquidity (left axis) alongside the S&P 500 Index (right axis) to visualize the relationship between market liquidity and equity market performance.")
