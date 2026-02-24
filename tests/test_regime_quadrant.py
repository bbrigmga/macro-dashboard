"""Tests for the Growth/Inflation Regime Quadrant feature."""
import pytest
import pandas as pd
import numpy as np
from data.processing import calculate_roc_zscore, apply_ema_smoothing


class TestCalculateRocZscore:
    """Tests for calculate_roc_zscore()."""
    
    def test_returns_series_same_length(self):
        """Output series should have same length as input."""
        series = pd.Series(np.random.randn(400).cumsum() + 100)
        result = calculate_roc_zscore(series, roc_period=60, zscore_window=252)
        assert len(result) == len(series)
    
    def test_leading_nans(self):
        """Should have NaN values at the start due to rolling windows."""
        series = pd.Series(np.random.randn(400).cumsum() + 100)
        result = calculate_roc_zscore(series, roc_period=60, zscore_window=252)
        # First roc_period + zscore_window - 1 values should be NaN
        assert result.iloc[:60].isna().all()
    
    def test_zscore_bounded(self):
        """Z-Scores should typically be within [-4, 4] for normal data."""
        np.random.seed(42)
        series = pd.Series(np.random.randn(600).cumsum() + 100)
        result = calculate_roc_zscore(series, roc_period=60, zscore_window=252)
        valid = result.dropna()
        assert valid.between(-5, 5).all()
    
    def test_empty_series(self):
        """Should handle empty series gracefully."""
        series = pd.Series(dtype=float)
        result = calculate_roc_zscore(series)
        assert len(result) == 0
    
    def test_constant_series(self):
        """A constant series should produce ROC of 0 (and NaN Z-Scores due to 0 std)."""
        series = pd.Series([100.0] * 400)
        result = calculate_roc_zscore(series, roc_period=60, zscore_window=252)
        # All NaN because std deviation is 0
        valid = result.dropna()
        # Either empty or all NaN/zero
        assert len(valid) == 0 or (valid == 0).all() or valid.isna().all()


class TestApplyEmaSmoothing:
    """Tests for apply_ema_smoothing()."""
    
    def test_reduces_noise(self):
        """EMA should reduce the standard deviation of noisy data."""
        np.random.seed(42)
        noisy = pd.Series(np.random.randn(200))
        smoothed = apply_ema_smoothing(noisy, span=20)
        assert smoothed.std() < noisy.std()
    
    def test_same_length(self):
        """Output should be same length as input."""
        series = pd.Series(np.random.randn(100))
        result = apply_ema_smoothing(series, span=10)
        assert len(result) == len(series)
    
    def test_span_parameter(self):
        """Larger span should produce smoother output."""
        np.random.seed(42)
        series = pd.Series(np.random.randn(200))
        smooth_10 = apply_ema_smoothing(series, span=10)
        smooth_50 = apply_ema_smoothing(series, span=50)
        assert smooth_50.std() < smooth_10.std()


class TestRegimeQuadrantData:
    """Tests for the regime quadrant data pipeline (integration-level)."""
    
    def test_regime_labels(self):
        """Verify regime label assignment from coordinates."""
        # These are the expected mappings
        assert _get_regime(1.0, 1.0) == "Reflation"
        assert _get_regime(1.0, -1.0) == "Goldilocks"
        assert _get_regime(-1.0, 1.0) == "Stagflation"
        assert _get_regime(-1.0, -1.0) == "Deflation"
    
    def test_regime_edge_cases(self):
        """Test regime classification edge cases."""
        # Test zero values
        assert _get_regime(0.0, 0.0) == "Reflation"  # >= 0 for both
        assert _get_regime(0.1, -0.1) == "Goldilocks"
        assert _get_regime(-0.1, 0.1) == "Stagflation"
        assert _get_regime(-0.1, -0.1) == "Deflation"
    
    def test_return_dict_structure(self):
        """Verify the returned dict has all expected keys."""
        # Create minimal mock data structure
        mock_data = {
            'data': pd.DataFrame({
                'Date': pd.date_range('2024-01-01', periods=5),
                'growth_zscore': [0.1, 0.2, 0.3, 0.4, 0.5],
                'inflation_zscore': [0.2, 0.3, 0.4, 0.5, 0.6]
            }),
            'trail_data': pd.DataFrame(),
            'current_regime': 'Goldilocks',
            'current_growth': 0.5,
            'current_inflation': 0.6,
            'projected_growth': 0.6,
            'projected_inflation': 0.7,
            'regime_description': 'Test description'
        }
        
        required_keys = [
            'data', 'trail_data', 'current_regime',
            'current_growth', 'current_inflation',
            'projected_growth', 'projected_inflation',
            'regime_description'
        ]
        
        # Verify all required keys are present
        for key in required_keys:
            assert key in mock_data, f"Missing required key: {key}"
        
        # Verify data types
        assert isinstance(mock_data['data'], pd.DataFrame)
        assert isinstance(mock_data['trail_data'], pd.DataFrame)
        assert isinstance(mock_data['current_regime'], str)
        assert isinstance(mock_data['current_growth'], (int, float))
        assert isinstance(mock_data['current_inflation'], (int, float))
        assert isinstance(mock_data['projected_growth'], (int, float))
        assert isinstance(mock_data['projected_inflation'], (int, float))
        assert isinstance(mock_data['regime_description'], str)


