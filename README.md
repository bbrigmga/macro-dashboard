# Macro Economic Indicators Dashboard

A Streamlit dashboard that tracks and visualizes key macro economic indicators including Average Weekly Hours, Core CPI, Initial Jobless Claims, PCE (Personal Consumption Expenditures), and Manufacturing PMI Proxy. The dashboard provides real-time data visualization, warning signals, and interpretation guidelines for each indicator.

## Features

- Real-time data from FRED (Federal Reserve Economic Data)
- Interactive charts for each economic indicator
- Warning signals and interpretation guidelines
- Danger combination detection
- Defensive playbook recommendations
- Core principles for market analysis
- Summary table with current status of all indicators

## Code Structure

The codebase follows a modular architecture for better maintainability:

```
macro_dashboard/
├── app.py                  # Main application entry point
├── requirements.txt        # Dependencies
├── .env.example            # Example environment variables
├── README.md               # Documentation
├── data/                   # Data handling modules
│   ├── __init__.py
│   ├── fred_client.py      # FRED API client
│   ├── indicators.py       # Data fetching for each indicator
│   └── processing.py       # Data processing utilities
├── visualization/          # Visualization modules
│   ├── __init__.py
│   ├── charts.py           # Chart creation functions
│   └── indicators.py       # Indicator-specific visualizations
└── ui/                     # UI components
    ├── __init__.py
    ├── dashboard.py        # Main dashboard layout
    ├── summary.py          # Summary section
    └── indicators.py       # Individual indicator sections
```

## Local Setup

1. Clone this repository:
```bash
git clone [your-repository-url]
cd [repository-name]
```

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

5. Run the dashboard locally:
```bash
streamlit run app.py
```

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
The dashboard uses a simple framework for risk assessment:
- PCE dropping + Stable jobs = Add risk
- PCE rising + Rising claims = Get defensive

## Maintenance

The dashboard automatically updates with new data as it becomes available:
- Initial Jobless Claims: Updated weekly (Thursday)
- PCE: Updated monthly
- Core CPI: Updated monthly
- Average Weekly Hours: Updated monthly
- Manufacturing PMI Proxy: Updated monthly (calculated from multiple indicators)

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Note

This dashboard is for informational purposes only and should not be considered as financial advice. Always conduct your own research and consult with financial professionals before making investment decisions.
