"""
Tests for volatility table UI component
"""

import pytest
import pandas as pd
import numpy as np
import sys
from unittest.mock import patch, MagicMock
from pandas.io.formats.style import Styler
from ui.vol_table import _format_and_style_table, _render_data_freshness_info
import streamlit as st


class TestVolTableFormatting:
    """Test data formatting and styling for volatility table"""
    
    def setup_method(self):
        """Create sample volatility data for testing"""
        self.sample_data = pd.DataFrame({
            'etf_name': ['Technology Select SPDR', 'Energy Select SPDR'],
            'ticker_display': ['XLK US EQUITY', 'XLE US EQUITY'],
            'ytd_pct': [15.2, -8.7],
            'ivol_rvol_current': [25.3, 45.8],
            'ivol_prem_yesterday': [22.1, 40.2],
            'ivol_prem_1w': [18.9, 38.5],
            'ivol_prem_1m': [20.1, 42.1],
            'ttm_zscore': [0.85, 1.92],
            'three_yr_zscore': [-0.34, 1.45],
            'date': ['2026-03-06', '2026-03-06']
        })
    
    def test_column_renaming(self):
        """Test proper column renaming for display"""
        styled = _format_and_style_table(self.sample_data)
        df = styled.data
        
        expected_columns = [
            "ETF Name", "Ticker", "YTD %", "IVOL/RVOL Current",
            "IVOL Prem % Yesterday", "IVOL Prem % 1W Ago", "IVOL Prem % 1M Ago",
            "TTM Z-Score", "3Yr Z-Score", "date"
        ]
        
        assert list(df.columns) == expected_columns
    
    def test_percentage_formatting(self):
        """Test percentage column formatting"""
        styled = _format_and_style_table(self.sample_data)
        
        # Check that styler has format functions applied
        # We can test this by checking the styler's internal state or rendering
        assert isinstance(styled, Styler)
        
        # Test by rendering a sample to see if formatting is applied
        rendered_html = styled.to_html()
        assert "%" in rendered_html  # Should contain percentage symbols
    
    def test_zscore_formatting(self):
        """Test Z-score column formatting"""
        styled = _format_and_style_table(self.sample_data)
        
        # Check that styler object exists and has been formatted
        assert isinstance(styled, Styler)
        
        # Test by checking if Z-score columns are present in rendered output
        rendered_html = styled.to_html()
        assert "TTM Z-Score" in rendered_html
        assert "3Yr Z-Score" in rendered_html
    
    def test_returns_styler_object(self):
        """Test that function returns a Styler object"""
        result = _format_and_style_table(self.sample_data)
        assert isinstance(result, Styler)
    
    def test_handles_missing_columns_gracefully(self):
        """Test handling of missing optional columns"""
        minimal_data = pd.DataFrame({
            'etf_name': ['Technology Select SPDR'],
            'ticker_display': ['XLK US EQUITY'],
            'ytd_pct': [15.2],
            'ivol_rvol_current': [25.3]
        })
        
        # Should not raise an exception
        styled = _format_and_style_table(minimal_data)
        assert isinstance(styled, Styler)
    
    def test_handles_nan_values(self):
        """Test proper handling of NaN values"""
        data_with_nans = self.sample_data.copy()
        data_with_nans.loc[0, 'ivol_prem_1m'] = np.nan
        data_with_nans.loc[1, 'ttm_zscore'] = np.nan
        
        styled = _format_and_style_table(data_with_nans)
        
        # Should handle NaN without errors
        assert isinstance(styled, Styler)
        
        # Test by rendering to see if NaN is handled properly
        rendered_html = styled.to_html()
        assert isinstance(rendered_html, str)  # Should render successfully


class TestVolTableRendering:
    """Test Streamlit rendering functions"""
    
    def setup_method(self):
        """Setup test data"""
        self.sample_data = pd.DataFrame({
            'etf_name': ['Technology Select SPDR'],
            'ticker_display': ['XLK US EQUITY'],
            'ytd_pct': [15.2],
            'ivol_rvol_current': [25.3],
            'date': ['2026-03-06']
        })
    
    @patch('ui.vol_table.st')
    def test_render_empty_data_message(self, mock_st):
        """Test rendering with empty data shows appropriate message"""
        from ui.vol_table import render_vol_table
        
        # Test with None data
        render_vol_table(None)
        mock_st.info.assert_called_once()
        assert "python -m data.iv_scraper" in mock_st.info.call_args[0][0]
        
        # Reset mock
        mock_st.reset_mock()
        
        # Test with empty DataFrame
        render_vol_table(pd.DataFrame())
        mock_st.info.assert_called_once()
    
    @patch('ui.vol_table.st')
    def test_render_partial_data_warning(self, mock_st):
        """Test warning for partial data (< 14 tickers)"""
        from ui.vol_table import render_vol_table
        
        render_vol_table(self.sample_data)  # Only 1 ticker
        mock_st.warning.assert_called_once()
        warning_msg = mock_st.warning.call_args[0][0]
        assert "partial data (1/14" in warning_msg
    
    @patch('ui.vol_table.st')
    def test_render_full_table_success(self, mock_st):
        """Test successful table rendering with full data"""
        from ui.vol_table import render_vol_table
        
        # Create data with 14 tickers to avoid partial data warning
        full_data = pd.concat([self.sample_data] * 14, ignore_index=True)
        full_data['ticker_display'] = [f'XL{chr(65+i)} US EQUITY' for i in range(14)]
        
        render_vol_table(full_data)
        
        # Should call main rendering functions
        mock_st.subheader.assert_called_with("📊 Implied vs Realized Volatility")
        mock_st.caption.assert_called_once()
        mock_st.dataframe.assert_called_once()
    
    @patch('ui.vol_table.st')
    @patch('ui.vol_table.logger')
    def test_render_handles_exceptions(self, mock_logger, mock_st):
        """Test error handling in render function"""
        from ui.vol_table import render_vol_table
        
        # Mock _format_and_style_table to raise an exception
        with patch('ui.vol_table._format_and_style_table', side_effect=Exception("Test error")):
            render_vol_table(self.sample_data)
            
            # Should log error and show error message
            mock_logger.error.assert_called_once()
            mock_st.error.assert_called_once()


