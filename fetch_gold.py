#!/usr/bin/env python3
"""
Script to fetch Gold COMEX prices using YahooClient and process the data.
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from data.yahoo_client import YahooClient
import pandas as pd

def main():
    # Initialize the client
    client = YahooClient()

    # Fetch historical data for Gold COMEX (GC=F)
    # Fetch last 365 days of daily data
    df = client.get_historical_prices(ticker='GC=F', periods=365, frequency='1d')

    # Ensure the DataFrame matches dashboard format (Date and value columns)
    assert 'Date' in df.columns, "Date column missing"
    assert 'value' in df.columns, "value column missing"

    # Summary
    print("Gold COMEX Data Fetch Summary:")
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