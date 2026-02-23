"""Tests for warning signal generation."""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch
from visualization.warning_signals import (
    create_warning_indicator,
    create_warning_status,
    create_trend_indicator,
    generate_indicator_warning,
    generate_usd_liquidity_warning,
    generate_pmi_warning
)
from src.config.indicator_registry import IndicatorConfig


class TestCreateWarningIndicator:
    """Test create_warning_indicator function."""
    
    def test_higher_is_bad_above_threshold(self):
        """Test warning when value is above threshold (higher is bad)."""
        result = create_warning_indicator(100, 50, higher_is_bad=True)
        assert result == "🔴"  # Red for bad
    
    def test_higher_is_bad_below_threshold(self):
        """Test warning when value is below threshold (higher is bad)."""
        result = create_warning_indicator(30, 50, higher_is_bad=True)
        assert result == "🟢"  # Green for good
    
    def test_lower_is_bad_below_threshold(self):
        """Test warning when value is below threshold (lower is bad)."""
        result = create_warning_indicator(30, 50, higher_is_bad=False)
        assert result == "🔴"  # Red for bad
    
    def test_lower_is_bad_above_threshold(self):
        """Test warning when value is above threshold (lower is bad)."""
        result = create_warning_indicator(100, 50, higher_is_bad=False)
        assert result == "🟢"  # Green for good
    
    def test_neutral_indicator(self):
        """Test neutral indicator override."""
        result = create_warning_indicator(100, 50, neutral=True)
        assert result == "⚪"  # Grey for neutral


class TestCreateWarningStatus:
    """Test create_warning_status function."""
    
    def test_single_threshold_higher_is_bad(self):
        """Test status with single threshold (higher is bad)."""
        labels = ["Good", "Bad"]
        result = create_warning_status(60, [50], labels, higher_is_bad=True)
        assert result == "Bad"
        
        result = create_warning_status(40, [50], labels, higher_is_bad=True)
        assert result == "Good"
    
    def test_multiple_thresholds_higher_is_bad(self):
        """Test status with multiple thresholds (higher is bad)."""
        thresholds = [50, 75, 100]
        labels = ["Normal", "Warning", "Alert", "Critical"]
        
        result = create_warning_status(30, thresholds, labels, higher_is_bad=True)
        assert result == "Normal"
        
        result = create_warning_status(60, thresholds, labels, higher_is_bad=True)
        assert result == "Warning"
        
        result = create_warning_status(80, thresholds, labels, higher_is_bad=True)
        assert result == "Alert"
        
        result = create_warning_status(120, thresholds, labels, higher_is_bad=True)
        assert result == "Critical"
    
    def test_multiple_thresholds_lower_is_bad(self):
        """Test status with multiple thresholds (lower is bad)."""
        thresholds = [100, 75, 50]  # Descending order for lower is bad
        labels = ["Critical", "Alert", "Warning", "Normal"]
        
        result = create_warning_status(120, thresholds, labels, higher_is_bad=False)
        assert result == "Critical"
        
        result = create_warning_status(80, thresholds, labels, higher_is_bad=False)
        assert result == "Alert"
    
    def test_mismatched_labels_raises_error(self):
        """Test that mismatched labels and thresholds raise error."""
        thresholds = [50, 75]
        labels = ["Good", "Bad"]  # Should be 3 labels for 2 thresholds
        
        with pytest.raises(ValueError, match="Number of labels should be one more"):
            create_warning_status(60, thresholds, labels)


