"""
Generic chart builder that handles line, dual_axis, bar chart types.

This eliminates the need for individual chart functions for similar chart types.
Uses IndicatorConfig from the registry to determine chart parameters.
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from src.config.indicator_registry import IndicatorConfig
from visualization.charts import create_line_chart, apply_dark_theme, THEME
import importlib


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


def create_indicator_chart(data: dict, config: IndicatorConfig) -> go.Figure:
    """
    Generic chart builder that handles line, dual_axis, bar types.
    
    Args:
        data (dict): Data dictionary containing DataFrame and metadata
        config (IndicatorConfig): Configuration from the indicator registry
        
    Returns:
        go.Figure: Plotly figure object
    """
    # Extract DataFrame from data dict
    df = data.get('data')
    if df is None or df.empty:
        # Return empty chart with message
        fig = go.Figure()
        fig.update_layout(
            title=f"{config.display_name} - No Data Available",
            annotations=[dict(text="No data available", showarrow=False, x=0.5, y=0.5)]
        )
        return apply_dark_theme(fig)
    
    # Limit to specified number of periods and sort by date
    plot_data = df.tail(config.periods).copy()
    plot_data = plot_data.sort_values('Date')
    
    # Prepare date column for display
    plot_data = prepare_date_for_display(plot_data, frequency=config.frequency or 'M')
    
    # Handle different chart types
    if config.chart_type == "line":
        return _create_line_chart(plot_data, config)
    elif config.chart_type == "dual_axis":
        return _create_dual_axis_chart(plot_data, config)
    elif config.chart_type == "bar":
        return _create_bar_chart(plot_data, config)
    elif config.chart_type == "custom":
        return _create_custom_chart(data, config)
    else:
        raise ValueError(f"Unknown chart_type: {config.chart_type}")


def _create_line_chart(df: pd.DataFrame, config: IndicatorConfig) -> go.Figure:
    """Create a standard line chart."""
    # Fill any null values in the value column
    if config.value_column in df.columns:
        df[config.value_column] = df[config.value_column].fillna(0)
    
    # Create the chart using existing create_line_chart function
    threshold_label = f"Threshold ({config.threshold})" if config.threshold else None
    
    fig = create_line_chart(
        df,
        'Date_Str',  # Use prepared date string
        config.value_column,
        config.display_name,
        color=config.chart_color,
        show_legend=False,
        threshold=config.threshold,
        threshold_label=threshold_label
    )
    
    # Update layout for consistent styling
    fig.update_layout(
        height=config.card_chart_height,
        yaxis=dict(
            title=dict(
                text=config.value_column,
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


def _create_dual_axis_chart(df: pd.DataFrame, config: IndicatorConfig) -> go.Figure:
    """Create a dual-axis chart (for indicators like copper/gold + yield)."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # This is a placeholder - actual dual-axis logic would need to be
    # customized based on the specific indicator requirements
    # For now, fall back to line chart
    return _create_line_chart(df, config)


def _create_bar_chart(df: pd.DataFrame, config: IndicatorConfig) -> go.Figure:
    """Create a bar chart."""
    fig = go.Figure()
    
    # Fill any null values
    if config.value_column in df.columns:
        df[config.value_column] = df[config.value_column].fillna(0)
    
    fig.add_trace(go.Bar(
        x=df['Date_Str'],
        y=df[config.value_column],
        name=config.display_name,
        marker=dict(color=config.chart_color)
    ))
    
    # Add threshold line if specified
    if config.threshold is not None:
        fig.add_shape(
            type="line",
            x0=0,
            y0=config.threshold,
            x1=1,
            y1=config.threshold,
            xref="paper",
            yref="y",
            line=dict(
                color=THEME['line_colors']['warning'],
                width=1,
                dash="dash",
            )
        )
    
    fig.update_layout(
        title=dict(
            text=config.display_name,
            font=dict(size=14)
        ),
        height=config.card_chart_height,
        showlegend=False,
        yaxis=dict(
            title=dict(
                text=config.value_column,
                font=dict(size=10)
            ),
            tickfont=dict(size=9)
        ),
        xaxis=dict(
            tickangle=45,
            tickfont=dict(size=9)
        )
    )
    
    return apply_dark_theme(fig)


def _create_custom_chart(data: dict, config: IndicatorConfig) -> go.Figure:
    """Create a custom chart by dynamically importing and calling the specified function."""
    if not config.custom_chart_fn:
        raise ValueError("custom_chart_fn must be specified for custom chart type")
    
    # Parse module and function name
    module_path, function_name = config.custom_chart_fn.rsplit('.', 1)
    
    try:
        # Import the module and get the function
        module = importlib.import_module(module_path)
        chart_function = getattr(module, function_name)
        
        # Call the custom chart function, only pass periods if the function accepts it
        import inspect
        sig = inspect.signature(chart_function)
        if 'periods' in sig.parameters:
            return chart_function(data, config.periods)
        return chart_function(data)
        
    except (ImportError, AttributeError) as e:
        # Fallback to basic line chart if custom function fails
        print(f"Warning: Could not load custom chart function {config.custom_chart_fn}: {e}")
        df = data.get('data', pd.DataFrame())
        if not df.empty:
            plot_data = df.tail(config.periods).copy()
            plot_data = prepare_date_for_display(plot_data, frequency=config.frequency or 'M')
            return _create_line_chart(plot_data, config)
        else:
            fig = go.Figure()
            fig.update_layout(
                title=f"{config.display_name} - Error Loading Chart",
                annotations=[dict(text="Error loading custom chart", showarrow=False, x=0.5, y=0.5)]
            )
            return apply_dark_theme(fig)