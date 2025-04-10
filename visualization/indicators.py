"""
Functions for creating visualizations for specific indicators with a modern finance-based theme.
"""
import pandas as pd
import plotly.graph_objects as go  # This is imported as go
import plotly.express as px
from visualization.charts import (
    create_line_chart, 
    create_pmi_component_chart,
    THEME,
    apply_dark_theme
)
from visualization.warning_signals import create_warning_indicator

def prepare_date_for_display(df, date_column='Date', frequency='M'):
    """
    Prepare date column for display by converting to string format.
    
    Args:
        df (pd.DataFrame): DataFrame with date column
        date_column (str, optional): Name of date column
        frequency (str, optional): Frequency of data ('D' for daily, 'W' for weekly, 'M' for monthly)
        
    Returns:
        pd.DataFrame: DataFrame with added string date column
    """
    df = df.copy()
    dates = pd.to_datetime(df[date_column])
    
    if frequency == 'W':
        # Weekly format: MM/DD/YY (e.g., '01/12/23')
        df['Date_Str'] = dates.dt.strftime('%m/%d/%y')
    else:
        # Monthly format: MMM YYYY (e.g., 'Jan 2023')
        df['Date_Str'] = dates.dt.strftime('%b %Y')
    
    return df


def create_hours_worked_chart(hours_data, periods=18):
    """
    Create a chart for Average Weekly Hours data with modern styling.
    
    Args:
        hours_data (dict): Dictionary with hours worked data
        periods (int, optional): Number of periods to display
        
    Returns:
        go.Figure: Plotly figure object
    """
    # Get the data and prepare for display
    hours_plot_data = hours_data['data'].tail(periods).copy()
    hours_plot_data = prepare_date_for_display(hours_plot_data)
    
    # Ensure data is sorted properly
    hours_plot_data = hours_plot_data.sort_values('Date')
    
    # Fill any null values
    hours_plot_data['Hours'] = hours_plot_data['Hours'].fillna(0)
    
    # Create the chart
    fig = create_line_chart(
        hours_plot_data,
        'Date_Str',
        'Hours',
        'Average Weekly Hours',
        color=THEME['line_colors']['primary'],
        show_legend=False
    )
    
    # Set y-axis title
    fig.update_layout(
        yaxis=dict(
            title=dict(
                text="Hours",
                font=dict(size=10)
            ),
            tickfont=dict(size=9)
        ),
        xaxis=dict(
            tickangle=45,
            tickfont=dict(size=9),
            type='category'  # Set type to category for proper ordering
        )
    )
    
    return fig


def create_core_cpi_chart(core_cpi_data, periods=18):
    """
    Create a chart for Core CPI data with modern styling.
    
    Args:
        core_cpi_data (dict): Dictionary with Core CPI data
        periods (int, optional): Number of periods to display
        
    Returns:
        go.Figure: Plotly figure object
    """
    # Get the data and prepare for display
    cpi_plot_data = core_cpi_data['data'].tail(periods).copy()
    cpi_plot_data = prepare_date_for_display(cpi_plot_data)
    
    # Ensure data is sorted properly
    cpi_plot_data = cpi_plot_data.sort_values('Date')
    
    # Fill any null values
    cpi_plot_data['CPI_MoM'] = cpi_plot_data['CPI_MoM'].fillna(0)
    
    # Create a figure with MoM as the main axis
    fig = create_line_chart(
        cpi_plot_data,
        'Date_Str',
        'CPI_MoM',
        'Core CPI MoM % Change',
        color=THEME['line_colors']['danger'],
        show_legend=False
    )
    
    # Update layout
    fig.update_layout(
        yaxis=dict(
            title=dict(
                text="MoM %",
                font=dict(size=10, color=THEME['line_colors']['danger'])
            ),
            tickfont=dict(size=9)
        ),
        xaxis=dict(
            tickangle=45,
            tickfont=dict(size=9),
            type='category'  # Set type to category for proper ordering
        )
    )
    
    return fig