class TestGenerateIndicatorWarning:
    """Test generate_indicator_warning function."""
    
    def test_below_threshold_bullish(self, test_indicator_config):
        """Test below threshold condition - bullish case."""
        config = test_indicator_config
        config.bullish_condition = "below_threshold"
        config.threshold = 400000
        
        data = {'latest_value': 350000}
        
        result = generate_indicator_warning(data, config)
        
        assert result['status'] == 'Bullish'
        assert 'details' in result
    
    def test_below_threshold_bearish(self, test_indicator_config):
        """Test below threshold condition - bearish case."""
        config = test_indicator_config
        config.bullish_condition = "below_threshold"
        config.threshold = 400000
        
        data = {'latest_value': 450000}
        
        result = generate_indicator_warning(data, config)
        
        assert result['status'] == 'Bearish'
        assert 'details' in result
    
    def test_above_threshold_bullish(self, test_indicator_config):
        """Test above threshold condition - bullish case."""
        config = test_indicator_config
        config.bullish_condition = "above_threshold"
        config.threshold = 2.0
        
        data = {'latest_value': 2.5}
        
        result = generate_indicator_warning(data, config)
        
        assert result['status'] == 'Bullish'
        assert 'details' in result
    
    def test_above_threshold_bearish(self, test_indicator_config):
        """Test above threshold condition - bearish case.""" 
        config = test_indicator_config
        config.bullish_condition = "above_threshold"
        config.threshold = 2.0
        
        data = {'latest_value': 1.5}
        
        result = generate_indicator_warning(data, config)
        
        assert result['status'] == 'Bearish'
        assert 'details' in result
    
    def test_decreasing_condition_general_bearish(self, test_indicator_config):
        """Test decreasing condition for general indicators (increasing is bearish)."""
        config = test_indicator_config
        config.bullish_condition = "decreasing"
        config.key = "initial_claims"  # General indicator where increasing is bad
        
        data = {'initial_claims_increasing': True, 'initial_claims_decreasing': False}
        
        result = generate_indicator_warning(data, config)
        
        assert result['status'] == 'Bearish'
    
    def test_decreasing_condition_general_bullish(self, test_indicator_config):
        """Test decreasing condition for general indicators (decreasing is bullish)."""
        config = test_indicator_config
        config.bullish_condition = "decreasing"
        config.key = "initial_claims"
        
        data = {'initial_claims_increasing': False, 'initial_claims_decreasing': True}
        
        result = generate_indicator_warning(data, config)
        
        assert result['status'] == 'Bullish'
    
    def test_decreasing_condition_special_indicators_bullish(self, test_indicator_config):
        """Test decreasing condition for special indicators (increasing is bullish)."""
        config = test_indicator_config
        config.bullish_condition = "decreasing"
        config.key = "hours_worked"  # Special indicator where increasing is good
        
        data = {'hours_worked_increasing': True, 'hours_worked_decreasing': False}
        
        result = generate_indicator_warning(data, config)
        
        assert result['status'] == 'Bullish'
    
    def test_decreasing_condition_special_indicators_bearish(self, test_indicator_config):
        """Test decreasing condition for special indicators (decreasing is bearish)."""
        config = test_indicator_config
        config.bullish_condition = "decreasing"
        config.key = "new_orders"  # Special indicator where decreasing is bad
        
        data = {'new_orders_increasing': False, 'new_orders_decreasing': True}
        
        result = generate_indicator_warning(data, config)
        
        assert result['status'] == 'Bearish'
    
    def test_decreasing_condition_neutral(self, test_indicator_config):
        """Test decreasing condition with neutral trend."""
        config = test_indicator_config
        config.bullish_condition = "decreasing"
        
        data = {'test_indicator_increasing': False, 'test_indicator_decreasing': False}
        
        result = generate_indicator_warning(data, config)
        
        assert result['status'] == 'Neutral'
    
    @patch('importlib.import_module')
    def test_custom_bullish_condition(self, mock_import, test_indicator_config):
        """Test custom bullish condition with custom function."""
        config = test_indicator_config
        config.bullish_condition = "custom"
        config.custom_status_fn = "visualization.warning_signals.generate_pmi_warning"
        
        # Mock the custom function
        mock_module = Mock()
        mock_function = Mock(return_value="Current PMI Score: 52.5 (Bullish expansion)")
        mock_module.generate_pmi_warning = mock_function
        mock_import.return_value = mock_module
        
        data = {'pmi_score': 52.5}
        
        result = generate_indicator_warning(data, config)
        
        assert result['status'] == 'Bullish'
        assert 'Bullish expansion' in result['details']
    
    def test_no_data_available(self, test_indicator_config):
        """Test handling when no data is available."""
        config = test_indicator_config
        config.bullish_condition = "below_threshold"
        config.threshold = 400000
        
        data = {'latest_value': None}
        
        result = generate_indicator_warning(data, config)
        
        assert result['status'] == 'Neutral'
        assert 'No data available' in result['details']

    def test_below_threshold_with_numpy_array_latest_value(self, test_indicator_config):
        """Test threshold checks handle numpy array values by using latest element."""
        config = test_indicator_config
        config.bullish_condition = "below_threshold"
        config.threshold = 400000

        data = {'latest_value': np.array([410000, 390000])}

        result = generate_indicator_warning(data, config)

        assert result['status'] == 'Bullish'

    def test_decreasing_condition_with_numpy_array_flags(self, test_indicator_config):
        """Test trend flags as numpy arrays do not trigger ambiguous truth-value errors."""
        config = test_indicator_config
        config.bullish_condition = "decreasing"
        config.key = "hours_worked"

        data = {
            'hours_worked_increasing': np.array([False, True]),
            'hours_worked_decreasing': np.array([False, False])
        }

        result = generate_indicator_warning(data, config)

        assert result['status'] == 'Bullish'
    
    def test_invalid_config_type(self):
        """Test that invalid config type raises TypeError."""
        data = {'latest_value': 100}
        config = {"not": "a config object"}
        
        with pytest.raises(TypeError, match="config must be an IndicatorConfig object"):
            generate_indicator_warning(data, config)


