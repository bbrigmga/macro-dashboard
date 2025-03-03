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
            tickfont=dict(size=9)
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
            tickfont=dict(size=9)
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
            tickfont=dict(size=9)
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
            tickfont=dict(size=9)
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
            tickfont=dict(size=9)
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
        
        # Convert to trillions before creating the chart
        liquidity_plot_data['USD_Liquidity_T'] = liquidity_plot_data['USD_Liquidity'] / 1000000
        
        # Create a figure with two y-axes
        import plotly.graph_objects as go  # Ensure go is available in this scope
        fig = go.Figure()
        
        # Add USD Liquidity trace
        fig.add_trace(go.Scatter(
            x=liquidity_plot_data['Date_Str'],
            y=liquidity_plot_data['USD_Liquidity_T'],
            name='USD Liquidity',
            line=dict(color=THEME['line_colors']['success'], width=2)  # Green color
        ))
        
        # Add S&P 500 trace on secondary y-axis if available
        if 'SP500' in liquidity_plot_data.columns:
            fig.add_trace(go.Scatter(
                x=liquidity_plot_data['Date_Str'],
                y=liquidity_plot_data['SP500'],
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
                tickformat='.2f'  # Format to 2 decimal places
            ),
            xaxis=dict(
                tickangle=45,
                tickfont=dict(size=9)
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
                    side='right'
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
    Create a DataFrame for PMI components with modern styling.
    
    Args:
        pmi_data (dict): Dictionary with PMI data
        
    Returns:
        pd.DataFrame: DataFrame with PMI component data
    """
    component_data = {
        'Component': list(pmi_data['component_values'].keys()),
        'Weight': [f"{pmi_data['component_weights'][comp]*100:.0f}%" for comp in pmi_data['component_values'].keys()],
        'Value': [f"{pmi_data['component_values'][comp]:.1f}" for comp in pmi_data['component_values'].keys()],
        'Status': [create_warning_indicator(pmi_data['component_values'][comp] < 50, 0.5, higher_is_bad=True) 
                for comp in pmi_data['component_values'].keys()]
    }
    
    return pd.DataFrame(component_data)
