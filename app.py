import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import yfinance as yf
from fredapi import Fred
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Configure page settings
st.set_page_config(
    page_title="Macro Dashboard",
    page_icon="📊",
    layout="wide"
)

# Initialize FRED API
fred = Fred(api_key=os.getenv('FRED_API_KEY'))

# Title and introduction
st.title("📊 Macro Economic Indicators Dashboard")

# Add tweet link button
st.link_button("View Original Tweet Thread by @a_vroenne", "https://x.com/a_vroenne/status/1867241557658829130")

# Function to create a warning signal indicator
def create_warning_indicator(value, threshold, higher_is_bad=True):
    if higher_is_bad:
        color = "red" if value > threshold else "green"
    else:
        color = "red" if value < threshold else "green"
    return f"🔴" if color == "red" else "🟢"

# Helper function to convert datetime index to numpy datetime64 array
def convert_dates(df):
    if isinstance(df.index, pd.DatetimeIndex):
        df = df.copy()
        df.index = df.index.to_numpy()
    return df

# Fetch all data first for summary
claims_data = pd.DataFrame(fred.get_series('ICSA'), columns=['Value']).reset_index()
claims_data.columns = ['Date', 'Claims']
# Convert Date to numpy datetime64 to avoid FutureWarning
claims_data['Date'] = pd.to_datetime(claims_data['Date']).to_numpy()
recent_claims = claims_data['Claims'].tail(4).values
claims_increasing = all(recent_claims[i] < recent_claims[i+1] for i in range(len(recent_claims)-1))

pce_data = pd.DataFrame(fred.get_series('PCEPI'), columns=['Value']).reset_index()
pce_data.columns = ['Date', 'PCE']
# Convert Date to numpy datetime64 to avoid FutureWarning
pce_data['Date'] = pd.to_datetime(pce_data['Date']).to_numpy()
pce_data['PCE_YoY'] = pce_data['PCE'].pct_change(periods=12) * 100
current_pce = pce_data['PCE_YoY'].iloc[-1]
pce_rising = pce_data['PCE_YoY'].iloc[-1] > pce_data['PCE_YoY'].iloc[-2]

core_cpi_data = pd.DataFrame(fred.get_series('CPILFESL'), columns=['Value']).reset_index()
core_cpi_data.columns = ['Date', 'CPI']
# Convert Date to numpy datetime64 to avoid FutureWarning
core_cpi_data['Date'] = pd.to_datetime(core_cpi_data['Date']).to_numpy()
core_cpi_data['CPI_YoY'] = core_cpi_data['CPI'].pct_change(periods=12) * 100
current_cpi = core_cpi_data['CPI_YoY'].iloc[-1]

# Fetch Hours Worked data
hours_data = pd.DataFrame(fred.get_series('PRS85006031'), columns=['Value']).reset_index()
hours_data.columns = ['Date', 'Hours']
# Convert Date to numpy datetime64 to avoid FutureWarning
hours_data['Date'] = pd.to_datetime(hours_data['Date']).to_numpy()
# Calculate 3-month moving average
hours_data['MA3'] = hours_data['Hours'].rolling(window=3).mean()
# Calculate YoY change for both actual and MA
hours_data['YoY_Change'] = hours_data['Hours'].pct_change(periods=12) * 100
hours_data['MA3_YoY_Change'] = hours_data['MA3'].pct_change(periods=12) * 100

# Handle outliers by capping extreme values
def cap_outliers(series, lower_limit=-5, upper_limit=5):
    return series.clip(lower=lower_limit, upper=upper_limit)

hours_data['YoY_Change_Capped'] = cap_outliers(hours_data['YoY_Change'])
hours_data['MA3_YoY_Change_Capped'] = cap_outliers(hours_data['MA3_YoY_Change'])

# Use the actual values for analysis but capped values for display
current_hours_change = hours_data['YoY_Change'].iloc[-1]
current_hours_ma_change = hours_data['MA3_YoY_Change'].iloc[-1]
# Cap the display values
current_hours_change_display = cap_outliers(pd.Series([current_hours_change])).iloc[0]
current_hours_ma_change_display = cap_outliers(pd.Series([current_hours_ma_change])).iloc[0]
hours_weakening = current_hours_ma_change < 0