class TestGenerateUsdLiquidityWarning:
    """Test generate_usd_liquidity_warning function."""
    
    def test_usd_liquidity_warning_format(self):
        """Test that USD liquidity warning returns proper format."""
        # Sample data structure for USD liquidity
        data = {
            'current_liquidity': 4500,
            'liquidity_change_billions': 50,
            'change_pct': 1.1,
            'latest_fed_balance': 7000,
            'latest_rrp': 2500,
            'latest_treasury': 600
        }
        
        result = generate_usd_liquidity_warning(data)
        
        # Should be a string containing formatted warning information
        assert isinstance(result, str)
        assert 'liquidity' in result.lower()
        # Should contain current values
        assert '4500' in result or '4,500' in result
    
    def test_usd_liquidity_warning_with_missing_data(self):
        """Test USD liquidity warning with incomplete data."""
        data = {'current_liquidity': None}
        
        result = generate_usd_liquidity_warning(data)
        
        assert isinstance(result, str)
        # Should handle missing data gracefully

    def test_usd_liquidity_warning_with_numpy_flag_arrays(self):
        """Test USD liquidity warning handles numpy array flags without boolean ambiguity."""
        data = {
            'current_liquidity': np.array([4400, 4500]),
            'liquidity_increasing': np.array([False, True]),
            'liquidity_decreasing': np.array([False, False])
        }

        result = generate_usd_liquidity_warning(data)

        assert isinstance(result, str)
        assert 'Bullish' in result


class TestGeneratePmiWarning:
    """Test generate_pmi_warning function."""
    
    def test_pmi_warning_expansion(self):
        """Test PMI warning in expansion territory."""
        data = {'pmi_score': 52.5}
        
        result = generate_pmi_warning(data)
        
        assert isinstance(result, str)
        assert '52.5' in result
        # PMI above 50 indicates expansion
        assert 'expansion' in result.lower() or 'bullish' in result.lower()
    
    def test_pmi_warning_contraction(self):
        """Test PMI warning in contraction territory."""
        data = {'pmi_score': 48.2}
        
        result = generate_pmi_warning(data)
        
        assert isinstance(result, str)
        assert '48.2' in result
        # PMI below 50 indicates contraction
        assert 'contraction' in result.lower() or 'bearish' in result.lower()
    
    def test_pmi_warning_neutral(self):
        """Test PMI warning at neutral level."""
        data = {'pmi_score': 50.0}
        
        result = generate_pmi_warning(data)
        
        assert isinstance(result, str)
        assert '50.0' in result or '50' in result
    
    def test_pmi_warning_with_missing_data(self):
        """Test PMI warning with missing data."""
        data = {'pmi_score': None}
        
        result = generate_pmi_warning(data)
        
        assert isinstance(result, str)
        # Should handle missing data gracefully


class TestWarningIntegration:
    """Integration tests for warning system."""
    
    def test_all_registry_indicators_can_generate_warnings(self, all_indicator_configs):
        """Test that all indicators in registry can generate warnings."""
        from src.config.indicator_registry import INDICATOR_REGISTRY
        
        for key, config in INDICATOR_REGISTRY.items():
            # Create minimal data for each indicator
            data = {'latest_value': 100}
            
            if config.bullish_condition == 'custom':
                # Skip custom indicators as they require specific data formats
                continue
            
            try:
                result = generate_indicator_warning(data, config)
                assert 'status' in result
                assert 'details' in result
                assert result['status'] in ['Bullish', 'Bearish', 'Neutral']
            except Exception as e:
                pytest.fail(f"Warning generation failed for {key}: {e}")
    
    def test_warning_status_consistency(self):
        """Test that warning statuses are consistent."""
        valid_statuses = {'Bullish', 'Bearish', 'Neutral'}
        
        config = IndicatorConfig(
            key="test",
            display_name="Test",
            emoji="🧪",
            fred_series=["TEST"],
            chart_type="line",
            value_column="value",
            periods=12,
            frequency="m",
            bullish_condition="below_threshold",
            threshold=100.0,
            warning_description="Test",
            chart_color="#000000"
        )
        
        # Test various data scenarios
        test_cases = [
            {'latest_value': 50},   # Below threshold
            {'latest_value': 150},  # Above threshold
            {'latest_value': None}, # No data
        ]
        
        for data in test_cases:
            result = generate_indicator_warning(data, config)
            assert result['status'] in valid_statuses