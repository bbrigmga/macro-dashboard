# Macro Economic Indicators Dashboard

A Streamlit dashboard that tracks and visualizes key macro economic indicators including Initial Jobless Claims, PCE (Personal Consumption Expenditures), and ISM Manufacturing Index. The dashboard provides real-time data visualization, warning signals, and interpretation guidelines for each indicator.

## Features

- Real-time data from FRED (Federal Reserve Economic Data)
- Interactive charts for each economic indicator
- Warning signals and interpretation guidelines
- Defensive playbook recommendations
- Core principles for market analysis

## Setup Instructions

1. Clone this repository or download the files

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Get a FRED API key:
   - Go to https://fred.stlouisfed.org/docs/api/api_key.html
   - Create a free account and request an API key
   - Copy your API key

4. Set up your environment:
   - Copy `.env.example` to a new file named `.env`
   - Replace `your_api_key_here` with your actual FRED API key

5. Run the dashboard:
```bash
streamlit run app.py
```

## Indicators Tracked

1. **Initial Jobless Claims**
   - Weekly unemployment claims data
   - Warning signals for consecutive increases
   - Trend analysis and interpretation

2. **PCE (Personal Consumption Expenditures)**
   - The Fed's preferred inflation measure
   - Year-over-year change tracking
   - Combined analysis with other indicators

3. **ISM Manufacturing Index**
   - Monthly manufacturing business survey
   - Expansion/contraction threshold monitoring
   - Trend analysis and warning combinations

## Usage

The dashboard automatically updates with the latest data from FRED. Each indicator section includes:
- Interactive charts
- Current status indicators
- Warning signals to watch for
- Interpretation guidelines
- Recommended actions based on signals

## Defensive Playbook

The dashboard includes a comprehensive defensive playbook that activates when warning signals align, providing guidance on:
- Portfolio review strategies
- Position sizing
- Risk management
- Cash reserve management

## Maintenance

The dashboard automatically updates with new data as it becomes available:
- Initial Jobless Claims: Updated weekly (Thursday)
- PCE: Updated monthly
- ISM Manufacturing: Updated monthly

## Note

This dashboard is for informational purposes only and should not be considered as financial advice. Always conduct your own research and consult with financial professionals before making investment decisions.
