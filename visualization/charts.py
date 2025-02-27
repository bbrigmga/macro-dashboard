"""
Functions for creating charts and visualizations.
"""
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd


def create_line_chart(df, x_column, y_column, title, color='blue', show_legend=False):
    """
    Create a line chart using Plotly.
    
    Args:
        df (pd.DataFrame): DataFrame with data
        x_column (str): Column name for x-axis
        y_column (str): Column name for y-axis
        title (str): Chart title
        color (str, optional): Line color
        show_legend (bool, optional): Whether to show the legend
        
    Returns:
        go.Figure: Plotly figure object
    """
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df[x_column],
        y=df[y_column],
        name=y_column,
        line=dict(color=color)
    ))
    fig.update_layout(
        title=title,
        showlegend=show_legend
    )
    return fig


def create_line_chart_with_threshold(df, x_column, y_column, title, threshold=None, 
                                    threshold_label=None, color='blue', show_legend=True):
    """
    Create a line chart with a horizontal threshold line.
    
    Args:
        df (pd.DataFrame): DataFrame with data
        x_column (str): Column name for x-axis
        y_column (str): Column name for y-axis
        title (str): Chart title
        threshold (float, optional): Value for horizontal threshold line
        threshold_label (str, optional): Label for threshold line
        color (str, optional): Line color
        show_legend (bool, optional): Whether to show the legend
        
    Returns:
        go.Figure: Plotly figure object
    """
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df[x_column],
        y=df[y_column],
        name=y_column,
        line=dict(color=color)
    ))
    
    # Add threshold line if specified
    if threshold is not None:
        fig.add_shape(
            type="line",
            x0=0,
            y0=threshold,
            x1=1,
            y1=threshold,
            xref="paper",
            yref="y",
            line=dict(
                color="red",
                width=1,
                dash="dash",
            )
        )
        
        # Add annotation for the threshold line
        if threshold_label:
            fig.add_annotation(
                x=0.95,
                y=threshold,
                xref="paper",
                yref="y",
                text=threshold_label,
                showarrow=False,
                font=dict(
                    color="red",
                    size=10
                ),
                align="right"
            )
    
    fig.update_layout(
        title=title,
        showlegend=show_legend
    )
    return fig


def create_pmi_component_chart(component_data):
    """
    Create a chart for PMI components.
    
    Args:
        component_data (dict): Dictionary with component data
        
    Returns:
        go.Figure: Plotly figure object
    """
    # Convert component data to DataFrame
    df = pd.DataFrame({
        'Component': list(component_data['component_values'].keys()),
        'Value': list(component_data['component_values'].values()),
        'Weight': [component_data['component_weights'][comp] * 100 for comp in component_data['component_values'].keys()]
    })
    
    # Create a horizontal bar chart
    fig = px.bar(
        df, 
        y='Component', 
        x='Value', 
        color='Value',
        color_continuous_scale=['red', 'yellow', 'green'],
        range_color=[40, 60],
        labels={'Value': 'Index Value', 'Component': ''},
        title='PMI Components',
        orientation='h'
    )
    
    # Add a vertical line at 50 (expansion/contraction threshold)
    fig.add_shape(
        type="line",
        x0=50,
        y0=-0.5,
        x1=50,
        y1=len(df) - 0.5,
        line=dict(
            color="black",
            width=1,
            dash="dash",
        )
    )
    
    # Add weight annotations
    for i, row in df.iterrows():
        fig.add_annotation(
            x=row['Value'],
            y=i,
            text=f"{row['Weight']:.0f}%",
            showarrow=False,
            font=dict(color="black"),
            xshift=15
        )
    
    fig.update_layout(
        xaxis=dict(range=[40, 60]),
        showlegend=False
    )
    
    return fig


# Warning indicator function moved to visualization/warning_signals.py
