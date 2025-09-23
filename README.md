# Macro Economic Indicators Dashboard

A Streamlit dashboard that tracks and visualizes key macro economic indicators to help forecast market conditions and economic trends. The dashboard displays 9 comprehensive indicators with real-time data from FRED (Federal Reserve Economic Data) and Yahoo Finance, providing interactive charts, warning signals, interpretation guidelines, and risk assessment frameworks.

## Features

- Real-time data from FRED (Federal Reserve Economic Data) and Yahoo Finance
- Interactive charts for 9 comprehensive economic indicators
- Warning signals and interpretation guidelines for each indicator
- Danger combination detection with risk assessment framework
- Defensive playbook recommendations based on indicator combinations
- Core principles for disciplined market analysis
- Summary table with current status and positioning guidance
- Release schedule tracking for data updates
- Modern finance-themed UI with responsive design

## Code Structure

The codebase follows a modular architecture for better maintainability and scalability:

```
macro_dashboard/
├── app.py                          # Main Streamlit application entry point
├── requirements.txt                # Python dependencies
├── .env.example                    # Example environment variables template
├── README.md                       # Project documentation
├── .gitignore                      # Git ignore rules
├── Macro Dashboard.code-workspace  # VS Code workspace configuration
├── Dockerfile                      # Docker container configuration
├── .devcontainer/                  # Development container configuration
│   └── devcontainer.json
├── data/                           # Data handling and API client modules
│   ├── __init__.py
│   ├── fred_client.py              # FRED API client with caching
│   ├── yahoo_client.py             # Yahoo Finance API client
│   ├── indicators.py               # Economic indicators data fetching and processing
│   ├── processing.py               # Data processing utilities
│   ├── pce_fix.py                  # PCE data processing fixes
│   └── release_schedule.py         # Economic data release schedule tracking
├── ui/                             # User interface components
│   ├── __init__.py
│   ├── dashboard.py                # Main dashboard layout and status tables
│   ├── indicators.py               # Individual indicator card displays
│   └── custom.css                  # Custom CSS styling
├── visualization/                  # Chart and visualization modules
│   ├── __init__.py
│   ├── charts.py                   # Core chart creation functions and theming
│   ├── indicators.py               # Indicator-specific chart functions
│   └── warning_signals.py          # Warning signal generation and display
├── fetch_copper.py                 # Script for fetching copper price data
├── fetch_gold.py                   # Script for fetching gold price data
├── calculate_copper_gold_ratio.py  # Copper/gold ratio calculation script
├── create_copper_gold_yield_chart.py # Chart creation script
└── copper_gold_yield_chart.html    # Generated HTML chart output
```

## Local Setup

1. Clone this repository:
```bash
git clone [your-repository-url]
cd [repository-name]
```

2. Set up a Python virtual environment (recommended):
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
# source venv/bin/activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

4. Get a FRED API key:
    - Go to https://fred.stlouisfed.org/docs/api/api_key.html
    - Create a free account and request an API key
    - Copy your API key

5. Set up your environment:
    - Copy `.env.example` to a new file named `.env`
    - Replace `your_api_key_here` with your actual FRED API key

6. Run the dashboard locally:
```bash
streamlit run app.py
```

**Note:** If you encounter issues installing pandas with Python 3.13, consider using Python 3.12 or conda for better package compatibility.

## Deployment on Streamlit Cloud

This dashboard can be deployed for free on Streamlit Cloud:

1. Push your code to GitHub:
   - Create a new repository on GitHub
   - Push your code:
   ```bash
   git remote add origin [your-github-repo-url]
   git branch -M main
   git push -u origin main
   ```

2. Deploy on Streamlit Cloud:
   - Go to https://streamlit.io/cloud
   - Sign in with your GitHub account
   - Click "New app"
   - Select your repository, branch, and main file (app.py)
   - Add your FRED API key as a secret:
     - In the app settings, add a secret named `FRED_API_KEY`
     - Set its value to your FRED API key

3. Your app will be available at a public URL provided by Streamlit

## Security Notes

- Never commit your `.env` file containing your FRED API key
- Use environment variables or secrets management for API keys
- The `.gitignore` file is configured to exclude the `.env` file

