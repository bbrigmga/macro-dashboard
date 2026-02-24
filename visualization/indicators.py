"""
Functions for creating visualizations for specific indicators with a modern finance-based theme.
"""
import pandas as pd
import plotly.graph_objects as go
from src.config.indicator_registry import INDICATOR_REGISTRY, get_indicator_config
from visualization.generic_chart import create_indicator_chart as create_generic_chart
from visualization.charts import (
    create_line_chart,
    create_copper_gold_yield_chart,
    create_credit_spread_chart,
    create_pscf_chart,
    create_xlp_xly_ratio_chart,
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





def create_usd_liquidity_chart(usd_liquidity_data, periods=120):
    """
    Create a chart for USD Liquidity data and S&P 500 (quarterly).

    Args:
        usd_liquidity_data (dict): Dictionary containing 'data' DataFrame.
        periods (int, optional): Number of *months* of history to display (used to calculate quarters).

    Returns:
        go.Figure: Plotly figure object
    """
    import plotly.graph_objects as go # Ensure go is imported at function scope
    import pandas as pd
    from datetime import datetime

    # Extract data
    quarterly_data = usd_liquidity_data.get('data')
    sp500_data = usd_liquidity_data.get('sp500_data')  # Explicitly get SP500 data
    num_quarters = periods // 3 + 1 # Approx quarters to display based on months

    # Basic validation
    if quarterly_data is None or quarterly_data.empty:
        fig = go.Figure()
        fig.update_layout(title="Quarterly Liquidity/S&P 500 Data Not Available")
        return apply_dark_theme(fig)

    # Prepare quarterly data
    plot_data = quarterly_data.tail(num_quarters).copy()
    plot_data['Date'] = pd.to_datetime(plot_data['Date']) # Ensure datetime type
    plot_data = plot_data.sort_values('Date')
    
    # Check if SP500 column exists in quarterly_data
    has_sp500_in_quarterly = 'SP500' in plot_data.columns

    # If SP500 is not in quarterly_data but we have sp500_data, merge it in
    if not has_sp500_in_quarterly and sp500_data is not None and not sp500_data.empty:
        sp500_plot_data = sp500_data.tail(num_quarters).copy()
        sp500_plot_data['Date'] = pd.to_datetime(sp500_plot_data['Date'])
        plot_data = pd.merge(plot_data, sp500_plot_data, on='Date', how='left')
        has_sp500 = True
    else:
        has_sp500 = has_sp500_in_quarterly

    # Fill any null values (use ffill for quarterly data)
    plot_data['USD_Liquidity'] = plot_data['USD_Liquidity'].ffill()
    if has_sp500:
        plot_data['SP500'] = plot_data['SP500'].ffill()

    # Data is already in trillions
    plot_data['USD_Liquidity_T'] = plot_data['USD_Liquidity']
    
    # Get the current liquidity value from the header calculation
    current_liquidity = usd_liquidity_data.get('current_liquidity', None)
            
    # Create a figure with two y-axes
    fig = go.Figure()
    
    # Add USD Liquidity trace (Quarterly)
    fig.add_trace(go.Scatter(
        x=plot_data['Date'].tolist(),
        y=plot_data['USD_Liquidity_T'].tolist(),
        name='USD Liquidity (Quarterly)',
        line=dict(color=THEME['line_colors']['success'], width=2)
    ))

    # Add the latest calculated value as a special point if it exists and differs from the last quarterly value
    if current_liquidity is not None:
        current_liquidity_t = current_liquidity  # Already in trillions
        last_date = plot_data['Date'].iloc[-1]

        # Check if the current value differs significantly from the last quarterly value
        last_quarterly_value_t = plot_data['USD_Liquidity_T'].iloc[-1]
        if abs(current_liquidity_t - last_quarterly_value_t) > 0.01:  # If difference is more than 0.01T
            # Add a special point for the latest calculated value
            fig.add_trace(go.Scatter(
                x=[last_date],
                y=[current_liquidity_t],
                mode='markers',
                marker=dict(size=8, color=THEME['line_colors']['success'], symbol='star'),
                name='Latest USD Liquidity',
                hovertemplate='%{x|%b %y}: %{y:.2f}T<extra></extra>'
            ))

    # Add S&P 500 trace (Quarterly)
    if has_sp500 and not plot_data['SP500'].isnull().all():
        fig.add_trace(go.Scatter(
            x=plot_data['Date'].tolist(),
            y=plot_data['SP500'].tolist(),
            name='S&P 500 (Quarterly)',
            line=dict(color=THEME['line_colors']['primary'], width=1.5),
            yaxis='y2'
        ))
    
    # Use Plotly autorange for both y-axes so the chart always opens with the
    # full USD Liquidity series visible (including negative values).

    # Update layout for dual y-axes - Use date type for x-axis
    fig.update_layout(
        title=dict(
            text='USD Liquidity & S&P 500 (Quarterly)',
            font=dict(size=14)
        ),
        yaxis=dict(
            title=dict(
                text="Liquidity (% of GDP)",
                font=dict(size=10, color=THEME['line_colors']['success'])
            ),
            tickfont=dict(size=9),
            tickformat='.2f',
            autorange=True
        ),
        xaxis=dict(
            title=None, # Remove X-axis title
            tickangle=-45, # Angle ticks for better readability
            tickfont=dict(size=9),
            type='date', # Use date type now that frequency is consistent
            dtick="M6", # Show ticks every 6 months for 5-year view
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
    if has_sp500 and 'SP500' in plot_data.columns and not plot_data['SP500'].isnull().all():
        fig.update_layout(
            yaxis2=dict(
                title=dict(
                    text="S&P 500 Index",
                    font=dict(size=10, color=THEME['line_colors']['primary'])
                ),
                tickfont=dict(size=9),
                overlaying='y',
                side='right',
                autorange=True
            )
        )
    
    # Apply dark theme
    fig = apply_dark_theme(fig)
    fig.update_layout(height=520)
    
    return fig


def create_pmi_chart(pmi_data, periods=24):
    """
    Create a line chart for the Manufacturing PMI Proxy.

    Args:
        pmi_data (dict): Dictionary returned by calculate_pmi_proxy(), containing
                         'pmi_series' (pd.Series with DatetimeIndex).
        periods (int): Number of months to display.

    Returns:
        go.Figure: Plotly figure object
    """
    pmi_series = pmi_data.get('pmi_series')
    if pmi_series is None or pmi_series.empty:
        fig = go.Figure()
        fig.update_layout(title="Manufacturing PMI Proxy - No Data Available")
        return apply_dark_theme(fig)

    # Trim to the requested number of periods
    plot_series = pmi_series.tail(periods)

    dates = plot_series.index.tolist()
    values = plot_series.values.tolist()

    fig = go.Figure()

    # Main PMI line
    fig.add_trace(go.Scatter(
        x=dates,
        y=values,
        name='PMI Proxy',
        line=dict(color=THEME['line_colors']['success'], width=2),
        hovertemplate='%{x|%b %Y}: %{y:.1f}<extra></extra>'
    ))

    # 50-threshold reference line (contraction/expansion boundary)
    fig.add_hline(
        y=50,
        line_dash='dash',
        line_color=THEME.get('grid_color', '#555555'),
        annotation_text='50 (neutral)',
        annotation_position='bottom right'
    )

    fig = apply_dark_theme(fig)
    fig.update_layout(
        yaxis_title='PMI',
        yaxis=dict(range=[20, 80]),
        height=350
    )

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


def create_indicator_chart(indicator_key, indicator_data, periods=None):
    """
    Create an indicator chart using registry-driven approach.
    
    Args:
        indicator_key (str): The indicator key from the registry
        indicator_data (dict): Dictionary containing indicator data
        periods (int, optional): Number of periods to display (overrides config default)
        
    Returns:
        go.Figure: Plotly figure object
    """
    # Get the indicator configuration from registry
    config = get_indicator_config(indicator_key)
    if config is None:
        raise ValueError(f"Indicator config not found for key: {indicator_key}")
    
    # Custom chart function mapping for complex charts
    custom_chart_functions = {
        'create_usd_liquidity_chart': create_usd_liquidity_chart,
        'create_copper_gold_yield_chart': create_copper_gold_yield_chart,
        'create_credit_spread_chart': create_credit_spread_chart,
        'create_pscf_chart': create_pscf_chart,
        'create_xlp_xly_ratio_chart': create_xlp_xly_ratio_chart,
        'create_pmi_chart': create_pmi_chart,
    }
    
    # Use periods parameter if provided, otherwise use config default
    chart_periods = periods if periods is not None else getattr(config, 'periods', None)
    
    # Check if this indicator has a custom chart function
    custom_chart_fn = getattr(config, 'custom_chart_fn', None)
    # Support both bare names ("create_foo_chart") and dotted paths ("visualization.indicators.create_foo_chart")
    custom_chart_fn_key = custom_chart_fn.rsplit('.', 1)[-1] if custom_chart_fn else None
    if custom_chart_fn_key and custom_chart_fn_key in custom_chart_functions:
        # Call the custom chart function
        import inspect
        builder = custom_chart_functions[custom_chart_fn_key]
        sig = inspect.signature(builder)
        if chart_periods is not None and 'periods' in sig.parameters:
            return builder(indicator_data, periods=chart_periods)
        return builder(indicator_data)
    
    # Use the generic chart builder for standard indicators
    if chart_periods is not None:
        # Create a modified config with the override periods
        import types
        modified_config = types.SimpleNamespace(**vars(config))
        modified_config.periods = chart_periods
        return create_generic_chart(indicator_data, modified_config)
    
    return create_generic_chart(indicator_data, config)
