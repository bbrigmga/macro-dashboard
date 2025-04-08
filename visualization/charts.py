"""
Functions for creating charts and visualizations with a modern finance-based theme.
"""
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd


# Define theme colors
THEME = {
    'background': '#f5f7fa',  # Light gray-blue background
    'paper_bgcolor': '#ffffff',  # White paper background
    'font_color': '#333333',  # Dark text for contrast on light background
    'grid_color': 'rgba(0, 0, 0, 0.1)',  # Subtle dark grid lines
    'line_colors': {
        'primary': '#1a7fe0',
        'success': '#00c853',
        'warning': '#ff9800',
        'danger': '#f44336',
        'neutral': '#78909c'
    },
    'colorscale': [[0, '#f44336'], [0.5, '#ff9800'], [1, '#00c853']]
}


def apply_dark_theme(fig):
    """
    Apply the dark finance theme to a plotly figure.
    
    Args:
        fig (go.Figure): Plotly figure object
        
    Returns:
        go.Figure: Themed figure object
    """
    fig.update_layout(
        paper_bgcolor=THEME['paper_bgcolor'],
        plot_bgcolor=THEME['background'],
        font=dict(
            family="'Inter', 'Roboto', sans-serif",
            color=THEME['font_color']
        ),
        margin=dict(l=10, r=10, t=30, b=10),
        height=250
    )
    
    # Update axes
    fig.update_xaxes(
        gridcolor=THEME['grid_color'],
        zerolinecolor=THEME['grid_color']
    )
    fig.update_yaxes(
        gridcolor=THEME['grid_color'],
        zerolinecolor=THEME['grid_color']
    )
    
    return fig


def create_line_chart(df, x_column, y_column, title, color=None, show_legend=False, 
                        threshold=None, threshold_label=None):
    """
    Create a line chart using Plotly with the dark finance theme, optionally adding a threshold line.
    
    Args:
        df (pd.DataFrame): DataFrame with data
        x_column (str): Column name for x-axis
        y_column (str): Column name for y-axis
        title (str): Chart title
        color (str, optional): Line color. Defaults to primary theme color.
        show_legend (bool, optional): Whether to show the legend. Defaults to False.
        threshold (float, optional): Value for horizontal threshold line. Defaults to None.
        threshold_label (str, optional): Label for threshold line. Defaults to None.
        
    Returns:
        go.Figure: Plotly figure object
    """
    if color is None:
        color = THEME['line_colors']['primary']
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df[x_column].tolist(),  # Convert to list explicitly
        y=df[y_column].tolist(),  # Convert to list explicitly
        name=y_column,
        mode='lines+markers',  # Add markers to the line
        line=dict(color=color, width=2),
        marker=dict(color=color, size=6)  # Add marker styling
    ))

    # Add threshold line if specified
    if threshold is not None:
        threshold_color = THEME['line_colors']['warning']
        
        fig.add_shape(
            type="line",
            x0=0,
            y0=threshold,
            x1=1,
            y1=threshold,
            xref="paper",
            yref="y",
            line=dict(
                color=threshold_color,
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
                    color=threshold_color,
                    size=10
                ),
                align="right"
            )
    
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(size=14)
        ),
        showlegend=show_legend,
        xaxis=dict(type='category')  # Set type to category for proper ordering
    )
    
    return apply_dark_theme(fig)


def create_pmi_component_chart(component_data):
    """
    Create a chart for PMI components with the dark finance theme.
    
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
        color_continuous_scale=THEME['colorscale'],
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
            color=THEME['line_colors']['warning'],
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
            font=dict(color=THEME['font_color']),
            xshift=15
        )
    
    fig.update_layout(
        xaxis=dict(range=[40, 60]),
        showlegend=False,
        title=dict(
            text='PMI Components',
            font=dict(size=14)
        )
    )
    
    return apply_dark_theme(fig)
