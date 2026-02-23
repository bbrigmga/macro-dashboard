"""
Functions for creating the individual indicator cards with a modern finance-based UI.
"""
import streamlit as st
from visualization.indicators import (
    create_indicator_chart,
    create_pmi_components_table
)
from visualization.warning_signals import (
    generate_pmi_warning,
    generate_usd_liquidity_warning,
    create_warning_indicator,
    generate_indicator_warning
)
from data.release_schedule import get_next_release_date, format_release_date
from data.fred_client import FredClient
from data.processing import validate_indicator_data
from src.config.indicator_registry import INDICATOR_REGISTRY

CARD_CHART_HEIGHT = 360


def _render_status_badge(status: str) -> None:
    """
    Render colored status badge (Bullish/Bearish/Neutral).
    
    Args:
        status: The status to display ("Bullish", "Bearish", "Neutral")
    """
    colors = {"Bearish": "#f44336", "Bullish": "#00c853"}
    arrows = {"Bearish": "↓", "Bullish": "↑"}
    color = colors.get(status, "#78909c")  # Default to grey for Neutral
    arrow = arrows.get(status, "→")  # Default to right arrow for Neutral
    
    st.markdown(
        f"<div style='color: {color}; margin: 0; font-size: 1.1rem; font-weight: 600;'>{arrow} {status}</div>", 
        unsafe_allow_html=True
    )


