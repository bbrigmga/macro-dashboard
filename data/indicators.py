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
            recent_claims = claims_data['Claims'].tail(5).values
            
            # Get the corresponding dates for the recent values
            recent_dates = claims_data['Date'].tail(5).values
            
            # Check for consecutive increases and decreases (4 consecutive weeks)
            claims_increasing = check_consecutive_increase(recent_claims, 4)
            claims_decreasing = check_consecutive_decrease(recent_claims, 4)
            
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
            recent_pce_mom = pce_data['PCE_MoM'].tail(5).values
            
            # Get the corresponding dates for the recent values
            recent_dates = pce_data['Date'].tail(5).values
            
            # Check for consecutive increases and decreases (4 consecutive months)
            pce_increasing = check_consecutive_increase(recent_pce_mom, 4)
            pce_decreasing = check_consecutive_decrease(recent_pce_mom, 4)
            
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
            
            # Get the last 5 months of MoM changes (to check for 4 consecutive changes)
            recent_cpi_mom = core_cpi_data['CPI_MoM'].tail(5).values
            
            # Get the corresponding dates for the recent values
            recent_dates = core_cpi_data['Date'].tail(5).values
            
            # Check if MoM changes have been consistently increasing or decreasing (4 consecutive months)
            cpi_increasing = check_consecutive_increase(recent_cpi_mom, 4)
            cpi_decreasing = check_consecutive_decrease(recent_cpi_mom, 4)
            
            return {
                'data': core_cpi_data,
                'recent_cpi_mom': recent_cpi_mom,
                'cpi_increasing': cpi_increasing,
                'cpi_decreasing': cpi_decreasing,
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
            # Fetch WALCL and RRPONTTLD together
            series_ids = ['WALCL', 'RRPONTTLD']
            
            all_series = _self.fred_client.get_multiple_series(
                series_ids,
                periods=num_weeks, # Use calculated weeks
                frequency='W' # Explicitly Weekly
            )
            
            # Fetch WTREGEN data separately to ensure we get the latest value
            # This is a critical component of the USD Liquidity calculation
            wtregen_fetched = False
            wtregen_latest_value = None
            
            try:
                # First try to get the latest value directly
                wtregen_info = _self.fred_client.fred.get_series_info('WTREGEN')
                if wtregen_info is not None:
                    logger.info(f"Got WTREGEN series info: Last updated {wtregen_info.get('last_updated', 'unknown')}")
                
                # Now fetch the actual data series
                wtregen_data = _self.fred_client.get_series('WTREGEN', periods=num_weeks, frequency='W')
                
                if not wtregen_data.empty:
                    logger.info(f"Successfully fetched WTREGEN data with {len(wtregen_data)} rows")
                    
                    # Get the latest value from the data
                    if len(wtregen_data) > 0:
                        wtregen_latest_value = wtregen_data.iloc[-1, 1]  # Get the value from the last row
                        latest_date = wtregen_data.iloc[-1, 0]  # Get the date from the last row
                        logger.info(f"Latest WTREGEN value from API: {wtregen_latest_value} billion as of {latest_date}")
                    
                    # Add to all_series
                    all_series = pd.merge(all_series, wtregen_data, on='Date', how='left')
                    wtregen_fetched = True
            except Exception as e:
                logger.error(f"Error fetching WTREGEN data: {str(e)}")
                wtregen_fetched = False

            if all_series is None or all_series.empty or 'Date' not in all_series.columns:
                logger.error("Failed to fetch valid weekly data for USD Liquidity calculation.")
                raise ValueError("Failed to fetch necessary weekly data.")
            
            all_series = all_series.sort_values('Date').reset_index(drop=True)
            all_series['Date'] = pd.to_datetime(all_series['Date']) # Ensure Date is datetime

            # This section is now handled above with better error handling
            
            # Fetch S&P 500 data separately to ensure we get it even if other data fails
            sp500_data = None
            try:
                sp500_data = _self.fred_client.get_series('SP500', periods=num_weeks, frequency='W')
                if not sp500_data.empty:
                    sp500_data.columns = ['Date', 'SP500']
                    # Also merge into all_series for convenience
                    all_series = pd.merge(all_series, sp500_data, on='Date', how='left')
            except Exception as e:
                logger.warning(f"Failed to fetch S&P 500 data: {e}")
                # Create empty DataFrame with same structure for SP500 if fetch failed
                sp500_data = pd.DataFrame(columns=['Date', 'SP500'])
            
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
                
                # Find the last valid values for the components
                last_valid_walcl = all_series['WALCL'].dropna().iloc[-1] if not all_series['WALCL'].dropna().empty else 0
                last_valid_rrp = all_series['RRPONTTLD'].dropna().iloc[-1] if not all_series['RRPONTTLD'].dropna().empty else 0
                
                # Always prioritize the latest value we got directly from the API
                if wtregen_latest_value is not None:
                    # Use the latest value we got directly
                    last_valid_tga = wtregen_latest_value
                    logger.info(f"Using latest TGA value from API: {last_valid_tga} billion")
                # Fallback to data in the DataFrame if available
                elif 'WTREGEN' in all_series.columns and not all_series['WTREGEN'].dropna().empty:
                    # Use the last valid value from the data
                    last_valid_tga = all_series['WTREGEN'].dropna().iloc[-1]
                    logger.info(f"Using TGA value from merged data: {last_valid_tga} billion")
                else:
                    # Fallback to a known recent value if API fails
                    last_valid_tga = 595.741  # Example value from FRED as of 2025-04-30
                    logger.warning(f"WTREGEN data not available from API, using fallback value: {last_valid_tga} billion")
                
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
                if 'SP500' in all_series.columns:
                    weekly_data = all_series[['Date', 'USD_Liquidity', 'USD_Liquidity_WoW', 'SP500']].dropna(subset=['USD_Liquidity']).copy()
                else:
                    # Handle case where SP500 data is not available in all_series
                    weekly_data = all_series[['Date', 'USD_Liquidity', 'USD_Liquidity_WoW']].dropna(subset=['USD_Liquidity']).copy()
                
                # Determine if liquidity is increasing or decreasing
                if len(weekly_data) >= 4:
                    recent_liquidity = weekly_data['USD_Liquidity'].tail(4).values
                    liquidity_increasing = recent_liquidity[-1] > recent_liquidity[-2] > recent_liquidity[-3]
                    liquidity_decreasing = recent_liquidity[-1] < recent_liquidity[-2] < recent_liquidity[-3]
                else:
                    liquidity_increasing = False
                    liquidity_decreasing = False
            
            else:
                logger.error("Cannot calculate USD Liquidity: WALCL is required but not available")
                raise ValueError("Failed to calculate USD Liquidity")
            
            return {
                'weekly_data': weekly_data,
                'sp500_data': sp500_data,
                'current_liquidity': current_liquidity_calc,
                'current_liquidity_wow': current_liquidity_wow,
                'liquidity_increasing': liquidity_increasing,
                'liquidity_decreasing': liquidity_decreasing,
                'details': details
            }
            
        except Exception as e:
            logger.error(f"Error fetching USD Liquidity data: {str(e)}")
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

            # Get latest value
            latest_value = yield_curve_data['T10Y2Y'].iloc[-1]
            is_inverted = latest_value < 0

            return {
                'data': yield_curve_data,
                'is_inverted': is_inverted,
                'latest_value': latest_value
            }
        except Exception as e:
            logger.error(f"Error fetching Yield Curve Spread data: {str(e)}")
            raise

    @st.cache_data(ttl=3600*24) # Cache for 24 hours
    def get_copper_gold_ratio(_self, periods=365):
        """
        Get Copper/Gold Ratio vs US 10-year Treasury yield data.

        Args:
            periods (int, optional): Number of days of historical data to fetch

        Returns:
            dict: Dictionary with merged data and analysis
        """
        try:
            from data.yahoo_client import YahooClient

            # Initialize Yahoo client for commodity data
            yahoo_client = YahooClient()

            # Fetch Copper data using HG=F ticker only
            copper_df = None
            try:
                copper_df = yahoo_client.get_historical_prices(ticker='HG=F', periods=periods, frequency='1d')
                copper_df = copper_df.rename(columns={'value': 'copper'})
                logger.info("Successfully fetched copper data using HG=F ticker")
            except Exception as e:
                logger.error(f"Failed to fetch copper data with HG=F ticker: {e}")
                raise ValueError("Unable to fetch copper data from HG=F")

            # Fetch Gold COMEX data using GC=F ticker only
            gold_df = None
            try:
                gold_df = yahoo_client.get_historical_prices(ticker='GC=F', periods=periods, frequency='1d')
                gold_df = gold_df.rename(columns={'value': 'gold'})
                logger.info("Successfully fetched gold data using GC=F ticker")
            except Exception as e:
                logger.error(f"Failed to fetch gold data with GC=F ticker: {e}")
                raise ValueError("Unable to fetch gold data from GC=F")

            # Fetch US 10-year Treasury yield data
            try:
                yield_df = _self.fred_client.get_series('DGS10', periods=periods, frequency='D')
                yield_df.columns = ['Date', 'yield']
                logger.info("Successfully fetched treasury yield data")
            except Exception as e:
                logger.warning(f"Failed to fetch treasury yield data: {e}")
                # Create empty yield data as fallback
                yield_df = pd.DataFrame(columns=['Date', 'yield'])

            # Normalize Date columns to remove timezone info for merging
            copper_df['Date'] = pd.to_datetime(copper_df['Date']).dt.tz_localize(None)
            gold_df['Date'] = pd.to_datetime(gold_df['Date']).dt.tz_localize(None)
            if not yield_df.empty:
                yield_df['Date'] = pd.to_datetime(yield_df['Date']).dt.tz_localize(None)

            # Merge Copper and Gold data first
            merged_df = pd.merge(copper_df, gold_df, on='Date', how='outer')

            # Handle missing data: forward-fill, then drop any remaining NaNs
            merged_df = merged_df.sort_values('Date').ffill().dropna()

            # Compute Copper/Gold ratio
            merged_df['ratio'] = merged_df['copper'] / merged_df['gold']

            # Merge with yield data (if available)
            if not yield_df.empty:
                final_df = pd.merge(merged_df[['Date', 'ratio']], yield_df[['Date', 'yield']], on='Date', how='inner')
            else:
                final_df = merged_df[['Date', 'ratio']].copy()
                final_df['yield'] = None

            # Sort by date
            final_df = final_df.sort_values('Date')

            # Get latest values
            latest_ratio = final_df['ratio'].iloc[-1]
            latest_yield = final_df['yield'].iloc[-1] if 'yield' in final_df.columns and final_df['yield'].iloc[-1] is not None else 'N/A'

            return {
                'data': final_df,
                'latest_ratio': latest_ratio,
                'latest_yield': latest_yield
            }
        except Exception as e:
            logger.error(f"Error fetching Copper/Gold Ratio data: {str(e)}")
            # Return empty data structure instead of raising exception
            return {
                'data': pd.DataFrame(columns=['Date', 'ratio', 'yield']),
                'latest_ratio': 'N/A',
                'latest_yield': 'N/A'
            }
    
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
