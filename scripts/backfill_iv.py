#!/usr/bin/env python3
"""
Backfill a missing trading day in the IV/RV database.

Uses historical close + realized vol for the target date. Implied vol is estimated
from neighboring rows already stored in the database (Yahoo does not provide
historical options chains for past dates).

Usage:
    python scripts/backfill_iv.py --date 2026-06-02
    python scripts/backfill_iv.py --date 2026-06-02 --force
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, datetime
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data.iv_db import IVDatabase
from data.iv_scraper import IVScraper


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("scripts/scrape_iv.log", mode="a"),
        ],
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill one trading day of IV/RV data")
    parser.add_argument(
        "--date",
        required=True,
        help="Target trading day to backfill (YYYY-MM-DD), e.g. 2026-06-02",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing rows for this date if present",
    )
    return parser.parse_args()


def main() -> int:
    setup_logging()
    logger = logging.getLogger(__name__)
    args = parse_args()

    try:
        target = date.fromisoformat(args.date)
    except ValueError:
        print(f"Invalid --date {args.date!r}; use YYYY-MM-DD")
        return 1

    start = datetime.now()
    logger.info("Starting IV backfill for %s at %s", target, start)

    try:
        db = IVDatabase()
        scraper = IVScraper(db)
        result = scraper.backfill_date(target, force=args.force)
    except ValueError as e:
        print(f"Backfill aborted: {e}")
        return 1
    except Exception as e:
        logger.error("Fatal backfill error: %s", e, exc_info=True)
        print(f"ERROR: backfill failed: {e}")
        return 1

    print(
        f"Backfill {result['date']}: {result['success']} succeeded, "
        f"{result['skipped']} skipped, {result['failed']} failed"
    )
    if result.get("failed_tickers"):
        print(f"Failed tickers: {', '.join(result['failed_tickers'])}")

    methods = result.get("ticker_meta", {})
    interpolated = sum(1 for m in methods.values() if m == "interpolated")
    prior = sum(1 for m in methods.values() if m == "prior_day")
    if interpolated or prior:
        print(
            f"IV source: {interpolated} interpolated, {prior} prior-day "
            "(historical options IV not available for past dates)"
        )

    return 0 if result["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
