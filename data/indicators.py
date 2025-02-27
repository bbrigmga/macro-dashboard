"""
Functions for fetching and processing economic indicators.
"""
import pandas as pd
import numpy as np
from data.fred_client import FredClient
from data.processing import calculate_pct_change, check_consecutive_increase, check_consecutive_decrease, count_consecutive_changes


class IndicatorData:
    """Class for fetching and processing economic indicators."""
    
    def __init__(self, fred_client=None):
        """
        Initialize the indicator data handler.
        
        Args:
            fred_client (FredClient, optional): FRED API client. If None, a new client will be created.
        """
        self.fred_client = fred_client if fred_client else FredClient()
    
    def get_initial_claims(self, periods=52):
        """
        Get initial jobless claims data.
        
        Args:
            periods (int, optional): Number of periods to fetch
            
        Returns:
            dict: Dictionary with claims data and analysis
        """
        # Fetch claims data with weekly frequency
        claims_data = self.fred_client.get_series('ICSA', periods=periods, frequency='W')
        claims_data.columns = ['Date', 'Claims']
        
        # Get recent claims for analysis
        recent_claims = claims_data['Claims'].tail(4).values
        claims_increasing = check_consecutive_increase(recent_claims, 3)
        
        return {
            'data': claims_data,
            'recent_claims': recent_claims,
            'claims_increasing': claims_increasing,
            'current_value': claims_data['Claims'].iloc[-1]
        }
    
    def get_pce(self, periods=24):
        """
        Get Personal Consumption Expenditures (PCE) data.
        
        Args:
            periods (int, optional): Number of periods to fetch
            
        Returns:
            dict: Dictionary with PCE data and analysis
        """
        # Fetch PCE data with monthly frequency
        pce_data = self.fred_client.get_series('PCEPI', periods=periods, frequency='M')
        pce_data.columns = ['Date', 'PCE']
        
        # Calculate year-over-year and month-over-month percentage changes
        pce_data['PCE_YoY'] = calculate_pct_change(pce_data, 'PCE', periods=12)
        pce_data['PCE_MoM'] = calculate_pct_change(pce_data, 'PCE', periods=1)
        
        # Get current PCE and check if it's rising
        current_pce = pce_data['PCE_YoY'].iloc[-1]
        current_pce_mom = pce_data['PCE_MoM'].iloc[-1]
        pce_rising = pce_data['PCE_YoY'].iloc[-1] > pce_data['PCE_YoY'].iloc[-2]
        
        return {
            'data': pce_data,
            'current_pce': current_pce,
            'current_pce_mom': current_pce_mom,
            'pce_rising': pce_rising
        }
    
    def get_core_cpi(self, periods=24):
        """
        Get Core CPI (Consumer Price Index Less Food and Energy) data.
        
        Args:
            periods (int, optional): Number of periods to fetch
            
        Returns:
            dict: Dictionary with CPI data and analysis
        """
        # Fetch Core CPI data with monthly frequency
        core_cpi_data = self.fred_client.get_series('CPILFESL', periods=periods, frequency='M')
        core_cpi_data.columns = ['Date', 'CPI']
        
        # Calculate year-over-year and month-over-month percentage changes
        core_cpi_data['CPI_YoY'] = calculate_pct_change(core_cpi_data, 'CPI', periods=12)
        core_cpi_data['CPI_MoM'] = calculate_pct_change(core_cpi_data, 'CPI', periods=1)
        
        # Get the last 4 months of MoM changes
        recent_cpi_mom = core_cpi_data['CPI_MoM'].tail(4).values
        
        # Check if MoM changes have been accelerating
        cpi_accelerating = check_consecutive_increase(recent_cpi_mom, 3)
        
        return {
            'data': core_cpi_data,
            'recent_cpi_mom': recent_cpi_mom,
            'cpi_accelerating': cpi_accelerating,
            'current_cpi': core_cpi_data['CPI_YoY'].iloc[-1],
            'current_cpi_mom': core_cpi_data['CPI_MoM'].iloc[-1]
        }
    
    def get_hours_worked(self, periods=24):
        """
        Get Average Weekly Hours data.
        
        Args:
            periods (int, optional): Number of periods to fetch
            
        Returns:
            dict: Dictionary with hours worked data and analysis
        """
        # Fetch Hours Worked data with monthly frequency
        hours_data = self.fred_client.get_series('AWHAETP', periods=periods, frequency='M')
        hours_data.columns = ['Date', 'Hours']
        
        # Calculate month-over-month percentage change
        hours_data['MoM_Change'] = calculate_pct_change(hours_data, 'Hours', periods=1)
        
        # Cap outliers for display purposes
        hours_data['MoM_Change_Capped'] = hours_data['MoM_Change'].clip(lower=-2, upper=2)
        
        # Get recent hours for analysis
        recent_hours = hours_data['Hours'].tail(4).values
        
        # Check if hours have been decreasing for 3 or more consecutive months
        hours_weakening = count_consecutive_changes(recent_hours, decreasing=True) >= 3
        
        # Count consecutive declines
        consecutive_declines = count_consecutive_changes(recent_hours, decreasing=True)
        
        return {
            'data': hours_data,
            'recent_hours': recent_hours,
            'hours_weakening': hours_weakening,
            'consecutive_declines': consecutive_declines,
            'current_hours_change': hours_data['MoM_Change'].iloc[-1],
            'current_hours_change_display': hours_data['MoM_Change_Capped'].iloc[-1]
        }
    
    def calculate_pmi_proxy(self, periods=36, start_date=None):
        """
        Calculate a proxy for the ISM Manufacturing PMI using FRED data.
        
        Args:
            periods (int, optional): Number of periods to fetch if start_date is not provided
            start_date (str, optional): Start date for data in format 'YYYY-MM-DD'
            
        Returns:
            dict: Dictionary with PMI proxy data and analysis
        """
        # Define FRED series IDs for proxy variables
        series_ids = {
            'new_orders': 'DGORDER',      # Manufacturers' New Orders: Durable Goods
            'production': 'INDPRO',       # Industrial Production Index
            'employment': 'MANEMP',       # All Employees: Manufacturing
            'supplier_deliveries': 'AMTMUO',  # Manufacturers: Unfilled Orders for All Manufacturing Industries
            'inventories': 'BUSINV'       # Total Business Inventories
        }
        
        # Define PMI component weights
        weights = {
            'new_orders': 0.30,
            'production': 0.25,
            'employment': 0.20,
            'supplier_deliveries': 0.15,
            'inventories': 0.10
        }
        
        # Function to calculate diffusion-like index from percentage change
        def to_diffusion_index(pct_change, scale=10):
            return 50 + (pct_change * scale)
        
        # Get all series in one batch request
        all_series = self.fred_client.get_multiple_series(
            list(series_ids.values()),
            start_date=start_date,
            periods=periods if start_date is None else None,
            frequency='M'
        )
        
        # Rename columns to component names
        rename_map = {v: k for k, v in series_ids.items()}
        all_series.rename(columns=rename_map, inplace=True)
        
        # Keep only the component columns and Date
        component_columns = list(series_ids.keys())
        df = all_series[['Date'] + component_columns].copy()
        
        # Ensure monthly frequency
        df.set_index('Date', inplace=True)
        df = df.resample('M').last()
        
        # Calculate month-over-month percentage change
        # Only calculate pct_change on the component columns, not the DatetimeIndex
        df_pct_change = df[component_columns].ffill().pct_change() * 100  # Convert to percentage
        
        # Transform to diffusion-like indices
        df_diffusion = df_pct_change.apply(lambda x: to_diffusion_index(x))
        
        # Calculate the approximated PMI as a weighted average
        df['approximated_pmi'] = (df_diffusion * pd.Series(weights)).sum(axis=1)
        
        # Store component values for the latest month
        component_values = {}
        for component in series_ids.keys():
            component_values[component] = df_diffusion[component].iloc[-1]
        
        # Get current PMI and check if it's below 50
        current_pmi = df['approximated_pmi'].iloc[-1]
        pmi_below_50 = current_pmi < 50
        
        # Extract the PMI series with DatetimeIndex before resetting index
        pmi_series = df['approximated_pmi'].copy()
        
        # Reset index to get Date as a column for other operations
        df.reset_index(inplace=True)
        
        return {
            'latest_pmi': current_pmi,
            'pmi_series': pmi_series,  # Series with DatetimeIndex
            'component_values': component_values,
            'component_weights': weights,
            'pmi_below_50': pmi_below_50
        }
    
    def get_all_indicators(self):
        """
        Get all economic indicators and their analysis.
        
        Returns:
            dict: Dictionary with all indicator data and analysis
        """
        claims_data = self.get_initial_claims()
        pce_data = self.get_pce()
        core_cpi_data = self.get_core_cpi()
        hours_data = self.get_hours_worked()
        pmi_data = self.calculate_pmi_proxy(periods=36)
        
        return {
            'claims': claims_data,
            'pce': pce_data,
            'core_cpi': core_cpi_data,
            'hours_worked': hours_data,
            'pmi': pmi_data
        }
