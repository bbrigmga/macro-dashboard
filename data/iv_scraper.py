"""
Implied Volatility Scraper for ETF Universe

Extracts 30-day at-the-money implied volatility from yfinance options chains
and stores daily snapshots in SQLite database.
"""
import datetime as dt
import logging
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
import yfinance as yf

from .iv_db import IVDatabase
from .rv_calculator import RealizedVolCalculator
from .yahoo_client import YahooClient
from .market_utils import should_skip_scraping
from .volatility_logging import get_volatility_logger, log_performance_metric, log_data_quality_metric

# Set up enhanced logging
logger = get_volatility_logger(__name__)

# ETF Universe from specification
ETF_UNIVERSE = [
    {"ticker": "XLRE", "name": "Real Estate Sector SPDR ETF"},
    {"ticker": "XLF",  "name": "Financials Sector SPDR ETF"},
    {"ticker": "XLE",  "name": "Energy Sector SPDR ETF"},
    {"ticker": "XLC",  "name": "Communication Services SPDR ETF"},
    {"ticker": "XLK",  "name": "Technology Sector SPDR ETF"},
    {"ticker": "QQQ",  "name": "Power Shares QQQ Trust ETF"},
    {"ticker": "SPY",  "name": "SPDR S&P 500 Trust"},
    {"ticker": "XLV",  "name": "Health Care Sector SPDR ETF"},
    {"ticker": "XLB",  "name": "Materials Sector SPDR ETF"},
    {"ticker": "XLI",  "name": "Industrials Sector SPDR ETF"},
    {"ticker": "XLY",  "name": "Consumer Discretionary SPDR ETF"},
    {"ticker": "IWM",  "name": "I-Shares Russell 2000"},
    {"ticker": "XLU",  "name": "Utilities Sector SPDR ETF"},
    {"ticker": "XLP",  "name": "Consumer Staples Sector SPDR ETF"},
]