# Function to calculate PMI proxy
def calculate_pmi_proxy():
    # Define FRED series IDs for proxy variables
    series_ids = {
        'new_orders': 'DGORDER',      # Manufacturers' New Orders: Durable Goods
        'production': 'INDPRO',       # Industrial Production Index
        'employment': 'MANEMP',       # All Employees: Manufacturing
        'supplier_deliveries': 'AMTMUO',  # Manufacturers: Unfilled Orders for All Manufacturing Industries
        'inventories': 'BUSINV'       # Total Business Inventories
    }

    # Define PMI component weights
    weights = {
        'new_orders': 0.30,
        'production': 0.25,
        'employment': 0.20,
        'supplier_deliveries': 0.15,
        'inventories': 0.10
    }

    # Function to calculate diffusion-like index from percentage change
    def to_diffusion_index(pct_change, scale=10):
        return 50 + (pct_change * scale)

    # Pull the data for each series
    data = {}
    for component, series_id in series_ids.items():
        series = fred.get_series(series_id, observation_start='2020-01-01')
        series = series.resample('M').last()  # Ensure monthly frequency
        data[component] = series

    # Create a DataFrame
    df = pd.DataFrame(data)

    # Calculate month-over-month percentage change
    df_pct_change = df.pct_change() * 100  # Convert to percentage

    # Transform to diffusion-like indices
    df_diffusion = df_pct_change.apply(lambda x: to_diffusion_index(x))

    # Calculate the approximated PMI as a weighted average
    df['approximated_pmi'] = (df_diffusion * pd.Series(weights)).sum(axis=1)

    # Store component values for the latest month
    component_values = {}
    for component in series_ids.keys():
        component_values[component] = df_diffusion[component].iloc[-1]

    # Return the latest PMI value, the full time series, and component values
    return {
        'latest_pmi': df['approximated_pmi'].iloc[-1],
        'pmi_series': df['approximated_pmi'],
        'component_values': component_values,
        'component_weights': weights
    }

# Calculate PMI proxy
pmi_data = calculate_pmi_proxy()
current_pmi = pmi_data['latest_pmi']
pmi_below_50 = current_pmi < 50

# Check for danger combination
danger_combination = pmi_below_50 and claims_increasing and hours_weakening

# Check for risk-on opportunity
risk_on_opportunity = not pce_rising and not claims_increasing

# Create summary table with numbered indicators
summary_data = {
    'Indicator': [
        '1. Hours Worked (3M MA)',
        '2. Core CPI',
        '3. Initial Jobless Claims',
        '4. PCE (Inflation)',
        '5. Manufacturing PMI Proxy'
    ],
    'Status': [
        create_warning_indicator(hours_weakening, 0.5),
        create_warning_indicator(current_cpi, 2.0),
        create_warning_indicator(claims_increasing, 0.5),
        create_warning_indicator(current_pce, 2.0),
        create_warning_indicator(current_pmi < 50, 0.5)
    ],
    'Current Value': [
        f"{current_hours_ma_change_display:.1f}% YoY",
        f"{current_cpi:.1f}% YoY",
        f"{claims_data['Claims'].iloc[-1]:,.0f} claims",
        f"{current_pce:.1f}% YoY",
        f"{current_pmi:.1f}"
    ],
    'Interpretation': [
        'Weakening' if hours_weakening else 'Strong',
        'Above Target' if current_cpi > 2.0 else 'Within Target',
        'Rising' if claims_increasing else 'Stable/Decreasing',
        'Rising' if pce_rising else 'Falling',
        'Contraction' if pmi_below_50 else 'Expansion'
    ]
}

st.header("Current Market Signals Summary")
summary_df = pd.DataFrame(summary_data)
# Use st.dataframe instead of st.table with hide_index=True to properly hide the index
st.dataframe(summary_df, hide_index=True)

# Add overall market signal
st.subheader("Overall Market Signal")
if danger_combination:
    st.error("⚠️ DANGER COMBINATION DETECTED: Manufacturing PMI below 50 + Claims rising + Hours worked dropping")
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

st.markdown("""
This dashboard tracks key macro economic indicators that help forecast market conditions and economic trends.
Each indicator includes detailed explanations and warning signals to watch for.
""")

# 1. Hours Worked Section
st.header("1. Hours Worked 🕒")
st.markdown("""
**Description:** Average weekly hours worked in the private sector.
A declining trend can signal reduced economic activity and potential job market weakness.
""")

