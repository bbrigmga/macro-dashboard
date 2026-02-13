#!/usr/bin/env python3
"""
Script to create a dual-axis chart for Copper/Gold Ratio versus US 10-year Treasury yield.
"""
import sys
import os
from pathlib import Path

# Add the project root to Python path for proper imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from visualization.charts import THEME, apply_dark_theme
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure you're running this script from the project root directory")
    sys.exit(1)
import pandas as pd
import plotly.graph_objects as go
import numpy as np

def main():
    # Create mock data for demonstration
    print("Creating mock data for demonstration...")

    # Generate date range for the past year
    dates = pd.date_range(start='2023-09-18', end='2024-09-18', freq='D')

    # Mock Copper/Gold ratio data (typical range: 2.0-4.0)
    import numpy as np
    np.random.seed(42)  # For reproducible results

    # Create trending ratio data with some volatility
    base_ratio = 3.0
    trend = np.linspace(0, 0.5, len(dates))  # Slight upward trend
    noise = np.random.normal(0, 0.1, len(dates))  # Random noise
    ratios = base_ratio + trend + noise

    # Create ratio DataFrame
    ratio_df = pd.DataFrame({
        'Date': dates,
        'ratio': ratios
    })

    # Mock US 10-year Treasury yield data (typical range: 3.0-5.5%)
    base_yield = 4.0
    yield_trend = np.linspace(0, -0.5, len(dates))  # Slight downward trend
    yield_noise = np.random.normal(0, 0.05, len(dates))  # Random noise
    yields = base_yield + yield_trend + yield_noise

    # Create yield DataFrame
    yield_df = pd.DataFrame({
        'Date': dates,
        'value': yields
    })

    # Merge ratio and yield DataFrames on Date
    print("Merging Ratio and Yield DataFrames on Date...")
    final_df = pd.merge(ratio_df[['Date', 'ratio']], yield_df[['Date', 'value']],
                       on='Date', how='inner')

    # Sort by date
    final_df = final_df.sort_values('Date')

    print("\nData Summary:")
    print(f"Total merged records: {len(final_df)}")
    print(f"Date range: {final_df['Date'].min()} to {final_df['Date'].max()}")
    print(f"Ratio range: {final_df['ratio'].min():.4f} to {final_df['ratio'].max():.4f}")
    print(f"Yield range: {final_df['value'].min():.2f}% to {final_df['value'].max():.2f}%")
    print(f"Latest ratio: {final_df.iloc[-1]['ratio']:.4f}")
    print(f"Latest yield: {final_df.iloc[-1]['value']:.2f}%")

    # Create dual-axis chart
    print("\nCreating dual-axis chart...")

    fig = go.Figure()

    # Add Copper/Gold Ratio trace (primary y-axis)
    fig.add_trace(go.Scatter(
        x=final_df['Date'],
        y=final_df['ratio'],
        name='Copper/Gold Ratio',
        mode='lines+markers',
        line=dict(color=THEME['line_colors']['primary'], width=2),
        marker=dict(color=THEME['line_colors']['primary'], size=6),
        hovertemplate='%{x|%Y-%m-%d}<br>Copper/Gold Ratio: %{y:.4f}<extra></extra>'
    ))

    # Add US 10-year Treasury yield trace (secondary y-axis)
    fig.add_trace(go.Scatter(
        x=final_df['Date'],
        y=final_df['value'],
        name='US 10Y Treasury Yield',
        mode='lines+markers',
        line=dict(color=THEME['line_colors']['warning'], width=2),
        marker=dict(color=THEME['line_colors']['warning'], size=6),
        yaxis='y2',
        hovertemplate='%{x|%Y-%m-%d}<br>10Y Yield: %{y:.2f}%<extra></extra>'
    ))

    # Update layout for dual y-axes
    fig.update_layout(
        title=dict(
            text='Copper/Gold Ratio vs US 10-Year Treasury Yield',
            font=dict(size=14)
        ),
        yaxis=dict(
            title=dict(
                text="Copper/Gold Ratio",
                font=dict(size=10, color=THEME['line_colors']['primary'])
            ),
            tickfont=dict(size=9)
        ),
        yaxis2=dict(
            title=dict(
                text="10Y Treasury Yield (%)",
                font=dict(size=10, color=THEME['line_colors']['warning'])
            ),
            tickfont=dict(size=9),
            overlaying='y',
            side='right'
        ),
        xaxis=dict(
            title=None,
            tickangle=-45,
            tickfont=dict(size=9),
            type='date'
        ),
        showlegend=True,
        legend=dict(
            orientation="h",
            y=1.02,
            x=0.5,
            xanchor="center",
            font=dict(size=10)
        ),
        height=250
    )

    # Apply dark theme
    fig = apply_dark_theme(fig)

    # Save the chart as HTML
    output_file = 'copper_gold_yield_chart.html'
    fig.write_html(output_file)
    print(f"\nChart saved as {output_file}")

    print("\nChart Creation Summary:")
    print("- Dual-axis line chart created with Copper/Gold Ratio on primary y-axis")
    print("- US 10-year Treasury yield on secondary y-axis")
    print("- Applied dark theme with consistent styling")
    print("- Chart height set to 250px with markers on lines")
    print("- Data merged on Date column using inner join")
    print("- Forward-fill applied to handle missing values")
    print("- Chart saved as interactive HTML file")

if __name__ == "__main__":
    main()