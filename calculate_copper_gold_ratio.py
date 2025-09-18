#!/usr/bin/env python3
"""
Script to calculate Copper/Gold Ratio using fetched COMEX prices.
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from data.yahoo_client import YahooClient
import pandas as pd

def main():
    # Initialize the client
    client = YahooClient()

    # Fetch historical data for Copper COMEX (HG=F)
    print("Fetching Copper COMEX data...")
    copper_df = client.get_historical_prices(ticker='HG=F', periods=365, frequency='1d')
    copper_df = copper_df.rename(columns={'value': 'copper'})

    # Fetch historical data for Gold COMEX (GC=F)
    print("Fetching Gold COMEX data...")
    gold_df = client.get_historical_prices(ticker='GC=F', periods=365, frequency='1d')
    gold_df = gold_df.rename(columns={'value': 'gold'})

    # Merge DataFrames on Date
    print("Merging DataFrames on Date...")
    merged_df = pd.merge(copper_df, gold_df, on='Date', how='outer')

    # Handle missing data: forward-fill, then drop any remaining NaNs
    print("Handling missing data...")
    merged_df = merged_df.sort_values('Date').fillna(method='ffill').dropna()

    # Compute Copper/Gold ratio
    print("Computing Copper/Gold ratio...")
    merged_df['ratio'] = merged_df['copper'] / merged_df['gold']

    # Create new DataFrame with Date and ratio columns
    ratio_df = merged_df[['Date', 'ratio']].copy()

    # Summary
    print("\nCopper/Gold Ratio Calculation Summary:")
    print(f"Total records: {len(ratio_df)}")
    print(f"Date range: {ratio_df['Date'].min()} to {ratio_df['Date'].max()}")
    print(f"Ratio range: {ratio_df['ratio'].min():.4f} to {ratio_df['ratio'].max():.4f}")
    print(f"Latest ratio: {ratio_df.iloc[-1]['ratio']:.4f} on {ratio_df.iloc[-1]['Date']}")
    print(f"Average ratio: {ratio_df['ratio'].mean():.4f}")

    print("\nResulting Data Structure:")
    print(ratio_df.head(10))

    print("\nProcessing Applied:")
    print("- Fetched Copper (HG=F) and Gold (GC=F) COMEX prices from Yahoo Finance")
    print("- Merged DataFrames on Date column using outer join")
    print("- Forward-filled missing values to handle gaps")
    print("- Dropped any remaining NaN values after forward-fill")
    print("- Computed ratio as Copper value divided by Gold value")
    print("- Created new DataFrame with Date and ratio columns only")

if __name__ == "__main__":
    main()