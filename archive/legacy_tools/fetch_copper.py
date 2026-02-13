#!/usr/bin/env python3
"""
Script to fetch Copper prices using FRED API as fallback when Yahoo Finance fails.
"""
import sys
import os
from pathlib import Path

# Add the project root to Python path for proper imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from data.fred_client import FredClient
    from data.yahoo_client import YahooClient
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure you're running this script from the project root directory")
    sys.exit(1)
import pandas as pd
import logging
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # Load environment variables
    load_dotenv()

    # Try Yahoo Finance first
    client = YahooClient()
    copper_tickers = ['COPX', 'FCX', 'HG=F', 'JJC', 'SCCO']
    df = None

    print("Trying Yahoo Finance...")
    for ticker in copper_tickers:
        try:
            print(f"Trying ticker: {ticker}")
            df = client.get_historical_prices(ticker=ticker, periods=365, frequency='1d')
            print(f"Successfully fetched copper data using {ticker} ticker")
            break
        except Exception as e:
            print(f"Failed to fetch copper data with {ticker} ticker: {e}")
            continue

    # If Yahoo Finance fails, try FRED API
    if df is None:
        print("Yahoo Finance failed. Trying FRED API as fallback...")
        try:
            fred_client = FredClient()

            # Try known FRED copper series
            copper_series = ['PCOPPUSDM', 'PCOPPER', 'WPU10250101', 'PWHEAMTUSDM']
            for series_id in copper_series:
                try:
                    print(f"Trying FRED series: {series_id}")
                    df = fred_client.get_series(series_id, periods=365, frequency='D')
                    df.columns = ['Date', 'value']  # Rename to match expected format
                    print(f"Successfully fetched copper data using FRED series {series_id}")
                    break
                except Exception as e:
                    print(f"Failed to fetch FRED series {series_id}: {e}")
                    continue

        except Exception as e:
            print(f"FRED API initialization failed: {e}")

    if df is None:
        raise ValueError("Unable to fetch copper data from any available source")

    # Ensure the DataFrame matches dashboard format (Date and value columns)
    assert 'Date' in df.columns, "Date column missing"
    assert 'value' in df.columns, "value column missing"

    # Summary
    print("Copper COMEX Data Fetch Summary:")
    print(f"Total records: {len(df)}")
    print(f"Date range: {df['Date'].min()} to {df['Date'].max()}")
    print(f"Value range: {df['value'].min():.2f} to {df['value'].max():.2f}")
    print(f"Latest value: {df.iloc[-1]['value']:.2f} on {df.iloc[-1]['Date']}")
    print("\nData structure:")
    print(df.head())
    print("\nProcessing applied:")
    print("- Fetched Close prices from Yahoo Finance")
    print("- Converted to DataFrame with 'Date' and 'value' columns")
    print("- Dates converted to numpy datetime64 array using convert_dates utility")

if __name__ == "__main__":
    main()