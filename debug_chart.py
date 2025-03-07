"""
Debug script for isolating and fixing chart rendering issues in the Macro Dashboard.
This script focuses on creating a simple test chart to identify data feeding problems.
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from visualization.charts import apply_dark_theme, THEME

# Set up the Streamlit page
st.set_page_config(page_title="Chart Debug", layout="wide")
st.title("Chart Debugging Tool")

# Create sample data - this ensures we have clean, controlled test data
def create_sample_data():
    dates = pd.date_range(start='2023-01-01', periods=12, freq='M')
    values = [45, 48, 52, 55, 53, 51, 49, 47, 45, 48, 52, 54]
    
    df = pd.DataFrame({
        'Date': dates,
        'Value': values
    })
    
    # Create a string version of dates for display
    df['Date_Str'] = df['Date'].dt.strftime('%b %Y')
    
    return df

# Display the raw data
sample_data = create_sample_data()
st.subheader("Raw Data")
st.dataframe(sample_data)

# Create a simple bar chart - vertical orientation
st.subheader("Vertical Bar Chart")
st.write("Using explicit lists for x and y data:")

# Method 1: Create chart with explicit list conversion
fig1 = go.Figure()
fig1.add_trace(go.Bar(
    x=sample_data['Date_Str'].tolist(),  # Convert to list explicitly
    y=sample_data['Value'].tolist(),     # Convert to list explicitly
    name='Sample Data',
    marker_color=THEME['line_colors']['primary'],
    orientation='v'  # Explicitly set vertical orientation
))

fig1.update_layout(
    title="Sample Data - Explicit Lists",
    xaxis=dict(title="Date", type='category'),  # Set type='category' for categorical x-axis
    yaxis=dict(title="Value"),
    height=400
)

fig1 = apply_dark_theme(fig1)
st.plotly_chart(fig1, use_container_width=True)

# Method 2: Create chart with DataFrame columns directly
st.subheader("Using DataFrame columns directly:")
fig2 = go.Figure()
fig2.add_trace(go.Bar(
    x=sample_data['Date_Str'],  # Using DataFrame column directly
    y=sample_data['Value'],     # Using DataFrame column directly
    name='Sample Data',
    marker_color=THEME['line_colors']['success'],
    orientation='v'  # Explicitly set vertical orientation
))

fig2.update_layout(
    title="Sample Data - DataFrame Columns",
    xaxis=dict(title="Date", type='category'),  # Set type='category' for categorical x-axis
    yaxis=dict(title="Value"),
    height=400
)

fig2 = apply_dark_theme(fig2)
st.plotly_chart(fig2, use_container_width=True)

# Create a dual-axis chart
st.subheader("Dual-Axis Chart")
# Add a secondary metric to the sample data
sample_data['Secondary'] = [4.1, 4.3, 4.5, 4.2, 4.0, 3.8, 3.9, 4.1, 4.3, 4.5, 4.6, 4.7]

fig3 = go.Figure()

# Primary axis - bar chart
fig3.add_trace(go.Bar(
    x=sample_data['Date_Str'].tolist(),
    y=sample_data['Value'].tolist(),
    name='Primary Metric',
    marker_color=THEME['line_colors']['primary'],
    orientation='v'  # Explicitly set vertical orientation
))

# Secondary axis - line chart
fig3.add_trace(go.Scatter(
    x=sample_data['Date_Str'].tolist(),
    y=sample_data['Secondary'].tolist(),
    name='Secondary Metric',
    line=dict(color=THEME['line_colors']['danger'], width=2),
    mode='lines+markers',
    yaxis='y2'  # Use secondary y-axis
))

# Update layout for dual axes
fig3.update_layout(
    title="Dual-Axis Chart Example",
    xaxis=dict(title="Date", type='category'),
    yaxis=dict(
        title=dict(
            text="Primary Metric",
            font=dict(color=THEME['line_colors']['primary'])
        ),
        tickfont=dict(color=THEME['line_colors']['primary'])
    ),
    yaxis2=dict(
        title=dict(
            text="Secondary Metric",
            font=dict(color=THEME['line_colors']['danger'])
        ),
        tickfont=dict(color=THEME['line_colors']['danger']),
        overlaying="y",
        side="right"
    ),
    height=500,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

fig3 = apply_dark_theme(fig3)
st.plotly_chart(fig3, use_container_width=True)

# Debugging tips
st.subheader("Debugging Tips")
st.markdown("""
### Common Issues and Solutions:
1. **Data Type Issues**: 
   - Convert DataFrame columns to lists with `.tolist()`
   - Use `type='category'` for categorical x-axis data

2. **Bar Chart Orientation**: 
   - Set `orientation='v'` explicitly for vertical bars
   - For horizontal bars, use `orientation='h'` and swap x/y

3. **Dual-Axis Configuration**:
   - Use `yaxis='y2'` for the secondary axis trace
   - Set `overlaying="y"` in the layout for the secondary axis

4. **Data Preparation**:
   - Ensure data is properly sorted before plotting
   - Fill null values to prevent rendering issues
   - Use explicit data type conversions
""")
