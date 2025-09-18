#!/usr/bin/env python3
"""
Script to fetch US 10-year Treasury yield data using FredClient and process the data.
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from dotenv import load_dotenv
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