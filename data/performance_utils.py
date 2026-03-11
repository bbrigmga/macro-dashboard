"""
Performance optimization utilities for volatility data processing.

This module provides async versions of data fetching operations to improve
performance when processing multiple ETF tickers in parallel.
"""
import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import yfinance as yf

try:
    import aiohttp  # type: ignore
except ImportError:
    aiohttp = None  # Optional dependency

logger = logging.getLogger(__name__)


class AsyncIVFetcher:
    """
    Async wrapper for yfinance operations to enable parallel processing.
    
    This uses ThreadPoolExecutor to run yfinance operations in parallel
    since yfinance is synchronous but I/O bound (network requests).
    """
    
    def __init__(self, max_workers: int = 5):
        """
        Initialize async IV fetcher.
        
        Args:
            max_workers: Maximum number of concurrent threads for yfinance operations
        """
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    async def fetch_options_chain_async(self, ticker: str, exp_date: str) -> Optional[Tuple[Any, Any]]:
        """
        Fetch options chain asynchronously.
        
        Args:
            ticker: ETF ticker symbol
            exp_date: Expiration date string
            
        Returns:
            Tuple of (calls_df, puts_df) or None if failed
        """
        try:
            loop = asyncio.get_event_loop()
            
            def _fetch_chain():
                yf_ticker = yf.Ticker(ticker)
                chain = yf_ticker.option_chain(exp_date)
                return chain.calls, chain.puts
            
            return await loop.run_in_executor(self.executor, _fetch_chain)
            
        except Exception as e:
            logger.error(f"Async error fetching options chain for {ticker} {exp_date}: {e}")
            return None
    
    async def fetch_current_price_async(self, ticker: str) -> Optional[float]:
        """
        Fetch current price asynchronously.
        
        Args:
            ticker: ETF ticker symbol
            
        Returns:
            Current price or None if failed
        """
        try:
            loop = asyncio.get_event_loop()
            
            def _fetch_price():
                yf_ticker = yf.Ticker(ticker)
                
                # Try fast_info first
                try:
                    price = yf_ticker.fast_info.get('lastPrice')
                    if price and not pd.isna(price):
                        return float(price)
                except Exception:
                    pass
                
                # Fallback to info dict
                info = yf_ticker.info
                price = info.get('currentPrice') or info.get('regularMarketPrice')
                
                if price and not pd.isna(price):
                    return float(price)
                
                return None
            
            return await loop.run_in_executor(self.executor, _fetch_price)
            
        except Exception as e:
            logger.error(f"Async error fetching price for {ticker}: {e}")
            return None
    
    async def fetch_expirations_async(self, ticker: str) -> Optional[List[str]]:
        """
        Fetch available option expirations asynchronously.
        
        Args:
            ticker: ETF ticker symbol
            
        Returns:
            List of expiration date strings or None if failed
        """
        try:
            loop = asyncio.get_event_loop()
            
            def _fetch_expirations():
                yf_ticker = yf.Ticker(ticker)
                return list(yf_ticker.options)
            
            return await loop.run_in_executor(self.executor, _fetch_expirations)
            
        except Exception as e:
            logger.error(f"Async error fetching expirations for {ticker}: {e}")
            return None
    
    async def fetch_price_data_async(self, ticker: str, start_date, end_date) -> Optional[Any]:
        """
        Fetch historical price data asynchronously.
        
        Args:
            ticker: ETF ticker symbol
            start_date: Start date
            end_date: End date
            
        Returns:
            DataFrame with price data or None if failed
        """
        try:
            loop = asyncio.get_event_loop()
            
            def _fetch_prices():
                yf_ticker = yf.Ticker(ticker)
                return yf_ticker.history(start=start_date, end=end_date)
            
            return await loop.run_in_executor(self.executor, _fetch_prices)
            
        except Exception as e:
            logger.error(f"Async error fetching price data for {ticker}: {e}")
            return None
    
    def close(self):
        """Clean up executor resources."""
        self.executor.shutdown(wait=True)


