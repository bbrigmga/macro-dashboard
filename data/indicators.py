"""
Functions for fetching and processing economic indicators.
"""
import pandas as pd
import numpy as np
import datetime
import logging
import streamlit as st
from data.fred_client import FredClient
from data.processing import calculate_pct_change, check_consecutive_increase, check_consecutive_decrease, count_consecutive_changes

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def generate_sample_dates(periods, frequency='M'):
    """
    Generate sample dates for fallback data.
    
    Args:
        periods (int): Number of periods to generate
        frequency (str, optional): Frequency of dates ('D' for daily, 'W' for weekly, 'M' for monthly)
        
    Returns:
        list: List of datetime objects
    """
    end_date = datetime.datetime.now()
    
    if frequency == 'D':
        return [end_date - datetime.timedelta(days=i) for i in range(periods)][::-1]
    elif frequency == 'W':
        return [end_date - datetime.timedelta(weeks=i) for i in range(periods)][::-1]
    else:  # Monthly
        return [end_date - datetime.timedelta(days=30*i) for i in range(periods)][::-1]


class IndicatorData:
    """Class for fetching and processing economic indicators."""
    
    def __init__(self, fred_client=None):
        """
        Initialize the indicator data handler.
        
        Args:
            fred_client (FredClient, optional): FRED API client. If None, a new client will be created.
        """
        self.fred_client = fred_client if fred_client else FredClient()
    
    @st.cache_data(ttl=3600) # Cache for 1 hour
    def get_initial_claims(_self, periods=52):
        """
        Get initial jobless claims data.
        
        Args:
            periods (int, optional): Number of periods to fetch (52 weeks = 1 year)
            
        Returns:
            dict: Dictionary with claims data and analysis
        """
        try:
            # Fetch claims data with weekly frequency
            claims_data = _self.fred_client.get_series('ICSA', periods=periods, frequency='W')
            claims_data.columns = ['Date', 'Claims']
            
            # Get recent claims for analysis
            recent_claims = claims_data['Claims'].tail(4).values
            claims_increasing = check_consecutive_increase(recent_claims, 3)
            claims_decreasing = check_consecutive_decrease(recent_claims, 3)
            
            return {
                'data': claims_data,
                'recent_claims': recent_claims,
                'claims_increasing': claims_increasing,
                'claims_decreasing': claims_decreasing,
                'current_value': claims_data['Claims'].iloc[-1]
            }
        except Exception as e:
            logger.error(f"Failed to fetch or process claims data: {e}")
            raise
    
    @st.cache_data(ttl=3600*24) # Cache for 24 hours
    def get_pce(_self, periods=24):
        """
        Get Personal Consumption Expenditures (PCE) data.
        
        Args:
            periods (int, optional): Number of periods to fetch
            
        Returns:
            dict: Dictionary with PCE data and analysis
        """
        try:
            # Fetch PCE data with monthly frequency
            pce_data = _self.fred_client.get_series('PCE', periods=periods, frequency='M')
            pce_data.columns = ['Date', 'PCE']
            
            # Calculate year-over-year and month-over-month percentage changes
            pce_data['PCE_YoY'] = calculate_pct_change(pce_data, 'PCE', periods=12, fill_method=None)
            pce_data['PCE_MoM'] = calculate_pct_change(pce_data, 'PCE', periods=1, fill_method=None)
            
            # Get recent MoM values for trend analysis
            recent_pce_mom = pce_data['PCE_MoM'].tail(4).values
            
            # Check for consecutive increases and decreases
            pce_increasing = check_consecutive_increase(recent_pce_mom, 3)
            pce_decreasing = check_consecutive_decrease(recent_pce_mom, 3)
            
            # Get current PCE values
            current_pce = pce_data['PCE_YoY'].iloc[-1]
            current_pce_mom = pce_data['PCE_MoM'].iloc[-1]
            
            return {
                'data': pce_data,
                'recent_pce_mom': recent_pce_mom,
                'pce_increasing': pce_increasing,
                'pce_decreasing': pce_decreasing,
                'current_pce': current_pce,
                'current_pce_mom': current_pce_mom
            }
        except Exception as e:
            logger.error(f"Failed to fetch or process PCE data: {e}")
            raise
    
    @st.cache_data(ttl=3600*24) # Cache for 24 hours
    def get_core_cpi(_self, periods=24):
        """
        Get Core CPI (Consumer Price Index Less Food and Energy) data.
        
        Args:
            periods (int, optional): Number of periods to fetch
            
        Returns:
            dict: Dictionary with CPI data and analysis
        """
        try:
            # Fetch Core CPI data with monthly frequency
            core_cpi_data = _self.fred_client.get_series('CPILFESL', periods=periods, frequency='M')
            core_cpi_data.columns = ['Date', 'CPI']
            
            # Calculate year-over-year and month-over-month percentage changes
            core_cpi_data['CPI_YoY'] = calculate_pct_change(core_cpi_data, 'CPI', periods=12, fill_method=None)
            core_cpi_data['CPI_MoM'] = calculate_pct_change(core_cpi_data, 'CPI', periods=1, fill_method=None)
            
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
        except Exception as e:
            logger.error(f"Failed to fetch or process CPI data: {e}")
            raise
    
    @st.cache_data(ttl=3600*24) # Cache for 24 hours
    def get_hours_worked(_self, periods=24):
        """
        Get Average Weekly Hours data.
        
        Args:
            periods (int, optional): Number of periods to fetch
            
        Returns:
            dict: Dictionary with hours worked data and analysis
        """
        try:
            # Fetch Hours Worked data with monthly frequency
            hours_data = _self.fred_client.get_series('AWHAETP', periods=periods, frequency='M')
            hours_data.columns = ['Date', 'Hours']
            
            # Get recent hours for analysis
            recent_hours = hours_data['Hours'].tail(4).values
            
            # Count consecutive declines and increases
            consecutive_declines = count_consecutive_changes(recent_hours, decreasing=True)
            consecutive_increases = count_consecutive_changes(recent_hours, decreasing=False)
            
            return {
                'data': hours_data,
                'recent_hours': recent_hours,
                'consecutive_declines': consecutive_declines,
                'consecutive_increases': consecutive_increases
            }
        except Exception as e:
            logger.error(f"Failed to fetch or process Aggregate Hours data: {e}")
            raise
    
    @st.cache_data(ttl=3600*24) # Cache for 24 hours
    def calculate_pmi_proxy(_self, periods=36, start_date=None):
        """
        Calculate a proxy for the ISM Manufacturing PMI using FRED data.
        
        Args:
            periods (int, optional): Number of periods to fetch if start_date is not provided
            start_date (str, optional): Start date for data in format 'YYYY-MM-DD'
            
        Returns:
            dict: Dictionary with PMI proxy data and analysis
        """
        try:
            # Define FRED series IDs for proxy variables with additional validation
            series_ids = {
                'new_orders': 'AMTMNO',      # Manufacturing: New Orders
                'production': 'IPMAN',       # Industrial Production: Manufacturing
                'employment': 'MANEMP',      # Manufacturing Employment
                'supplier_deliveries': 'AMDMUS',  # Manufacturing: Supplier Deliveries
                'inventories': 'MNFCTRIMSA'  # Manufacturing Inventories (Seasonally Adjusted)
            }
            
            # Define PMI component weights
            weights = {
                'new_orders': 0.30,
                'production': 0.25,
                'employment': 0.20,
                'supplier_deliveries': 0.15,
                'inventories': 0.10
            }
            
            # Get all series in one batch request
            all_series = _self.fred_client.get_multiple_series(
                list(series_ids.values()),
                start_date=start_date,
                periods=periods if start_date is None else None,
                frequency='M'
            )
            
            # Rename columns to component names
            rename_map = {v: k for k, v in series_ids.items()}
            all_series.rename(columns=rename_map, inplace=True)
            
            # Check which components are available in the data
            available_components = []
            missing_components = []
            for component in series_ids.keys():
                if component in all_series.columns:
                    available_components.append(component)
                else:
                    missing_components.append(component)
            
            if missing_components:
                logger.warning(f"\nMissing PMI components: {', '.join(missing_components)}")
                
            if not available_components:
                raise ValueError("No PMI components available in the data")
            
            # Adjust weights to use only available components
            adjusted_weights = {}
            weight_sum = sum(weights[c] for c in available_components)
            for component in available_components:
                adjusted_weights[component] = weights[component] / weight_sum
            
            # Keep only the available component columns and Date
            df = all_series[['Date'] + available_components].copy()
            
            # Ensure monthly frequency
            df.set_index('Date', inplace=True)
            df = df.resample('M').last()
            
            # Calculate month-over-month percentage change
            df_pct_change = df[available_components].ffill().pct_change(fill_method=None) * 100  # Convert to percentage
            
            # Calculate standard deviation for each series over 10 years (120 months)
            # Use a more robust method to handle limited data
            def robust_rolling_std(series, window=120, min_periods=24):
                """
                Calculate rolling standard deviation with fallback to shorter windows
                
                Args:
                    series (pd.Series): Input series
                    window (int): Preferred rolling window
                    min_periods (int): Minimum periods required for calculation
                
                Returns:
                    pd.Series: Rolling standard deviation with fallback
                """
                # First try the full window
                std_series = series.rolling(window=window, min_periods=min_periods).std()
                
                # If all values are NaN, use a shorter window
                if std_series.isna().all():
                    logger.warning(f"Could not calculate std dev for {window}-month window. Falling back to shorter window.")
                    std_series = series.rolling(window=min_periods, min_periods=min_periods).std()
                
                # If still NaN, use the overall standard deviation
                if std_series.isna().all():
                    logger.warning(f"Could not calculate rolling std dev. Using overall standard deviation.")
                    overall_std = series.std()
                    std_series = pd.Series([overall_std] * len(series), index=series.index)
                
                # Fill NaNs with the last valid value
                std_series = std_series.ffill()
                
                return std_series

            # Calculate standard deviation using the robust method
            std_dev = pd.DataFrame(index=df_pct_change.index, columns=available_components)
            for component in available_components:
                std_dev[component] = robust_rolling_std(df_pct_change[component])
            
            # Update to_diffusion_index function to handle more edge cases
            def to_diffusion_index(pct_change, std_dev):
                # More robust handling of standard deviation
                if pd.isna(std_dev) or std_dev <= 0:
                    logger.warning(f"Invalid standard deviation: {std_dev}. Using default.")
                    return 50.0
                
                # Prevent extreme values by capping the scaling factor
                scaled_change = max(min(pct_change / std_dev, 3), -3)
                result = 50 + (scaled_change * 10)
                return max(0, min(100, result))
            
            # Transform to Diffusion Indices
            df_diffusion = pd.DataFrame(index=df.index, columns=available_components)
            for component in available_components:
                component_std = std_dev[component].iloc[-1]
                df_diffusion[component] = df_pct_change[component].apply(
                    lambda x, sd=component_std: to_diffusion_index(x, sd)
                )
            
            # Calculate the approximated PMI as a weighted average
            df['approximated_pmi'] = (df_diffusion * pd.Series(adjusted_weights)).sum(axis=1)
            
            # Get current PMI and check if it's below 50
            current_pmi = df['approximated_pmi'].iloc[-1]
            pmi_below_50 = current_pmi < 50
            
            # Get the PMI series with DatetimeIndex before resetting index
            pmi_series = df['approximated_pmi'].copy()
            
            # Reset index to get Date as a column for other operations
            df.reset_index(inplace=True)
            
        except Exception as e:
            logger.error(f"Failed to fetch or process PMI component data: {e}")
            raise
        
        return {
            'latest_pmi': current_pmi,
            'pmi_series': pmi_series,  # Series with DatetimeIndex
            'pmi_below_50': pmi_below_50,
            'component_values': df_diffusion,  # Add component values back
            'component_weights': adjusted_weights # Add weights back
        }
    
    @st.cache_data(ttl=3600*24) # Cache for 24 hours
    def get_usd_liquidity(_self, periods=36):
        """
        Get USD Liquidity data and S&P 500 data (both weekly).
        
        Args:
            periods (int, optional): Number of *months* of history to fetch (converted to weeks).
            
        Returns:
            dict: Dictionary containing weekly liquidity and S&P 500 data, and analysis.
        """
        try:
            # Convert periods (months) to approximate weeks
            num_weeks = periods * 4 + 4 # Add a buffer
            
            # --- Fetch Weekly Liquidity Components & SP500 --- 
            series_ids = ['WALCL', 'RRPONTTLD', 'WTREGEN', 'SP500']
            
            all_series = _self.fred_client.get_multiple_series(
                series_ids,
                periods=num_weeks, # Use calculated weeks
                frequency='W' # Explicitly Weekly
            )

            if all_series is None or all_series.empty or 'Date' not in all_series.columns:
                logger.error("Failed to fetch valid weekly data for USD Liquidity/SP500 calculation.")
                raise ValueError("Failed to fetch necessary weekly data.")
            
            all_series = all_series.sort_values('Date').reset_index(drop=True)
            all_series['Date'] = pd.to_datetime(all_series['Date']) # Ensure Date is datetime

            # === DEBUG: Log raw TGA data ===
            if 'WTREGEN' in all_series.columns:
                logger.debug(f"Raw WTREGEN tail:\n{all_series[['Date', 'WTREGEN']].tail()}")
            else:
                logger.debug("WTREGEN column not found in fetched data.")
            # ================================
            
            # --- Calculate Weekly USD Liquidity --- 
            if 'WALCL' in all_series.columns:
                all_series['USD_Liquidity'] = all_series['WALCL']
                
                if 'RRPONTTLD' in all_series.columns:
                    all_series['RRPONTTLD'] = all_series['RRPONTTLD'].fillna(0)
                    all_series['USD_Liquidity'] -= all_series['RRPONTTLD'] * 1000
                
                if 'WTREGEN' in all_series.columns:
                    all_series['WTREGEN'] = all_series['WTREGEN'].fillna(0)
                    all_series['USD_Liquidity'] -= all_series['WTREGEN'] * 1000
                
                # Calculate Week-over-Week (WoW) % change
                all_series['USD_Liquidity_WoW'] = all_series['USD_Liquidity'].pct_change(fill_method=None) * 100
                
                # Determine trend based on recent WoW changes (e.g., last 4 weeks)
                recent_wow = all_series['USD_Liquidity_WoW'].tail(4)
                avg_recent_wow = recent_wow.mean()
                liquidity_increasing = avg_recent_wow > 0.05 # Adjusted threshold for weekly
                liquidity_decreasing = avg_recent_wow < -0.05 # Adjusted threshold for weekly
                
                # Find the last valid values for the components
                last_valid_walcl = all_series['WALCL'].dropna().iloc[-1] if not all_series['WALCL'].dropna().empty else 0
                last_valid_rrp = all_series['RRPONTTLD'].dropna().iloc[-1] if not all_series['RRPONTTLD'].dropna().empty else 0
                last_valid_tga = all_series['WTREGEN'].dropna().iloc[-1] if not all_series['WTREGEN'].dropna().empty else 0
                
                # === DEBUG: Log last valid TGA ===
                logger.debug(f"Last valid TGA determined: {last_valid_tga}")
                # ================================
                
                # Calculate current liquidity based on last valid points
                current_liquidity_calc = last_valid_walcl - (last_valid_rrp * 1000) - (last_valid_tga * 1000)
                
                latest_data = all_series.iloc[-1]
                
                details = {
                    'WALCL': last_valid_walcl,
                    'RRPONTTLD': last_valid_rrp,
                    'WTREGEN': last_valid_tga
                }
                
                # Get the most recent WoW % change (can be NaN if latest liquidity is NaN)
                current_liquidity_wow = latest_data.get('USD_Liquidity_WoW', 'N/A')
                
                # Prepare weekly data for return
                weekly_data = all_series[['Date', 'USD_Liquidity', 'USD_Liquidity_WoW', 'SP500']].dropna(subset=['USD_Liquidity']).copy()
                sp500_weekly_data = all_series[['Date', 'SP500']].dropna().copy() # Separate SP500 for clarity if needed later

            else:
                logger.error("Cannot calculate USD Liquidity: WALCL is required but not available")
                raise ValueError("Failed to calculate USD Liquidity")
                
            # --- Combine Results --- 
            return {
                'weekly_data': weekly_data, # Contains both liquidity and SP500
                # 'sp500_weekly': sp500_weekly_data, # Could return separately if needed
                'recent_liquidity': all_series['USD_Liquidity'].tail(4).tolist(),
                'recent_liquidity_wow': all_series['USD_Liquidity_WoW'].tail(4).tolist(),
                'liquidity_increasing': liquidity_increasing,
                'liquidity_decreasing': liquidity_decreasing,
                'current_liquidity': current_liquidity_calc, # Use the calculated value from last valid points
                'current_liquidity_wow': current_liquidity_wow,
                'details': details
            }

        except ValueError as ve: # Catch specific value error from calculation
            logger.error(f"Calculation error for USD Liquidity: {ve}")
            raise # Re-raise calculation errors
        except Exception as e: # Catch other potential errors (API, processing)
            logger.error(f"Error fetching or processing weekly USD Liquidity or SP500 data: {e}")
            raise
    
    @st.cache_data(ttl=3600*24) # Cache for 24 hours
    def get_new_orders(_self, periods=24):
        """
        Get Non-Defense Durable Goods Orders data from FRED.
        
        Args:
            periods (int, optional): Number of periods to fetch
            
        Returns:
            dict: Dictionary with New Orders data and analysis
        """
        try:
            # Fetch New Orders data with monthly frequency
            new_orders_data = _self.fred_client.get_series('NEWORDER', periods=periods, frequency='M')
            new_orders_data.columns = ['Date', 'NEWORDER']
            
            # Calculate month-over-month percentage change
            new_orders_data['NEWORDER_MoM'] = calculate_pct_change(new_orders_data, 'NEWORDER', periods=1, fill_method=None)
            
            # Get the most recent values for analysis
            recent_values = new_orders_data['NEWORDER'].tail(4).values
            recent_mom_values = new_orders_data['NEWORDER_MoM'].tail(4).values
            
            # Check if MoM values have been increasing or decreasing consistently
            mom_increasing = check_consecutive_increase(recent_mom_values, 3)
            mom_decreasing = check_consecutive_decrease(recent_mom_values, 3)
            
            # Check if latest value is positive or negative
            latest_value = new_orders_data['NEWORDER_MoM'].iloc[-1]
            is_positive = latest_value > 0
            
            return {
                'data': new_orders_data,
                'recent_values': recent_values,
                'recent_mom_values': recent_mom_values,
                'mom_increasing': mom_increasing, 
                'mom_decreasing': mom_decreasing,
                'is_positive': is_positive,
                'latest_value': latest_value
            }
        except Exception as e:
            logger.error(f"Error fetching Non-Defense Durable Goods Orders data: {str(e)}")
            raise
    
    @st.cache_data(ttl=3600*24) # Cache for 24 hours
    def get_yield_curve(_self, periods=36, frequency='M'):
        """
        Get the 10Y-2Y Treasury Yield Spread data from FRED.
        
        Args:
            periods (int, optional): Number of periods to fetch
            frequency (str, optional): Frequency of data - 'D' for daily, 'M' for monthly
            
        Returns:
            dict: Dictionary with yield curve data and analysis
        """
        try:
            # Fetch yield curve spread data with specified frequency
            # For monthly data, we need more periods to get the same time span
            observation_period = periods
            if frequency == 'D':
                # For daily data, fetch ~3 years (756 trading days)
                observation_period = 756
            
            yield_curve_data = _self.fred_client.get_series('T10Y2Y', periods=observation_period, frequency=frequency)
            yield_curve_data.columns = ['Date', 'T10Y2Y']
            
            # If daily data but we want monthly for display, aggregate to monthly
            if frequency == 'D' and periods <= 60:  # Only aggregate if we're looking at a reasonable timeframe
                # Convert Date to datetime
                yield_curve_data['Date'] = pd.to_datetime(yield_curve_data['Date'])
                
                # Create a year-month column for grouping
                yield_curve_data['YearMonth'] = yield_curve_data['Date'].dt.to_period('M')
                
                # Group by year-month and get last day of each month (or avg)
                monthly_data = yield_curve_data.groupby('YearMonth').agg({
                    'Date': 'last',  # Last day of month
                    'T10Y2Y': 'mean'  # Average for the month
                }).reset_index()
                
                # Drop the YearMonth column
                monthly_data = monthly_data.drop('YearMonth', axis=1)
                
                # Limit to the specified number of periods
                yield_curve_data = monthly_data.tail(periods)
            
            # Get the most recent values for analysis
            recent_values = yield_curve_data['T10Y2Y'].tail(4).values
            
            # Check if values have been consistently changing
            spread_increasing = check_consecutive_increase(recent_values, 3)
            spread_decreasing = check_consecutive_decrease(recent_values, 3)
            
            # Get latest value
            latest_value = yield_curve_data['T10Y2Y'].iloc[-1]
            is_inverted = latest_value < 0
            
            return {
                'data': yield_curve_data,
                'recent_values': recent_values,
                'spread_increasing': spread_increasing,
                'spread_decreasing': spread_decreasing,
                'is_inverted': is_inverted,
                'latest_value': latest_value
            }
        except Exception as e:
            logger.error(f"Error fetching Yield Curve Spread data: {str(e)}")
            raise
    
    def get_all_indicators(self):
        """
        Get all economic indicators and their analysis.
        
        Returns:
            dict: Dictionary with all indicators
        """
        claims_data = self.get_initial_claims()
        pce_data = self.get_pce()
        core_cpi_data = self.get_core_cpi()
        hours_data = self.get_hours_worked()
        pmi_data = self.calculate_pmi_proxy(periods=36)
        usd_liquidity_data = self.get_usd_liquidity()
        new_orders_data = self.get_new_orders()
        yield_curve_data = self.get_yield_curve()
        
        return {
            'claims': claims_data,
            'pce': pce_data,
            'core_cpi': core_cpi_data,
            'hours_worked': hours_data,
            'pmi': pmi_data,
            'usd_liquidity': usd_liquidity_data,
            'new_orders': new_orders_data,
            'yield_curve': yield_curve_data
        }
