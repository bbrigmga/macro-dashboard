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
    create_pmi_components_table
)
from visualization.warning_signals import (
    generate_hours_worked_warning,
    generate_core_cpi_warning,
    generate_initial_claims_warning,
    generate_pce_warning,
    generate_pmi_warning,
    create_warning_indicator
)


def create_card_container(title, icon, current_value=None, status_emoji=None, status_text=None, status_class=None):
    """
    Create a styled card container with header and optional status indicators.
    
    Args:
        title (str): Card title
        icon (str): Icon emoji
        current_value (str, optional): Current value to display
        status_emoji (str, optional): Status emoji indicator
        status_text (str, optional): Status text
        status_class (str, optional): CSS class for status text
    """
    # Start the card
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    
    # Create a more streamlined header structure
    header_html = "<div class='card-header'>"
    
    # Create title with icon in a single line
    header_html += f"<h3 class='card-title'>{icon} {title}"
    
    # Add status indicators inline with title if provided
    if status_emoji and status_text:
        header_html += f" <span class='card-status-inline'><span>{status_emoji}</span> <span class='{status_class}'>{status_text}</span></span>"
    
    header_html += "</h3>"
    
    # Add current value section if provided
    if current_value:
        header_html += f"<div class='card-value-section'><span class='financial-figure'>{current_value}</span></div>"
    
    # Close the header
    header_html += "</div>"
    st.markdown(header_html, unsafe_allow_html=True)


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
        status_emoji = "🔴"
        status_text = "Bearish"
        status_class = "value-negative"
    elif hours_data['consecutive_increases'] >= 3:
        status_emoji = "🟢"
        status_text = "Bullish"
        status_class = "value-positive"
    else:
        status_emoji = "⚪"
        status_text = "Neutral"
        status_class = "value-neutral"
    
    # Format current value
    current_value = f"{current_hours:.1f} hours"
    
    # Create card with status and value in header
    create_card_container("Average Weekly Hours", "🕒", current_value, status_emoji, status_text, status_class)
    
    # Brief description
    st.markdown("""
    <p class='description' style='margin-bottom: 0.5rem;'>
    Average weekly hours of all employees in the private sector. 
    Declining trend signals reduced economic activity.
    </p>
    """, unsafe_allow_html=True)
    
    # Create and display the chart
    fig_hours = create_hours_worked_chart(hours_data)
    st.plotly_chart(fig_hours, use_container_width=True, height=250)
    
    # Expandable details section
    with st.expander("View Details"):
        st.markdown(generate_hours_worked_warning(hours_data), unsafe_allow_html=True)
        st.markdown("<div class='data-source'><a href='https://fred.stlouisfed.org/series/AWHAETP' target='_blank'>FRED Data: AWHAETP - Average Weekly Hours</a></div>", 
                   unsafe_allow_html=True)
    
    # Close the card div
    st.markdown("</div>", unsafe_allow_html=True)


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
        status_emoji = "🔴"
        status_text = "Bearish"
        status_class = "value-negative"
    elif cpi_decreasing:
        status_emoji = "🟢"
        status_text = "Bullish"
        status_class = "value-positive"
    else:
        status_emoji = "⚪"
        status_text = "Neutral"
        status_class = "value-neutral"
    
    # Format current value
    current_value = f"{current_cpi_mom:.2f}%"
    
    # Create card with status and value in header
    create_card_container("Core CPI", "📊", current_value, status_emoji, status_text, status_class)
    
    # Brief description
    st.markdown("""
    <p class='description' style='margin-bottom: 0.5rem;'>
    Core CPI measures inflation excluding volatile food and energy prices,
    providing a clearer picture of underlying inflation trends.
    </p>
    """, unsafe_allow_html=True)
    
    # Create and display the chart
    fig_cpi = create_core_cpi_chart(core_cpi_data)
    st.plotly_chart(fig_cpi, use_container_width=True, height=250)
    
    # Expandable details section
    with st.expander("View Details"):
        st.markdown(generate_core_cpi_warning(core_cpi_data), unsafe_allow_html=True)
        st.markdown("<div class='data-source'><a href='https://fred.stlouisfed.org/series/CPILFESL' target='_blank'>FRED Data: CPILFESL - Core Consumer Price Index</a></div>", 
                   unsafe_allow_html=True)
    
    # Close the card div
    st.markdown("</div>", unsafe_allow_html=True)


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
        status_emoji = "🔴"
        status_text = "Bearish"
        status_class = "value-negative"
    elif claims_decreasing:
        status_emoji = "🟢"
        status_text = "Bullish"
        status_class = "value-positive"
    else:
        status_emoji = "⚪"
        status_text = "Neutral"
        status_class = "value-neutral"
    
    # Format current value
    current_value = f"{current_claims:,.0f}"
    
    # Create card with status and value in header
    create_card_container("Initial Jobless Claims", "📈", current_value, status_emoji, status_text, status_class)
    
    # Brief description
    st.markdown("""
    <p class='description' style='margin-bottom: 0.5rem;'>
    Initial Jobless Claims show how many people filed for unemployment for the first time in a given week.
    Released every Thursday by the Department of Labor.
    </p>
    """, unsafe_allow_html=True)
    
    # Create and display the chart
    fig_claims = create_initial_claims_chart(claims_data)
    st.plotly_chart(fig_claims, use_container_width=True, height=250)
    
    # Expandable details section
    with st.expander("View Details"):
        st.markdown(generate_initial_claims_warning(claims_data), unsafe_allow_html=True)
        st.markdown("<div class='data-source'><a href='https://fred.stlouisfed.org/series/ICSA' target='_blank'>FRED Data: ICSA - Initial Claims for Unemployment Insurance</a></div>", 
                   unsafe_allow_html=True)
    
    # Close the card div
    st.markdown("</div>", unsafe_allow_html=True)


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
        status_emoji = "🔴"
        status_text = "Bearish"
        status_class = "value-negative"
    elif pce_decreasing:
        status_emoji = "🟢"
        status_text = "Bullish"
        status_class = "value-positive"
    else:
        status_emoji = "⚪"
        status_text = "Neutral"
        status_class = "value-neutral"
    
    # Format current value
    current_value = f"{current_pce_mom:.2f}%"
    
    # Create card with status and value in header
    create_card_container("Personal Consumption Expenditures", "💵", current_value, status_emoji, status_text, status_class)
    
    # Brief description
    st.markdown("""
    <p class='description' style='margin-bottom: 0.5rem;'>
    PCE is the Fed's preferred measure of inflation, tracking all spending across consumer, business, and government sectors.
    </p>
    """, unsafe_allow_html=True)
    
    # Create and display the chart
    fig_pce = create_pce_chart(pce_data)
    st.plotly_chart(fig_pce, use_container_width=True, height=250)
    
    # Expandable details section
    with st.expander("View Details"):
        st.markdown(generate_pce_warning(pce_data), unsafe_allow_html=True)
        st.markdown("<div class='data-source'><a href='https://fred.stlouisfed.org/series/PCEPI' target='_blank'>FRED Data: PCEPI - Personal Consumption Expenditures Price Index</a></div>", 
                   unsafe_allow_html=True)
    
    # Close the card div
    st.markdown("</div>", unsafe_allow_html=True)


