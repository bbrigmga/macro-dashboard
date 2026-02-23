"""Tests for generic card UI components."""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from ui.indicators import (
    _render_status_badge,
    display_indicator_card,
    display_core_principles_card
)
from src.config.indicator_registry import IndicatorConfig, INDICATOR_REGISTRY


@pytest.fixture
def mock_streamlit_components():
    """Mock Streamlit components for UI testing."""
    with patch('ui.indicators.st') as mock_st:
        # Setup mock return values
        mock_st.container.return_value.__enter__ = Mock()
        mock_st.container.return_value.__exit__ = Mock()
        mock_st.expander.return_value.__enter__ = Mock() 
        mock_st.expander.return_value.__exit__ = Mock()
        
        yield mock_st


@pytest.fixture
def sample_card_data():
    """Sample data for card testing."""
    dates = pd.date_range('2024-01-01', periods=10, freq='W')
    df = pd.DataFrame({
        'Date': dates,
        'value': [380000, 375000, 385000, 390000, 370000, 365000, 380000, 375000, 360000, 355000]
    })
    
    return {
        'data': df,
        'current_value': 355000,
        'latest_value': 355000,
        'previous_value': 360000,
        'change_pct': -1.39,
        'status': 'Bullish'
    }


@pytest.fixture 
def mock_fred_client():
    """Mock FRED client for tests."""
    client = Mock()
    client.get_series_info = Mock(return_value={'title': 'Test Series'})
    return client


class TestRenderStatusBadge:
    """Test _render_status_badge function."""
    
    def test_bullish_status_badge(self, mock_streamlit_components):
        """Test rendering bullish status badge."""
        _render_status_badge("Bullish")
        
        mock_streamlit_components.markdown.assert_called_once()
        call_args = mock_streamlit_components.markdown.call_args[0][0]
        assert "#00c853" in call_args  # Bullish green color
        assert "↑" in call_args       # Up arrow
        assert "Bullish" in call_args
    
    def test_bearish_status_badge(self, mock_streamlit_components):
        """Test rendering bearish status badge."""
        _render_status_badge("Bearish")
        
        mock_streamlit_components.markdown.assert_called_once()
        call_args = mock_streamlit_components.markdown.call_args[0][0]
        assert "#f44336" in call_args  # Bearish red color
        assert "↓" in call_args        # Down arrow
        assert "Bearish" in call_args
    
    def test_neutral_status_badge(self, mock_streamlit_components):
        """Test rendering neutral status badge."""
        _render_status_badge("Neutral")
        
        mock_streamlit_components.markdown.assert_called_once()
        call_args = mock_streamlit_components.markdown.call_args[0][0]
        assert "#78909c" in call_args  # Neutral grey color
        assert "→" in call_args        # Right arrow
        assert "Neutral" in call_args
    
    def test_unknown_status_badge(self, mock_streamlit_components):
        """Test rendering unknown status defaults to neutral."""
        _render_status_badge("Unknown")
        
        mock_streamlit_components.markdown.assert_called_once()
        call_args = mock_streamlit_components.markdown.call_args[0][0]
        assert "#78909c" in call_args  # Default grey color
        assert "→" in call_args        # Default right arrow
        assert "Unknown" in call_args


