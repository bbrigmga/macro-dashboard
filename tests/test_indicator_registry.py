"""Tests for indicator registry configuration."""

import pytest
from src.config.indicator_registry import (
    IndicatorConfig,
    INDICATOR_REGISTRY,
    get_indicator_config,
    list_indicators,
    get_indicators_by_chart_type,
    get_fred_indicators,
    get_yahoo_indicators
)


class TestIndicatorConfig:
    """Test IndicatorConfig dataclass."""
    
    def test_indicator_config_creation(self):
        """Test creating an IndicatorConfig instance."""
        config = IndicatorConfig(
            key="test",
            display_name="Test Indicator",
            emoji="🧪",
            fred_series=["TEST_SERIES"],
            chart_type="line",
            value_column="value",
            periods=12,
            frequency="m",
            bullish_condition="below_threshold",
            threshold=100.0,
            warning_description="Test warning",
            chart_color="#1f77b4"
        )
        
        assert config.key == "test"
        assert config.display_name == "Test Indicator"
        assert config.emoji == "🧪"
        assert config.fred_series == ["TEST_SERIES"]
        assert config.chart_type == "line"
        assert config.value_column == "value"
        assert config.periods == 12
        assert config.frequency == "m"
        assert config.bullish_condition == "below_threshold"
        assert config.threshold == 100.0
        assert config.warning_description == "Test warning"
        assert config.chart_color == "#1f77b4"
        assert config.card_chart_height == 360  # Default value
    
    def test_indicator_config_defaults(self):
        """Test IndicatorConfig default values."""
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
            threshold=None,
            warning_description="Test",
            chart_color="#000000"
        )
        
        assert config.card_chart_height == 360
        assert config.fred_link is None
        assert config.custom_chart_fn is None
        assert config.custom_status_fn is None
        assert config.cache_ttl == 3600
        assert config.yahoo_series is None
        assert config.pmi_components is None
        assert config.liquidity_components is None


class TestIndicatorRegistry:
    """Test INDICATOR_REGISTRY completeness and validity."""
    
    def test_registry_has_expected_count(self):
        """Test that registry contains expected number of indicators."""
        assert len(INDICATOR_REGISTRY) == 11
    
    def test_registry_contains_all_expected_indicators(self):
        """Test that all expected indicators are present."""
        expected_indicators = [
            'initial_claims', 'pce', 'core_cpi', 'hours_worked',
            'yield_curve', 'credit_spread', 'pscf_price', 'pmi_proxy',
            'usd_liquidity', 'new_orders', 'copper_gold_yield'
        ]
        
        for indicator in expected_indicators:
            assert indicator in INDICATOR_REGISTRY
    
    def test_all_configs_are_valid(self):
        """Test that all registry entries are valid IndicatorConfig instances."""
        for key, config in INDICATOR_REGISTRY.items():
            assert isinstance(config, IndicatorConfig)
            assert config.key == key
            assert config.display_name is not None
            assert config.emoji is not None
            assert config.chart_type in ['line', 'dual_axis', 'bar', 'custom']
            assert config.bullish_condition in ['below_threshold', 'above_threshold', 'decreasing', 'custom']
            assert isinstance(config.periods, int) and config.periods > 0
            assert config.chart_color.startswith('#')
    
    def test_frequency_values_are_valid(self):
        """Test that frequency values are valid or None."""
        valid_frequencies = ['d', 'w', 'm', 'q', None]
        
        for config in INDICATOR_REGISTRY.values():
            assert config.frequency in valid_frequencies
    
    def test_threshold_based_indicators_have_thresholds(self):
        """Test that threshold-based indicators have threshold values."""
        for config in INDICATOR_REGISTRY.values():
            if config.bullish_condition in ['below_threshold', 'above_threshold']:
                assert config.threshold is not None
                assert isinstance(config.threshold, (int, float))
    
    def test_custom_indicators_have_custom_functions(self):
        """Test that custom indicators have appropriate custom functions."""
        for config in INDICATOR_REGISTRY.values():
            if config.chart_type == 'custom':
                assert config.custom_chart_fn is not None
            if config.bullish_condition == 'custom':
                assert config.custom_status_fn is not None
    
    def test_data_sources_are_specified(self):
        """Test that each indicator has either FRED or Yahoo data sources."""
        for config in INDICATOR_REGISTRY.values():
            has_fred = config.fred_series and len(config.fred_series) > 0
            has_yahoo = config.yahoo_series and len(config.yahoo_series) > 0
            assert has_fred or has_yahoo, f"Indicator {config.key} has no data source"
    
    def test_pmi_has_components(self):
        """Test that PMI indicator has component configuration."""
        pmi_config = INDICATOR_REGISTRY.get('pmi_proxy')
        assert pmi_config is not None
        assert pmi_config.pmi_components is not None
        assert isinstance(pmi_config.pmi_components, dict)
        assert 'series' in pmi_config.pmi_components
        assert 'weights' in pmi_config.pmi_components
    
    def test_usd_liquidity_has_components(self):
        """Test that USD Liquidity indicator has component configuration.""" 
        liquidity_config = INDICATOR_REGISTRY.get('usd_liquidity')
        assert liquidity_config is not None
        assert liquidity_config.liquidity_components is not None
        assert isinstance(liquidity_config.liquidity_components, dict)
    
    def test_display_names_are_unique(self):
        """Test that display names are unique across indicators."""
        display_names = [config.display_name for config in INDICATOR_REGISTRY.values()]
        assert len(display_names) == len(set(display_names))
    
    def test_emojis_exist(self):
        """Test that all indicators have emojis."""
        for config in INDICATOR_REGISTRY.values():
            assert config.emoji is not None
            assert len(config.emoji) > 0


