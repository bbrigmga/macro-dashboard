"""
APScheduler Integration for Daily IV Scraping

This module provides an alternative to cron/GitHub Actions by running the
IV scraper as a background job within the Streamlit application.

Usage:
    from scripts.scheduler_integration import start_scheduler, stop_scheduler
    
    # In app.py
    start_scheduler()  # Call once when app starts
    
    # Optionally call stop_scheduler() on app shutdown
    stop_scheduler()

Requirements:
    - Add 'APScheduler>=3.10.0' to requirements.txt
    - Streamlit app must run continuously (not serverless)
    - Consider timezone settings for market hours
"""

import logging
import atexit
from datetime import datetime
from typing import Optional, TYPE_CHECKING

try:
    from apscheduler.schedulers.background import BackgroundScheduler  # type: ignore
    from apscheduler.triggers.cron import CronTrigger  # type: ignore
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False
    BackgroundScheduler = None  # type: ignore
    CronTrigger = None  # type: ignore

from data.iv_scraper import IVScraper
from data.iv_db import IVDatabase


logger = logging.getLogger(__name__)

# Global scheduler instance (type: ignore for when apscheduler is not available)
_scheduler: Optional["BackgroundScheduler"] = None  # type: ignore


def _scrape_job():
    """Background job function for IV scraping."""
    try:
        logger.info("Starting scheduled IV scrape...")
        
        db = IVDatabase()
        scraper = IVScraper(db)
        result = scraper.scrape_daily()
        
        success_count = result.get('success', 0)
        failed_count = result.get('failed', 0)
        
        logger.info(f"Scheduled scrape completed: {success_count} succeeded, {failed_count} failed")
        
    except Exception as e:
        logger.error(f"Scheduled scrape failed: {e}", exc_info=True)


def start_scheduler(
    hour: int = 16,
    minute: int = 30,
    timezone: str = "America/New_York"
) -> bool:
    """
    Start the background scheduler for daily IV scraping.
    
    Args:
        hour: Hour to run scrape (0-23, default 16 = 4 PM ET)
        minute: Minute to run scrape (0-59, default 30)
        timezone: Timezone for scheduling (default Eastern)
        
    Returns:
        bool: True if scheduler started successfully, False if APScheduler not available
    """
    global _scheduler
    
    if not APSCHEDULER_AVAILABLE:
        logger.warning("APScheduler not installed. Install with: pip install APScheduler>=3.10.0")
        return False
        
    if _scheduler is not None and _scheduler.running:
        logger.info("Scheduler already running")
        return True
        
    try:
        # Create scheduler
        _scheduler = BackgroundScheduler(timezone=timezone)  # type: ignore
        
        # Add job: Run Monday-Friday at specified time
        _scheduler.add_job(  # type: ignore
            _scrape_job,
            CronTrigger(hour=hour, minute=minute, day_of_week='mon-fri'),  # type: ignore
            id='daily_iv_scrape',
            name='Daily IV Scrape',
            max_instances=1,  # Prevent overlapping runs
            misfire_grace_time=3600  # Allow up to 1 hour delay
        )
        
        # Start scheduler
        _scheduler.start()  # type: ignore
        
        # Register shutdown handler
        atexit.register(stop_scheduler)
        
        next_run = _scheduler.get_job('daily_iv_scrape').next_run_time  # type: ignore
        logger.info(f"IV scraper scheduled to run weekdays at {hour:02d}:{minute:02d} {timezone}")
        logger.info(f"Next run: {next_run}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")
        return False


def stop_scheduler():
    """Stop the background scheduler."""
    global _scheduler
    
    if _scheduler is not None and _scheduler.running:
        try:
            _scheduler.shutdown(wait=False)
            logger.info("IV scraper scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")
        finally:
            _scheduler = None


def get_scheduler_status() -> dict:
    """
    Get current scheduler status and next run time.
    
    Returns:
        dict: Status information including running state and next run time
    """
    global _scheduler
    
    if not APSCHEDULER_AVAILABLE:
        return {
            'available': False,
            'running': False,
            'error': 'APScheduler not installed'
        }
        
    if _scheduler is None:
        return {
            'available': True,
            'running': False,
            'next_run': None
        }
        
    try:
        job = _scheduler.get_job('daily_iv_scrape')
        return {
            'available': True,
            'running': _scheduler.running,
            'next_run': job.next_run_time if job else None,
            'timezone': str(_scheduler.timezone) if hasattr(_scheduler, 'timezone') else None
        }
    except Exception as e:
        return {
            'available': True,
            'running': _scheduler.running if _scheduler else False,
            'error': str(e)
        }


def trigger_manual_scrape() -> dict:
    """
    Trigger an immediate IV scrape (useful for testing/manual runs).
    
    Returns:
        dict: Results from the scrape operation
    """
    try:
        logger.info("Manual IV scrape triggered")
        
        db = IVDatabase()
        scraper = IVScraper(db)
        result = scraper.scrape_daily()
        
        logger.info(f"Manual scrape completed: {result}")
        return result
        
    except Exception as e:
        error_msg = f"Manual scrape failed: {e}"
        logger.error(error_msg, exc_info=True)
        return {'success': 0, 'failed': 1, 'error': error_msg}


# Example usage in app.py:
"""
import streamlit as st
from scripts.scheduler_integration import start_scheduler, get_scheduler_status

# Start scheduler when app loads
if 'scheduler_started' not in st.session_state:
    scheduler_success = start_scheduler()
    st.session_state.scheduler_started = scheduler_success

# Show scheduler status in sidebar
with st.sidebar:
    status = get_scheduler_status()
    if status['available']:
        if status['running']:
            st.success("📅 IV Scraper: Scheduled")
            if status.get('next_run'):
                st.caption(f"Next run: {status['next_run'].strftime('%Y-%m-%d %H:%M')}")
        else:
            st.warning("📅 IV Scraper: Not scheduled")
    else:
        st.error("📅 APScheduler not available")
"""