## Indicators Tracked

1. **Average Weekly Hours**
    - Hours worked in the private sector
    - Warning signals for consecutive months of decline
    - Part of the danger combination when declining

2. **Core CPI (Consumer Price Index Less Food and Energy)**
    - Inflation excluding volatile food and energy prices
    - Month-over-month change tracking
    - Warning signals for accelerating inflation

3. **Initial Jobless Claims**
    - Weekly unemployment claims data
    - Warning signals for consecutive increases
    - Part of the danger combination when rising

4. **PCE (Personal Consumption Expenditures)**
    - The Fed's preferred inflation measure
    - Year-over-year change tracking
    - Combined analysis with other indicators

5. **Manufacturing PMI Proxy**
    - Proxy for ISM Manufacturing PMI using FRED data
    - Expansion/contraction threshold at 50
    - Part of the danger combination when below 50

6. **USD Liquidity**
    - Federal Reserve balance sheet minus reverse repo and Treasury General Account
    - Weekly data tracking liquidity conditions
    - Key indicator of monetary policy stance

7. **Non-Defense Durable Goods Orders**
    - New orders for manufacturing capital goods
    - Month-over-month percentage changes
    - Leading indicator of business investment

8. **2-10 Year Treasury Yield Spread**
    - Difference between 10-year and 2-year Treasury yields
    - Inverted spread signals potential recession risk
    - Key yield curve indicator

9. **Copper/Gold Ratio vs 10Y Treasury Yield**
    - Ratio of copper to gold commodity prices
    - Compared against 10-year Treasury yield
    - Bullish sentiment indicator when ratio rises

### Manufacturing PMI Proxy Calculation

The Manufacturing PMI Proxy is a sophisticated calculation using five key FRED economic series:

1. **Data Series Used**:
   - `AMTMNO`: New Orders
   - `IPMAN`: Production
   - `MANEMP`: Employment
   - `AMDMUS`: Supplier Deliveries
   - `MNFCTRIMSA`: Inventories

2. **Calculation Methodology**:
   - Calculate month-over-month percentage changes for each component
   - Transform to a diffusion index using the formula: 
     ```
     Diffusion Index = 50 + (pct_change / rolling_std_dev * 10)
     ```
   - Cap the index between 0 and 100

3. **Component Weights**:
   - New Orders: 30%
   - Production: 25%
   - Employment: 20%
   - Supplier Deliveries: 15%
   - Inventories: 10%

4. **Interpretation**:
   - Index above 50 indicates economic expansion
   - Index below 50 indicates economic contraction
   - Provides a proxy for the ISM Manufacturing Purchasing Managers' Index (PMI)

## Key Concepts

### Danger Combination
The dashboard tracks a specific combination of warning signals that indicate potential market trouble:
- Manufacturing PMI below 50
- Initial Claims rising for 3+ weeks
- Average Weekly Hours dropping for 3+ months

### Risk Framework
The dashboard uses a comprehensive framework for risk assessment based on PCE and Initial Claims:
- **Risk On**: PCE Bullish + Initial Claims Bullish/Neutral (favorable economic conditions)
- **Risk Off**: PCE Bearish + Initial Claims Bearish (stressful economic conditions)
- **Risk Neutral**: Mixed signals requiring caution

Additional context from USD Liquidity, yield curve positioning, and commodity ratios helps refine risk assessment.

## Maintenance

The dashboard automatically updates with new data as it becomes available from FRED and Yahoo Finance:
- Initial Jobless Claims: Updated weekly (Thursday)
- PCE: Updated monthly
- Core CPI: Updated monthly
- Average Weekly Hours: Updated monthly
- Manufacturing PMI Proxy: Updated monthly (calculated from multiple FRED indicators)
- USD Liquidity: Updated weekly (calculated from Fed balance sheet data)
- Non-Defense Durable Goods Orders: Updated monthly
- 2-10 Year Treasury Yield Spread: Updated daily
- Copper/Gold Ratio: Updated daily (from Yahoo Finance commodity data)

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Note

This dashboard is for informational purposes only and should not be considered as financial advice. Always conduct your own research and consult with financial professionals before making investment decisions.
