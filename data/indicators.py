"""
Functions for fetching and processing economic indicators.
"""
import pandas as pd
import numpy as np
import datetime
import logging
from data.fred_client import FredClient
from data.processing import calculate_pct_change, check_consecutive_increase, check_consecutive_decrease, count_consecutive_changes

# Set up logging
logging.basicConfig(level=logging.INFO)
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


def generate_sample_data(indicator_type, periods, frequency='M'):
    """
    Generate sample data for when API calls fail.
    
    Args:
        indicator_type (str): Type of indicator ('claims', 'pce', 'cpi', 'hours', 'liquidity')
        periods (int): Number of periods to generate
        frequency (str, optional): Frequency of data ('D' for daily, 'W' for weekly, 'M' for monthly)
        
    Returns:
        dict: Dictionary with sample data and analysis
    """
    dates = generate_sample_dates(periods, frequency)
    
    if indicator_type == 'claims':
        # Create sample claims data (random values around 200-250k)
        values = np.random.randint(200000, 250000, size=periods)
        df = pd.DataFrame({
            'Date': dates,
            'Claims': values
        })
        
        return {
            'data': df,
            'recent_claims': df['Claims'].tail(4).values,
            'claims_increasing': False,
            'claims_decreasing': False,
            'current_value': df['Claims'].iloc[-1]
        }
        
    elif indicator_type == 'pce':
        # Create sample PCE data
        base_value = 100.0
        pce_values = []
        for i in range(periods):
            base_value *= (1 + np.random.uniform(0.001, 0.003))
            pce_values.append(base_value)
            
        df = pd.DataFrame({
            'Date': dates,
            'PCE': pce_values,
            'PCE_YoY': 2.5 + np.random.uniform(-0.5, 0.5, size=periods),  # Around 2-3%
            'PCE_MoM': 0.2 + np.random.uniform(-0.1, 0.1, size=periods)   # Around 0.1-0.3%
        })
        
        return {
            'data': df,
            'recent_pce_mom': df['PCE_MoM'].tail(4).values,
            'pce_increasing': False,
            'pce_decreasing': False,
            'current_pce': df['PCE_YoY'].iloc[-1],
            'current_pce_mom': df['PCE_MoM'].iloc[-1]
        }
        
    elif indicator_type == 'cpi':
        # Create sample CPI data
        base_value = 300.0
        cpi_values = []
        for i in range(periods):
            base_value *= (1 + np.random.uniform(0.002, 0.004))
            cpi_values.append(base_value)
            
        df = pd.DataFrame({
            'Date': dates,
            'CPI': cpi_values,
            'CPI_YoY': 3.5 + np.random.uniform(-0.5, 0.5, size=periods),  # Around 3-4%
            'CPI_MoM': 0.3 + np.random.uniform(-0.1, 0.1, size=periods)   # Around 0.2-0.4%
        })
        
        return {
            'data': df,
            'recent_cpi_mom': df['CPI_MoM'].tail(4).values,
            'cpi_accelerating': False,
            'current_cpi': df['CPI_YoY'].iloc[-1],
            'current_cpi_mom': df['CPI_MoM'].iloc[-1]
        }
        
    elif indicator_type == 'hours':
        # Create sample hours data (random values around 34-35 hours)
        hours = 34.5 + np.random.uniform(-0.5, 0.5, size=periods)
        df = pd.DataFrame({
            'Date': dates,
            'Hours': hours
        })
        
        return {
            'data': df,
            'recent_hours': df['Hours'].tail(4).values,
            'consecutive_declines': 1,  # For demonstration
            'consecutive_increases': 2   # For demonstration
        }
        
    elif indicator_type == 'liquidity':
        # Create sample liquidity data
        base_value = 5000000  # 5 trillion in millions
        liquidity_values = []
        for i in range(periods):
            base_value += np.random.uniform(-100000, 100000)
            liquidity_values.append(base_value)
            
        df = pd.DataFrame({
            'Date': dates,
            'USD_Liquidity': liquidity_values,
            'USD_Liquidity_MoM': 0.5 + np.random.uniform(-1.0, 1.0, size=periods)
        })
        
        return {
            'data': df,
            'recent_liquidity': df['USD_Liquidity'].tail(4).values,
            'recent_liquidity_mom': df['USD_Liquidity_MoM'].tail(4).values,
            'liquidity_increasing': False,
            'liquidity_decreasing': False,
            'current_liquidity': df['USD_Liquidity'].iloc[-1],
            'current_liquidity_mom': df['USD_Liquidity_MoM'].iloc[-1]
        }
    
    elif indicator_type == 'pmi':
        # Return default PMI values
        return {
            'latest_pmi': 50.0,  # Neutral value
            'pmi_series': pd.Series([50.0]),  # Single neutral value
            'component_values': {
                'new_orders': 50.0,
                'production': 50.0,
                'employment': 50.0,
                'supplier_deliveries': 50.0,
                'inventories': 50.0
            },
            'component_weights': {
                'new_orders': 0.30,
                'production': 0.25,
                'employment': 0.20,
                'supplier_deliveries': 0.15,
                'inventories': 0.10
            },
            'pmi_below_50': False
        }
    
    else:
        logger.error(f"Unknown indicator type: {indicator_type}")
        return None


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
            periods (int, optional): Number of periods to fetch (52 weeks = 1 year)
            
        Returns:
            dict: Dictionary with claims data and analysis
        """
        try:
            # Fetch claims data with weekly frequency
            claims_data = self.fred_client.get_series('ICSA', periods=periods, frequency='W')
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
            logger.error(f"Error fetching initial claims data: {str(e)}")
            return generate_sample_data('claims', periods, frequency='W')
    
    def get_pce(self, periods=24):
        """
        Get Personal Consumption Expenditures (PCE) data.
        
        Args:
            periods (int, optional): Number of periods to fetch
            
        Returns:
            dict: Dictionary with PCE data and analysis
        """
        try:
            # Fetch PCE data with monthly frequency
            pce_data = self.fred_client.get_series('PCEPI', periods=periods, frequency='M')
            pce_data.columns = ['Date', 'PCE']
            
            # Calculate year-over-year and month-over-month percentage changes
            pce_data['PCE_YoY'] = calculate_pct_change(pce_data, 'PCE', periods=12)
            pce_data['PCE_MoM'] = calculate_pct_change(pce_data, 'PCE', periods=1)
            
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
            logger.error(f"Error fetching PCE data: {str(e)}")
            return generate_sample_data('pce', periods, frequency='M')
    
    def get_core_cpi(self, periods=24):
        """
        Get Core CPI (Consumer Price Index Less Food and Energy) data.
        
        Args:
            periods (int, optional): Number of periods to fetch
            
        Returns:
            dict: Dictionary with CPI data and analysis
        """
        try:
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
        except Exception as e:
            logger.error(f"Error fetching Core CPI data: {str(e)}")
            return generate_sample_data('cpi', periods, frequency='M')
    
    def get_hours_worked(self, periods=24):
        """
        Get Average Weekly Hours data.
        
        Args:
            periods (int, optional): Number of periods to fetch
            
        Returns:
            dict: Dictionary with hours worked data and analysis
        """
        try:
            # Fetch Hours Worked data with monthly frequency
            hours_data = self.fred_client.get_series('AWHAETP', periods=periods, frequency='M')
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
            logger.error(f"Error fetching hours worked data: {str(e)}")
            return generate_sample_data('hours', periods, frequency='M')
    
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
        
        try:
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
            
            # Check which components are available in the data
            available_components = []
            missing_components = []
            for component in series_ids.keys():
                if component in all_series.columns:
                    available_components.append(component)
                else:
                    missing_components.append(component)
            
            if missing_components:
                logger.warning(f"Missing PMI components: {', '.join(missing_components)}")
                
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
            # Only calculate pct_change on the component columns, not the DatetimeIndex
            df_pct_change = df[available_components].ffill().pct_change() * 100  # Convert to percentage
            
            # Transform to diffusion-like indices
            df_diffusion = df_pct_change.apply(lambda x: to_diffusion_index(x))
            
            # Calculate the approximated PMI as a weighted average
            df['approximated_pmi'] = (df_diffusion * pd.Series(adjusted_weights)).sum(axis=1)
            
            # Store component values for the latest month
            component_values = {}
            for component in available_components:
                component_values[component] = df_diffusion[component].iloc[-1]
            
            # For missing components, use a neutral value of 50
            for component in missing_components:
                component_values[component] = 50.0
            
            # Get current PMI and check if it's below 50
            current_pmi = df['approximated_pmi'].iloc[-1]
            pmi_below_50 = current_pmi < 50
            
            # Extract the PMI series with DatetimeIndex before resetting index
            pmi_series = df['approximated_pmi'].copy()
            
            # Reset index to get Date as a column for other operations
            df.reset_index(inplace=True)
            
        except Exception as e:
            logger.error(f"Error calculating PMI proxy: {str(e)}")
            return generate_sample_data('pmi', periods, frequency='M')
        
        return {
            'latest_pmi': current_pmi,
            'pmi_series': pmi_series,  # Series with DatetimeIndex
            'component_values': component_values,
            'component_weights': weights,
            'pmi_below_50': pmi_below_50
        }
    
    def get_usd_liquidity(self, periods=36):
        """
        Get USD Liquidity data calculated from FRED series.
        
        Args:
            periods (int, optional): Number of periods to fetch
            
        Returns:
            dict: Dictionary with USD Liquidity data and analysis
        """
        try:
            # Fetch required series with monthly frequency based on the simplified formula: WALCL-RRPONTTLD-WTREGEN
            # WALCL (millions) - Fed Balance Sheet
            # RRPONTTLD (billions) - Reverse Repo
            # WTREGEN (billions) - Treasury General Account
            # SP500 (S&P 500 Index) - for comparison
            series_ids = ['WALCL', 'RRPONTTLD', 'WTREGEN', 'SP500']
            
            logger.info(f"Fetching USD Liquidity data for series: {series_ids}")
            
            # Try fetching each series individually with detailed error handling
            individual_series = {}
            for series_id in series_ids:
                try:
                    series_data = self.fred_client.get_series(series_id, periods=periods, frequency='M')
                    individual_series[series_id] = series_data
                    logger.info(f"Successfully fetched {series_id}: {series_data.shape[0]} rows")
                except Exception as e:
                    logger.error(f"Error fetching {series_id}: {str(e)}")
            
            # Merge all successfully fetched series
            all_series = None
            for series_id, series_data in individual_series.items():
                # Convert to datetime index for resampling
                series_data_copy = series_data.copy()
                series_data_copy['Date'] = pd.to_datetime(series_data_copy['Date'])
                series_data_copy.set_index('Date', inplace=True)
                
                # Resample to monthly frequency (end of month)
                series_data_copy = series_data_copy.resample('M').last()
                
                # Forward fill missing values
                series_data_copy = series_data_copy.ffill()
                
                # Reset index to get Date as a column
                series_data_copy.reset_index(inplace=True)
                
                if all_series is None:
                    all_series = series_data_copy
                else:
                    all_series = pd.merge(all_series, series_data_copy, on='Date', how='outer')
            
            # If no series were fetched, return sample data
            if all_series is None:
                logger.error("No series were successfully fetched.")
                return generate_sample_data('liquidity', periods, frequency='M')
            
            # Check which series are available
            available_series = [s for s in series_ids if s in all_series.columns]
            missing_series = [s for s in series_ids if s not in all_series.columns]
            logger.info(f"Available series: {available_series}")
            logger.info(f"Missing series: {missing_series}")
            
            # Calculate USD Liquidity based on simplified formula: WALCL-RRPONTTLD-WTREGEN
            # Where:
            # WALCL (millions) - Fed Balance Sheet
            # RRPONTTLD (billions) - Reverse Repo
            # WTREGEN (billions) - Treasury General Account
            if 'WALCL' in all_series.columns:
                # Initialize USD_Liquidity with WALCL
                all_series['USD_Liquidity'] = all_series['WALCL']
                
                # Subtract RRPONTTLD * 1000 (convert billions to millions) if available
                if 'RRPONTTLD' in all_series.columns:
                    all_series['USD_Liquidity'] -= (all_series['RRPONTTLD'] * 1000)
                
                # Subtract WTREGEN * 1000 (convert billions to millions) if available
                if 'WTREGEN' in all_series.columns:
                    all_series['USD_Liquidity'] -= (all_series['WTREGEN'] * 1000)
                
                # Fill NaN values in USD_Liquidity
                all_series['USD_Liquidity'] = all_series['USD_Liquidity'].ffill()
            else:
                logger.error("Cannot calculate USD Liquidity: WALCL is required but not available")
                return generate_sample_data('liquidity', periods, frequency='M')
            
            # Calculate month-over-month percentage changes
            all_series['USD_Liquidity_MoM'] = calculate_pct_change(all_series, 'USD_Liquidity', periods=1)
            
            # Get recent values for trend analysis
            recent_liquidity = all_series['USD_Liquidity'].tail(4).values
            recent_liquidity_mom = all_series['USD_Liquidity_MoM'].tail(4).values
            
            # Check for consecutive increases and decreases
            liquidity_increasing = check_consecutive_increase(recent_liquidity, 3)
            liquidity_decreasing = check_consecutive_decrease(recent_liquidity, 3)
            
            # Get current values
            current_liquidity = all_series['USD_Liquidity'].iloc[-1]
            current_liquidity_mom = all_series['USD_Liquidity_MoM'].iloc[-1]
            
            return {
                'data': all_series,
                'recent_liquidity': recent_liquidity,
                'recent_liquidity_mom': recent_liquidity_mom,
                'liquidity_increasing': liquidity_increasing,
                'liquidity_decreasing': liquidity_decreasing,
                'current_liquidity': current_liquidity,
                'current_liquidity_mom': current_liquidity_mom
            }
        except Exception as e:
            logger.error(f"Error fetching USD Liquidity data: {str(e)}")
            return generate_sample_data('liquidity', periods, frequency='M')
    
    def get_all_indicators(self):
        """
        Get all economic indicators and their analysis.
        
        Returns:
            dict: Dictionary with all indicator data and analysis
        """
        # Fetch all indicators
        claims_data = self.get_initial_claims()
        pce_data = self.get_pce()
        core_cpi_data = self.get_core_cpi()
        hours_data = self.get_hours_worked()
        pmi_data = self.calculate_pmi_proxy(periods=36)
        usd_liquidity_data = self.get_usd_liquidity()
        
        return {
            'claims': claims_data,
            'pce': pce_data,
            'core_cpi': core_cpi_data,
            'hours_worked': hours_data,
            'pmi': pmi_data,
            'usd_liquidity': usd_liquidity_data
        }
