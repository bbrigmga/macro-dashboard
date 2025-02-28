"""
Functions for creating visualizations for specific indicators with a modern finance-based theme.
"""
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from visualization.charts import (
    create_line_chart, 
    create_line_chart_with_threshold, 
    create_pmi_component_chart,
    THEME,
    apply_dark_theme
)


def prepare_date_for_display(df, date_column='Date'):
    """
    Prepare date column for display by converting to string format.
    
    Args:
        df (pd.DataFrame): DataFrame with date column
        date_column (str, optional): Name of date column
        
    Returns:
        pd.DataFrame: DataFrame with added string date column
    """
    df = df.copy()
    df['Date_Str'] = pd.to_datetime(df[date_column]).dt.strftime('%b %Y')  # More compact date format
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
        periods (int, optional): Number of periods to display
        
    Returns:
        go.Figure: Plotly figure object
    """
    # Get the data and prepare for display
    claims_plot_data = claims_data['data'].tail(periods).copy()
    claims_plot_data = prepare_date_for_display(claims_plot_data)
    
    # Create the chart with our custom function instead of px.line
    fig = create_line_chart(
        claims_plot_data,
        'Date_Str',
        'Claims',
        'Weekly Initial Jobless Claims',
        color=THEME['line_colors']['warning'],
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


def create_pmi_components_table(pmi_data):
    """
    Create a DataFrame for PMI components with modern styling.
    
    Args:
        pmi_data (dict): Dictionary with PMI data
        
    Returns:
        pd.DataFrame: DataFrame with PMI component data
    """
    from visualization.warning_signals import create_warning_indicator
    
    component_data = {
        'Component': list(pmi_data['component_values'].keys()),
        'Weight': [f"{pmi_data['component_weights'][comp]*100:.0f}%" for comp in pmi_data['component_values'].keys()],
        'Value': [f"{pmi_data['component_values'][comp]:.1f}" for comp in pmi_data['component_values'].keys()],
        'Status': [create_warning_indicator(pmi_data['component_values'][comp] < 50, 0.5, higher_is_bad=True) 
                for comp in pmi_data['component_values'].keys()]
    }
    
    return pd.DataFrame(component_data)