def create_initial_claims_chart(claims_data, periods=26):
    """
    Create a chart for Initial Jobless Claims data with modern styling.
    
    Args:
        claims_data (dict): Dictionary with claims data
        periods (int, optional): Number of periods to display (26 weeks = 6 months)
        
    Returns:
        go.Figure: Plotly figure object
    """
    # Get the data and prepare for display
    claims_plot_data = claims_data['data'].tail(periods).copy()
    claims_plot_data = prepare_date_for_display(claims_plot_data, frequency='W')
    
    # Ensure data is sorted properly
    claims_plot_data = claims_plot_data.sort_values('Date')
    
    # Fill any null values
    claims_plot_data['Claims'] = claims_plot_data['Claims'].fillna(0)
    
    # Use create_line_chart for consistency with other charts
    # Using 300,000 as a threshold which is a common benchmark for jobless claims
    fig = create_line_chart(
        claims_plot_data,
        'Date_Str',
        'Claims',
        'Weekly Initial Jobless Claims',
        color=THEME['line_colors']['primary'],  # Changed to primary color for consistency
        show_legend=False
    )
    
    # Update layout
    fig.update_layout(
        yaxis=dict(
            title=dict(
                text="Claims",
                font=dict(size=10)
            ),
            tickfont=dict(size=9)
        ),
        xaxis=dict(
            tickangle=45,
            tickfont=dict(size=9),
            type='category'  # Set type to category for proper ordering
        )
    )
    
    return fig


def create_pce_chart(pce_data, periods=18):
    """
    Create a chart for PCE data with modern styling.
    
    Args:
        pce_data (dict): Dictionary with PCE data
        periods (int, optional): Number of periods to display
        
    Returns:
        go.Figure: Plotly figure object
    """
    # Get the data and prepare for display
    pce_plot_data = pce_data['data'].tail(periods).copy()
    pce_plot_data = prepare_date_for_display(pce_plot_data)
    
    # Ensure data is sorted properly
    pce_plot_data = pce_plot_data.sort_values('Date')
    
    # Fill any null values
    pce_plot_data['PCE_MoM'] = pce_plot_data['PCE_MoM'].fillna(0)
    
    # Create the chart with our custom function instead of px.line
    fig = create_line_chart(
        pce_plot_data,
        'Date_Str',
        'PCE_MoM',
        'PCE MoM % Change',
        color=THEME['line_colors']['danger'],
        show_legend=False
    )
    
    # Update layout
    fig.update_layout(
        yaxis=dict(
            title=dict(
                text="MoM %",
                font=dict(size=10)
            ),
            tickfont=dict(size=9)
        ),
        xaxis=dict(
            tickangle=45,
            tickfont=dict(size=9),
            type='category'  # Set type to category for proper ordering
        )
    )
    
    return fig


def create_pmi_chart(pmi_data, periods=18):
    """
    Create a chart for PMI data with modern styling.
    
    Args:
        pmi_data (dict): Dictionary with PMI data
        periods (int, optional): Number of periods to display
        
    Returns:
        go.Figure: Plotly figure object
    """
    # First, convert the PMI series to a DataFrame with a date index
    pmi_series = pmi_data['pmi_series']
    pmi_df = pd.DataFrame(pmi_series)
    pmi_df.reset_index(inplace=True)
    pmi_df.columns = ['Date', 'PMI']
    
    # Get the last N months of data
    pmi_plot_data = pmi_df.tail(periods).copy()
    pmi_plot_data = prepare_date_for_display(pmi_plot_data)
    
    # Ensure data is sorted properly
    pmi_plot_data = pmi_plot_data.sort_values('Date')
    
    # Fill any null values
    pmi_plot_data['PMI'] = pmi_plot_data['PMI'].fillna(0)
    
    # Create the chart
    fig = create_line_chart(
        pmi_plot_data,
        'Date_Str',
        'PMI',
        'Manufacturing PMI Proxy',
        color=THEME['line_colors']['primary'],
        show_legend=False
    )
    
    # Update layout
    fig.update_layout(
        yaxis=dict(
            title=dict(
                text="PMI Value",
                font=dict(size=10)
            ),
            tickfont=dict(size=9)
        ),
        xaxis=dict(
            tickangle=45,
            tickfont=dict(size=9),
            type='category'  # Set type to category for proper ordering
        )
    )
    
    return fig