# Create Hours Worked chart with both actual and MA lines - convert dates to strings to avoid FutureWarning
hours_plot_data = hours_data.tail(24).copy()
# Convert numpy datetime64 to string format to avoid FutureWarning
hours_plot_data['Date_Str'] = pd.to_datetime(hours_plot_data['Date']).dt.strftime('%Y-%m-%d')
fig_hours = go.Figure()
fig_hours.add_trace(go.Scatter(
    x=hours_plot_data['Date_Str'],
    y=hours_plot_data['YoY_Change_Capped'],
    name='Actual',
    line=dict(color='blue')
))
fig_hours.add_trace(go.Scatter(
    x=hours_plot_data['Date_Str'],
    y=hours_plot_data['MA3_YoY_Change_Capped'],
    name='3-Month MA',
    line=dict(color='red', dash='dash')
))
fig_hours.update_layout(
    title='Hours Worked Year-over-Year % Change (Last 24 Months)',
    showlegend=True,
    yaxis=dict(
        range=[-5, 5],  # Set a fixed y-axis range to focus on relevant data
        title="Percent Change (%)"
    )
)
st.plotly_chart(fig_hours, use_container_width=True)

# Add FRED reference link
st.markdown("[FRED Data Source: PRS85006031 - Nonfarm Business Sector: Hours Worked](https://fred.stlouisfed.org/series/PRS85006031)")

# Warning signals for Hours Worked
st.subheader("Warning Signals 🚨")
st.markdown(f"""
Current Status: {create_warning_indicator(hours_weakening, 0.5)} 
Latest YoY Change (3M MA): {current_hours_ma_change_display:.1f}%

**Key Warning Signals to Watch:**
- Declining 3-month moving average
- Negative year-over-year change
- Part of the danger combination: Manufacturing PMI below 50 + Claims rising + Hours worked dropping
""")

# 2. Core CPI Section
st.header("2. Core CPI (Consumer Price Index Less Food and Energy) 📊")
st.markdown("""
**Description:** Core CPI measures inflation excluding volatile food and energy prices.
This provides a clearer picture of underlying inflation trends.
""")

# Create Core CPI chart - convert dates to strings to avoid FutureWarning
cpi_plot_data = core_cpi_data.tail(24).copy()
# Convert numpy datetime64 to string format to avoid FutureWarning
cpi_plot_data['Date_Str'] = pd.to_datetime(cpi_plot_data['Date']).dt.strftime('%Y-%m-%d')
fig_cpi = px.line(cpi_plot_data, x='Date_Str', y='CPI_YoY',
                  title='Core CPI Year-over-Year % Change (Last 24 Months)')
fig_cpi.update_layout(showlegend=False)
st.plotly_chart(fig_cpi, use_container_width=True)

# Add FRED reference link
st.markdown("[FRED Data Source: CPILFESL - Core Consumer Price Index](https://fred.stlouisfed.org/series/CPILFESL)")

# Warning signals for Core CPI
st.subheader("Warning Signals 🚨")
st.markdown(f"""
Current Status: {create_warning_indicator(current_cpi, 2.0)} 
Current Core CPI YoY: {current_cpi:.1f}%

**Key Warning Signals to Watch:**
- Core CPI above 2% Fed target
- Acceleration in monthly rate
- Divergence from PCE trends
""")

# 3. Initial Jobless Claims Section
st.header("3. Initial Jobless Claims 📈")
st.markdown("""
**Description:** Initial Jobless Claims show how many people filed for unemployment for the first time in a given week.
Released every Thursday by the Department of Labor.
""")

# Create claims chart - convert dates to strings to avoid FutureWarning
claims_plot_data = claims_data.tail(52).copy()
# Convert numpy datetime64 to string format to avoid FutureWarning
claims_plot_data['Date_Str'] = pd.to_datetime(claims_plot_data['Date']).dt.strftime('%Y-%m-%d')
fig_claims = px.line(claims_plot_data, x='Date_Str', y='Claims',
                     title='Weekly Initial Jobless Claims (Last 52 Weeks)')
fig_claims.update_layout(showlegend=False)
st.plotly_chart(fig_claims, use_container_width=True)

# Add FRED reference link
st.markdown("[FRED Data Source: ICSA - Initial Claims for Unemployment Insurance](https://fred.stlouisfed.org/series/ICSA)")

