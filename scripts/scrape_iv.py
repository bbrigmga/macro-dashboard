#!/usr/bin/env python3
"""
Daily IV Scraper — Standalone Entry Point

This script can be run via cron, GitHub Actions, or any scheduler to collect
implied volatility data for all tracked ETFs.

Usage:
    python scripts/scrape_iv.py

Exit codes:
    0: Success (all or some tickers scraped successfully)  
    1: Complete failure (database error, import issues, etc.)
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data.iv_scraper import IVScraper
from data.iv_db import IVDatabase


def setup_logging():
    """Configure logging for the scraper."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('scripts/scrape_iv.log', mode='a')
        ]
    )


def main():
    """Main entry point for daily IV scraping."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    start_time = datetime.now()
    logger.info(f"Starting daily IV scrape at {start_time}")
    
    try:
        # Initialize database and scraper
        logger.info("Initializing database and scraper...")
        db = IVDatabase()
        scraper = IVScraper(db)
        
        # Run the daily scrape
        logger.info("Beginning scrape process...")
        result = scraper.scrape_daily()
        
        # Log results
        success_count = result.get('success', 0)
        failed_count = result.get('failed', 0)
        total_count = success_count + failed_count
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        logger.info(f"Scrape completed in {duration}")
        logger.info(f"Results: {success_count}/{total_count} succeeded, {failed_count} failed")
        
        if 'results' in result:
            # Log individual ticker results
            for ticker, status in result['results'].items():
                if status == 'success':
                    logger.info(f"  ✓ {ticker}: Success")
                else:
                    logger.warning(f"  ✗ {ticker}: {status}")
        
        # Print summary to stdout (for cron/actions)
        print(f"Daily IV scrape complete: {success_count} succeeded, {failed_count} failed")
        
        # Exit with success even if some tickers failed
        # (complete failure would have been caught in except block)
        return 0
        
    except Exception as e:
        logger.error(f"Fatal error during scrape: {e}", exc_info=True)
        print(f"ERROR: Daily IV scrape failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)