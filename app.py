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
pce_rising = pce_data['PCE_YoY'].iloc[-1] > pce_data['PCE_YoY'].iloc[-2]

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

# Fetch ISM Manufacturing data
try:
    ism_data = pd.DataFrame(fred.get_series('NAPM'), columns=['Value']).reset_index()
    ism_data.columns = ['Date', 'ISM']
    current_ism = ism_data['ISM'].iloc[-1]
    ism_below_50 = current_ism < 50
except:
    # Fallback to manufacturing employment if ISM data is unavailable
    ism_data = pd.DataFrame(fred.get_series('MANEMP'), columns=['Value']).reset_index()
    ism_data.columns = ['Date', 'ISM']
    ism_data['ISM_YoY'] = ism_data['ISM'].pct_change(periods=12) * 100
    current_ism = ism_data['ISM'].iloc[-1]
    ism_below_50 = False  # Not applicable for employment data

# Check for danger combination
danger_combination = ism_below_50 and claims_increasing and hours_weakening

# Check for risk-on opportunity
risk_on_opportunity = not pce_rising and not claims_increasing

# Create summary table
st.header("Current Market Signals Summary")
summary_data = {
    'Indicator': [
        'Initial Jobless Claims',
        'PCE (Inflation)',
        'Core CPI',
        'Hours Worked (3M MA)',
        'ISM Manufacturing'
    ],
    'Status': [
        create_warning_indicator(claims_increasing, 0.5),
        create_warning_indicator(current_pce, 2.0),
        create_warning_indicator(current_cpi, 2.0),
        create_warning_indicator(hours_weakening, 0.5),
        create_warning_indicator(ism_below_50, 0.5)
    ],
    'Current Value': [
        f"{claims_data['Claims'].iloc[-1]:,.0f} claims",
        f"{current_pce:.1f}% YoY",
        f"{current_cpi:.1f}% YoY",
        f"{current_hours_ma_change:.1f}% YoY",
        f"{current_ism:.1f}"
    ],
    'Interpretation': [
        'Rising' if claims_increasing else 'Stable/Decreasing',
        'Rising' if pce_rising else 'Falling',
        'Above Target' if current_cpi > 2.0 else 'Within Target',
        'Weakening' if hours_weakening else 'Strong',
        'Contraction' if ism_below_50 else 'Expansion'
    ]
}

summary_df = pd.DataFrame(summary_data)
st.table(summary_df)

# Add overall market signal
st.subheader("Overall Market Signal")
if danger_combination:
    st.error("⚠️ DANGER COMBINATION DETECTED: ISM below 50 + Claims rising + Hours worked dropping")
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

**Playbook for Rising Claims:**
- Scale back aggressive positions
- Shift toward defensive sectors
- Build cash reserves
- "Small moves early beat big moves late"
""")

# 2. PCE Section
st.header("2. Personal Consumption Expenditures (PCE) 💵")
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
- Part of the danger combination: ISM below 50 + Claims rising 3 weeks straight + Hours worked dropping
""")

# 5. ISM Manufacturing Section
st.header("5. ISM Manufacturing Index 🏭")
st.markdown("""
**Description:** A monthly survey of manufacturing businesses showing if factories are growing or shrinking.
- Above 50 = Growth/Expansion
- Below 50 = Contraction

"Think of it as the economy's pulse"
""")

# Create ISM Manufacturing chart
fig_ism = px.line(ism_data.tail(24), x='Date', y='ISM',
                  title='ISM Manufacturing Index (Last 24 Months)')
fig_ism.add_hline(y=50, line_dash="dash", line_color="red",
                  annotation_text="Expansion/Contraction Line")
fig_ism.update_layout(showlegend=False)
st.plotly_chart(fig_ism, use_container_width=True)

# Warning signals for ISM
st.subheader("Warning Signals 🚨")
st.markdown(f"""
Current Status: {create_warning_indicator(ism_below_50, 0.5)} 
Current ISM: {current_ism:.1f} ({'Contraction' if ism_below_50 else 'Expansion'})

**Key Insight:** "Watch trends, not levels."

**Danger Combination to Watch:**
- ISM below 50
- Claims rising 3 weeks straight
- Hours worked dropping

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
