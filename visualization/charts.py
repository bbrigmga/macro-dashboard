"""
Functions for creating charts and visualizations with a modern finance-based theme.
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from src.config.settings import Settings

# Initialize settings
settings = Settings()
THEME = settings.chart.theme_colors


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
        x=df[x_column],  # Avoid tolist() to prevent unnecessary copies
        y=df[y_column],  # Avoid tolist() to prevent unnecessary copies
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
        showlegend=show_legend
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


def create_copper_gold_yield_chart(copper_gold_data):
    """
    Create a dual-axis chart for Copper/Gold Ratio vs US 10-Year Treasury Yield.

    Args:
        copper_gold_data (dict): Dictionary containing merged data with Date, ratio, and yield columns

    Returns:
        go.Figure: Plotly figure object with dual y-axes
    """
    final_df = copper_gold_data.get('data', pd.DataFrame())
    if final_df.empty:
        return go.Figure()

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.7, 0.3],
        specs=[[{"secondary_y": True}], [{"secondary_y": False}]]
    )

    fig.add_trace(
        go.Scatter(
            x=final_df['Date'],
            y=final_df['ratio'],
            name='Copper/Gold Ratio',
            line=dict(color='#1f77b4', width=2),
            hovertemplate='%{x|%Y-%m-%d}<br>Copper/Gold Ratio: %{y:.4f}<extra></extra>'
        ),
        row=1,
        col=1
    )

    fig.add_trace(
        go.Scatter(
            x=final_df['Date'],
            y=final_df['yield'],
            name='10Y Yield (%)',
            line=dict(color='#d62728', width=2),
            hovertemplate='%{x|%Y-%m-%d}<br>10Y Yield: %{y:.2f}%<extra></extra>'
        ),
        row=1,
        col=1,
        secondary_y=True
    )

    if 'corr' in final_df.columns:
        fig.add_trace(
            go.Scatter(
                x=final_df['Date'],
                y=final_df['corr'],
                name='60-Week Correlation',
                fill='tozeroy',
                line=dict(color='#ff7f0e'),
                hovertemplate='%{x|%Y-%m-%d}<br>Corr: %{y:.2f}<extra></extra>'
            ),
            row=2,
            col=1
        )

    fig.update_layout(
        title=dict(text='Copper/Gold Ratio vs 10Y Treasury + 60W Correlation', font=dict(size=14)),
        height=520,
        template='plotly_white',
        yaxis=dict(title=dict(text='Copper/Gold Ratio', font=dict(color='#1f77b4')), tickfont=dict(color='#1f77b4')),
        yaxis2=dict(title=dict(text='10Y Yield (%)', font=dict(color='#d62728')), tickfont=dict(color='#d62728'), overlaying='y', side='right'),
        yaxis3=dict(title=dict(text='Correlation'), range=[-1, 1], gridcolor='#eee'),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        hovermode='x unified',
        margin=dict(l=10, r=10, t=40, b=10)
    )

    return fig


def create_yield_curve_chart(yield_curve_data):
    """
    Create a chart for the 2-10 Year Treasury Spread (T10Y2Y).

    Args:
        yield_curve_data (dict): Dictionary containing spread data with 'Date' and 'T10Y2Y' columns

    Returns:
        go.Figure: Plotly figure object
    """
    df = yield_curve_data.get('data', pd.DataFrame())
    if df.empty:
        return go.Figure()

    df = df.copy()
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date')

    value_col = 'T10Y2Y' if 'T10Y2Y' in df.columns else 'value'

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df['Date'],
        y=df[value_col],
        name='2-10Y Spread',
        mode='lines+markers',
        line=dict(color='#f44336', width=2),
        marker=dict(color='#f44336', size=4),
        hovertemplate='%{x|%b %Y}<br>Spread: %{y:.2f}%<extra></extra>'
    ))

    # Zero line to mark inversion threshold
    fig.add_hline(
        y=0,
        line_dash='dash',
        line_color='rgba(255, 193, 7, 0.7)',
        line_width=1
    )

    fig.update_layout(
        title=dict(text='2-10 Year Treasury Spread', font=dict(size=14)),
        height=360,
        showlegend=False,
        yaxis=dict(
            title=dict(text='Spread (%)', font=dict(size=10)),
            tickfont=dict(size=9),
            ticksuffix='%'
        ),
        xaxis=dict(
            title=None,
            tickfont=dict(size=9),
            type='date',
            dtick='M12',
            tickformat='%Y'
        ),
        hovermode='x unified',
        margin=dict(l=10, r=10, t=40, b=10)
    )

    return apply_dark_theme(fig)


def create_credit_spread_chart(credit_spread_data):
    """
    Create a chart for the ICE BofA US High Yield OAS (BAMLH0A0HYM2).

    Args:
        credit_spread_data (dict): Dictionary containing spread data with 'Date' and 'value' columns

    Returns:
        go.Figure: Plotly figure object
    """
    df = credit_spread_data.get('data', pd.DataFrame())
    if df.empty:
        return go.Figure()

    df = df.copy()
    df['Date_Str'] = pd.to_datetime(df['Date']).dt.strftime('%b %Y')

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df['Date_Str'],
        y=df['value'],
        name='HY OAS',
        mode='lines',
        line=dict(color='#9c27b0', width=2),
        fill='tozeroy',
        fillcolor='rgba(156, 39, 176, 0.08)',
        hovertemplate='%{x}<br>Spread: %{y:.2f}%<extra></extra>'
    ))

    # Add threshold line at 5%
    fig.add_hline(
        y=5.0,
        line_dash='dash',
        line_color='rgba(255, 165, 0, 0.6)',
        annotation_text='Threshold (5.0)',
        annotation_position='top right',
        annotation_font_size=10
    )

    fig.update_layout(
        title=dict(text='US High Yield OAS – Credit Spreads (5Y)', font=dict(size=14)),
        showlegend=False,
        yaxis=dict(
            title=dict(text='value', font=dict(size=10)),
            tickfont=dict(size=9),
            ticksuffix='%'
        ),
        xaxis=dict(
            title=None,
            tickfont=dict(size=9),
            tickangle=45
        ),
        hovermode='x unified',
        margin=dict(l=10, r=10, t=40, b=10)
    )

    fig = apply_dark_theme(fig)
    fig.update_layout(height=360)
    return fig


def create_pscf_chart(pscf_data):
    """
    Create a price chart for PSCF (Invesco S&P SmallCap Financials ETF).

    Args:
        pscf_data (dict): Dictionary containing price data with 'Date' and 'value' columns

    Returns:
        go.Figure: Plotly figure object
    """
    df = pscf_data.get('data', pd.DataFrame())
    if df.empty:
        return go.Figure()

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df['Date'],
        y=df['value'],
        name='PSCF',
        mode='lines',
        line=dict(color=THEME['line_colors']['primary'], width=2),
        fill='tozeroy',
        fillcolor='rgba(26, 127, 224, 0.08)',
        hovertemplate='%{x|%Y-%m-%d}<br>Price: $%{y:.2f}<extra></extra>'
    ))

    fig.update_layout(
        title=dict(text='PSCF – Small Cap Financials ETF (5Y)', font=dict(size=14)),
        height=520,
        showlegend=False,
        yaxis=dict(
            title=dict(text='Price ($)', font=dict(size=10)),
            tickfont=dict(size=9),
            tickprefix='$'
        ),
        xaxis=dict(
            title=None,
            tickfont=dict(size=9),
            type='date'
        ),
        hovermode='x unified',
        margin=dict(l=10, r=10, t=40, b=10)
    )

    return apply_dark_theme(fig)


def create_xlp_xly_ratio_chart(xlp_xly_data):
    """
    Create a chart for the XLP/XLY (Consumer Staples / Consumer Discretionary) ratio.

    Args:
        xlp_xly_data (dict): Dictionary containing ratio data with 'Date' and 'value' columns

    Returns:
        go.Figure: Plotly figure object
    """
    df = xlp_xly_data.get('data', pd.DataFrame())
    if df.empty:
        return go.Figure()

    df = df.copy()
    df['Date_Str'] = pd.to_datetime(df['Date']).dt.strftime('%b %Y')

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df['Date_Str'],
        y=df['value'],
        name='XLP/XLY',
        mode='lines+markers',
        line=dict(color='#26a69a', width=2),
        marker=dict(color='#26a69a', size=6),
        hovertemplate='%{x}<br>Ratio: %{y:.4f}<extra></extra>'
    ))

    # Add a flat reference line at 1.0 (parity)
    fig.add_hline(
        y=1.0,
        line_dash='dash',
        line_color='rgba(255,255,255,0.35)',
        annotation_text='Parity',
        annotation_position='top right',
        annotation_font_size=10
    )

    fig.update_layout(
        title=dict(text='XLP/XLY – Staples vs Discretionary (3Y)', font=dict(size=14)),
        showlegend=False,
        yaxis=dict(
            title=dict(text='Ratio', font=dict(size=10)),
            tickfont=dict(size=9),
            tickformat='.3f'
        ),
        xaxis=dict(
            title=None,
            tickfont=dict(size=9),
            tickangle=45
        ),
        hovermode='x unified',
        margin=dict(l=10, r=10, t=40, b=10)
    )

    fig = apply_dark_theme(fig)
    # Override height after apply_dark_theme (which defaults to 250)
    fig.update_layout(height=360)
    return fig


def create_regime_quadrant_chart(data: dict):
    """
    Create the Growth/Inflation Regime Quadrant Chart (Snail Trail).
    
    Args:
        data: Dictionary with regime quadrant data from IndicatorData.get_regime_quadrant_data()
        
    Returns:
        go.Figure: Plotly figure object
    """
    import numpy as np
    
    # Extract data
    trail_data = data.get('trail_data', pd.DataFrame())
    current_growth = data.get('current_growth', 0.0)
    current_inflation = data.get('current_inflation', 0.0)
    projected_growth = data.get('projected_growth', current_growth)
    projected_inflation = data.get('projected_inflation', current_inflation)
    current_regime = data.get('current_regime', 'Unknown')
    
    # Handle empty data case
    if trail_data.empty or len(trail_data) == 0:
        fig = go.Figure()
        fig.add_annotation(
            x=0.5, y=0.5,
            text="No regime data available",
            xref="paper", yref="paper",
            showarrow=False,
            font=dict(size=16, color="gray")
        )
        fig = apply_dark_theme(fig)
        fig.update_layout(height=500)
        return fig
    
    # Fixed axis range of ±3 for both axes
    x_range = [-3, 3]
    y_range = [-3, 3]
    
    fig = go.Figure()
    
    # Add quadrant background shading
    fig.add_shape(type="rect", x0=0, x1=x_range[1], y0=0, y1=y_range[1],
                  fillcolor="rgba(255, 152, 0, 0.08)", line=dict(width=0))  # Top-Right: Reflation
    fig.add_shape(type="rect", x0=0, x1=x_range[1], y0=y_range[0], y1=0,
                  fillcolor="rgba(76, 175, 80, 0.08)", line=dict(width=0))   # Bottom-Right: Goldilocks  
    fig.add_shape(type="rect", x0=x_range[0], x1=0, y0=0, y1=y_range[1],
                  fillcolor="rgba(244, 67, 54, 0.08)", line=dict(width=0))   # Top-Left: Stagflation
    fig.add_shape(type="rect", x0=x_range[0], x1=0, y0=y_range[0], y1=0,
                  fillcolor="rgba(33, 150, 243, 0.08)", line=dict(width=0))  # Bottom-Left: Deflation
    
    # Add zero lines
    fig.add_hline(y=0, line=dict(color='rgba(128,128,128,0.5)', width=2))
    fig.add_vline(x=0, line=dict(color='rgba(128,128,128,0.5)', width=2))
    
    # Add quadrant labels
    label_offset = 0.1
    fig.add_annotation(x=x_range[1] - label_offset, y=y_range[1] - label_offset,
                      text="Reflation<br>Commodities, Energy", showarrow=False,
                      xref="x", yref="y", xanchor="right", yanchor="top",
                      font=dict(size=10, color="rgba(255, 152, 0, 0.8)"))
    
    fig.add_annotation(x=x_range[1] - label_offset, y=y_range[0] + label_offset,
                      text="Goldilocks<br>Tech, Equities", showarrow=False,
                      xref="x", yref="y", xanchor="right", yanchor="bottom",
                      font=dict(size=10, color="rgba(76, 175, 80, 0.8)"))
    
    fig.add_annotation(x=x_range[0] + label_offset, y=y_range[1] - label_offset,
                      text="Stagflation<br>Gold, Cash", showarrow=False,
                      xref="x", yref="y", xanchor="left", yanchor="top",
                      font=dict(size=10, color="rgba(244, 67, 54, 0.8)"))
    
    fig.add_annotation(x=x_range[0] + label_offset, y=y_range[0] + label_offset,
                      text="Deflation<br>Long Bonds, Utilities", showarrow=False,
                      xref="x", yref="y", xanchor="left", yanchor="bottom",
                      font=dict(size=10, color="rgba(33, 150, 243, 0.8)"))
    
    # Create trail: marker sizes and colors with gradient effect
    n_points = len(trail_data)
    if n_points > 0:
        # Marker sizes: grow from 3 to 14 toward the present
        trail_sizes = np.linspace(3, 14, n_points)
        
        # Color gradient: start faded, end bright
        trail_colors = np.linspace(0.15, 1.0, n_points)
        
        # Add the snail trail
        fig.add_trace(go.Scatter(
            x=trail_data['growth_zscore'],
            y=trail_data['inflation_zscore'],
            mode='lines+markers',
            marker=dict(
                size=trail_sizes,
                color=trail_colors,
                colorscale=[[0, 'rgba(255,111,0,0.15)'], [1, 'rgba(255,111,0,1.0)']],
                showscale=False,
            ),
            line=dict(
                color='rgba(255,111,0,0.4)',
                width=1.5,
            ),
            hovertemplate='Date: %{text}<br>Growth: %{x:.2f}<br>Inflation: %{y:.2f}<extra></extra>',
            text=trail_data['Date'].dt.strftime('%b %d, %Y') if hasattr(trail_data['Date'], 'dt') else trail_data['Date'],
            name='Regime Trail',
            showlegend=False,
        ))
    
    # Add current point
    fig.add_trace(go.Scatter(
        x=[current_growth],
        y=[current_inflation],
        mode='markers+text',
        marker=dict(size=18, color='#ff6f00', line=dict(color='white', width=2)),
        text=[current_regime],
        textposition='top center',
        textfont=dict(size=12, color='#ff6f00'),
        name='Current Regime',
        showlegend=False,
        hovertemplate=f'Current: {current_regime}<br>Growth: {current_growth:.2f}<br>Inflation: {current_inflation:.2f}<extra></extra>'
    ))
    
    # Add projected arrow if different from current
    if abs(projected_growth - current_growth) > 0.01 or abs(projected_inflation - current_inflation) > 0.01:
        fig.add_annotation(
            x=projected_growth,
            y=projected_inflation,
            ax=current_growth,
            ay=current_inflation,
            xref='x', yref='y',
            axref='x', ayref='y',
            showarrow=True,
            arrowhead=3,
            arrowsize=1.5,
            arrowwidth=2,
            arrowcolor='rgba(255,111,0,0.6)',
            standoff=10,
        )
    
    # Apply layout
    fig.update_layout(
        height=500,
        xaxis=dict(
            title="Growth Momentum (CPER/GLD Z-Score)",
            zeroline=True, zerolinewidth=2, zerolinecolor='rgba(128,128,128,0.5)',
            range=x_range,
        ),
        yaxis=dict(
            title="Inflation Momentum (TIP/IEF Z-Score)",
            zeroline=True, zerolinewidth=2, zerolinecolor='rgba(128,128,128,0.5)',
            range=y_range,
        ),
        margin=dict(l=60, r=60, t=40, b=60),
        hovermode='closest',
        title=dict(text='Growth/Inflation Regime Quadrant', font=dict(size=14))
    )
    
    # Apply dark theme
    fig = apply_dark_theme(fig)
    fig.update_layout(height=500)  # Override the default height from apply_dark_theme
    
    return fig
