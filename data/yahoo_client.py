"""
Yahoo Finance client for fetching historical price data.
"""
import yfinance as yf
import pandas as pd
import logging
from datetime import datetime, timedelta
from data.processing import convert_dates

# Set up logging
logger = logging.getLogger(__name__)

class YahooClient:
    """Client for interacting with Yahoo Finance API."""

    def __init__(self):
        """Initialize the Yahoo Finance client."""
        logger.info("Yahoo Finance Client initialized")

    def get_historical_prices(self, ticker: str, start_date: str = None,
                              end_date: str = None, periods: int = None,
                              frequency: str = '1d') -> pd.DataFrame:
        """
        Get historical price data from Yahoo Finance.

        Args:
            ticker (str): Yahoo Finance ticker symbol (e.g., 'HG=F')
            start_date (str, optional): Start date in format 'YYYY-MM-DD'
            end_date (str, optional): End date in format 'YYYY-MM-DD'
            periods (int, optional): Number of periods to fetch (will calculate start_date if not provided)
            frequency (str, optional): Data frequency ('1d' for daily, '1wk' for weekly, '1mo' for monthly)

        Returns:
            pd.DataFrame: DataFrame with 'Date' and 'value' columns
        """
        # Validate ticker
        if not ticker or not isinstance(ticker, str):
            raise ValueError(f"Invalid ticker: {ticker}")

        # Calculate start_date based on periods if not provided
        if start_date is None and periods is not None:
            end = datetime.now() if end_date is None else datetime.strptime(end_date, '%Y-%m-%d')

            if frequency == '1d':
                start = end - timedelta(days=periods + 10)  # Add buffer
            elif frequency == '1wk':
                start = end - timedelta(weeks=periods + 2)  # Add buffer
            else:  # Monthly
                start = end - timedelta(days=(periods + 2) * 30)  # Add buffer

            start_date = start.strftime('%Y-%m-%d')

        try:
            # Fetch data from Yahoo Finance
            ticker_obj = yf.Ticker(ticker)
            df = ticker_obj.history(start=start_date, end=end_date, interval=frequency)

            # Validate data
            if df is None or df.empty:
                logger.warning(f"No data found for ticker {ticker}")
                raise ValueError(f"No data found for ticker {ticker}")

            # Select Close price as value
            df = df[['Close']].reset_index()
            df.columns = ['Date', 'value']

            # Ensure Date is datetime
            df['Date'] = pd.to_datetime(df['Date'])

            # Use processing utility to convert dates
            df = convert_dates(df.set_index('Date')).reset_index()

            logger.info(f"Successfully fetched {len(df)} records for {ticker}")
            return df

        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {str(e)}")
            raise