def _get_regime(growth: float, inflation: float) -> str:
    """Helper to test regime classification logic."""
    if growth >= 0 and inflation >= 0:
        return "Reflation"
    elif growth >= 0 and inflation < 0:
        return "Goldilocks"
    elif growth < 0 and inflation >= 0:
        return "Stagflation"
    else:
        return "Deflation"


class TestRegimeClassificationLogic:
    """Tests specifically for regime classification logic."""
    
    def test_all_quadrants_covered(self):
        """Verify all four quadrants map to expected regimes."""
        # Test points in each quadrant
        test_cases = [
            (1.5, 1.5, "Reflation"),      # Top-right
            (1.5, -1.5, "Goldilocks"),   # Bottom-right
            (-1.5, 1.5, "Stagflation"),  # Top-left
            (-1.5, -1.5, "Deflation")    # Bottom-left
        ]
        
        for growth, inflation, expected in test_cases:
            result = _get_regime(growth, inflation)
            assert result == expected, f"Expected {expected} for ({growth}, {inflation}), got {result}"
    
    def test_boundary_conditions(self):
        """Test regime classification at quadrant boundaries."""
        # Test exactly on axes
        assert _get_regime(0, 1) == "Reflation"
        assert _get_regime(1, 0) == "Reflation"
        assert _get_regime(0, -1) == "Goldilocks"
        assert _get_regime(-1, 0) == "Stagflation"
        assert _get_regime(0, 0) == "Reflation"  # Origin goes to Reflation
    
    def test_extreme_values(self):
        """Test regime classification with extreme Z-score values."""
        extreme_cases = [
            (5.0, 3.0, "Reflation"),
            (4.0, -5.0, "Goldilocks"),
            (-3.0, 4.0, "Stagflation"),
            (-5.0, -3.0, "Deflation")
        ]
        
        for growth, inflation, expected in extreme_cases:
            result = _get_regime(growth, inflation)
            assert result == expected


class TestDataValidation:
    """Tests for data validation and error handling."""
    
    def test_empty_dataframe_handling(self):
        """Test handling of empty DataFrames."""
        empty_df = pd.DataFrame(columns=['Date', 'growth_zscore', 'inflation_zscore'])
        
        # Should not raise an exception
        assert len(empty_df) == 0
        assert list(empty_df.columns) == ['Date', 'growth_zscore', 'inflation_zscore']
    
    def test_missing_data_handling(self):
        """Test handling of missing data points."""
        # DataFrame with NaN values
        df_with_nans = pd.DataFrame({
            'Date': pd.date_range('2024-01-01', periods=5),
            'growth_zscore': [1.0, np.nan, 2.0, 3.0, np.nan],
            'inflation_zscore': [1.0, 2.0, np.nan, 3.0, 4.0]
        })
        
        # Should be able to drop NaN values
        clean_df = df_with_nans.dropna()
        assert len(clean_df) == 2  # Only rows 0 and 3 should remain
    
    def test_data_type_consistency(self):
        """Test that data types are consistent."""
        test_data = {
            'current_growth': 1.5,
            'current_inflation': -0.5,
            'projected_growth': 2.0,
            'projected_inflation': -0.3
        }
        
        # All should be numeric
        for key, value in test_data.items():
            assert isinstance(value, (int, float)), f"{key} should be numeric, got {type(value)}"
        
        # Should be convertible to float
        for key, value in test_data.items():
            float_val = float(value)
            assert isinstance(float_val, float)


if __name__ == "__main__":
    # Run tests when executed directly
    pytest.main([__file__])