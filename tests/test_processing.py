"""Tests for data processing utility functions."""

import pytest
import pandas as pd
import numpy as np
from data.processing import (
    convert_dates,
    calculate_pct_change, 
    cap_outliers,
    check_consecutive_increase,
    check_consecutive_decrease,
    count_consecutive_changes,
    validate_indicator_data
)


class TestConvertDates:
    """Test convert_dates function."""
    
    def test_convert_datetime_index(self):
        """Test conversion of DataFrame with datetime index."""
        dates = pd.date_range('2024-01-01', periods=5, freq='D')
        df = pd.DataFrame({'value': [1, 2, 3, 4, 5]}, index=dates)
        
        result = convert_dates(df)
        
        # Should convert to numpy datetime64 array
        assert isinstance(result.index, np.ndarray)
        assert result.index.dtype.kind == 'M'  # datetime64
        assert len(result) == 5
        
    def test_convert_non_datetime_index(self):
        """Test that non-datetime indexes are unchanged."""
        df = pd.DataFrame({'value': [1, 2, 3, 4, 5]})
        
        result = convert_dates(df)
        
        # Should be unchanged
        assert isinstance(result.index, pd.RangeIndex)
        pd.testing.assert_frame_equal(result, df)
    
    def test_preserves_index_name(self):
        """Test that index name is preserved."""
        dates = pd.date_range('2024-01-01', periods=3, freq='D')
        df = pd.DataFrame({'value': [1, 2, 3]}, index=dates)
        df.index.name = 'custom_date'
        
        result = convert_dates(df)
        
        assert result.index.name == 'custom_date'


class TestCalculatePctChange:
    """Test calculate_pct_change function."""
    
    def test_basic_pct_change(self):
        """Test basic percentage change calculation."""
        df = pd.DataFrame({'value': [100, 110, 121, 133.1]})
        
        result = calculate_pct_change(df, 'value')
        
        # First value should be NaN, rest should be ~10%
        assert pd.isna(result.iloc[0])
        assert abs(result.iloc[1] - 10.0) < 0.01
        assert abs(result.iloc[2] - 10.0) < 0.01
        assert abs(result.iloc[3] - 10.0) < 0.01
    
    def test_pct_change_with_periods(self):
        """Test percentage change with custom periods."""
        df = pd.DataFrame({'value': [100, 105, 110, 115, 120]})
        
        result = calculate_pct_change(df, 'value', periods=2)
        
        # First two values should be NaN
        assert pd.isna(result.iloc[0])
        assert pd.isna(result.iloc[1])
        # Third value should be ~10% (110 vs 100)
        assert abs(result.iloc[2] - 10.0) < 0.01
    
    def test_annualized_pct_change(self):
        """Test annualized percentage change."""
        df = pd.DataFrame({'value': [100, 110]})
        
        result = calculate_pct_change(df, 'value', periods=1, annualize=True)
        
        # Should be 10% * 12 = 120%
        assert abs(result.iloc[1] - 120.0) < 0.01
    
    def test_empty_dataframe(self):
        """Test with empty DataFrame."""
        df = pd.DataFrame(columns=['value'])
        
        result = calculate_pct_change(df, 'value')
        
        assert len(result) == 0
    
    def test_single_row_dataframe(self):
        """Test with single row DataFrame."""
        df = pd.DataFrame({'value': [100]})
        
        result = calculate_pct_change(df, 'value')
        
        assert len(result) == 1
        assert pd.isna(result.iloc[0])


class TestCapOutliers:
    """Test cap_outliers function."""
    
    def test_cap_outliers_basic(self):
        """Test basic outlier capping."""
        series = pd.Series([0.5, 1.0, -3.0, 2.5, 1.5])
        
        result = cap_outliers(series, lower_limit=-2, upper_limit=2)
        
        expected = pd.Series([0.5, 1.0, -2.0, 2.0, 1.5])
        pd.testing.assert_series_equal(result, expected)
    
    def test_no_outliers(self):
        """Test when no outliers exist."""
        series = pd.Series([0.5, 1.0, -1.5, 1.8, -0.5])
        
        result = cap_outliers(series, lower_limit=-2, upper_limit=2)
        
        # Should be unchanged
        pd.testing.assert_series_equal(result, series)
    
    def test_empty_series(self):
        """Test with empty series."""
        series = pd.Series(dtype=float)
        
        result = cap_outliers(series)
        
        assert len(result) == 0


