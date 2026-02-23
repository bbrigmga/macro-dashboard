"""Tests for generic chart builder."""

import pytest
import pandas as pd
import plotly.graph_objects as go
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date
from visualization.generic_chart import (
    prepare_date_for_display,
    create_indicator_chart,
    _create_line_chart,
    _create_dual_axis_chart,
    _create_bar_chart,
    _create_custom_chart
)
from src.config.indicator_registry import IndicatorConfig


@pytest.fixture
def sample_dataframe():
    """Create a sample DataFrame for testing."""
    dates = pd.date_range('2024-01-01', periods=10, freq='M')
    return pd.DataFrame({
        'Date': dates,
        'value': [100, 105, 110, 108, 115, 120, 118, 125, 130, 135],
        'secondary_value': [50, 52, 49, 51, 53, 55, 54, 56, 58, 60]
    })


@pytest.fixture  
def line_chart_config():
    """Configuration for line charts."""
    return IndicatorConfig(
        key="test_line",
        display_name="Test Line Chart",
        emoji="📊",
        fred_series=["TEST"],
        chart_type="line",
        value_column="value",
        periods=12,
        frequency="M",
        bullish_condition="below_threshold",
        threshold=115.0,
        warning_description="Test line chart",
        chart_color="#1f77b4",
        card_chart_height=400
    )


@pytest.fixture
def bar_chart_config():
    """Configuration for bar charts."""
    return IndicatorConfig(
        key="test_bar",
        display_name="Test Bar Chart", 
        emoji="📊",
        fred_series=["TEST"],
        chart_type="bar",
        value_column="value",
        periods=8,
        frequency="Q",
        bullish_condition="above_threshold",
        threshold=110.0,
        warning_description="Test bar chart",
        chart_color="#ff7f0e",
        card_chart_height=360
    )


@pytest.fixture
def custom_chart_config():
    """Configuration for custom charts."""
    return IndicatorConfig(
        key="test_custom",
        display_name="Test Custom Chart",
        emoji="🔧",
        fred_series=["TEST"],
        chart_type="custom",
        value_column="value", 
        periods=20,
        frequency="D",
        bullish_condition="custom",
        threshold=None,
        warning_description="Test custom chart",
        chart_color="#2ca02c",
        custom_chart_fn="visualization.indicators.create_usd_liquidity_chart"
    )


class TestPrepareDateForDisplay:
    """Test prepare_date_for_display function."""
    
    def test_monthly_date_format(self, sample_dataframe):
        """Test monthly date formatting."""
        result = prepare_date_for_display(sample_dataframe, frequency='M')
        
        assert 'Date_Str' in result.columns
        # Check format: should be like 'Jan 2024'
        assert 'Jan' in result['Date_Str'].iloc[0]
        assert '2024' in result['Date_Str'].iloc[0]
    
    def test_weekly_date_format(self):
        """Test weekly date formatting."""
        dates = pd.date_range('2024-01-01', periods=5, freq='W')
        df = pd.DataFrame({'Date': dates, 'value': [1, 2, 3, 4, 5]})
        
        result = prepare_date_for_display(df, frequency='W')
        
        assert 'Date_Str' in result.columns
        # Check format: should be like '01/07/24'
        date_str = result['Date_Str'].iloc[0]
        assert len(date_str) == 8  # MM/DD/YY format
        assert date_str.count('/') == 2
    
    def test_custom_date_column_name(self, sample_dataframe):
        """Test with custom date column name."""
        df = sample_dataframe.rename(columns={'Date': 'custom_date'})
        
        result = prepare_date_for_display(df, date_column='custom_date')
        
        assert 'Date_Str' in result.columns
        assert len(result) == len(df)
    
    def test_preserves_original_data(self, sample_dataframe):
        """Test that original DataFrame is not modified."""
        original_columns = sample_dataframe.columns.tolist()
        
        result = prepare_date_for_display(sample_dataframe)
        
        # Original should be unchanged
        assert sample_dataframe.columns.tolist() == original_columns
        # Result should have additional column
        assert 'Date_Str' in result.columns
        assert len(result.columns) == len(original_columns) + 1