class BatchProcessor:
    """
    Process multiple tickers in batches with concurrency control.
    """
    
    @staticmethod
    async def process_tickers_batch(
        tickers: List[str], 
        process_func,
        batch_size: int = 3, 
        max_concurrent: int = 3
    ) -> Dict[str, Any]:
        """
        Process tickers in batches with concurrency control.
        
        Args:
            tickers: List of ticker symbols to process
            process_func: Async function to process each ticker
            batch_size: Number of tickers per batch
            max_concurrent: Maximum concurrent operations
            
        Returns:
            Dict mapping ticker to process results
        """
        results = {}
        
        # Process in batches to avoid overwhelming the API
        for i in range(0, len(tickers), batch_size):
            batch = tickers[i:i + batch_size]
            
            # Limit concurrent operations within each batch
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def process_with_semaphore(ticker):
                async with semaphore:
                    return await process_func(ticker)
            
            # Process batch concurrently
            batch_tasks = [process_with_semaphore(ticker) for ticker in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Collect results
            for ticker, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Error processing {ticker}: {result}")
                    results[ticker] = None
                else:
                    results[ticker] = result
            
            # Brief pause between batches to be respectful to API
            await asyncio.sleep(1)
        
        return results


def optimize_dataframe_operations(df) -> Any:
    """
    Optimize pandas DataFrame operations for better performance.
    
    Args:
        df: Input DataFrame
        
    Returns:
        Optimized DataFrame
    """
    if df.empty:
        return df
    
    # Use more efficient dtypes
    for col in df.columns:
        if df[col].dtype == 'object':
            # Try to convert to category if low cardinality
            nunique = df[col].nunique()
            if nunique < len(df) * 0.5:  # Less than 50% unique values
                try:
                    df[col] = df[col].astype('category')
                except (ValueError, TypeError):
                    pass
        elif df[col].dtype == 'int64':
            # Downcast integers if possible
            try:
                df[col] = pd.to_numeric(df[col], downcast='integer')
            except (ValueError, TypeError):
                pass
        elif df[col].dtype == 'float64':
            # Downcast floats if possible  
            try:
                df[col] = pd.to_numeric(df[col], downcast='float')
            except (ValueError, TypeError):
                pass
    
    return df


async def parallel_iv_extraction(iv_scraper, tickers: List[str]) -> Dict[str, Any]:
    """
    Extract IV data for multiple tickers in parallel.
    
    Args:
        iv_scraper: IVScraper instance
        tickers: List of ticker symbols
        
    Returns:
        Dict mapping ticker to IV extraction results
    """
    async_fetcher = AsyncIVFetcher(max_workers=3)
    
    try:
        async def extract_iv_for_ticker(ticker: str) -> Optional[Dict[str, Any]]:
            """Extract IV data for a single ticker."""
            try:
                # Get current price
                current_price = await async_fetcher.fetch_current_price_async(ticker)
                if not current_price:
                    return None
                
                # Get expirations
                expirations = await async_fetcher.fetch_expirations_async(ticker)
                if not expirations:
                    return None
                
                # For simplicity, just use the first suitable expiration
                # In a full implementation, would do the 30-day interpolation
                suitable_exp = None
                for exp in expirations:
                    dte = iv_scraper._days_to_expiration(exp)
                    if 20 <= dte <= 45:  # Approximate 30-day range
                        suitable_exp = exp
                        break
                
                if not suitable_exp:
                    return None
                
                # Fetch options chain
                chain_result = await async_fetcher.fetch_options_chain_async(ticker, suitable_exp)
                if not chain_result:
                    return None
                
                calls_df, puts_df = chain_result
                
                # Extract IV using existing synchronous logic
                # (would need to adapt the full logic for async)
                if not calls_df.empty and 'impliedVolatility' in calls_df.columns:
                    # Find ATM strike
                    atm_strike = iv_scraper._find_atm_strike(
                        current_price, 
                        calls_df['strike'].tolist()
                    )
                    
                    # Get IV at ATM
                    atm_calls = calls_df[calls_df['strike'] == atm_strike]
                    if not atm_calls.empty:
                        iv = atm_calls['impliedVolatility'].iloc[0]
                        if not pd.isna(iv) and iv > 0:
                            return {
                                'iv': float(iv),
                                'price': current_price,
                                'strike': atm_strike,
                                'expiration': suitable_exp
                            }
                
                return None
                
            except Exception as e:
                logger.error(f"Error extracting IV for {ticker}: {e}")
                return None
        
        # Process all tickers with batching
        results = await BatchProcessor.process_tickers_batch(
            tickers, 
            extract_iv_for_ticker,
            batch_size=3,
            max_concurrent=2
        )
        
        return results
        
    finally:
        async_fetcher.close()


# For backwards compatibility, provide a sync wrapper
def parallel_iv_extraction_sync(iv_scraper, tickers: List[str]) -> Dict[str, Any]:
    """
    Synchronous wrapper for parallel IV extraction.
    
    Args:
        iv_scraper: IVScraper instance  
        tickers: List of ticker symbols
        
    Returns:
        Dict mapping ticker to IV extraction results
    """
    try:
        import pandas as pd  # Import here to avoid circular imports
        
        # Run the async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            return loop.run_until_complete(
                parallel_iv_extraction(iv_scraper, tickers)
            )
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error in parallel IV extraction: {e}")
        return {ticker: None for ticker in tickers}