def display_pmi_card(pmi_data):
    """
    Display the Manufacturing PMI Proxy as a card.
    
    Args:
        pmi_data (dict): Dictionary with PMI data
    """
    # Calculate current value and status
    latest_pmi = pmi_data['latest_pmi']
    
    if latest_pmi < 50:
        status_emoji = "🔴"
        status_text = "Bearish"
        status_class = "value-negative"
    else:
        status_emoji = "🟢"
        status_text = "Bullish"
        status_class = "value-positive"
    
    # Format current value
    current_value = f"{latest_pmi:.1f}"
    
    # Create card with status and value in header
    create_card_container("Manufacturing PMI Proxy", "🏭", current_value, status_emoji, status_text, status_class)
    
    # Brief description
    st.markdown("""
    <p class='description' style='margin-bottom: 0.5rem;'>
    A proxy for the ISM Manufacturing PMI using FRED data.
    PMI values above 50 indicate expansion, below 50 indicate contraction.
    </p>
    """, unsafe_allow_html=True)
    
    # Create and display the chart
    fig_pmi = create_pmi_chart(pmi_data)
    st.plotly_chart(fig_pmi, use_container_width=True, height=250)
    
    # Expandable details section
    with st.expander("View Details"):
        st.markdown(generate_pmi_warning(pmi_data), unsafe_allow_html=True)
        
        # Display PMI components in a compact table
        st.subheader("PMI Components")
        component_df = create_pmi_components_table(pmi_data)
        st.dataframe(component_df, hide_index=True, height=200)
        
        st.markdown("""
        <div class='data-source'>
        FRED Data Sources: 
        <a href="https://fred.stlouisfed.org/series/DGORDER" target="_blank">DGORDER</a>,
        <a href="https://fred.stlouisfed.org/series/INDPRO" target="_blank">INDPRO</a>,
        <a href="https://fred.stlouisfed.org/series/MANEMP" target="_blank">MANEMP</a>,
        <a href="https://fred.stlouisfed.org/series/AMTMUO" target="_blank">AMTMUO</a>,
        <a href="https://fred.stlouisfed.org/series/BUSINV" target="_blank">BUSINV</a>
        </div>
        """, unsafe_allow_html=True)
    
    # Close the card div
    st.markdown("</div>", unsafe_allow_html=True)