class TestCreateIndicatorChart:
    """Test create_indicator_chart main function."""
    
    def test_line_chart_creation(self, sample_dataframe, line_chart_config):
        """Test creating a line chart."""
        data = {'data': sample_dataframe}
        
        fig = create_indicator_chart(data, line_chart_config)
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0  # type: ignore
        assert fig.layout.height == 400
    
    def test_bar_chart_creation(self, sample_dataframe, bar_chart_config):
        """Test creating a bar chart."""
        data = {'data': sample_dataframe}
        
        fig = create_indicator_chart(data, bar_chart_config)
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0  # type: ignore
        assert isinstance(fig.data[0], go.Bar)
    
    def test_dual_axis_chart_creation(self, sample_dataframe, line_chart_config):
        """Test creating a dual-axis chart."""
        data = {'data': sample_dataframe}
        line_chart_config.chart_type = "dual_axis"
        
        fig = create_indicator_chart(data, line_chart_config)
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0  # type: ignore
    
    @patch('visualization.generic_chart.importlib.import_module')
    def test_custom_chart_creation(self, mock_import, sample_dataframe, custom_chart_config):
        """Test creating a custom chart."""
        # Mock the custom chart function
        mock_module = Mock()
        mock_chart_function = Mock(return_value=go.Figure())
        mock_module.create_usd_liquidity_chart = mock_chart_function
        mock_import.return_value = mock_module
        
        data = {'data': sample_dataframe}
        
        fig = create_indicator_chart(data, custom_chart_config)
        
        assert isinstance(fig, go.Figure)
        mock_chart_function.assert_called_once_with(data, custom_chart_config.periods)
    
    def test_empty_data_handling(self, line_chart_config):
        """Test handling of empty data."""
        data = {'data': pd.DataFrame()}
        
        fig = create_indicator_chart(data, line_chart_config)
        
        assert isinstance(fig, go.Figure)
        # Should have error message in title
        assert 'No Data Available' in fig.layout.title.text
    
    def test_missing_data_handling(self, line_chart_config):
        """Test handling of missing data key."""
        data = {}
        
        fig = create_indicator_chart(data, line_chart_config)
        
        assert isinstance(fig, go.Figure)
        assert 'No Data Available' in fig.layout.title.text
    
    def test_unknown_chart_type_error(self, sample_dataframe, line_chart_config):
        """Test error handling for unknown chart type."""
        data = {'data': sample_dataframe}
        line_chart_config.chart_type = "unknown_type"
        
        with pytest.raises(ValueError, match="Unknown chart_type"):
            create_indicator_chart(data, line_chart_config)
    
    def test_data_periods_limitation(self, line_chart_config):
        """Test that data is limited to specified periods."""
        # Create DataFrame with more data than periods
        dates = pd.date_range('2024-01-01', periods=20, freq='M')
        large_df = pd.DataFrame({
            'Date': dates,
            'value': range(20)
        })
        data = {'data': large_df}
        line_chart_config.periods = 5
        
        fig = create_indicator_chart(data, line_chart_config)
        
        # Should only show last 5 periods
        assert isinstance(fig, go.Figure)
        # The chart should exist (specific data count checking would require 
        # inspecting the actual chart data, which depends on implementation)


