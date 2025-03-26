"""
Functions for creating visualizations for specific indicators with a modern finance-based theme.
"""
import pandas as pd
import plotly.graph_objects as go  # This is imported as go
import plotly.express as px
from visualization.charts import (
    create_line_chart, 
    create_line_chart_with_threshold, 
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
    fig = create_line_chart_with_threshold(
        cpi_plot_data,
        'Date_Str',
        'CPI_MoM',
        'Core CPI MoM % Change',
        threshold=0.3,
        threshold_label='0.3% threshold',
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
    
    # Use create_line_chart_with_threshold for consistency with other charts
    # Using 300,000 as a threshold which is a common benchmark for jobless claims
    fig = create_line_chart_with_threshold(
        claims_plot_data,
        'Date_Str',
        'Claims',
        'Weekly Initial Jobless Claims',
        threshold=300000,
        threshold_label='300K benchmark',
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
    fig = create_line_chart_with_threshold(
        pmi_plot_data,
        'Date_Str',
        'PMI',
        'Manufacturing PMI Proxy',
        threshold=50,
        threshold_label='Expansion/Contraction',
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


def create_usd_liquidity_chart(usd_liquidity_data, periods=36):  # Changed from 18 to 36 months (3 years)
    """
    Create a chart for USD Liquidity data with modern styling.
    Also includes S&P 500 data on a secondary y-axis for comparison.
    
    Args:
        usd_liquidity_data (dict): Dictionary with USD Liquidity data
        periods (int, optional): Number of periods to display
        
    Returns:
        go.Figure: Plotly figure object
    """
    # Get the data and prepare for display
    if 'data' in usd_liquidity_data and 'Date' in usd_liquidity_data['data'].columns and 'USD_Liquidity' in usd_liquidity_data['data'].columns:
        liquidity_plot_data = usd_liquidity_data['data'].tail(periods).copy()
        liquidity_plot_data = prepare_date_for_display(liquidity_plot_data)
        
        # Ensure data is sorted properly
        liquidity_plot_data = liquidity_plot_data.sort_values('Date')
        
        # Fill any null values
        liquidity_plot_data['USD_Liquidity'] = liquidity_plot_data['USD_Liquidity'].fillna(0)
        if 'SP500' in liquidity_plot_data.columns:
            liquidity_plot_data['SP500'] = liquidity_plot_data['SP500'].fillna(0)
        
        # Convert to trillions before creating the chart
        liquidity_plot_data['USD_Liquidity_T'] = liquidity_plot_data['USD_Liquidity'] / 1000000
        
        # Create a figure with two y-axes
        import plotly.graph_objects as go  # Ensure go is available in this scope
        fig = go.Figure()
        
        # Add USD Liquidity trace
        fig.add_trace(go.Scatter(
            x=liquidity_plot_data['Date_Str'].tolist(),  # Convert to list explicitly
            y=liquidity_plot_data['USD_Liquidity_T'].tolist(),  # Convert to list explicitly
            name='USD Liquidity',
            line=dict(color=THEME['line_colors']['success'], width=2)  # Green color
        ))
        
        # Add S&P 500 trace on secondary y-axis if available
        if 'SP500' in liquidity_plot_data.columns:
            fig.add_trace(go.Scatter(
                x=liquidity_plot_data['Date_Str'].tolist(),  # Convert to list explicitly
                y=liquidity_plot_data['SP500'].tolist(),  # Convert to list explicitly
                name='S&P 500',
                line=dict(color=THEME['line_colors']['primary'], width=2),  # Blue color
                yaxis='y2'
            ))
        
        # Update layout for dual y-axes
        fig.update_layout(
            title=dict(
                text='USD Liquidity & S&P 500',
                font=dict(size=14)
            ),
            yaxis=dict(
                title=dict(
                    text="Trillions USD",
                    font=dict(size=10, color=THEME['line_colors']['success'])
                ),
                tickfont=dict(size=9),
                tickformat='.2f',  # Format to 2 decimal places
                range=[5.7, max(liquidity_plot_data['USD_Liquidity_T']) * 1.05]  # Set minimum to 5.7 trillion
            ),
            xaxis=dict(
                tickangle=45,
                tickfont=dict(size=9),
                type='category'  # Set type to category for proper ordering
            ),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        # Add secondary y-axis for S&P 500 if available
        if 'SP500' in liquidity_plot_data.columns:
            fig.update_layout(
                yaxis2=dict(
                    title=dict(
                        text="S&P 500",
                        font=dict(size=10, color=THEME['line_colors']['primary'])
                    ),
                    tickfont=dict(size=9),
                    overlaying='y',
                    side='right',
                    range=[3200, max(liquidity_plot_data['SP500']) * 1.05]  # Set minimum to 3200
                )
            )
        
        # Apply dark theme
        fig = apply_dark_theme(fig)
        
        return fig
    else:
        # Create an empty figure if data is not available
        # Import is already at the top, but adding here for clarity and consistency
        import plotly.graph_objects as go
        fig = go.Figure()
        fig.update_layout(
            title="USD Liquidity Data Not Available",
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
        )
        return apply_dark_theme(fig)


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
    
    return pd.DataFrame({
        'Component': list(pmi_data['component_values'].keys()),
        'Ticker': [component_tickers.get(comp, 'N/A') for comp in pmi_data['component_values'].keys()],
        'Weight': [f"{pmi_data['component_weights'][comp]*100:.0f}%" for comp in pmi_data['component_values'].keys()],
        'Value': [f"{pmi_data['component_values'][comp]:.1f}" for comp in pmi_data['component_values'].keys()],
        'Status': [create_warning_indicator(pmi_data['component_values'][comp] < 50, 0.5, higher_is_bad=True) 
                for comp in pmi_data['component_values'].keys()]
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
    fig = create_line_chart_with_threshold(
        orders_plot_data,
        'Date_Str',
        'NEWORDER_MoM',
        'Non-Defense Durable Goods Orders',
        threshold=0,
        threshold_label='Growth/Contraction',
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
    # Get the data
    curve_plot_data = yield_curve_data['data'].copy()
    
    # Convert dates explicitly to datetime objects
    curve_plot_data['Date'] = pd.to_datetime(curve_plot_data['Date'])
    
    # Sort by date to ensure chronological order
    curve_plot_data = curve_plot_data.sort_values('Date')
    
    # Create display dates based on frequency (daily or monthly)
    is_daily = len(curve_plot_data) > 50  # Heuristic to determine if data is daily
    
    if is_daily:
        # For daily data, use more detailed formatting
        curve_plot_data['Date_Str'] = curve_plot_data['Date'].dt.strftime('%Y-%m-%d')
        
        # For daily data, select a subset of dates for cleaner x-axis
        total_points = len(curve_plot_data)
        
        # For 3 years of data, show more ticks (one per quarter)
        display_ticks = min(18, total_points)  # Display at most 18 ticks for 3 years (6 per year)
        tick_indices = [int(i * (total_points - 1) / (display_ticks - 1)) for i in range(display_ticks)]
        
        # For x-axis labels, use month-year format for better readability
        curve_plot_data['Month_Year'] = curve_plot_data['Date'].dt.strftime('%b %Y')
    else:
        # For monthly data, use simpler formatting
        curve_plot_data['Date_Str'] = curve_plot_data['Date'].dt.strftime('%b %Y')
    
    # Fill any null values to avoid rendering issues
    curve_plot_data['T10Y2Y'] = curve_plot_data['T10Y2Y'].fillna(0)
    
    # Create a figure directly using go.Figure
    import plotly.graph_objects as go
    fig = go.Figure()
    
    # Add the yield curve line
    fig.add_trace(go.Scatter(
        x=curve_plot_data['Date_Str'].tolist(),  # Convert to list explicitly
        y=curve_plot_data['T10Y2Y'].tolist(),    # Convert to list explicitly
        name='Yield Spread',
        line=dict(color=THEME['line_colors']['warning'], width=2)
    ))
    
    # Add a horizontal line at zero (inversion threshold)
    fig.add_shape(
        type="line",
        x0=0,
        y0=0,
        x1=1,
        y1=0,
        xref="paper",
        yref="y",
        line=dict(
            color=THEME['line_colors']['warning'],
            width=1,
            dash="dash",
        )
    )
    
    # Add an annotation for the inversion line
    fig.add_annotation(
        x=0.95,
        y=0,
        xref="paper",
        yref="y",
        text="Inversion Line",
        showarrow=False,
        font=dict(
            size=10,
            color=THEME['line_colors']['warning']
        ),
        bgcolor="rgba(0,0,0,0.5)",
        bordercolor=THEME['line_colors']['warning'],
        borderwidth=1,
        borderpad=4,
        yshift=10
    )
    
    # Update layout
    fig.update_layout(
        title=dict(
            text='10Y-2Y Treasury Yield Spread (3-Year History)',
            font=dict(size=14)
        ),
        yaxis=dict(
            title=dict(
                text="Spread (%)",
                font=dict(size=10)
            ),
            tickfont=dict(size=9),
            tickformat='.2f'  # Format to 2 decimal places
        ),
        margin=dict(l=40, r=40, t=40, b=80),  # Add more margin at bottom for date labels
        showlegend=False
    )
    
    # Customize x-axis based on data frequency
    if is_daily:
        # For daily data, we need to be selective about which ticks to show
        tick_vals = [curve_plot_data['Date_Str'].iloc[i] for i in tick_indices]
        tick_text = [curve_plot_data['Month_Year'].iloc[i] for i in tick_indices]
        
        fig.update_layout(
            xaxis=dict(
                tickangle=45,
                tickfont=dict(size=9),
                type='category',
                tickmode='array',
                tickvals=tick_vals,
                ticktext=tick_text
            )
        )
    else:
        # For monthly data, we can show all ticks
        fig.update_layout(
            xaxis=dict(
                tickangle=45,
                tickfont=dict(size=9),
                type='category'
            )
        )
    
    # Apply dark theme
    fig = apply_dark_theme(fig)
    
    return fig
