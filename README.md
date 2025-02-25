# Macro Economic Indicators Dashboard

A Streamlit dashboard that tracks and visualizes key macro economic indicators including Initial Jobless Claims, PCE (Personal Consumption Expenditures), Core CPI, Non-farm Payrolls, and Manufacturing Employment. The dashboard provides real-time data visualization, warning signals, and interpretation guidelines for each indicator.

## Features

- Real-time data from FRED (Federal Reserve Economic Data)
- Interactive charts for each economic indicator
- Warning signals and interpretation guidelines
- Defensive playbook recommendations
- Core principles for market analysis
- Summary table with current status of all indicators

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

1. **Initial Jobless Claims**
   - Weekly unemployment claims data
   - Warning signals for consecutive increases
   - Trend analysis and interpretation

2. **PCE (Personal Consumption Expenditures)**
   - The Fed's preferred inflation measure
   - Year-over-year change tracking
   - Combined analysis with other indicators

3. **Core CPI**
   - Inflation excluding food and energy
   - Monthly rate changes
   - Comparison with PCE trends

4. **Non-farm Payrolls**
   - Monthly employment changes
   - Trend analysis
   - Job market health indicators

5. **Manufacturing Employment**
   - Sector health indicator
   - Year-over-year changes
   - Combined analysis with other metrics

## Maintenance

The dashboard automatically updates with new data as it becomes available:
- Initial Jobless Claims: Updated weekly (Thursday)
- PCE: Updated monthly
- Core CPI: Updated monthly
- Non-farm Payrolls: Updated monthly
- Manufacturing Employment: Updated monthly

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Note

This dashboard is for informational purposes only and should not be considered as financial advice. Always conduct your own research and consult with financial professionals before making investment decisions.