def display_defensive_playbook_card():
    """
    Display the Defensive Playbook as a card.
    """
    create_card_container("Defensive Playbook", "🛡️")
    
    st.markdown("""
    <p class='description'>
    When warning signals align, consider this defensive strategy:
    </p>
    <ol style='padding-left: 1.5rem; margin-top: 0.5rem;'>
        <li><strong>Review Tech Holdings</strong>
            <ul style='margin-top: 0.2rem; margin-bottom: 0.5rem;'>
                <li style='font-size: 0.85rem;'>Evaluate position sizes</li>
                <li style='font-size: 0.85rem;'>Consider trimming high-beta names</li>
            </ul>
        </li>
        <li><strong>Shift to Quality Stocks</strong>
            <ul style='margin-top: 0.2rem; margin-bottom: 0.5rem;'>
                <li style='font-size: 0.85rem;'>Focus on strong balance sheets</li>
                <li style='font-size: 0.85rem;'>Prefer profitable companies</li>
            </ul>
        </li>
        <li><strong>Keep Dry Powder Ready</strong>
            <ul style='margin-top: 0.2rem; margin-bottom: 0.5rem;'>
                <li style='font-size: 0.85rem;'>Build cash reserves</li>
                <li style='font-size: 0.85rem;'>Wait for signals to clear</li>
            </ul>
        </li>
        <li><strong>Risk Management</strong>
            <ul style='margin-top: 0.2rem; margin-bottom: 0.5rem;'>
                <li style='font-size: 0.85rem;'>Scale back aggressive positions</li>
                <li style='font-size: 0.85rem;'>Make gradual moves</li>
            </ul>
        </li>
    </ol>
    <p class='description' style='font-style: italic; margin-top: 0.5rem;'>
    Then return to growth when trends improve.
    </p>
    """, unsafe_allow_html=True)
    
    # Close the card div
    st.markdown("</div>", unsafe_allow_html=True)


def display_core_principles_card():
    """
    Display the Core Principles as a card.
    """
    create_card_container("Core Principles", "📋")
    
    st.markdown("""
    <p class='description' style='font-weight: 600; margin-bottom: 0.5rem;'>Remember:</p>
    <ul style='padding-left: 1.5rem; margin-top: 0;'>
        <li style='font-size: 0.85rem;'>Never trade on one signal alone</li>
        <li style='font-size: 0.85rem;'>Wait for confirmation</li>
        <li style='font-size: 0.85rem;'>Make gradual moves</li>
        <li style='font-size: 0.85rem;'>Stay disciplined</li>
    </ul>
    
    <p class='description' style='font-weight: 600; margin-bottom: 0.5rem; margin-top: 1rem;'>Market Dynamics:</p>
    <ul style='padding-left: 1.5rem; margin-top: 0;'>
        <li style='font-size: 0.85rem;'>Markets are driven by simple forces: Jobs, Spending, Business activity</li>
        <li style='font-size: 0.85rem;'>Like weather forecasting, you can't predict every storm</li>
        <li style='font-size: 0.85rem;'>But you can spot conditions that make storms likely</li>
    </ul>
    """, unsafe_allow_html=True)
    
    # Close the card div
    st.markdown("</div>", unsafe_allow_html=True)
