# Implied & Realized Volatility Dashboard — Spec Sheet

## Overview
Streamlit component that displays a table of US equity sector ETFs with implied volatility (IV), 
realized volatility (RV), and IV premium/discount metrics. Includes a daily scraper to build 
historical IV data over time.

## Architecture

### 1. Daily IV Scraper (`iv_scraper.py`)
- Runs once daily (via cron or Streamlit scheduler or GitHub Actions)
- For each ETF in the universe, pull the current options chain using `yfinance`
- Calculate 30-day ATM implied volatility:
  - Find options expiring closest to 30 DTE (interpolate between two nearest expirations if needed)
  - Select ATM strikes (closest to current price)
  - Average the call and put IV for the ATM strike
  - Annualize if not already (yfinance IVs are typically annualized)
- Store daily record to SQLite database (`iv_data.db`):
  - Table: `daily_iv` — columns: `date`, `ticker`, `iv_30d`, `close_price`
- Also store the daily closing price (for RV calculation)

### 2. Realized Volatility Calculator (`rv_calculator.py`)
- Pull last 30 trading days of closing prices from `yfinance` (or from stored data)
- Calculate 30-day realized volatility:
  - daily_returns = ln(close_t / close_t-1)
  - rv_30d = std(daily_returns over 30 days) * sqrt(252)  # annualized
- Return annualized RV for each ticker

### 3. ETF Universe
| Name | Ticker |
|------|--------|
| Real Estate Sector SPDR ETF | XLRE |
| Financials Sector SPDR ETF | XLF |
| Energy Sector SPDR ETF | XLE |
| Communication Services SPDR ETF | XLC |
| Technology Sector SPDR ETF | XLK |
| Power Shares QQQ Trust ETF | QQQ |
| SPDR S&P 500 Trust | SPY |
| Health Care Sector SPDR ETF | XLV |
| Materials Sector SPDR ETF | XLB |
| Industrials Sector SPDR ETF | XLI |
| Consumer Discretionary SPDR ETF | XLY |
| I-Shares Russell 2000 | IWM |
| Utilities Sector SPDR ETF | XLU |
| Consumer Staples Sector SPDR ETF | XLP |

### 4. Streamlit Table Component (`vol_table.py`)
- Display a styled DataFrame table with the following columns:

| Column | Description | Calculation |
|--------|-------------|-------------|
| ETF Name | Full name | Static |
| Ticker | Bloomberg-style (e.g., "XLRE US EQUITY") | Static |
| YTD % | Year-to-date total return | `(current_price / price_at_jan1) - 1` via yfinance |
| IVOL/RVOL Current | IV premium as % | `((iv_30d / rv_30d) - 1) * 100` |
| IVOL Prem % Yesterday | IV premium from prior day | From stored DB data |
| IVOL Prem % 1W Ago | IV premium from 5 trading days ago | From stored DB data |
| IVOL Prem % 1M Ago | IV premium from ~21 trading days ago | From stored DB data |
| TTM Z-Score | Trailing 12-month z-score of current IV premium | `(current_prem - mean_prem_252d) / std_prem_252d` |
| 3Yr Z-Score | 3-year z-score of current IV premium | `(current_prem - mean_prem_756d) / std_prem_756d` |

- Sort table by YTD % descending (matching screenshot)
- Apply conditional formatting (heatmap coloring):
  - Green for high positive values, red/yellow for negative
  - Use `Styler.background_gradient()` or custom color map
- Z-Score columns: green for high, red for low

### 5. Database Schema (`iv_data.db` — SQLite)
```sql
CREATE TABLE daily_iv (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,          -- YYYY-MM-DD
    ticker TEXT NOT NULL,
    close_price REAL NOT NULL,
    iv_30d REAL,                 -- annualized 30-day ATM implied vol
    rv_30d REAL,                 -- annualized 30-day realized vol
    iv_premium REAL,             -- (iv/rv - 1) * 100
    ytd_return REAL,
    UNIQUE(date, ticker)
);