class IVScraper:
    """Scrapes implied volatility data from yfinance options chains."""
    
    def __init__(self, db: IVDatabase):
        """
        Initialize IV scraper with database connection.
        
        Args:
            db: IVDatabase instance for storing data
        """
        self.db = db
        self.yahoo_client = YahooClient()
        self.rv_calculator = RealizedVolCalculator(self.yahoo_client)
        self._session = None
        self._crumb = None
        logger.info("IV Scraper initialized")

    def _get_authenticated_session(self):
        """
        Build (or reuse) an authenticated curl_cffi session for Yahoo Finance.

        Yahoo Finance's options API requires a session cookie + crumb.  The
        standard yfinance 0.2/1.x cookie strategy relies on fc.yahoo.com which
        is blocked on many corporate networks.  We bypass that by:
          1. Hitting the Yahoo Finance homepage with Chrome impersonation to
             collect A1/A3 session cookies.
          2. Fetching a crumb from query1.finance.yahoo.com/v1/test/getcrumb.
        The session is cached on the instance so per-ticker calls reuse it.

        Returns:
            Tuple of (session, crumb) or (None, None) on failure.
        """
        if self._session is not None and self._crumb is not None:
            return self._session, self._crumb
        try:
            from curl_cffi import requests as cffi_requests
            session = cffi_requests.Session(impersonate="chrome110")
            session.get('https://finance.yahoo.com', timeout=15)
            crumb_r = session.get(
                'https://query1.finance.yahoo.com/v1/test/getcrumb',
                timeout=10
            )
            if crumb_r.status_code == 200:
                self._session = session
                self._crumb = crumb_r.text.strip()
                logger.debug("Yahoo Finance options session established")
                return self._session, self._crumb
            logger.error(f"Failed to get Yahoo Finance crumb: HTTP {crumb_r.status_code}")
            return None, None
        except Exception as e:
            logger.error(f"Failed to initialize Yahoo Finance options session: {e}")
            return None, None

    def _get_option_expirations(self, ticker: str) -> Tuple:
        """
        Fetch option expiration dates directly from the Yahoo Finance v7 API.

        Bypasses yfinance's broken fc.yahoo.com cookie path and calls the
        options endpoint directly with our own authenticated session.

        Returns:
            Tuple of 'YYYY-MM-DD' expiration date strings, or empty tuple.
        """
        session, crumb = self._get_authenticated_session()
        if not session:
            return ()
        try:
            r = session.get(
                f'https://query2.finance.yahoo.com/v7/finance/options/{ticker}',
                params={'crumb': crumb},
                timeout=20
            )
            if r.status_code != 200:
                # Session expired — re-authenticate once and retry
                self._session = None
                self._crumb = None
                session, crumb = self._get_authenticated_session()
                if not session:
                    return ()
                r = session.get(
                    f'https://query2.finance.yahoo.com/v7/finance/options/{ticker}',
                    params={'crumb': crumb},
                    timeout=20
                )
                if r.status_code != 200:
                    return ()
            data = r.json()
            chain = data.get('optionChain', {}).get('result', [])
            if not chain:
                return ()
            ts_list = chain[0].get('expirationDates', [])
            # Yahoo Finance timestamps are midnight UTC; use UTC to avoid
            # off-by-one-day errors on machines west of UTC.
            return tuple(
                dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc).strftime('%Y-%m-%d')
                for ts in ts_list
            )
        except Exception as e:
            logger.error(f"Error fetching option expirations for {ticker}: {e}")
            return ()

    def _get_option_chain_direct(
        self, ticker: str, exp_date: str
    ) -> Tuple[Optional['pd.DataFrame'], Optional['pd.DataFrame']]:
        """
        Fetch the full options chain for a specific expiration directly from
        Yahoo Finance v7 API, returning DataFrames compatible with the rest of
        the IV extraction pipeline.

        Returns:
            Tuple of (calls_df, puts_df) or (None, None) on failure.
        """
        session, crumb = self._get_authenticated_session()
        if not session:
            return None, None
        try:
            # Reconstruct midnight-UTC timestamp to match Yahoo Finance's encoding
            exp_ts = int(
                dt.datetime(
                    *[int(x) for x in exp_date.split('-')],
                    tzinfo=dt.timezone.utc
                ).timestamp()
            )
            r = session.get(
                f'https://query2.finance.yahoo.com/v7/finance/options/{ticker}',
                params={'date': exp_ts, 'crumb': crumb},
                timeout=20
            )
            if r.status_code != 200:
                return None, None
            data = r.json()
            chain = data.get('optionChain', {}).get('result', [])
            if not chain:
                return None, None
            opts_list = chain[0].get('options', [])
            if not opts_list:
                return None, None
            opts = opts_list[0]
            calls_df = pd.DataFrame(opts.get('calls', []))
            puts_df = pd.DataFrame(opts.get('puts', []))
            return calls_df, puts_df
        except Exception as e:
            logger.error(f"Error fetching option chain for {ticker} {exp_date}: {e}")
            return None, None
    
    def _get_current_price(self, ticker: str) -> Optional[float]:
        """
        Get current price for ticker.
        
        Tries cached price data via YahooClient first (avoids live API call when
        cache is fresh), then falls back to live yfinance as a last resort.
        
        Args:
            ticker: ETF ticker symbol
            
        Returns:
            Current price or None if failed to retrieve
        """
        # Try cached/incremental price via YahooClient first
        try:
            price_df = self.yahoo_client.get_historical_prices(ticker, periods=1)
            if not price_df.empty:
                price = float(price_df['value'].iloc[-1])
                if price > 0 and not pd.isna(price):
                    return price
        except Exception:
            pass

        # Fall back to live yfinance if cache is empty or stale
        try:
            yf_ticker = yf.Ticker(ticker)
            
            # Try fast_info first (faster), fallback to info
            try:
                price = yf_ticker.fast_info.last_price  # yfinance 1.x attribute
                if price and not pd.isna(price):
                    return float(price)
            except Exception:
                pass
                
            # Fallback to info dict
            info = yf_ticker.info
            price = info.get('currentPrice') or info.get('regularMarketPrice')
            
            if price and not pd.isna(price):
                return float(price)
                
            logger.warning(f"Could not get current price for {ticker}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting current price for {ticker}: {e}")
            return None
    
    def _days_to_expiration(self, exp_date_str: str) -> int:
        """
        Calculate days to expiration from date string.
        
        Args:
            exp_date_str: Expiration date in 'YYYY-MM-DD' format
            
        Returns:
            Number of calendar days to expiration
        """
        try:
            exp_date = dt.datetime.strptime(exp_date_str, '%Y-%m-%d').date()
            today = dt.date.today()
            return (exp_date - today).days
        except Exception as e:
            logger.error(f"Error parsing expiration date {exp_date_str}: {e}")
            return 0
    
    def _find_atm_strike(self, current_price: float, strikes: List[float]) -> float:
        """
        Find the strike closest to current price (ATM).
        
        Args:
            current_price: Current underlying price
            strikes: List of available strike prices
            
        Returns:
            Strike price closest to current price
        """
        if not strikes:
            return current_price
            
        return min(strikes, key=lambda x: abs(x - current_price))
    
    def _get_iv_at_strike(self, options_df: pd.DataFrame, strike: float) -> Optional[Tuple[float, dict]]:
        """
        Get implied volatility at specific strike with quality metrics.
        
        Args:
            options_df: Options dataframe (calls or puts)
            strike: Strike price to lookup
            
        Returns:
            Tuple of (IV, quality_metrics) or None if not found
            quality_metrics contains: volume, bid_ask_spread, quality_score
        """
        if options_df.empty:
            return None
            
        def _extract_iv_with_quality(row) -> Optional[Tuple[float, dict]]:
            """Extract IV and compute quality metrics from options row."""
            if row.empty:
                return None
                
            # Get IV
            iv = row.get('impliedVolatility', np.nan)
            if pd.isna(iv) or iv <= 0:
                return None
                
            # Get quality metrics
            volume = row.get('volume', 0) or 0
            bid = row.get('bid', 0) or 0
            ask = row.get('ask', 0) or 0
            
            # Calculate bid-ask spread as percentage of mid price
            if bid > 0 and ask > bid:
                mid_price = (bid + ask) / 2.0
                bid_ask_spread_pct = ((ask - bid) / mid_price) * 100.0 if mid_price > 0 else 100.0
            else:
                bid_ask_spread_pct = 100.0  # Wide spread if no bid/ask
            
            # Quality score (0-100, higher is better)
            quality_score = 100.0
            
            # Penalize low volume (less than 10 contracts)
            if volume < 10:
                quality_score *= 0.7
            elif volume < 50:
                quality_score *= 0.85
                
            # Penalize wide bid-ask spreads
            if bid_ask_spread_pct > 50:
                quality_score *= 0.3  # Very wide spread
            elif bid_ask_spread_pct > 25:
                quality_score *= 0.6  # Wide spread
            elif bid_ask_spread_pct > 10:
                quality_score *= 0.8  # Moderate spread
                
            # Sanity check on IV values (typical ETF IV range: 0.05 to 2.0)
            if iv < 0.02 or iv > 3.0:
                quality_score *= 0.4  # Suspicious IV value
                
            quality_metrics = {
                'volume': volume,
                'bid_ask_spread_pct': bid_ask_spread_pct,
                'quality_score': quality_score,
                'bid': bid,
                'ask': ask
            }
            
            return float(iv), quality_metrics
        
        # Find exact strike match first
        exact_match = options_df[options_df['strike'] == strike]
        if not exact_match.empty and 'impliedVolatility' in exact_match.columns:
            result = _extract_iv_with_quality(exact_match.iloc[0])
            if result:
                return result
        
        # If no exact match or IV is invalid, try nearby strikes
        strikes = sorted(options_df['strike'].unique())
        best_result = None
        best_distance = float('inf')
        
        for s in strikes:
            distance = abs(s - strike) / strike  # Relative distance
            if distance <= 0.05:  # Within 5% of target strike
                row = options_df[options_df['strike'] == s]
                if not row.empty and 'impliedVolatility' in row.columns:
                    result = _extract_iv_with_quality(row.iloc[0])
                    if result and distance < best_distance:
                        best_result = result
                        best_distance = distance
        
        return best_result
    
    @staticmethod
    def _is_monthly_expiration(date_str: str) -> bool:
        """
        Return True if the given date is the standard monthly option expiration
        (3rd Friday of the month: day falls between 15 and 21 inclusive).
        """
        try:
            d = dt.date.fromisoformat(date_str)
            return d.weekday() == 4 and 15 <= d.day <= 21
        except Exception:
            return False

    def _get_atm_iv(self, ticker: str) -> Optional[Tuple[float, dict]]:
        """
        Extract 30-day at-the-money implied volatility from options chains with quality assessment.
        
        Interpolates between the two nearest standard monthly expirations (3rd Friday)
        to get an accurate 30-day estimate with better liquidity than weekly options.
        Falls back to all expirations if no monthlies are available.
        
        Args:
            ticker: ETF ticker symbol
            
        Returns:
            Tuple of (30-day ATM IV (annualized), quality_metrics) or None if extraction failed
        """
        try:
            # Get current price
            current_price = self._get_current_price(ticker)
            if not current_price:
                logger.warning(f"Could not get current price for {ticker}")
                return None
            
            # Get available expirations via direct Yahoo Finance API
            # (bypasses yfinance's fc.yahoo.com cookie path which fails on many networks)
            expirations = self._get_option_expirations(ticker)
            if not expirations:
                logger.warning(f"No option expirations for {ticker}")
                return None
            
            # Calculate DTE for each expiration and find those around 30 days
            exp_with_dte = []
            target_dte = 30
            
            for exp_str in expirations:
                dte = self._days_to_expiration(exp_str)
                if dte > 0:  # Only future expirations
                    exp_with_dte.append((exp_str, dte))
            
            if not exp_with_dte:
                logger.warning(f"No valid future expirations for {ticker}")
                return None
            
            # Sort by DTE
            exp_with_dte.sort(key=lambda x: x[1])

            # Prefer standard monthly expirations (3rd Friday) for better liquidity.
            # Monthly options carry more open interest and tighter spreads than weeklies,
            # especially for less-actively-traded sector ETFs.
            monthly_exp_with_dte = [
                (exp_str, dte) for exp_str, dte in exp_with_dte
                if self._is_monthly_expiration(exp_str)
            ]
            if monthly_exp_with_dte:
                candidates = monthly_exp_with_dte
                logger.debug(f"{ticker}: Using {len(monthly_exp_with_dte)} monthly expirations "
                             f"(skipped {len(exp_with_dte) - len(monthly_exp_with_dte)} weeklies)")
            else:
                candidates = exp_with_dte
                logger.debug(f"{ticker}: No monthly expirations found, falling back to all "
                             f"{len(exp_with_dte)} expirations")

            # Find expirations bracketing 30 DTE
            lower_exp = None
            upper_exp = None
            exact_exp = None
            
            for exp_str, dte in candidates:
                if dte == target_dte:
                    exact_exp = (exp_str, dte)
                    break
                elif dte < target_dte:
                    lower_exp = (exp_str, dte)
                elif dte > target_dte and not upper_exp:
                    upper_exp = (exp_str, dte)
                    break
            
            # Determine which expirations to use
            if exact_exp:
                # Perfect 30-day match
                expirations_to_use = [exact_exp]
            elif lower_exp and upper_exp:
                # Interpolate between two expirations
                expirations_to_use = [lower_exp, upper_exp]
            elif upper_exp:
                # Only longer expiration available, use it
                expirations_to_use = [upper_exp]
            elif lower_exp:
                # Only shorter expiration available, use it 
                expirations_to_use = [lower_exp]
            else:
                logger.warning(f"No suitable expiration found for {ticker}")
                return None
            
            # Extract IV for each expiration with quality metrics
            iv_data = []
            for exp_str, dte in expirations_to_use:
                result = self._extract_iv_for_expiration(ticker, exp_str, current_price)
                if result is not None:
                    iv, quality = result
                    iv_data.append((dte, iv, quality))
            
            if not iv_data:
                logger.warning(f"Could not extract IV for any expiration for {ticker}")
                return None
            
            # If only one expiration, return its IV and quality
            if len(iv_data) == 1:
                dte, iv, quality = iv_data[0]
                quality['interpolated'] = False
                quality['dte_used'] = dte
                return iv, quality
            
            # Interpolate between two expirations
            if len(iv_data) == 2:
                (dte1, iv1, quality1), (dte2, iv2, quality2) = iv_data
                # Linear interpolation weighted by DTE proximity to 30 days
                weight = (target_dte - dte1) / (dte2 - dte1) if dte2 != dte1 else 0.5
                interpolated_iv = iv1 + weight * (iv2 - iv1)
                
                # Combine quality metrics (weighted average by quality scores)
                q1_weight = quality1['quality_score']
                q2_weight = quality2['quality_score'] 
                total_weight = q1_weight + q2_weight
                
                if total_weight > 0:
                    combined_quality = {
                        'volume': (quality1['volume'] * q1_weight + quality2['volume'] * q2_weight) / total_weight,
                        'bid_ask_spread_pct': (quality1['bid_ask_spread_pct'] * q1_weight + quality2['bid_ask_spread_pct'] * q2_weight) / total_weight,
                        'quality_score': (quality1['quality_score'] + quality2['quality_score']) / 2.0,
                        'interpolated': True,
                        'dte_used_lower': dte1,
                        'dte_used_upper': dte2,
                        'interpolation_weight': weight
                    }
                else:
                    combined_quality = {
                        'volume': (quality1['volume'] + quality2['volume']) / 2.0,
                        'bid_ask_spread_pct': (quality1['bid_ask_spread_pct'] + quality2['bid_ask_spread_pct']) / 2.0,
                        'quality_score': (quality1['quality_score'] + quality2['quality_score']) / 2.0,
                        'interpolated': True,
                        'dte_used_lower': dte1,
                        'dte_used_upper': dte2,
                        'interpolation_weight': weight
                    }
                
                logger.debug(f"{ticker}: Interpolated IV between {dte1}d ({iv1:.4f}) "
                           f"and {dte2}d ({iv2:.4f}) = {interpolated_iv:.4f} "
                           f"(Combined quality: {combined_quality['quality_score']:.1f})")
                
                return interpolated_iv, combined_quality
            
            # Fallback to first IV if multiple available
            dte, iv, quality = iv_data[0]
            quality['interpolated'] = False
            quality['dte_used'] = dte
            return iv, quality
            
        except Exception as e:
            logger.error(f"Error extracting ATM IV for {ticker}: {e}")
            return None
    
    def _extract_iv_for_expiration(self, ticker: str, exp_date: str, current_price: float) -> Optional[Tuple[float, dict]]:
        """
        Extract ATM IV for a specific expiration with quality assessment.
        
        Args:
            ticker: ETF ticker symbol
            exp_date: Expiration date string
            current_price: Current underlying price
            
        Returns:
            Tuple of (ATM IV, quality_metrics) for this expiration or None
        """
        try:
            # Get options chain via direct Yahoo Finance API
            calls_df, puts_df = self._get_option_chain_direct(ticker, exp_date)
            if calls_df is None or puts_df is None:
                logger.warning(f"Failed to fetch options chain for {ticker} {exp_date}")
                return None

            if calls_df.empty and puts_df.empty:
                logger.warning(f"Empty options chain for {ticker} {exp_date}")
                return None
            
            # Find ATM strike
            all_strikes = set()
            if not calls_df.empty and 'strike' in calls_df.columns:
                all_strikes.update(calls_df['strike'].tolist())
            if not puts_df.empty and 'strike' in puts_df.columns:
                all_strikes.update(puts_df['strike'].tolist())
            
            if not all_strikes:
                logger.warning(f"No strikes found for {ticker} {exp_date}")
                return None
            
            atm_strike = self._find_atm_strike(current_price, list(all_strikes))
            
            # Get IV from calls and puts at ATM strike with quality metrics
            call_result = self._get_iv_at_strike(calls_df, atm_strike) if not calls_df.empty else None
            put_result = self._get_iv_at_strike(puts_df, atm_strike) if not puts_df.empty else None
            
            call_iv, call_quality = call_result if call_result else (None, None)
            put_iv, put_quality = put_result if put_result else (None, None)
            
            # Combine call and put data
            if call_iv is not None and put_iv is not None:
                # Average IVs weighted by quality scores
                call_weight = call_quality['quality_score']
                put_weight = put_quality['quality_score']
                total_weight = call_weight + put_weight
                
                if total_weight > 0:
                    weighted_iv = (call_iv * call_weight + put_iv * put_weight) / total_weight
                else:
                    weighted_iv = (call_iv + put_iv) / 2.0
                
                # Combine quality metrics (average where applicable, sum volumes)
                combined_quality = {
                    'volume': call_quality['volume'] + put_quality['volume'],
                    'bid_ask_spread_pct': (call_quality['bid_ask_spread_pct'] + put_quality['bid_ask_spread_pct']) / 2.0,
                    'quality_score': (call_quality['quality_score'] + put_quality['quality_score']) / 2.0,
                    'data_source': 'calls_and_puts'
                }
                
                logger.debug(f"{ticker} {exp_date}: Call IV={call_iv:.4f} (Q:{call_quality['quality_score']:.1f}), "
                           f"Put IV={put_iv:.4f} (Q:{put_quality['quality_score']:.1f}), "
                           f"Weighted={weighted_iv:.4f}")
                
                return weighted_iv, combined_quality
                
            elif call_iv is not None:
                logger.debug(f"{ticker} {exp_date}: Using Call IV={call_iv:.4f} (Q:{call_quality['quality_score']:.1f})")
                call_quality['data_source'] = 'calls_only'
                return call_iv, call_quality
                
            elif put_iv is not None:
                logger.debug(f"{ticker} {exp_date}: Using Put IV={put_iv:.4f} (Q:{put_quality['quality_score']:.1f})")
                put_quality['data_source'] = 'puts_only'  
                return put_iv, put_quality
                
            else:
                logger.warning(f"No valid IV found at ATM strike {atm_strike} for {ticker} {exp_date}")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting IV for {ticker} {exp_date}: {e}")
            return None
    
    def _get_ytd_return(self, ticker: str) -> Optional[float]:
        """
        Calculate year-to-date return for ticker.
        
        Args:
            ticker: ETF ticker symbol
            
        Returns:
            YTD return as decimal (e.g., 0.15 = 15%) or None if calculation failed
        """
        try:
            current_year = dt.date.today().year
            jan_1 = dt.date(current_year, 1, 1)
            
            # Get price data from Jan 1 to today via YahooClient (uses file-based cache)
            data = self.yahoo_client.get_historical_prices(
                ticker=ticker,
                start_date=jan_1.isoformat(),
                end_date=dt.date.today().isoformat()
            )
            
            if data is None or data.empty:
                logger.warning(f"No price data available for {ticker} YTD calculation")
                return None
            
            if 'value' not in data.columns:
                logger.warning(f"No close price data for {ticker}")
                return None
            
            # Get first and last close prices
            close_prices = data['value'].dropna()
            
            if len(close_prices) < 2:
                logger.warning(f"Insufficient price data for {ticker} YTD calculation")
                return None
            
            jan_1_price = close_prices.iloc[0]
            current_price = close_prices.iloc[-1]
            
            if jan_1_price <= 0:
                logger.warning(f"Invalid Jan 1 price for {ticker}: {jan_1_price}")
                return None
            
            ytd_return = (current_price / jan_1_price) - 1.0
            
            logger.debug(f"{ticker} YTD: {jan_1_price:.2f} -> {current_price:.2f} = {ytd_return:.4f}")
            
            return ytd_return
            
        except Exception as e:
            logger.error(f"Error calculating YTD return for {ticker}: {e}")
            return None
    
    def scrape_daily(self) -> Dict[str, int]:
        """
        Scrape daily IV/RV data for all ETFs in universe and store in database.
        
        Returns:
            Dictionary with 'success' and 'failed' counts
        """
        # Check if we should skip scraping due to market closure
        should_skip, skip_reason = should_skip_scraping()
        if should_skip:
            logger.info(skip_reason)
            return {
                "success": 0,
                "failed": 0,
                "total": len(ETF_UNIVERSE),
                "failed_tickers": [],
                "skipped": True,
                "skip_reason": skip_reason
            }
        
        logger.info("Starting daily IV scraping for ETF universe")
        
        today = dt.date.today().isoformat()
        success_count = 0
        failed_count = 0
        failed_tickers = []
        
        for etf_info in ETF_UNIVERSE:
            ticker = etf_info["ticker"]
            name = etf_info["name"]
            
            try:
                # Skip if today's data already exists in the database
                existing = self.db.get_latest(ticker)
                if existing and existing.get('date') == today:
                    logger.info(f"Skipping {ticker} - already have today's data")
                    success_count += 1
                    continue

                logger.info(f"Processing {ticker} ({name})")
                
                # Get current close price
                current_price = self._get_current_price(ticker)
                if not current_price:
                    logger.warning(f"Failed to get current price for {ticker}")
                    failed_count += 1
                    failed_tickers.append(ticker)
                    continue
                
                # Get 30-day ATM IV with quality assessment
                iv_result = self._get_atm_iv(ticker)
                if iv_result is None:
                    logger.warning(f"Failed to get IV for {ticker}")
                    failed_count += 1
                    failed_tickers.append(ticker)
                    continue
                
                iv_30d, quality_metrics = iv_result
                
                # Log quality information with enhanced format
                quality_score = quality_metrics['quality_score']
                log_data_quality_metric(
                    "iv_scrape_quality", 
                    quality_score, 
                    threshold=50.0,
                    ticker=ticker
                )
                
                if quality_score < 50:
                    logger.warning(f"{ticker}: Low quality IV data (Q:{quality_score:.1f}, "
                                 f"Vol:{quality_metrics['volume']}, Spread:{quality_metrics['bid_ask_spread_pct']:.1f}%)")
                else:
                    logger.debug(f"{ticker}: Good quality IV data (Q:{quality_score:.1f})")
                
                
                # Calculate 30-day realized volatility
                rv_30d = self.rv_calculator.get_rv_for_ticker(ticker, window=30)
                if rv_30d is None:
                    logger.warning(f"Failed to calculate RV for {ticker}")
                    failed_count += 1
                    failed_tickers.append(ticker)
                    continue
                
                # Calculate IV premium: ((iv / rv) - 1) * 100
                if rv_30d > 0:
                    iv_premium = ((iv_30d / rv_30d) - 1.0) * 100.0
                else:
                    logger.warning(f"RV is zero or negative for {ticker}, cannot calculate IV premium")
                    iv_premium = None
                
                # Calculate YTD return
                ytd_return = self._get_ytd_return(ticker)
                
                # Store in database (do NOT use "with self.db" — that closes the connection)
                self.db.upsert_daily(
                    date=today,
                    ticker=ticker,
                    close_price=current_price,
                    iv_30d=iv_30d,
                    rv_30d=rv_30d,
                    iv_premium=iv_premium,
                    ytd_return=ytd_return
                )
                
                logger.info(f"Successfully processed {ticker}: "
                           f"Price=${current_price:.2f}, "
                           f"IV={iv_30d:.4f}, "
                           f"RV={rv_30d:.4f}, "
                           f"Premium={iv_premium:.2f}% (if available), "
                           f"YTD={ytd_return:.4f} (if available)")
                
                success_count += 1
                
            except Exception as e:
                logger.error(f"Error processing {ticker}: {e}")
                failed_count += 1
                failed_tickers.append(ticker)
        
        # Log summary
        total = len(ETF_UNIVERSE)
        logger.info(f"Scraping completed: {success_count}/{total} successful, {failed_count} failed")
        
        if failed_tickers:
            logger.warning(f"Failed tickers: {', '.join(failed_tickers)}")
        
        return {
            "success": success_count,
            "failed": failed_count,
            "total": total,
            "failed_tickers": failed_tickers
        }


def run_scraper():
    """Standalone entry point for running the IV scraper."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Initialize components
        db = IVDatabase()
        scraper = IVScraper(db)
        
        # Run the scraper
        result = scraper.scrape_daily()
        
        # Print summary
        print(f"\n=== IV Scraping Results ===")
        print(f"Success: {result['success']}/{result['total']} tickers")
        print(f"Failed: {result['failed']} tickers")
        
        if result['failed_tickers']:
            print(f"Failed tickers: {', '.join(result['failed_tickers'])}")
        
        return result
        
    except Exception as e:
        logger.error(f"Fatal error running IV scraper: {e}")
        print(f"Fatal error: {e}")
        return {"success": 0, "failed": 0, "total": 0, "failed_tickers": []}


if __name__ == "__main__":
    run_scraper()