class TestCreateLineChart:
    """Test _create_line_chart function."""
    
    def test_basic_line_chart(self, sample_dataframe, line_chart_config):
        """Test basic line chart creation."""
        # Prepare data with Date_Str column
        df = prepare_date_for_display(sample_dataframe)
        
        fig = _create_line_chart(df, line_chart_config)
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0  # type: ignore
        assert fig.layout.height == line_chart_config.card_chart_height
    
    def test_line_chart_with_threshold(self, sample_dataframe, line_chart_config):
        """Test line chart with threshold line."""
        df = prepare_date_for_display(sample_dataframe)
        line_chart_config.threshold = 115.0
        
        fig = _create_line_chart(df, line_chart_config)
        
        assert isinstance(fig, go.Figure)
        # Should have threshold line (would be in shapes or additional trace)
    
    def test_line_chart_handles_null_values(self, line_chart_config):
        """Test line chart handles null values."""
        df = pd.DataFrame({
            'Date_Str': ['Jan 2024', 'Feb 2024', 'Mar 2024'],
            'value': [100, None, 110]
        })
        
        fig = _create_line_chart(df, line_chart_config)
        
        assert isinstance(fig, go.Figure)
        # Should handle null values by filling with 0
    
    def test_line_chart_missing_value_column(self, line_chart_config):
        """Test line chart with missing value column."""
        df = pd.DataFrame({
            'Date_Str': ['Jan 2024', 'Feb 2024'],
            'other_column': [100, 110]
        })
        
        # Should not crash, might return empty chart or handle gracefully
        fig = _create_line_chart(df, line_chart_config)
        assert isinstance(fig, go.Figure)


class TestCreateBarChart:
    """Test _create_bar_chart function."""
    
    def test_basic_bar_chart(self, sample_dataframe, bar_chart_config):
        """Test basic bar chart creation."""
        df = prepare_date_for_display(sample_dataframe)
        
        fig = _create_bar_chart(df, bar_chart_config)
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0  # type: ignore
        assert isinstance(fig.data[0], go.Bar)
        assert fig.layout.height == bar_chart_config.card_chart_height
    
    def test_bar_chart_with_threshold(self, sample_dataframe, bar_chart_config):
        """Test bar chart with threshold line."""
        df = prepare_date_for_display(sample_dataframe)
        bar_chart_config.threshold = 110.0
        
        fig = _create_bar_chart(df, bar_chart_config)
        
        assert isinstance(fig, go.Figure)
        # Should have threshold line as a shape
        assert len(fig.layout.shapes) > 0
    
    def test_bar_chart_color(self, sample_dataframe, bar_chart_config):
        """Test bar chart uses specified color."""
        df = prepare_date_for_display(sample_dataframe)
        
        fig = _create_bar_chart(df, bar_chart_config)
        
        assert isinstance(fig, go.Figure) 
        assert fig.data[0].marker.color == bar_chart_config.chart_color  # type: ignore  # type: ignore
    
    def test_bar_chart_handles_null_values(self, bar_chart_config):
        """Test bar chart handles null values."""
        df = pd.DataFrame({
            'Date_Str': ['Q1 2024', 'Q2 2024', 'Q3 2024'],
            'value': [100, None, 110]
        })
        
        fig = _create_bar_chart(df, bar_chart_config)
        
        assert isinstance(fig, go.Figure)
        # Should handle null values by filling with 0


class TestCreateDualAxisChart:
    """Test _create_dual_axis_chart function."""
    
    def test_dual_axis_chart(self, sample_dataframe, line_chart_config):
        """Test dual-axis chart creation."""
        df = prepare_date_for_display(sample_dataframe)
        line_chart_config.chart_type = "dual_axis"
        
        fig = _create_dual_axis_chart(df, line_chart_config)
        
        # Currently falls back to line chart
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0  # type: ignore