def display_indicator_card(indicator_key: str, data: dict, fred_client=None) -> None:
    """
    Generic indicator card renderer driven by the registry.
    
    Args:
        indicator_key: Key of the indicator in the registry (e.g., "initial_claims")
        data: Dictionary containing indicator data
        fred_client: Optional FRED client for release dates
    """
    config = INDICATOR_REGISTRY[indicator_key]
    
    with st.container():
        # Title at the top
        st.subheader(f"{config.emoji} {config.display_name}")
        
        # Add release date info
        next_release = get_next_release_date(indicator_key, fred_client)
        st.caption(format_release_date(next_release))
        
        # Validate indicator data
        if not validate_indicator_data(data, config):
            st.warning("⚠️ Data unavailable or invalid for this indicator")
            return
        
        # Generate warning/status information
        warning = generate_indicator_warning(data, config)
        status = warning["status"]
        
        # Render status badge
        _render_status_badge(status)
        
        # Display current value - try to extract from data
        current_value = None
        if 'current_value' in data:
            current_value = data['current_value']
        elif f'current_{indicator_key}' in data:
            current_value = data[f'current_{indicator_key}']
        elif 'latest_value' in data:
            current_value = data['latest_value']
        elif f'latest_{indicator_key}' in data:
            current_value = data[f'latest_{indicator_key}']
        elif f'{indicator_key}_data' in data and isinstance(data[f'{indicator_key}_data'], dict):
            inner_data = data[f'{indicator_key}_data']
            if 'current_value' in inner_data:
                current_value = inner_data['current_value']
        
        # Special handling for specific indicators based on their known data structure
        if indicator_key == "initial_claims" and current_value is None:
            current_value = data.get('current_value')
        elif indicator_key == "hours_worked" and current_value is None:
            recent_hours = data.get('recent_hours', [])
            if len(recent_hours) > 0:
                current_value = recent_hours[-1]
        elif indicator_key == "core_cpi" and current_value is None:
            current_value = data.get('current_cpi_mom')
        elif indicator_key == "pce" and current_value is None:
            current_value = data.get('current_pce_mom')
        elif indicator_key == "pmi_proxy" and current_value is None:
            current_value = data.get('latest_pmi')
        elif indicator_key == "usd_liquidity" and current_value is None:
            current_value = data.get('current_liquidity')
        
        # Format and display the current value
        if current_value is not None:
            if indicator_key == "initial_claims":
                formatted_value = f"{int(current_value):,}"
            elif indicator_key == "hours_worked":
                formatted_value = f"{current_value:.1f} hours"
            elif indicator_key in ["core_cpi", "pce"]:
                formatted_value = f"{current_value:.2f}%"
            elif indicator_key == "pmi_proxy":
                formatted_value = f"{current_value:.1f}"
            elif indicator_key == "usd_liquidity":
                # Format large numbers
                if current_value >= 1000000:
                    formatted_value = f"{current_value/1000000:.2f}T"
                elif current_value >= 1000:
                    formatted_value = f"{current_value/1000:.2f}B"
                else:
                    formatted_value = f"{current_value:,.0f}M"
            else:
                formatted_value = f"{current_value:,.2f}"
        else:
            formatted_value = "N/A"
        
        st.markdown(f"<div style='color: #000000; font-size: 0.9rem;'>{formatted_value}</div>", unsafe_allow_html=True)
        
        # Create and display the chart
        fig = create_indicator_chart(indicator_key, data)
        chart_height = getattr(config, 'card_chart_height', 250)
        st.plotly_chart(fig, use_container_width=True, height=chart_height, key=f"chart_{indicator_key}")
        
        # Expandable details section
        with st.expander("View Details"):
            st.markdown(warning["details"], unsafe_allow_html=True)
            if config.fred_link:
                st.markdown(f"[View on FRED]({config.fred_link})")
            
            # Special custom content for PMI
            if indicator_key == "pmi_proxy":
                st.subheader("PMI Components")
                component_df = create_pmi_components_table(data)
                st.write(component_df)
                
                st.markdown("""
                FRED Data Sources: 
                - [AMTMNO - Manufacturing: New Orders](https://fred.stlouisfed.org/series/AMTMNO)
                - [IPMAN - Industrial Production: Manufacturing](https://fred.stlouisfed.org/series/IPMAN)
                - [MANEMP - Manufacturing Employment](https://fred.stlouisfed.org/series/MANEMP)
                - [AMDMUS - Manufacturing: Supplier Deliveries](https://fred.stlouisfed.org/series/AMDMUS)
                - [MNFCTRIMSA - Manufacturing Inventories (Seasonally Adjusted)](https://fred.stlouisfed.org/series/MNFCTRIMSA)
                """)
            
            # Special custom content for USD Liquidity
            elif indicator_key == "usd_liquidity":
                st.write("Tariff receipts are added back as they represent inflows that are parked in the Treasury General Account but are not a real drain on liquidity like taxes.")
                
                # Display the actual values used in the calculation
                if 'details' in data:
                    import numpy as np
                    details = data['details']
                    walcl = details.get('WALCL', 0)
                    rrponttld = details.get('RRPONTTLD', 0)
                    wtregen = details.get('WTREGEN', 0)
                    currcir = details.get('CURRCIR', 0)
                    gdp = details.get('GDP', details.get('GDPC1', 1))
                    tariff_flow = details.get('Tariff_Flow', 0)

                    # Check for NaN values and replace with zeros
                    walcl = 0 if np.isnan(walcl) else walcl
                    rrponttld = 0 if np.isnan(rrponttld) else rrponttld
                    wtregen = 0 if np.isnan(wtregen) else wtregen
                    currcir = 0 if np.isnan(currcir) else currcir
                    gdp = 1 if np.isnan(gdp) else gdp
                    tariff_flow = 0 if np.isnan(tariff_flow) else tariff_flow

                    st.write("**Calculation Details:**")
                    st.write(f"Fed Balance Sheet (WALCL): ${walcl:,.0f}B")
                    st.write(f"Reverse Repo (RRPONTTLD): ${rrponttld:,.0f}B")
                    st.write(f"Treasury General Account (WTREGEN): ${wtregen:,.0f}B")
                    st.write(f"Currency in Circulation (CURRCIR): ${currcir:,.0f}B")
                    st.write(f"Tariff Flow: ${tariff_flow:,.0f}B")
                    st.write(f"GDP: ${gdp:,.0f}T")
                    
                    # Calculate and display the intermediate steps
                    numerator = walcl - rrponttld - wtregen - currcir + tariff_flow
                    st.write(f"**Numerator:** {walcl:,.0f} - {rrponttld:,.0f} - {wtregen:,.0f} - {currcir:,.0f} + {tariff_flow:,.0f} = ${numerator:,.0f}B")
                    result = numerator / gdp * 100
                    st.write(f"**Result:** {numerator:,.0f} / {gdp:,.0f} × 100 = {result:.2f}%")


# Replaced by generic display_indicator_card function


# Replaced by generic display_indicator_card function


# Replaced by generic display_indicator_card function


# Replaced by generic display_indicator_card function


# Replaced by generic display_indicator_card function


# Replaced by generic display_indicator_card function


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
        
        st.markdown("**Defensive Playbook:**")
        st.markdown("- Review tech holdings and shift to quality stocks")
        st.markdown("- Keep dry powder (cash) ready")
        st.markdown("- Wait for signals to clear before returning to growth")


# Replaced by generic display_indicator_card function


# Replaced by generic display_indicator_card function


# Replaced by generic display_indicator_card function


# Replaced by generic display_indicator_card function


# Replaced by generic display_indicator_card function
