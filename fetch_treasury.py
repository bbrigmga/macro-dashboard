#!/usr/bin/env python3
"""
Script to fetch US 10-year Treasury yield data using FredClient and process the data.
"""
import sys
import os
from pathlib import Path

# Add the project root to Python path for proper imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from dotenv import load_dotenv
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure python-dotenv is installed and you're running from project root")
    sys.exit(1)
load_dotenv()  # Load environment variables from .env file

from data.fred_client import FredClient
from data.processing import convert_dates
import pandas as pd

def main():
    # Initialize the client
    client = FredClient()

    # Fetch historical data for US 10-year Treasury yield (DGS10)
    # Fetch last 10 years of daily data
    df = client.get_series(series_id='DGS10', periods=3650, frequency='D')

    # Rename column to 'value' to match dashboard format
    df = df.rename(columns={'DGS10': 'value'})

    # Apply processing utilities
    df = convert_dates(df)

    # Ensure the DataFrame matches dashboard format (Date and value columns)
    assert 'Date' in df.columns, "Date column missing"
    assert 'value' in df.columns, "value column missing"

    # Summary
    print("US 10-year Treasury Yield Data Fetch Summary:")
    print(f"Total records: {len(df)}")
    print(f"Date range: {df['Date'].min()} to {df['Date'].max()}")
    print(f"Value range: {df['value'].min():.2f} to {df['value'].max():.2f}")
    print(f"Latest value: {df.iloc[-1]['value']:.2f} on {df.iloc[-1]['Date']}")
    print("\nData structure:")
    print(df.head())
    print("\nProcessing applied:")
    print("- Fetched daily data from FRED API for series DGS10")
    print("- Renamed 'DGS10' column to 'value'")
    print("- Applied convert_dates utility to normalize Date column")

if __name__ == "__main__":
    main()