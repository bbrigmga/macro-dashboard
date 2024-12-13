import streamlit as st
import pandas as pd
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

# Function to create a warning signal indicator
def create_warning_indicator(value, threshold, higher_is_bad=True):
    if higher_is_bad:
        color = "red" if value > threshold else "green"
    else:
        color = "red" if value < threshold else "green"
    return f"🔴" if color == "red" else "🟢"

# Fetch all data first for summary
claims_data = pd.DataFrame(fred.get_series('ICSA'), columns=['Value']).reset_index()
claims_data.columns = ['Date', 'Claims']
recent_claims = claims_data['Claims'].tail(4).values
claims_increasing = all(recent_claims[i] < recent_claims[i+1] for i in range(len(recent_claims)-1))

pce_data = pd.DataFrame(fred.get_series('PCEPI'), columns=['Value']).reset_index()
pce_data.columns = ['Date', 'PCE']
pce_data['PCE_YoY'] = pce_data['PCE'].pct_change(periods=12) * 100
current_pce = pce_data['PCE_YoY'].iloc[-1]

core_cpi_data = pd.DataFrame(fred.get_series('CPILFESL'), columns=['Value']).reset_index()
core_cpi_data.columns = ['Date', 'CPI']
core_cpi_data['CPI_YoY'] = core_cpi_data['CPI'].pct_change(periods=12) * 100
current_cpi = core_cpi_data['CPI_YoY'].iloc[-1]

# Fetch Hours Worked data
hours_data = pd.DataFrame(fred.get_series('PRS85006031'), columns=['Value']).reset_index()
hours_data.columns = ['Date', 'Hours']
# Calculate 3-month moving average
hours_data['MA3'] = hours_data['Hours'].rolling(window=3).mean()
# Calculate YoY change for both actual and MA
hours_data['YoY_Change'] = hours_data['Hours'].pct_change(periods=12) * 100
hours_data['MA3_YoY_Change'] = hours_data['MA3'].pct_change(periods=12) * 100
current_hours_change = hours_data['YoY_Change'].iloc[-1]
current_hours_ma_change = hours_data['MA3_YoY_Change'].iloc[-1]
hours_weakening = current_hours_ma_change < 0

mfg_data = pd.DataFrame(fred.get_series('MANEMP'), columns=['Value']).reset_index()
mfg_data.columns = ['Date', 'Manufacturing']
mfg_data['YoY_Change'] = mfg_data['Manufacturing'].pct_change(periods=12) * 100
current_mfg_change = mfg_data['YoY_Change'].iloc[-1]
mfg_trend = "Contracting" if current_mfg_change < 0 else "Expanding"

# Create summary table
st.header("Current Market Signals Summary")
summary_data = {
    'Indicator': [
        'Initial Jobless Claims',
        'PCE (Inflation)',
        'Core CPI',
        'Hours Worked (3M MA)',
        'Manufacturing Employment'
    ],
    'Status': [
        create_warning_indicator(claims_increasing, 0.5),
        create_warning_indicator(current_pce, 2.0),
        create_warning_indicator(current_cpi, 2.0),
        create_warning_indicator(hours_weakening, 0.5),
        create_warning_indicator(current_mfg_change, 0, higher_is_bad=False)
    ],
    'Current Value': [
        f"{claims_data['Claims'].iloc[-1]:,.0f} claims",
        f"{current_pce:.1f}% YoY",
        f"{current_cpi:.1f}% YoY",
        f"{current_hours_ma_change:.1f}% YoY",
        f"{current_mfg_change:.1f}% YoY"
    ],
    'Interpretation': [
        'Rising' if claims_increasing else 'Stable/Decreasing',
        'Above Target' if current_pce > 2.0 else 'Within Target',
        'Above Target' if current_cpi > 2.0 else 'Within Target',
        'Weakening' if hours_weakening else 'Strong',
        'Contracting' if current_mfg_change < 0 else 'Expanding'
    ]
}

summary_df = pd.DataFrame(summary_data)
st.table(summary_df)

st.markdown("""
🔴 = Warning Signal / Needs Attention
🟢 = Normal / Healthy Range
""")

st.markdown("""
This dashboard tracks key macro economic indicators that help forecast market conditions and economic trends.
Each indicator includes detailed explanations and warning signals to watch for.
""")

# 1. Initial Jobless Claims Section
st.header("1. Initial Jobless Claims 📈")
st.markdown("""
**Description:** Initial Jobless Claims show how many people filed for unemployment for the first time in a given week.
Released every Thursday by the Department of Labor.
""")

# Create claims chart
fig_claims = px.line(claims_data.tail(52), x='Date', y='Claims',
                     title='Weekly Initial Jobless Claims (Last 52 Weeks)')
fig_claims.update_layout(showlegend=False)
st.plotly_chart(fig_claims, use_container_width=True)