class TestRegistryHelperFunctions:
    """Test registry helper functions."""
    
    def test_get_indicator_config_valid(self):
        """Test getting a valid indicator config."""
        config = get_indicator_config('initial_claims')
        
        assert isinstance(config, IndicatorConfig)
        assert config.key == 'initial_claims'
        assert config.display_name == 'Initial Jobless Claims'
    
    def test_get_indicator_config_invalid(self):
        """Test getting an invalid indicator config raises KeyError."""
        with pytest.raises(KeyError, match="Indicator 'nonexistent' not found"):
            get_indicator_config('nonexistent')
    
    def test_list_indicators(self):
        """Test listing all indicator keys."""
        indicators = list_indicators()
        
        assert isinstance(indicators, list)
        assert len(indicators) == 11
        assert 'initial_claims' in indicators
        assert 'pce' in indicators
        assert 'usd_liquidity' in indicators
    
    def test_get_indicators_by_chart_type(self):
        """Test filtering indicators by chart type."""
        line_charts = get_indicators_by_chart_type('line')
        custom_charts = get_indicators_by_chart_type('custom')
        dual_axis_charts = get_indicators_by_chart_type('dual_axis')
        
        assert isinstance(line_charts, list)
        assert isinstance(custom_charts, list)
        assert isinstance(dual_axis_charts, list)
        
        # Should have multiple line charts
        assert len(line_charts) > 0
        
        # Should have some custom charts 
        assert len(custom_charts) > 0
        
        # Verify all returned configs have the correct chart type
        for config in line_charts:
            assert config.chart_type == 'line'
        
        for config in custom_charts:
            assert config.chart_type == 'custom'
        
        for config in dual_axis_charts:
            assert config.chart_type == 'dual_axis'
    
    def test_get_fred_indicators(self):
        """Test getting indicators that use FRED data."""
        fred_indicators = get_fred_indicators()
        
        assert isinstance(fred_indicators, list)
        assert len(fred_indicators) > 0
        
        # All returned indicators should have FRED series
        for config in fred_indicators:
            assert config.fred_series is not None
            assert len(config.fred_series) > 0
    
    def test_get_yahoo_indicators(self):
        """Test getting indicators that use Yahoo Finance data."""
        yahoo_indicators = get_yahoo_indicators()
        
        assert isinstance(yahoo_indicators, list)
        
        # All returned indicators should have Yahoo series
        for config in yahoo_indicators:
            assert config.yahoo_series is not None
            assert len(config.yahoo_series) > 0
    
    def test_chart_type_coverage(self):
        """Test that we have reasonable coverage of chart types."""
        chart_types = {}
        for config in INDICATOR_REGISTRY.values():
            chart_type = config.chart_type
            if chart_type not in chart_types:
                chart_types[chart_type] = 0
            chart_types[chart_type] += 1
        
        # Should have at least these chart types
        assert 'line' in chart_types
        assert 'custom' in chart_types
        
        # Line charts should be the most common
        assert chart_types['line'] >= 5
    
    def test_bullish_condition_coverage(self):
        """Test that we have coverage of different bullish conditions."""
        conditions = {}
        for config in INDICATOR_REGISTRY.values():
            condition = config.bullish_condition
            if condition not in conditions:
                conditions[condition] = 0
            conditions[condition] += 1
        
        # Should have multiple condition types
        assert len(conditions) >= 3
        assert 'below_threshold' in conditions  # Most common for economic data
        assert 'decreasing' in conditions      # For trend-based signals


class TestIndicatorSpecificValidation:
    """Test specific indicator configurations."""
    
    def test_initial_claims_config(self):
        """Test Initial Claims configuration."""
        config = INDICATOR_REGISTRY['initial_claims']
        
        assert config.display_name == 'Initial Jobless Claims'
        assert 'ICSA' in config.fred_series
        assert config.chart_type == 'line'
        assert config.bullish_condition == 'below_threshold'
        assert config.threshold is not None
    
    def test_pce_config(self):
        """Test PCE configuration."""
        config = INDICATOR_REGISTRY['pce']
        
        assert config.display_name == 'Personal Consumption Expenditures (PCE)'
        assert 'PCE' in config.fred_series
        assert config.chart_type == 'line'
    
    def test_copper_gold_config(self):
        """Test Copper/Gold configuration for Yahoo data."""
        config = INDICATOR_REGISTRY['copper_gold_yield']
        
        assert config.yahoo_series is not None
        assert len(config.yahoo_series) > 0
        # Should include copper and gold symbols
        yahoo_symbols = config.yahoo_series
        assert any('HG' in symbol for symbol in yahoo_symbols)  # Copper
        assert any('GC' in symbol for symbol in yahoo_symbols)  # Gold
    
    def test_usd_liquidity_custom_functions(self):
        """Test USD Liquidity has custom functions."""
        config = INDICATOR_REGISTRY['usd_liquidity']
        
        assert config.chart_type == 'custom'
        assert config.custom_chart_fn is not None
        assert config.liquidity_components is not None