class TestConsecutiveChecks:
    """Test consecutive increase/decrease functions."""
    
    def test_check_consecutive_increase_true(self):
        """Test consecutive increase detection - positive case."""
        values = [100, 105, 110, 115]
        
        result = check_consecutive_increase(values, count=3)
        
        assert result is True
    
    def test_check_consecutive_increase_false(self):
        """Test consecutive increase detection - negative case."""
        values = [100, 105, 103, 110]
        
        result = check_consecutive_increase(values, count=3)
        
        assert result is False
    
    def test_check_consecutive_increase_insufficient_data(self):
        """Test consecutive increase with insufficient data."""
        values = [100, 105]
        
        result = check_consecutive_increase(values, count=3)
        
        assert result is False
    
    def test_check_consecutive_decrease_true(self):
        """Test consecutive decrease detection - positive case."""
        values = [120, 115, 110, 105]
        
        result = check_consecutive_decrease(values, count=3)
        
        assert result is True
    
    def test_check_consecutive_decrease_false(self):
        """Test consecutive decrease detection - negative case."""
        values = [120, 115, 118, 110]
        
        result = check_consecutive_decrease(values, count=3)
        
        assert result is False
    
    def test_check_consecutive_decrease_insufficient_data(self):
        """Test consecutive decrease with insufficient data."""
        values = [120, 115]
        
        result = check_consecutive_decrease(values, count=3)
        
        assert result is False
    
    def test_count_consecutive_decreases(self):
        """Test counting consecutive decreases."""
        values = [130, 125, 120, 115, 118, 116]  # 3 decreases, then mixed
        
        result = count_consecutive_changes(values, decreasing=True)
        
        assert result == 1  # Only the last decrease (118->116)
    
    def test_count_consecutive_increases(self):
        """Test counting consecutive increases."""
        values = [100, 102, 105, 108, 110, 107]  # 4 increases, then decrease
        
        result = count_consecutive_changes(values, decreasing=False)
        
        assert result == 0  # Last change was a decrease
    
    def test_count_consecutive_all_decreasing(self):
        """Test counting when all values are decreasing."""
        values = [150, 140, 130, 120, 110]
        
        result = count_consecutive_changes(values, decreasing=True)
        
        assert result == 4  # 4 consecutive decreases


class TestValidateIndicatorData:
    """Test validate_indicator_data function."""
    
    def test_valid_data_with_latest_value(self):
        """Test validation with valid latest_value."""
        data = {
            'latest_value': 375000,
            'data': pd.DataFrame({'value': [380000, 375000]})
        }
        
        result = validate_indicator_data(data)
        
        assert result is True
    
    def test_valid_data_with_dataframe_only(self):
        """Test validation with valid DataFrame only."""
        data = {
            'data': pd.DataFrame({'value': [380000, 375000]})
        }
        
        result = validate_indicator_data(data)
        
        assert result is True
    
    def test_invalid_data_none(self):
        """Test validation with None data."""
        result = validate_indicator_data(None)
        
        assert result is False
    
    def test_invalid_data_empty_dict(self):
        """Test validation with empty dict."""
        result = validate_indicator_data({})
        
        assert result is False
    
    def test_invalid_data_error_state(self):
        """Test validation with error in data."""
        data = {'error': 'API Error'}
        
        result = validate_indicator_data(data)
        
        assert result is False
    
    def test_invalid_data_status_error(self):
        """Test validation with status error."""
        data = {'status': 'data_error'}
        
        result = validate_indicator_data(data)
        
        assert result is False
    
    def test_invalid_data_none_values(self):
        """Test validation with None values."""
        data = {
            'latest_value': None,
            'data': pd.DataFrame()  # Empty DataFrame
        }
        
        result = validate_indicator_data(data)
        
        assert result is False
    
    def test_valid_data_alternative_fields(self):
        """Test validation with alternative field names."""
        data = {
            'pmi_score': 52.5,
            'current_liquidity': 4500
        }
        
        result = validate_indicator_data(data)
        
        assert result is True
    
    def test_invalid_data_nan_values(self):
        """Test validation with NaN values."""
        data = {
            'latest_value': np.nan,
            'latest_ratio': float('nan')
        }
        
        result = validate_indicator_data(data)
        
        assert result is False
    
    def test_valid_data_zero_value(self):
        """Test validation with zero value (should be valid)."""
        data = {
            'latest_value': 0.0
        }
        
        result = validate_indicator_data(data)
        
        assert result is True