# Warning signals for Claims
st.subheader("Warning Signals 🚨")
st.markdown(f"""
Current Status: {create_warning_indicator(claims_increasing, 0.5)} 
{'⚠️ Claims have been rising for 3+ weeks - Consider defensive positioning' if claims_increasing else '✅ Claims trend stable/decreasing - Market conditions normal'}

**Key Warning Signals to Watch:**
- Three consecutive weeks of rising claims
- Claims rising while PCE is also rising
- Sudden spike in claims (>10% week-over-week)
""")

# 2. PCE Section
st.header("2. Personal Consumption Expenditures (PCE) 💵")
st.markdown("""
**Description:** PCE is the Fed's preferred measure of inflation, tracking all spending across consumer, business, and government sectors.
Released monthly by the Bureau of Economic Analysis.
""")

# Create PCE chart
fig_pce = px.line(pce_data.tail(24), x='Date', y='PCE_YoY',
                  title='PCE Year-over-Year % Change (Last 24 Months)')
fig_pce.update_layout(showlegend=False)
st.plotly_chart(fig_pce, use_container_width=True)

# Warning signals for PCE
st.subheader("Warning Signals 🚨")
st.markdown(f"""
Current Status: {create_warning_indicator(current_pce, 2.0)} 
Current PCE YoY: {current_pce:.1f}%

**Key Warning Signals to Watch:**
- PCE rising + Rising jobless claims = Defensive positioning needed
- PCE above Fed's 2% target
- PCE rising faster than expected
""")

# 3. Core CPI Section
st.header("3. Core CPI (Consumer Price Index Less Food and Energy) 📊")
st.markdown("""
**Description:** Core CPI measures inflation excluding volatile food and energy prices.
This provides a clearer picture of underlying inflation trends.
""")

# Create Core CPI chart
fig_cpi = px.line(core_cpi_data.tail(24), x='Date', y='CPI_YoY',
                  title='Core CPI Year-over-Year % Change (Last 24 Months)')
fig_cpi.update_layout(showlegend=False)
st.plotly_chart(fig_cpi, use_container_width=True)

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

# 4. Hours Worked Section
st.header("4. Hours Worked 🕒")
st.markdown("""
**Description:** Average weekly hours worked in the private sector.
A declining trend can signal reduced economic activity and potential job market weakness.
""")

# Create Hours Worked chart with both actual and MA lines
fig_hours = go.Figure()
fig_hours.add_trace(go.Scatter(
    x=hours_data.tail(24)['Date'],
    y=hours_data.tail(24)['YoY_Change'],
    name='Actual',
    line=dict(color='blue')
))
fig_hours.add_trace(go.Scatter(
    x=hours_data.tail(24)['Date'],
    y=hours_data.tail(24)['MA3_YoY_Change'],
    name='3-Month MA',
    line=dict(color='red', dash='dash')
))
fig_hours.update_layout(
    title='Hours Worked Year-over-Year % Change (Last 24 Months)',
    showlegend=True
)
st.plotly_chart(fig_hours, use_container_width=True)

# Warning signals for Hours Worked
st.subheader("Warning Signals 🚨")
st.markdown(f"""
Current Status: {create_warning_indicator(hours_weakening, 0.5)} 
Latest YoY Change (3M MA): {current_hours_ma_change:.1f}%

**Key Warning Signals to Watch:**
- Declining 3-month moving average
- Negative year-over-year change
- Divergence between actual and moving average
- Combined weakness with rising jobless claims
""")

# 5. Manufacturing Employment Section
st.header("5. Manufacturing Employment 🏭")
st.markdown("""
**Description:** Manufacturing employment data serves as a proxy for manufacturing sector health.
A rising trend indicates sector expansion, while a declining trend suggests contraction.
""")

# Create Manufacturing Employment chart
fig_ism = px.line(mfg_data.tail(24), x='Date', y='YoY_Change',
                  title='Manufacturing Employment Year-over-Year % Change (Last 24 Months)')
fig_ism.add_hline(y=0, line_dash="dash", line_color="red",
                  annotation_text="Growth/Contraction Line")
fig_ism.update_layout(showlegend=False)
st.plotly_chart(fig_ism, use_container_width=True)

# Warning signals for Manufacturing
st.subheader("Warning Signals 🚨")
st.markdown(f"""
Current Status: {create_warning_indicator(current_mfg_change, 0, higher_is_bad=False)} 
Current YoY Change: {current_mfg_change:.1f}% ({mfg_trend})

**Danger Combination to Watch:**
- Manufacturing employment declining
- Claims rising 3 weeks straight
- PCE rising
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
""")

# Core Principles Section
st.header("Core Principles 📋")
st.markdown("""
**Remember:**
- Never trade on one signal alone
- Wait for confirmation
- Make gradual moves
- Stay disciplined
- Focus on being profitable, not being right

**Market Dynamics:**
- Markets are driven by simple forces: Jobs, Spending, Business activity
- Like weather forecasting, you can't predict every storm
- But you can spot conditions that make storms likely
- These indicators help identify those conditions
""")

# Add footer with data disclaimer
st.markdown("""
---
*Data sourced from FRED (Federal Reserve Economic Data). Updated automatically with each release.*
""")