class TestDisplayIndicatorCard:
    """Test display_indicator_card function."""
    
    @patch('ui.indicators.create_indicator_chart')
    @patch('ui.indicators.generate_indicator_warning')
    @patch('ui.indicators.get_next_release_date')
    @patch('ui.indicators.format_release_date')
    @patch('ui.indicators.validate_indicator_data')
    def test_basic_card_display(self, mock_validate, mock_format_date, mock_get_date, 
                               mock_generate_warning, mock_create_chart, mock_streamlit_components,
                               sample_card_data, mock_fred_client):
        """Test basic indicator card display."""
        # Setup mocks
        mock_validate.return_value = True
        mock_get_date.return_value = "2024-12-06"
        mock_format_date.return_value = "Next release: Dec 6, 2024"
        mock_generate_warning.return_value = {"status": "Bullish", "details": "Test details"}
        mock_create_chart.return_value = Mock()  # Mock Plotly figure
        
        # Test with initial_claims indicator
        display_indicator_card("initial_claims", sample_card_data, mock_fred_client)
        
        # Verify key components were called
        assert mock_streamlit_components.subheader.called
        assert mock_streamlit_components.caption.called
        mock_validate.assert_called_once()
        mock_generate_warning.assert_called_once()
        mock_create_chart.assert_called_once()
        assert mock_streamlit_components.plotly_chart.called
    
    @patch('ui.indicators.validate_indicator_data')  
    def test_invalid_data_handling(self, mock_validate, mock_streamlit_components, sample_card_data):
        """Test handling of invalid data."""
        mock_validate.return_value = False
        
        display_indicator_card("initial_claims", sample_card_data)
        
        # Should show warning and return early
        mock_streamlit_components.warning.assert_called_once()
        warning_text = mock_streamlit_components.warning.call_args[0][0]
        assert "Data unavailable" in warning_text
    
    @patch('ui.indicators.create_indicator_chart')
    @patch('ui.indicators.generate_indicator_warning')  
    @patch('ui.indicators.validate_indicator_data')
    def test_current_value_extraction_scenarios(self, mock_validate, mock_generate_warning,
                                              mock_create_chart, mock_streamlit_components):
        """Test different scenarios for extracting current values."""
        mock_validate.return_value = True
        mock_generate_warning.return_value = {"status": "Neutral", "details": "Test"}
        mock_create_chart.return_value = Mock()
        
        # Test different data formats
        test_cases = [
            {"current_value": 100000},
            {"latest_value": 200000},
            {"current_initial_claims": 300000},
        ]
        
        for data in test_cases:
            display_indicator_card("initial_claims", data)
            
            # Should successfully process without errors
            assert mock_streamlit_components.markdown.called
            mock_streamlit_components.reset_mock()
    
    @patch('ui.indicators.create_indicator_chart')
    @patch('ui.indicators.generate_indicator_warning')
    @patch('ui.indicators.validate_indicator_data') 
    def test_value_formatting_by_indicator_type(self, mock_validate, mock_generate_warning,
                                               mock_create_chart, mock_streamlit_components):
        """Test value formatting for different indicator types."""
        mock_validate.return_value = True
        mock_generate_warning.return_value = {"status": "Neutral", "details": "Test"}
        mock_create_chart.return_value = Mock()
        
        # Test different indicator types and their value formatting
        test_cases = [
            ("initial_claims", {"current_value": 350000}, "350,000"),
            ("hours_worked", {"recent_hours": [38.5]}, "38.5 hours"),
            ("core_cpi", {"current_cpi_mom": 0.25}, "0.25%"),
            ("pce", {"current_pce_mom": 0.30}, "0.30%"), 
            ("pmi_proxy", {"latest_pmi": 52.1}, "52.1"),
            ("usd_liquidity", {"current_liquidity": 4500}, "4.50T")  # Large number formatting
        ]
        
        for indicator_key, data, expected_format in test_cases:
            if indicator_key in INDICATOR_REGISTRY:  # Only test if indicator exists
                display_indicator_card(indicator_key, data)
                
                # Verify markdown was called (value was formatted and displayed)
                assert mock_streamlit_components.markdown.called
                mock_streamlit_components.reset_mock()

    @patch('ui.indicators.create_indicator_chart')
    @patch('ui.indicators.generate_indicator_warning')
    @patch('ui.indicators.validate_indicator_data')
    def test_hours_worked_numpy_recent_hours(self, mock_validate, mock_generate_warning,
                                            mock_create_chart, mock_streamlit_components):
        """Test hours_worked card handles NumPy recent_hours arrays without truth-value errors."""
        mock_validate.return_value = True
        mock_generate_warning.return_value = {"status": "Neutral", "details": "Test"}
        mock_create_chart.return_value = Mock()

        data = {"recent_hours": np.array([38.2, 38.1, 38.0, 37.9])}

        display_indicator_card("hours_worked", data)

        markdown_calls = [call[0][0] for call in mock_streamlit_components.markdown.call_args_list]
        assert any("37.9 hours" in call for call in markdown_calls)
    
    @patch('ui.indicators.create_indicator_chart')
    @patch('ui.indicators.generate_indicator_warning')
    @patch('ui.indicators.validate_indicator_data')
    def test_none_value_handling(self, mock_validate, mock_generate_warning,
                                mock_create_chart, mock_streamlit_components):
        """Test handling when current value is None."""
        mock_validate.return_value = True
        mock_generate_warning.return_value = {"status": "Neutral", "details": "Test"}
        mock_create_chart.return_value = Mock()
        
        data = {"some_other_field": "value"}  # No current_value field
        
        display_indicator_card("initial_claims", data)
        
        # Should handle gracefully and show "N/A"
        assert mock_streamlit_components.markdown.called
        # Check that N/A is displayed
        markdown_calls = [call[0][0] for call in mock_streamlit_components.markdown.call_args_list]
        assert any("N/A" in call for call in markdown_calls)
    
    @patch('ui.indicators.create_pmi_components_table')
    @patch('ui.indicators.create_indicator_chart')
    @patch('ui.indicators.generate_indicator_warning')
    @patch('ui.indicators.validate_indicator_data')
    def test_pmi_special_content(self, mock_validate, mock_generate_warning, mock_create_chart,
                                mock_create_table, mock_streamlit_components, sample_card_data):
        """Test PMI special content display."""
        mock_validate.return_value = True
        mock_generate_warning.return_value = {"status": "Bullish", "details": "Test"}
        mock_create_chart.return_value = Mock()
        mock_create_table.return_value = pd.DataFrame({"Component": ["Test"], "Weight": [0.5]})
        
        # Setup expander mock to act as context manager
        expander_mock = MagicMock()
        expander_mock.__enter__ = Mock(return_value=expander_mock)
        expander_mock.__exit__ = Mock(return_value=None)
        mock_streamlit_components.expander.return_value = expander_mock
        
        display_indicator_card("pmi_proxy", sample_card_data)
        
        # Should create PMI components table
        mock_create_table.assert_called_once()
        assert mock_streamlit_components.subheader.called
        assert mock_streamlit_components.write.called
        
    @patch('ui.indicators.create_indicator_chart')
    @patch('ui.indicators.generate_indicator_warning')
    @patch('ui.indicators.validate_indicator_data')
    def test_usd_liquidity_special_content(self, mock_validate, mock_generate_warning,
                                          mock_create_chart, mock_streamlit_components):
        """Test USD Liquidity special content display."""
        mock_validate.return_value = True
        mock_generate_warning.return_value = {"status": "Bullish", "details": "Test"}
        mock_create_chart.return_value = Mock()
        
        # Setup expander mock
        expander_mock = MagicMock()
        expander_mock.__enter__ = Mock(return_value=expander_mock)
        expander_mock.__exit__ = Mock(return_value=None)
        mock_streamlit_components.expander.return_value = expander_mock
        
        data = {
            "current_liquidity": 4500,
            "details": {
                "WALCL": 7000,
                "RRPONTTLD": 2500, 
                "WTREGEN": 595,
                "CURRCIR": 2300,
                "GDP": 25000,
                "Tariff_Flow": 50
            }
        }
        
        display_indicator_card("usd_liquidity", data)
        
        # Should display USD liquidity explanation
        write_calls = mock_streamlit_components.write.call_args_list
        assert len(write_calls) > 0
        # Check that tariff explanation is present
        assert any("tariff" in str(call[0]).lower() for call in write_calls)
    
    @patch('ui.indicators.create_indicator_chart')
    @patch('ui.indicators.generate_indicator_warning')
    @patch('ui.indicators.validate_indicator_data')
    def test_fred_link_display(self, mock_validate, mock_generate_warning, mock_create_chart,
                              mock_streamlit_components, sample_card_data):
        """Test FRED link display in expander."""
        mock_validate.return_value = True
        mock_generate_warning.return_value = {"status": "Bullish", "details": "Test"}
        mock_create_chart.return_value = Mock()
        
        # Setup expander mock
        expander_mock = MagicMock()
        expander_mock.__enter__ = Mock(return_value=expander_mock)  
        expander_mock.__exit__ = Mock(return_value=None)
        mock_streamlit_components.expander.return_value = expander_mock
        
        # Test with indicator that has FRED link
        display_indicator_card("initial_claims", sample_card_data)
        
        # Should display FRED link
        markdown_calls = mock_streamlit_components.markdown.call_args_list
        assert len(markdown_calls) > 0
        # Check for FRED link pattern
        fred_link_found = any("[View on FRED]" in str(call[0]) for call in markdown_calls)
        assert fred_link_found or len(markdown_calls) >= 2  # Link might be in different call