# Warning signals for Claims
st.subheader("Warning Signals 🚨")
st.markdown(f"""
Current Status: {create_warning_indicator(claims_increasing, 0.5)} 
{'⚠️ Claims have been rising for 3+ weeks - Consider defensive positioning' if claims_increasing else '✅ Claims trend stable/decreasing - Market conditions normal'}

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

# 4. PCE Section
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

# Create PCE chart - convert dates to strings to avoid FutureWarning
pce_plot_data = pce_data.tail(24).copy()
# Convert numpy datetime64 to string format to avoid FutureWarning
pce_plot_data['Date_Str'] = pd.to_datetime(pce_plot_data['Date']).dt.strftime('%Y-%m-%d')
fig_pce = px.line(pce_plot_data, x='Date_Str', y='PCE_YoY',
                  title='PCE Year-over-Year % Change (Last 24 Months)')
fig_pce.update_layout(showlegend=False)
st.plotly_chart(fig_pce, use_container_width=True)

# Add FRED reference link
st.markdown("[FRED Data Source: PCEPI - Personal Consumption Expenditures Price Index](https://fred.stlouisfed.org/series/PCEPI)")

# Warning signals for PCE
st.subheader("Warning Signals 🚨")
st.markdown(f"""
Current Status: {create_warning_indicator(current_pce, 2.0)} 
Current PCE YoY: {current_pce:.1f}%
Trend: {'Rising' if pce_rising else 'Falling'}

**Key Framework:**
- PCE dropping + Stable jobs = Add risk
- PCE rising + Rising claims = Get defensive

**What PCE Tells Us:**
- Rate trends
- Market conditions
- Risk appetite

**Remember:** "Everyone watches CPI, but PCE guides policy."
""")

# 5. Manufacturing PMI Proxy Section
st.header("5. Manufacturing PMI Proxy 🏭")
st.markdown("""
**Description:** A proxy for the ISM Manufacturing PMI using FRED data.
This index approximates manufacturing sector activity using a weighted average of key economic indicators.

PMI values above 50 indicate expansion, while values below 50 indicate contraction.
""")

# Create PMI chart
# First, convert the PMI series to a DataFrame with a date index
pmi_series = pmi_data['pmi_series']
pmi_df = pd.DataFrame(pmi_series)
pmi_df.reset_index(inplace=True)
pmi_df.columns = ['Date', 'PMI']

# Get the last 24 months of data
pmi_plot_data = pmi_df.tail(24).copy()
# Convert numpy datetime64 to string format to avoid FutureWarning
pmi_plot_data['Date_Str'] = pd.to_datetime(pmi_plot_data['Date']).dt.strftime('%Y-%m-%d')

# Create PMI chart
fig_pmi = go.Figure()
fig_pmi.add_trace(go.Scatter(
    x=pmi_plot_data['Date_Str'],
    y=pmi_plot_data['PMI'],
    name='PMI Proxy',
    line=dict(color='blue')
))
# Add a horizontal line at 50 (expansion/contraction threshold)
fig_pmi.add_hline(y=50, line_dash="dash", line_color="red",
                 annotation_text="Expansion/Contraction Threshold", 
                 annotation_position="bottom right")
fig_pmi.update_layout(
    title='Manufacturing PMI Proxy (Last 24 Months)',
    showlegend=True
)
st.plotly_chart(fig_pmi, use_container_width=True)

# Display PMI components
st.subheader("PMI Components")
component_data = {
    'Component': list(pmi_data['component_values'].keys()),
    'Weight': [f"{pmi_data['component_weights'][comp]*100:.0f}%" for comp in pmi_data['component_values'].keys()],
    'Value': [f"{pmi_data['component_values'][comp]:.1f}" for comp in pmi_data['component_values'].keys()],
    'Status': [create_warning_indicator(pmi_data['component_values'][comp] < 50, 0.5, higher_is_bad=True) 
               for comp in pmi_data['component_values'].keys()]
}
component_df = pd.DataFrame(component_data)
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
Current Status: {create_warning_indicator(current_pmi < 50, 0.5)} 
Current PMI Proxy Value: {current_pmi:.1f}

**Key Warning Signals to Watch:**
- PMI below 50 (indicating contraction)
- Declining trend over multiple months
- Part of the danger combination: PMI below 50 + Claims rising + Hours worked dropping

**Key Insight:** "PMI is a leading indicator of manufacturing health."

"When these align, protect capital first."
""")

# Defensive Playbook Section
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

# Core Principles Section
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

# Add footer with data disclaimer
st.markdown("""
---
*Data sourced from FRED (Federal Reserve Economic Data). Updated automatically with each release.*
""")