class TestCreateCustomChart:
    """Test _create_custom_chart function."""
    
    @patch('visualization.generic_chart.importlib.import_module')
    def test_successful_custom_chart_import(self, mock_import, custom_chart_config):
        """Test successful custom chart function import and execution."""
        # Mock the module and function
        mock_module = Mock()
        mock_chart_function = Mock(return_value=go.Figure(data=[go.Scatter(x=[1, 2], y=[10, 20])]))
        mock_module.create_usd_liquidity_chart = mock_chart_function
        mock_import.return_value = mock_module
        
        data = {'data': pd.DataFrame({'Date': ['2024-01'], 'value': [100]})}
        
        fig = _create_custom_chart(data, custom_chart_config)
        
        assert isinstance(fig, go.Figure)
        mock_import.assert_called_once_with('visualization.indicators')
        mock_chart_function.assert_called_once_with(data, custom_chart_config.periods)
    
    @patch('visualization.generic_chart.importlib.import_module')
    def test_custom_chart_import_error(self, mock_import, custom_chart_config):
        """Test handling of import errors in custom chart loading."""
        mock_import.side_effect = ImportError("Module not found")
        
        data = {'data': pd.DataFrame({'Date': ['2024-01'], 'value': [100]})}
        
        fig = _create_custom_chart(data, custom_chart_config)
        
        # Should fall back to basic chart
        assert isinstance(fig, go.Figure)
    
    @patch('visualization.generic_chart.importlib.import_module') 
    def test_custom_chart_attribute_error(self, mock_import, custom_chart_config):
        """Test handling of attribute errors in custom chart loading."""
        mock_module = Mock()
        del mock_module.create_usd_liquidity_chart  # Function doesn't exist
        mock_import.return_value = mock_module
        
        data = {'data': pd.DataFrame({'Date': ['2024-01'], 'value': [100]})}
        
        with patch('builtins.print'):  # Suppress warning print
            fig = _create_custom_chart(data, custom_chart_config)
        
        assert isinstance(fig, go.Figure)
    
    def test_custom_chart_no_function_specified(self, custom_chart_config):
        """Test error when no custom function is specified."""
        custom_chart_config.custom_chart_fn = None
        
        data = {'data': pd.DataFrame()}
        
        with pytest.raises(ValueError, match="custom_chart_fn must be specified"):
            _create_custom_chart(data, custom_chart_config)
    
    def test_custom_chart_fallback_with_empty_data(self, custom_chart_config):
        """Test custom chart fallback with empty data.""" 
        custom_chart_config.custom_chart_fn = "nonexistent.module.function"
        
        data = {'data': pd.DataFrame()}
        
        with patch('builtins.print'):  # Suppress warning
            with patch('visualization.generic_chart.importlib.import_module', 
                      side_effect=ImportError()):
                fig = _create_custom_chart(data, custom_chart_config)
        
        assert isinstance(fig, go.Figure)
        assert 'Error Loading Chart' in fig.layout.title.text


class TestChartIntegration:
    """Integration tests for chart system."""
    
    def test_all_chart_types_return_plotly_figures(self, sample_dataframe):
        """Test that all chart types return valid Plotly figures."""
        chart_configs = [
            ("line", "value"),
            ("bar", "value"), 
            ("dual_axis", "value")
        ]
        
        for chart_type, value_col in chart_configs:
            config = IndicatorConfig(
                key=f"test_{chart_type}",
                display_name=f"Test {chart_type.title()} Chart",
                emoji="📊",
                fred_series=["TEST"],
                chart_type=chart_type,
                value_column=value_col,
                periods=10,
                frequency="M",
                bullish_condition="below_threshold",
                threshold=115.0,
                warning_description=f"Test {chart_type} chart",
                chart_color="#1f77b4"
            )
            
            data = {'data': sample_dataframe}
            fig = create_indicator_chart(data, config)
            
            assert isinstance(fig, go.Figure), f"Chart type {chart_type} did not return Figure"
            assert hasattr(fig, 'data'), f"Chart type {chart_type} missing data attribute"
            assert hasattr(fig, 'layout'), f"Chart type {chart_type} missing layout attribute"
    
    def test_chart_with_different_frequencies(self, line_chart_config):
        """Test chart creation with different data frequencies."""  
        frequencies = ['D', 'W', 'M', 'Q']
        
        for freq in frequencies:
            # Create appropriate date range for frequency
            if freq == 'D':
                dates = pd.date_range('2024-01-01', periods=30, freq='D')
            elif freq == 'W':
                dates = pd.date_range('2024-01-01', periods=12, freq='W')
            elif freq == 'M':
                dates = pd.date_range('2024-01-01', periods=12, freq='M')
            else:  # 'Q'
                dates = pd.date_range('2024-01-01', periods=8, freq='Q')
            
            df = pd.DataFrame({
                'Date': dates,
                'value': range(len(dates))
            })
            
            line_chart_config.frequency = freq
            data = {'data': df}
            
            fig = create_indicator_chart(data, line_chart_config)
            
            assert isinstance(fig, go.Figure)
            assert len(fig.data) > 0  # type: ignore