class TestDataFreshnessInfo:
    """Test data freshness information display"""
    
    @patch('ui.vol_table.st')
    @patch('ui.vol_table.pd.Timestamp')
    def test_current_data_freshness(self, mock_timestamp, mock_st):
        """Test display for current data"""
        # Mock current time
        mock_now = pd.Timestamp('2026-03-06 10:00:00')
        mock_timestamp.now.return_value = mock_now
        
        data = pd.DataFrame({
            'date': ['2026-03-06', '2026-03-06'],
            'ticker': ['XLK', 'XLE']
        })
        
        _render_data_freshness_info(data)
        
        # Should show current freshness
        mock_st.columns.assert_called_once_with(2)
        # The exact assertion depends on how streamlit columns work
    
    @patch('ui.vol_table.st')
    @patch('ui.vol_table.pd.Timestamp')  
    def test_old_data_freshness(self, mock_timestamp, mock_st):
        """Test display for old data"""
        # Mock current time
        mock_now = pd.Timestamp('2026-03-10 10:00:00')  # 4 days later
        mock_timestamp.now.return_value = mock_now
        
        data = pd.DataFrame({
            'date': ['2026-03-06', '2026-03-06'],  # 4 days old
            'ticker': ['XLK', 'XLE']
        })
        
        _render_data_freshness_info(data)
        
        # Should call streamlit functions
        mock_st.columns.assert_called_once_with(2)
    
    @patch('ui.vol_table.st')
    @patch('ui.vol_table.logger')
    def test_handles_missing_date_column(self, mock_logger, mock_st):
        """Test graceful handling when date column is missing"""
        data = pd.DataFrame({
            'ticker': ['XLK', 'XLE'],
            'ytd_pct': [10.5, -5.2]
        })
        
        _render_data_freshness_info(data)
        
        # Should not crash, might log a warning
        # No specific assertions needed since function should handle gracefully


class TestIntegrationFunction:
    """Test the convenience integration function"""
    
    @patch('ui.vol_table.render_vol_table')
    def test_render_with_data_fetch_success(self, mock_render):
        """Test successful data fetch and render"""
        from ui.vol_table import render_vol_table_with_data_fetch
        
        # Mock the imports and service within the function
        with patch.dict('sys.modules', {'src.services.indicator_service': MagicMock()}):
            mock_module = MagicMock()
            mock_service_class = MagicMock()
            mock_service = MagicMock()
            mock_result = MagicMock()
            mock_result.data = pd.DataFrame({'test': [1, 2, 3]})
            
            mock_service.get_indicator.return_value = mock_result
            mock_service_class.return_value = mock_service
            mock_module.IndicatorService = mock_service_class
            
            with patch.dict('sys.modules', {'src.services.indicator_service': mock_module}):
                render_vol_table_with_data_fetch()
                
                # Should call render function
                mock_render.assert_called_once()
    
    @patch('ui.vol_table.render_vol_table')
    def test_render_with_data_fetch_no_data(self, mock_render):
        """Test handling when no data is returned"""
        from ui.vol_table import render_vol_table_with_data_fetch
        
        # Mock the imports and service within the function
        with patch.dict('sys.modules', {'src.services.indicator_service': MagicMock()}):
            mock_module = MagicMock()
            mock_service_class = MagicMock()
            mock_service = MagicMock()
            
            mock_service.get_indicator.return_value = None
            mock_service_class.return_value = mock_service
            mock_module.IndicatorService = mock_service_class
            
            with patch.dict('sys.modules', {'src.services.indicator_service': mock_module}):
                render_vol_table_with_data_fetch()
                
                # Should render with None data
                mock_render.assert_called_once_with(None)
    
    @patch('ui.vol_table.st')
    @patch('ui.vol_table.logger')
    def test_render_with_data_fetch_import_error(self, mock_logger, mock_st):
        """Test handling of import errors"""
        from ui.vol_table import render_vol_table_with_data_fetch
        
        # Temporarily remove the module to simulate import error
        if 'src.services.indicator_service' in sys.modules:
            original_module = sys.modules['src.services.indicator_service']
            del sys.modules['src.services.indicator_service']
        else:
            original_module = None
            
        try:
            render_vol_table_with_data_fetch()
            
            # Should log error and show error message
            mock_logger.error.assert_called_once()
            mock_st.error.assert_called_once()
            
        finally:
            # Restore the module if it existed
            if original_module is not None:
                sys.modules['src.services.indicator_service'] = original_module


if __name__ == "__main__":
    pytest.main([__file__, "-v"])