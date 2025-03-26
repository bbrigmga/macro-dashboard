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
        
        # Create sample component values for the latest data point
        walcl_value = 8500000  # 8.5 trillion in millions
        rrponttld_value = 2000  # 2 trillion in billions
        wtregen_value = 700  # 700 billion
        
        return {
            'data': df,
            'recent_liquidity': df['USD_Liquidity'].tail(4).values,
            'recent_liquidity_mom': df['USD_Liquidity_MoM'].tail(4).values,
            'liquidity_increasing': False,
            'liquidity_decreasing': False,
            'current_liquidity': df['USD_Liquidity'].iloc[-1],
            'current_liquidity_mom': df['USD_Liquidity_MoM'].iloc[-1],
            'details': {
                'WALCL': walcl_value,
                'RRPONTTLD': rrponttld_value,
                'WTREGEN': wtregen_value
            }
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
            pce_data = self.fred_client.get_series('PCE', periods=periods, frequency='M')
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
        logger.info("\n" + "="*80)
        logger.info("Starting PMI Proxy Calculation")
        logger.info("="*80)
        
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
        
        try:
            # Log the series IDs being requested
            logger.info("\nRequesting PMI proxy series:")
            logger.info(f"Series IDs: {list(series_ids.values())}")
            logger.info(f"Periods: {periods}")
            logger.info(f"Start Date: {start_date}")
            
            # Validate FRED series before fetching
            logger.info("\nValidating FRED series:")
            for component, series_id in series_ids.items():
                try:
                    # Check if series exists and has recent data
                    series_info = self.fred_client.fred.get_series_info(series_id)
                    logger.info(f"\nSeries {series_id} ({component}) info:")
                    for key, value in series_info.items():
                        logger.info(f"  {key}: {value}")
                except Exception as series_check_error:
                    logger.error(f"Error checking series {series_id} ({component}): {str(series_check_error)}")
            
            # Get all series in one batch request
            logger.info("\nFetching all series data...")
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
                    # Log first few rows of each available component
                    logger.info(f"\n{component} first 5 rows:")
                    logger.info(all_series[component].head().to_string())
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
            
            # Log adjusted weights
            logger.info("\nAdjusted weights:")
            for component, weight in adjusted_weights.items():
                logger.info(f"  {component}: {weight:.3f}")
            
            # Keep only the available component columns and Date
            df = all_series[['Date'] + available_components].copy()
            
            # Ensure monthly frequency
            df.set_index('Date', inplace=True)
            df = df.resample('M').last()
            
            # Calculate month-over-month percentage change
            df_pct_change = df[available_components].ffill().pct_change() * 100  # Convert to percentage
            
            # Log percentage changes
            logger.info("\nPercentage changes first 5 rows:")
            logger.info(df_pct_change.head().to_string())
            
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
                std_series = std_series.fillna(method='ffill')
                
                return std_series

            # Calculate standard deviation using the robust method
            std_dev = pd.DataFrame(index=df_pct_change.index, columns=available_components)
            for component in available_components:
                std_dev[component] = robust_rolling_std(df_pct_change[component])
            
            # Log standard deviations
            logger.info("\nStandard deviations first 5 rows:")
            logger.info(std_dev.head().to_string())
            
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
                logger.info(f"\nProcessing {component}:")
                logger.info(f"  Using standard deviation: {component_std}")
                df_diffusion[component] = df_pct_change[component].apply(
                    lambda x, sd=component_std: to_diffusion_index(x, sd)
                )
            
            # Log diffusion indices
            logger.info("\nDiffusion indices first 5 rows:")
            logger.info(df_diffusion.head().to_string())
            
            # Calculate the approximated PMI as a weighted average
            df['approximated_pmi'] = (df_diffusion * pd.Series(adjusted_weights)).sum(axis=1)
            
            # Log final PMI values
            logger.info("\nApproximated PMI first 5 rows:")
            logger.info(df['approximated_pmi'].head().to_string())
            
            # Store component values for the latest month
            component_values = {}
            for component in available_components:
                component_values[component] = df_diffusion[component].iloc[-1]
            
            # Log component values
            logger.info("\nFinal component values:")
            for component, value in component_values.items():
                logger.info(f"  {component}: {value:.2f}")
            
            # For missing components, use a neutral value of 50
            for component in missing_components:
                component_values[component] = 50.0
            
            # Get current PMI and check if it's below 50
            current_pmi = df['approximated_pmi'].iloc[-1]
            pmi_below_50 = current_pmi < 50
            
            # Log final PMI details
            logger.info("\nFinal PMI Results:")
            logger.info(f"  Current PMI: {current_pmi:.2f}")
            logger.info(f"  PMI Below 50: {pmi_below_50}")
            logger.info("="*80 + "\n")
            
            # Extract the PMI series with DatetimeIndex before resetting index
            pmi_series = df['approximated_pmi'].copy()
            
            # Reset index to get Date as a column for other operations
            df.reset_index(inplace=True)
            
        except Exception as e:
            logger.error("\nComprehensive error calculating PMI proxy:")
            logger.error(str(e))
            # Include full traceback for debugging
            import traceback
            logger.error(traceback.format_exc())
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
            logger.info(f"Current date: {datetime.datetime.now().strftime('%Y-%m-%d')}")
            
            # Try fetching each series individually with detailed error handling
            individual_series = {}
            for series_id in series_ids:
                try:
                    # Use 'd' (daily) frequency to get the most recent data available
                    # and then we'll convert to monthly in the processing step
                    series_data = self.fred_client.get_series(series_id, periods=periods*30, frequency='d')
                    
                    # Log the raw data received from FRED API
                    logger.info(f"Raw data for {series_id}:")
                    if not series_data.empty:
                        logger.info(f"Date range: {series_data['Date'].min()} to {series_data['Date'].max()}")
                        logger.info(f"Number of data points: {len(series_data)}")
                        # Log the last 5 data points to see the most recent values
                        logger.info(f"Last 5 data points for {series_id}:")
                        for idx, row in series_data.tail(5).iterrows():
                            logger.info(f"  {row['Date']}: {row[series_id]}")
                    
                    individual_series[series_id] = series_data
                    logger.info(f"Successfully fetched {series_id}: {series_data.shape[0]} rows")
                    
                    # Log the most recent value for each series
                    if not series_data.empty:
                        latest_date = series_data['Date'].iloc[-1]
                        latest_value = series_data[series_id].iloc[-1]
                        logger.info(f"Latest {series_id} value ({latest_date}): {latest_value}")
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
                # Use 'last' to get the most recent value in each month
                series_data_copy = series_data_copy.resample('M').last()
                
                # Forward fill missing values
                series_data_copy = series_data_copy.ffill()
                
                # Reset index to get Date as a column
                series_data_copy.reset_index(inplace=True)
                
                # Log the resampled data
                logger.info(f"Resampled monthly data for {series_id}:")
                if not series_data_copy.empty:
                    logger.info(f"Date range: {series_data_copy['Date'].min()} to {series_data_copy['Date'].max()}")
                    logger.info(f"Number of data points: {len(series_data_copy)}")
                    # Log the last 5 data points to see the most recent values
                    logger.info(f"Last 5 monthly data points for {series_id}:")
                    for idx, row in series_data_copy.tail(5).iterrows():
                        logger.info(f"  {row['Date'].strftime('%Y-%m-%d')}: {row[series_id]}")
                
                if all_series is None:
                    all_series = series_data_copy
                else:
                    all_series = pd.merge(all_series, series_data_copy, on='Date', how='outer')
            
            # If no series were fetched, return sample data
            if all_series is None:
                logger.error("No series were successfully fetched.")
                return generate_sample_data('liquidity', periods, frequency='M')
            
            # Sort by date to ensure the latest data is at the end
            all_series = all_series.sort_values('Date')
            
            # Check which series are available
            available_series = [s for s in series_ids if s in all_series.columns]
            missing_series = [s for s in series_ids if s not in all_series.columns]
            logger.info(f"Available series: {available_series}")
            logger.info(f"Missing series: {missing_series}")
            
            # Log the latest date in the merged dataset
            if not all_series.empty:
                latest_date = all_series['Date'].iloc[-1]
                logger.info(f"Latest date in merged dataset: {latest_date}")
                
                # Log the latest values for each series in the merged dataset
                for series_id in available_series:
                    latest_value = all_series[series_id].iloc[-1]
                    logger.info(f"Latest {series_id} value in merged dataset: {latest_value}")
            
            # Calculate USD Liquidity based on simplified formula: WALCL-RRPONTTLD-WTREGEN
            # Where:
            # WALCL (millions) - Fed Balance Sheet
            # RRPONTTLD (billions) - Reverse Repo
            # WTREGEN (billions) - Treasury General Account
            if 'WALCL' in all_series.columns:
                # Initialize USD_Liquidity with WALCL
                all_series['USD_Liquidity'] = all_series['WALCL']
                logger.info(f"Initial USD_Liquidity (WALCL): {all_series['USD_Liquidity'].iloc[-1]}")
                
                # Subtract RRPONTTLD * 1000 (convert billions to millions) if available
                if 'RRPONTTLD' in all_series.columns:
                    rrponttld_millions = all_series['RRPONTTLD'] * 1000
                    all_series['USD_Liquidity'] -= rrponttld_millions
                    logger.info(f"RRPONTTLD: {all_series['RRPONTTLD'].iloc[-1]} billion")
                    logger.info(f"RRPONTTLD in millions: {rrponttld_millions.iloc[-1]}")
                    logger.info(f"USD_Liquidity after subtracting RRPONTTLD: {all_series['USD_Liquidity'].iloc[-1]}")
                
                # Subtract WTREGEN * 1000 (convert billions to millions) if available
                if 'WTREGEN' in all_series.columns:
                    wtregen_millions = all_series['WTREGEN'] * 1000
                    all_series['USD_Liquidity'] -= wtregen_millions
                    logger.info(f"WTREGEN: {all_series['WTREGEN'].iloc[-1]} billion")
                    logger.info(f"WTREGEN in millions: {wtregen_millions.iloc[-1]}")
                    logger.info(f"USD_Liquidity after subtracting WTREGEN: {all_series['USD_Liquidity'].iloc[-1]}")
                
                # Fill NaN values in USD_Liquidity
                all_series['USD_Liquidity'] = all_series['USD_Liquidity'].ffill()
                logger.info(f"Final USD_Liquidity: {all_series['USD_Liquidity'].iloc[-1]}")
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
            
            # Extract actual values for the latest data point
            walcl = all_series['WALCL'].iloc[-1]  # Latest WALCL
            rrponttld = all_series['RRPONTTLD'].iloc[-1] if 'RRPONTTLD' in all_series.columns else 0  # Latest RRPONTTLD
            wtregen = all_series['WTREGEN'].iloc[-1] if 'WTREGEN' in all_series.columns else 0  # Latest WTREGEN
            
            # Log the final component values and calculation
            logger.info(f"Final component values for USD Liquidity calculation:")
            logger.info(f"WALCL: {walcl} million")
            logger.info(f"RRPONTTLD: {rrponttld} billion")
            logger.info(f"WTREGEN: {wtregen} billion")
            logger.info(f"USD_Liquidity = {walcl} - ({rrponttld} * 1000) - ({wtregen} * 1000) = {current_liquidity}")

            # Prepare details for the USD liquidity charts
            details = {
                'WALCL': walcl,
                'RRPONTTLD': rrponttld,
                'WTREGEN': wtregen
            }

            # Include details in the return value or chart data
            return {
                'data': all_series,
                'recent_liquidity': recent_liquidity,
                'recent_liquidity_mom': recent_liquidity_mom,
                'liquidity_increasing': liquidity_increasing,
                'liquidity_decreasing': liquidity_decreasing,
                'current_liquidity': current_liquidity,
                'current_liquidity_mom': current_liquidity_mom,
                'details': details
            }
        except Exception as e:
            logger.error(f"Error fetching USD Liquidity data: {str(e)}")
            return generate_sample_data('liquidity', periods, frequency='M')
    
    def get_new_orders(self, periods=24):
        """
        Get Non-Defense Durable Goods Orders data from FRED.
        
        Args:
            periods (int, optional): Number of periods to fetch
            
        Returns:
            dict: Dictionary with New Orders data and analysis
        """
        try:
            # Fetch New Orders data with monthly frequency
            new_orders_data = self.fred_client.get_series('NEWORDER', periods=periods, frequency='M')
            new_orders_data.columns = ['Date', 'NEWORDER']
            
            # Calculate month-over-month percentage change
            new_orders_data['NEWORDER_MoM'] = calculate_pct_change(new_orders_data, 'NEWORDER', periods=1)
            
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
            # Generate sample data as a fallback
            sample_dates = generate_sample_dates(periods, frequency='M')
            
            # Create sample orders data (random values)
            orders_values = np.random.normal(loc=60000, scale=2000, size=periods)
            
            # Create sample MoM % changes that roughly correlate with orders_values
            mom_values = np.diff(orders_values) / orders_values[:-1] * 100
            mom_values = np.insert(mom_values, 0, 0.0)  # Add a 0 for the first month
            
            sample_df = pd.DataFrame({
                'Date': sample_dates,
                'NEWORDER': orders_values,
                'NEWORDER_MoM': mom_values
            })
            
            return {
                'data': sample_df,
                'recent_values': orders_values[-4:],
                'recent_mom_values': mom_values[-4:],
                'mom_increasing': False,
                'mom_decreasing': False,
                'is_positive': mom_values[-1] > 0,
                'latest_value': mom_values[-1]
            }
            
    def get_yield_curve(self, periods=36, frequency='M'):
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
            
            yield_curve_data = self.fred_client.get_series('T10Y2Y', periods=observation_period, frequency=frequency)
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
            # Generate sample data as a fallback
            sample_dates = generate_sample_dates(periods, frequency=frequency)
            
            # Create slightly descending sample values hovering around 0
            base = np.linspace(1.5, -0.5, periods)  # Start positive, end slightly negative
            noise = np.random.normal(0, 0.2, periods)  # Add some noise
            spread_values = base + noise
            
            sample_df = pd.DataFrame({
                'Date': sample_dates,
                'T10Y2Y': spread_values
            })
            
            return {
                'data': sample_df,
                'recent_values': spread_values[-4:],
                'spread_increasing': False,
                'spread_decreasing': True,
                'is_inverted': spread_values[-1] < 0,
                'latest_value': spread_values[-1]
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
