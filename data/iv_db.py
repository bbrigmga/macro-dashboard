"""
SQLite Database Layer for Implied/Realized Volatility Data
Provides persistent storage for daily IV/RV snapshots.
"""

import sqlite3
from pathlib import Path
from typing import Dict, Optional, Any, Tuple
from datetime import datetime, date
import pandas as pd
import logging

from .volatility_logging import get_volatility_logger, log_performance_metric

# Set up enhanced logging
logger = get_volatility_logger(__name__)


class IVDatabase:
    """Database access layer for daily implied/realized volatility data."""
    
    def __init__(self, db_path: str = "data/volatility/iv_data.db"):
        """Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = None
        self._init_db()
    
    def _init_db(self) -> None:
        """Create tables if they don't exist."""
        self.conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            timeout=30.0  # 30 second timeout for database locks
        )
        self.conn.execute("PRAGMA foreign_keys = ON")
        
        # Apply performance optimizations immediately
        self.optimize_connection()
        
        schema_sql = """
        CREATE TABLE IF NOT EXISTS daily_iv (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            ticker TEXT NOT NULL,
            close_price REAL NOT NULL,
            iv_30d REAL,
            rv_30d REAL,
            iv_premium REAL,
            ytd_return REAL,
            UNIQUE(date, ticker)
        );
        
        CREATE INDEX IF NOT EXISTS idx_daily_iv_ticker_date 
        ON daily_iv(ticker, date);
        """
        
        self.conn.executescript(schema_sql)
        self.conn.commit()
        logger.info(f"Initialized IV database at {self.db_path}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close connection."""
        if self.conn:
            self.conn.close()
    
    def close(self) -> None:
        """Explicitly close database connection."""
        if self.conn:
            self.conn.close()
    
    def upsert_daily(
        self,
        date: str,
        ticker: str,
        close_price: float,
        iv_30d: Optional[float] = None,
        rv_30d: Optional[float] = None,
        iv_premium: Optional[float] = None,
        ytd_return: Optional[float] = None
    ) -> None:
        """Insert or replace daily IV/RV data for a ticker.
        
        Args:
            date: Date string (YYYY-MM-DD)
            ticker: Stock ticker symbol
            close_price: Closing price
            iv_30d: 30-day implied volatility (decimal, e.g. 0.18 = 18%)
            rv_30d: 30-day realized volatility (decimal)
            iv_premium: IV premium over RV (decimal)
            ytd_return: Year-to-date return (decimal)
        """
        sql = """
        INSERT OR REPLACE INTO daily_iv 
        (date, ticker, close_price, iv_30d, rv_30d, iv_premium, ytd_return)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        
        self.conn.execute(sql, (
            date, ticker, close_price, iv_30d, rv_30d, iv_premium, ytd_return
        ))
        self.conn.commit()
        
        logger.debug(f"Upserted {ticker} data for {date}")
    
    def get_latest(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get most recent data for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dictionary with latest data or None if not found
        """
        sql = """
        SELECT date, ticker, close_price, iv_30d, rv_30d, iv_premium, ytd_return
        FROM daily_iv
        WHERE ticker = ?
        ORDER BY date DESC
        LIMIT 1
        """
        
        cursor = self.conn.execute(sql, (ticker,))
        row = cursor.fetchone()
        
        if row is None:
            return None
        
        return {
            'date': row[0],
            'ticker': row[1],
            'close_price': row[2],
            'iv_30d': row[3],
            'rv_30d': row[4],
            'iv_premium': row[5],
            'ytd_return': row[6]
        }
    
    def get_history(
        self, 
        ticker: str, 
        lookback_days: int = 252
    ) -> pd.DataFrame:
        """Get historical data for Z-score calculation.
        
        Args:
            ticker: Stock ticker symbol
            lookback_days: Number of days to look back
            
        Returns:
            DataFrame with historical IV/RV data
        """
        sql = """
        SELECT date, ticker, close_price, iv_30d, rv_30d, iv_premium, ytd_return
        FROM daily_iv
        WHERE ticker = ?
        ORDER BY date DESC
        LIMIT ?
        """
        
        df = pd.read_sql_query(
            sql, 
            self.conn, 
            params=(ticker, lookback_days),
            parse_dates=['date']
        )
        
        # Sort by date ascending for time series analysis
        df = df.sort_values('date')
        
        logger.debug(f"Retrieved {len(df)} historical records for {ticker}")
        return df
    
    def get_all_latest(self) -> pd.DataFrame:
        """Get latest data for all tickers.
        
        Returns:
            DataFrame with latest row per ticker for table display
        """
        sql = """
        SELECT date, ticker, close_price, iv_30d, rv_30d, iv_premium, ytd_return
        FROM daily_iv d1
        WHERE date = (
            SELECT MAX(date)
            FROM daily_iv d2
            WHERE d2.ticker = d1.ticker
        )
        ORDER BY ticker
        """
        
        df = pd.read_sql_query(
            sql,
            self.conn,
            parse_dates=['date']
        )
        
        logger.debug(f"Retrieved latest data for {len(df)} tickers")
        return df
    
    def get_snapshot(
        self, 
        date: str, 
        ticker: str
    ) -> Optional[Dict[str, Any]]:
        """Get data for specific date and ticker.
        
        Args:
            date: Date string (YYYY-MM-DD)
            ticker: Stock ticker symbol
            
        Returns:
            Dictionary with data or None if not found
        """
        sql = """
        SELECT date, ticker, close_price, iv_30d, rv_30d, iv_premium, ytd_return
        FROM daily_iv
        WHERE date = ? AND ticker = ?
        """
        
        cursor = self.conn.execute(sql, (date, ticker))
        row = cursor.fetchone()
        
        if row is None:
            return None
        
        return {
            'date': row[0],
            'ticker': row[1],
            'close_price': row[2],
            'iv_30d': row[3],
            'rv_30d': row[4],
            'iv_premium': row[5],
            'ytd_return': row[6]
        }
    
    def get_all_tickers(self) -> list[str]:
        """Get list of all unique tickers in database.
        
        Returns:
            List of ticker symbols
        """
        sql = "SELECT DISTINCT ticker FROM daily_iv ORDER BY ticker"
        cursor = self.conn.execute(sql)
        return [row[0] for row in cursor.fetchall()]
    
    def delete_ticker(self, ticker: str) -> int:  
        """Delete all data for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Number of rows deleted
        """
        sql = "DELETE FROM daily_iv WHERE ticker = ?"
        cursor = self.conn.execute(sql, (ticker,))
        self.conn.commit()
        
        deleted_count = cursor.rowcount
        logger.info(f"Deleted {deleted_count} records for ticker {ticker}")
        return deleted_count
    
    # Performance optimization methods
    
    def upsert_daily_batch(self, records: list[dict]) -> int:
        """
        Insert or replace multiple daily records in a single transaction.
        
        Args:
            records: List of dicts with keys: date, ticker, close_price, 
                    iv_30d, rv_30d, iv_premium, ytd_return
                    
        Returns:
            Number of records processed
        """
        sql = """
        INSERT OR REPLACE INTO daily_iv 
        (date, ticker, close_price, iv_30d, rv_30d, iv_premium, ytd_return)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        
        records_data = [
            (
                record['date'],
                record['ticker'], 
                record['close_price'],
                record.get('iv_30d'),
                record.get('rv_30d'),
                record.get('iv_premium'),
                record.get('ytd_return')
            )
            for record in records
        ]
        
        # Use executemany for batch processing
        self.conn.executemany(sql, records_data)
        self.conn.commit()
        
        logger.info(f"Batch upserted {len(records)} records")
        return len(records)
    
    def get_multiple_latest(self, tickers: list[str]) -> pd.DataFrame:
        """
        Get latest data for multiple tickers in a single query.
        
        Args:
            tickers: List of ticker symbols
            
        Returns:
            DataFrame with latest data for requested tickers
        """
        if not tickers:
            return pd.DataFrame()
        
        # Create placeholders for IN clause
        placeholders = ','.join(['?'] * len(tickers))
        
        sql = f"""
        SELECT date, ticker, close_price, iv_30d, rv_30d, iv_premium, ytd_return
        FROM daily_iv d1
        WHERE ticker IN ({placeholders})
        AND date = (
            SELECT MAX(date)
            FROM daily_iv d2
            WHERE d2.ticker = d1.ticker
        )
        ORDER BY ticker
        """
        
        df = pd.read_sql_query(
            sql,
            self.conn,
            params=tickers,
            parse_dates=['date']
        )
        
        logger.debug(f"Retrieved latest data for {len(df)}/{len(tickers)} requested tickers")
        return df
    
    def get_multiple_history(self, tickers: list[str], lookback_days: int = 252) -> pd.DataFrame:
        """
        Get historical data for multiple tickers in a single query.
        
        Args:
            tickers: List of ticker symbols
            lookback_days: Number of days to look back
            
        Returns:
            DataFrame with historical data for all requested tickers
        """
        if not tickers:
            return pd.DataFrame()
        
        placeholders = ','.join(['?'] * len(tickers))
        
        sql = f"""
        SELECT date, ticker, close_price, iv_30d, rv_30d, iv_premium, ytd_return
        FROM (
            SELECT *,
                   ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) as rn
            FROM daily_iv
            WHERE ticker IN ({placeholders})
        ) ranked
        WHERE rn <= ?
        ORDER BY ticker, date DESC
        """
        
        params = tickers + [lookback_days]
        df = pd.read_sql_query(
            sql,
            self.conn, 
            params=params,
            parse_dates=['date']
        )
        
        logger.debug(f"Retrieved historical data for {len(df)} total records across {len(tickers)} tickers")
        return df
    
    def get_collection_stats(self, anchor_ticker: str = 'SPY') -> dict:
        """
        Return collection health stats for the status panel.

        Uses a single anchor ticker (default SPY, the most reliably scraped)
        to determine which business days have data and which are missing.

        Returns dict with keys:
            total_days        - int: distinct trading days stored
            first_date        - date | None
            latest_date       - date | None
            days_since_latest - int: calendar days since latest record
            missing_days      - list[str]: YYYY-MM-DD strings of expected
                                business days with no record in the DB
            tickers_latest_date - dict[str, str]: per-ticker latest date
        """
        import datetime

        # All stored dates for anchor ticker
        cursor = self.conn.execute(
            "SELECT DISTINCT date FROM daily_iv WHERE ticker = ? ORDER BY date",
            (anchor_ticker,)
        )
        stored_dates = {row[0][:10] for row in cursor.fetchall()}  # normalise to YYYY-MM-DD

        if not stored_dates:
            return {
                'total_days': 0,
                'first_date': None,
                'latest_date': None,
                'days_since_latest': None,
                'missing_days': [],
                'tickers_latest_date': {},
            }

        sorted_dates = sorted(stored_dates)
        first_date  = datetime.date.fromisoformat(sorted_dates[0])
        latest_date = datetime.date.fromisoformat(sorted_dates[-1])
        today       = datetime.date.today()

        # Expected business days in the stored range (Mon-Fri)
        # We only flag gaps up to *latest_date* so we don't blame the scheduler
        # for "missing" days that haven't happened yet.
        expected = pd.bdate_range(start=first_date, end=latest_date)
        missing_days = [
            d.strftime('%Y-%m-%d')
            for d in expected
            if d.strftime('%Y-%m-%d') not in stored_dates
        ]

        # Per-ticker latest date
        cursor2 = self.conn.execute(
            "SELECT ticker, MAX(date) FROM daily_iv GROUP BY ticker ORDER BY ticker"
        )
        tickers_latest = {row[0]: row[1][:10] for row in cursor2.fetchall()}

        days_since = (today - latest_date).days

        return {
            'total_days': len(stored_dates),
            'first_date': first_date,
            'latest_date': latest_date,
            'days_since_latest': days_since,
            'missing_days': missing_days,
            'tickers_latest_date': tickers_latest,
        }

    def vacuum_database(self) -> None:
        """
        Optimize database by reclaiming unused space and updating statistics.
        Call this periodically for better query performance.
        """
        logger.info("Vacuuming database to optimize performance...")
        self.conn.execute("VACUUM")
        self.conn.execute("ANALYZE")
        self.conn.commit()
        logger.info("Database vacuum completed")
    
    def enable_wal_mode(self) -> None:
        """
        Enable Write-Ahead Logging for better concurrent access.
        Call once during initialization for better performance.
        """
        logger.info("Enabling WAL mode for better performance...")
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.commit()
        logger.info("WAL mode enabled")
        
    def optimize_connection(self) -> None:
        """
        Apply performance optimizations to the database connection.
        """
        # Increase cache size (default is 2MB, increase to 10MB)
        self.conn.execute("PRAGMA cache_size = -10000")
        
        # Enable memory-mapped I/O (faster file access)
        self.conn.execute("PRAGMA mmap_size = 268435456")  # 256MB
        
        # Optimize for performance over safety (acceptable for this use case)
        self.conn.execute("PRAGMA synchronous = NORMAL")
        
        # Enable WAL mode for better concurrency
        self.enable_wal_mode()
        
        self.conn.commit()
        logger.info("Database connection optimized for performance")