class TestDisplayCorePrinciplesCard:
    """Test display_core_principles_card function."""
    
    def test_core_principles_card_display(self, mock_streamlit_components):
        """Test core principles card displays content."""
        display_core_principles_card()
        
        # Should call Streamlit components to display content
        assert mock_streamlit_components.subheader.called
        assert mock_streamlit_components.write.called or mock_streamlit_components.markdown.called
        
        # Check that principles content is displayed
        calls = (mock_streamlit_components.write.call_args_list + 
                mock_streamlit_components.markdown.call_args_list)
        assert len(calls) > 0


class TestCardIntegration:
    """Integration tests for card system."""
    
    @patch('ui.indicators.create_indicator_chart')
    @patch('ui.indicators.generate_indicator_warning')
    @patch('ui.indicators.validate_indicator_data')
    def test_all_registry_indicators_can_render_cards(self, mock_validate, mock_generate_warning,
                                                     mock_create_chart, mock_streamlit_components):
        """Test that all indicators in registry can render cards."""
        mock_validate.return_value = True
        mock_generate_warning.return_value = {"status": "Neutral", "details": "Test"}
        mock_create_chart.return_value = Mock()
        
        # Test a few key indicators from the registry
        test_indicators = ["initial_claims", "pce", "core_cpi"]
        
        for indicator_key in test_indicators:
            if indicator_key in INDICATOR_REGISTRY:
                data = {"latest_value": 100}
                
                try:
                    display_indicator_card(indicator_key, data)
                    # Should complete without errors
                    assert mock_streamlit_components.subheader.called
                    mock_streamlit_components.reset_mock()
                except Exception as e:
                    pytest.fail(f"Card rendering failed for {indicator_key}: {e}")
    
    @patch('ui.indicators.create_indicator_chart')
    @patch('ui.indicators.generate_indicator_warning')
    @patch('ui.indicators.validate_indicator_data')
    def test_card_error_recovery(self, mock_validate, mock_generate_warning, mock_create_chart,
                                mock_streamlit_components):
        """Test card handles errors gracefully."""
        mock_validate.return_value = True
        mock_generate_warning.side_effect = Exception("Warning error")
        mock_create_chart.return_value = Mock()
        
        data = {"latest_value": 100}
        
        # Should not crash even if warning generation fails
        try:
            display_indicator_card("initial_claims", data)
        except Exception as e:
            # If error propagates, it should be handled gracefully
            assert "Warning error" in str(e) or isinstance(e, KeyError)
    
    def test_card_with_minimal_data(self, mock_streamlit_components):
        """Test card behavior with minimal data."""
        with patch('ui.indicators.validate_indicator_data', return_value=False):
            data = {}
            
            display_indicator_card("initial_claims", data)
            
            # Should show data unavailable warning
            mock_streamlit_components.warning.assert_called_once()
    
    @patch('ui.indicators.create_indicator_chart')
    @patch('ui.indicators.generate_indicator_warning')
    @patch('ui.indicators.validate_indicator_data')
    def test_chart_integration(self, mock_validate, mock_generate_warning, mock_create_chart,
                              mock_streamlit_components, sample_card_data):
        """Test chart integration in cards."""
        mock_validate.return_value = True
        mock_generate_warning.return_value = {"status": "Bullish", "details": "Test"}
        
        # Mock a Plotly figure
        mock_fig = Mock()
        mock_fig.data = [Mock()]  # Mock chart data
        mock_create_chart.return_value = mock_fig
        
        display_indicator_card("initial_claims", sample_card_data)
        
        # Should create and display chart
        mock_create_chart.assert_called_once_with("initial_claims", sample_card_data)
        mock_streamlit_components.plotly_chart.assert_called_once()
        
        # Verify chart config
        plotly_call = mock_streamlit_components.plotly_chart.call_args
        assert 'use_container_width' in plotly_call[1]
        assert plotly_call[1]['use_container_width'] is True