def create_gundlach_ratio_chart(copper_data, treasury_data, gold_data=None, periods=48):
    """
    Create a chart for the Gundlach Ratio (Copper/Gold ratio) and US 10Y Treasury Yield.
    
    Args:
        copper_data (dict): Dictionary with copper price data (PCOPPUSDM)
        treasury_data (dict): Dictionary with 10Y Treasury yield data (DGS10)
        gold_data (dict, optional): Dictionary with gold price data from goldapi.io
        periods (int, optional): Number of months of data to display (default: 48 for 4 years)
        
    Returns:
        go.Figure: Plotly figure object
    """
    # Create figure with dual y-axes and reduced height
    fig = go.Figure()
    
    try:
        # Get copper and treasury data
        copper_plot_data = copper_data['data'].copy()
        treasury_plot_data = treasury_data['data'].copy()
        
        # Ensure dates are properly converted to datetime
        copper_plot_data['Date'] = pd.to_datetime(copper_plot_data['Date'])
        treasury_plot_data['Date'] = pd.to_datetime(treasury_plot_data['Date'])
        
        # Sort by date and limit to requested period
        copper_plot_data = copper_plot_data.sort_values('Date').tail(periods)
        treasury_plot_data = treasury_plot_data.sort_values('Date').tail(periods)
        
        # Get gold data if available
        if gold_data is not None and 'data' in gold_data and not gold_data['data'].empty:
            gold_plot_data = gold_data['data'].copy()
            gold_plot_data['Date'] = pd.to_datetime(gold_plot_data['Date'])
            gold_plot_data = gold_plot_data.sort_values('Date')
            
            # First merge treasury and copper data to get common dates
            common_data = pd.merge(treasury_plot_data, copper_plot_data, on='Date', how='inner')
            
            # Then merge with gold data if available
            if not gold_plot_data.empty:
                merged_data = pd.merge(common_data, gold_plot_data, on='Date', how='inner')
                
                # If we have data after all merges
                if not merged_data.empty:
                    # Convert copper price from USD per metric ton to USD per pound
                    # 1 metric ton = 2204.62 pounds
                    METRIC_TON_TO_POUNDS = 2204.62
                    merged_data['CopperPricePerPound'] = merged_data['PCOPPUSDM'] / METRIC_TON_TO_POUNDS
                    
                    # Calculate the Copper/Gold ratio using price per pound / price per troy ounce
                    merged_data['CopperGoldRatio'] = merged_data['CopperPricePerPound'] / merged_data['GoldPrice']
                    
                    # Prepare date strings for better display - use compact format
                    merged_data['Date_Str'] = merged_data['Date'].dt.strftime('%b %y')
                    merged_data = merged_data.sort_values('Date')
                    
                    # Select fewer points for a cleaner display - approximately 12 points
                    display_stride = max(1, len(merged_data) // 12)
                    display_indices = list(range(0, len(merged_data), display_stride))
                    if len(merged_data) - 1 not in display_indices:
                        display_indices.append(len(merged_data) - 1)  # Always include the last point
                    
                    display_data = merged_data.iloc[display_indices].copy()
                    
                    # Add trace for Copper/Gold ratio (primary axis)
                    fig.add_trace(
                        go.Scatter(
                            x=display_data['Date_Str'].tolist(),
                            y=display_data['CopperGoldRatio'].tolist(),
                            name='Copper/Gold Ratio',
                            line=dict(color=THEME['line_colors']['primary'], width=2)
                        )
                    )
                    
                    # Add trace for 10Y Treasury Yield (secondary axis) - using SAME x-axis points
                    fig.add_trace(
                        go.Scatter(
                            x=display_data['Date_Str'].tolist(),
                            y=display_data['DGS10'].tolist(),
                            name='US 10Y Treasury Yield',
                            line=dict(color=THEME['line_colors']['warning'], width=2, dash='dot'),
                            yaxis='y2'  # Use secondary y-axis
                        )
                    )
                    
                    # Track if we have data to display
                    has_display_data = True
                else:
                    has_display_data = False
                    print("No data points after merging all datasets")
            else:
                has_display_data = False
                print("Gold data is empty")
                
            # Check if we have any data to display
            if has_display_data:
                # Add layout with tighter margins and less height
                fig.update_layout(
                    title="",
                    height=250,  # Increased height to 250px for better data visibility
                    margin=dict(t=0, b=0, l=20, r=20),  # Even tighter margins
                    legend=dict(
                        orientation="h",
                        y=1.05,
                        x=0.5,
                        xanchor="center",
                        font=dict(size=8)
                    ),
                    hovermode="x unified",
                    autosize=True,
                    template="plotly_white",
                    yaxis=dict(
                        title="Copper/Gold Ratio",
                        titlefont=dict(size=10),
                        side="left",
                        tickfont=dict(size=8),
                        fixedrange=True,  # Prevent y-axis zooming for consistency
                        showgrid=True,
                        gridwidth=1,
                        gridcolor='rgba(220,220,220,0.2)',  # Lighter grid
                        tickformat='.2f'  # Format to 2 decimal places
                    ),
                    yaxis2=dict(
                        title="10Y Treasury Yield (%)",
                        titlefont=dict(size=10),
                        side="right",
                        overlaying="y",
                        tickfont=dict(size=8),
                        fixedrange=True,  # Prevent y-axis zooming for consistency
                        showgrid=False,
                        tickformat='.1f'  # Format to 1 decimal place for percentages
                    ),
                    xaxis=dict(
                        tickangle=45,
                        tickfont=dict(size=8),
                        type='category',
                        fixedrange=True,  # Prevent x-axis zooming for consistency
                        showgrid=True,
                        gridwidth=1,
                        gridcolor='rgba(220,220,220,0.2)',  # Lighter grid
                        # Use all available x-axis ticks
                        tickmode='array',
                        tickvals=display_data['Date_Str'].tolist()
                    )
                )
            else:
                print("No display data available")
        else:
            print("Could not merge copper and gold data")
    except Exception as e:
        print(f"Error creating Gundlach Ratio chart: {str(e)}")
        import traceback
        traceback.print_exc()
    
    return fig


def create_usd_liquidity_chart(usd_liquidity_data, periods=36):
    """
    Create a chart for USD Liquidity data and S&P 500 (both weekly).
    
    Args:
        usd_liquidity_data (dict): Dictionary containing 'weekly_data' DataFrame.
        periods (int, optional): Number of *months* of history to display (used to calculate weeks).
        
    Returns:
        go.Figure: Plotly figure object
    """
    import plotly.graph_objects as go # Ensure go is imported at function scope

    # Extract data
    weekly_data = usd_liquidity_data.get('weekly_data')
    num_weeks = periods * 4 + 4 # Approx weeks to display based on months

    # Basic validation
    if weekly_data is None or weekly_data.empty:
        fig = go.Figure()
        fig.update_layout(title="Weekly Liquidity/S&P 500 Data Not Available")
        return apply_dark_theme(fig)
        
    # Prepare weekly data
    plot_data = weekly_data.tail(num_weeks).copy()
    plot_data['Date'] = pd.to_datetime(plot_data['Date']) # Ensure datetime type
    plot_data = plot_data.sort_values('Date')
    
    # Fill any null values (use ffill for weekly data)
    plot_data['USD_Liquidity'] = plot_data['USD_Liquidity'].ffill()
    plot_data['SP500'] = plot_data['SP500'].ffill()
    
    # Convert to trillions
    plot_data['USD_Liquidity_T'] = plot_data['USD_Liquidity'] / 1000000
            
    # Create a figure with two y-axes
    fig = go.Figure()
    
    # Add USD Liquidity trace (Weekly)
    fig.add_trace(go.Scatter(
        x=plot_data['Date'].tolist(), 
        y=plot_data['USD_Liquidity_T'].tolist(),
        name='USD Liquidity (Weekly)',
        line=dict(color=THEME['line_colors']['success'], width=2)
    ))
    
    # Add S&P 500 trace (Weekly)
    if 'SP500' in plot_data.columns and not plot_data['SP500'].isnull().all():
        fig.add_trace(go.Scatter(
            x=plot_data['Date'].tolist(), 
            y=plot_data['SP500'].tolist(), 
            name='S&P 500 (Weekly)',
            line=dict(color=THEME['line_colors']['primary'], width=1.5),
            yaxis='y2'
        ))
    
    # Determine dynamic ranges for axes
    liquidity_min = 5.7 # Keep floor for liquidity
    liquidity_max = plot_data['USD_Liquidity_T'].max() * 1.05 if not plot_data.empty else 10
    sp500_min = 3200 # Keep floor for SP500
    sp500_max = plot_data['SP500'].max() * 1.05 if 'SP500' in plot_data.columns and not plot_data['SP500'].isnull().all() else 5000

    # Remove manual tick calculation

    # Update layout for dual y-axes - Use date type for x-axis
    fig.update_layout(
        title=dict(
            text='USD Liquidity & S&P 500 (Weekly)',
            font=dict(size=14)
        ),
        yaxis=dict(
            title=dict(
                text="Trillions USD",
                font=dict(size=10, color=THEME['line_colors']['success'])
            ),
            tickfont=dict(size=9),
            tickformat='.2f',
            range=[liquidity_min, liquidity_max]
        ),
        xaxis=dict(
            title=None, # Remove X-axis title
            tickangle=-45, # Angle ticks for better readability
            tickfont=dict(size=9),
            type='date', # Use date type now that frequency is consistent
            dtick="M1", # Show ticks every 1 month for clarity on weekly data
            tickformat="%b '%y" # Format as 'Jan '23'
        ),
        showlegend=True,
        legend=dict(
            orientation="h",
            y=1.02,
            x=0.5,
            xanchor="center",
            font=dict(size=8)
        )
    )
    
    # Add secondary y-axis for S&P 500 if data exists
    if 'SP500' in plot_data.columns and not plot_data['SP500'].isnull().all():
        fig.update_layout(
            yaxis2=dict(
                title=dict(
                    text="S&P 500 Index",
                    font=dict(size=10, color=THEME['line_colors']['primary'])
                ),
                tickfont=dict(size=9),
                overlaying='y',
                side='right',
                range=[sp500_min, sp500_max]
            )
        )
    
    # Apply dark theme
    fig = apply_dark_theme(fig)
    
    return fig


def create_pmi_components_table(pmi_data):
    """
    Create a table of PMI components with their values and weights.
    
    Args:
        pmi_data (dict): Dictionary with PMI data
        
    Returns:
        pd.DataFrame: Table of PMI components
    """
    # Define FRED series IDs for the components
    component_tickers = {
        'new_orders': 'AMTMNO',
        'production': 'IPMAN',
        'employment': 'MANEMP',
        'supplier_deliveries': 'AMDMUS',
        'inventories': 'MNFCTRIMSA'
    }
    
    # Get the latest values for each component
    latest_values = pmi_data['component_values'].iloc[-1]
    available_components = latest_values.index # Use the index from the latest row
    
    return pd.DataFrame({
        'Component': list(available_components),
        'Ticker': [component_tickers.get(comp, 'N/A') for comp in available_components],
        'Weight': [f"{pmi_data['component_weights'][comp]*100:.0f}%" for comp in available_components],
        'Value': [f"{latest_values[comp]:.1f}" for comp in available_components],
        'Status': [create_warning_indicator(latest_values[comp] < 50, 0.5, higher_is_bad=True) 
                   for comp in available_components]
    })


def create_new_orders_chart(new_orders_data, periods=18):
    """
    Create a chart for Non-Defense Durable Goods Orders month-over-month % change.
    
    Args:
        new_orders_data (dict): Dictionary with New Orders data
        periods (int, optional): Number of periods to display
        
    Returns:
        go.Figure: Plotly figure object
    """
    # Get the data and prepare for display
    orders_plot_data = new_orders_data['data'].tail(periods).copy()
    orders_plot_data = prepare_date_for_display(orders_plot_data)
    
    # Ensure data is sorted properly
    orders_plot_data = orders_plot_data.sort_values('Date')
    
    # Fill any null values
    orders_plot_data['NEWORDER_MoM'] = orders_plot_data['NEWORDER_MoM'].fillna(0)
    
    # Create the chart - using 0 as threshold for growth vs contraction
    fig = create_line_chart(
        orders_plot_data,
        'Date_Str',
        'NEWORDER_MoM',
        'Non-Defense Durable Goods Orders',
        color=THEME['line_colors']['primary'],
        show_legend=False
    )
    
    # Update layout
    fig.update_layout(
        yaxis=dict(
            title=dict(
                text="MoM % Change",
                font=dict(size=10)
            ),
            tickfont=dict(size=9)
        ),
        xaxis=dict(
            tickangle=45,
            tickfont=dict(size=9),
            type='category'  # Set type to category for proper ordering
        )
    )
    
    return fig


def create_yield_curve_chart(yield_curve_data, periods=36):
    """
    Create a chart for the 10Y-2Y Treasury Yield Spread (yield curve).
    
    Args:
        yield_curve_data (dict): Dictionary with yield curve data
        periods (int, optional): Number of periods to display
        
    Returns:
        go.Figure: Plotly figure object
    """
    # Get the data and prepare for display
    curve_plot_data = yield_curve_data['data'].tail(periods).copy()
    curve_plot_data = prepare_date_for_display(curve_plot_data)
    
    # Ensure data is sorted properly
    curve_plot_data = curve_plot_data.sort_values('Date')
    
    # Fill any null values
    curve_plot_data['T10Y2Y'] = curve_plot_data['T10Y2Y'].fillna(0)
    
    # Create the chart using the same function as durable goods
    fig = create_line_chart(
        curve_plot_data,
        'Date_Str',
        'T10Y2Y',
        '10Y-2Y Treasury Yield Spread',
        color=THEME['line_colors']['warning'],
        show_legend=False
    )
    
    # Update y-axis title
    fig.update_layout(
        yaxis=dict(
            title=dict(
                text="Spread (%)",
                font=dict(size=10)
            ),
            tickfont=dict(size=9)
        ),
        xaxis=dict(
            tickangle=45,
            tickfont=dict(size=9),
            type='category'  # Set type to category for proper ordering
        )
    )
    
    return fig
