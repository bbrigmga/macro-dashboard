#!/usr/bin/env python3
"""Print IV database collection stats (used by CI and local diagnostics)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# CI uses stdout for KEY=value lines; keep logs off stdout in env mode.
if "--format" in sys.argv:
    fmt_idx = sys.argv.index("--format")
    if fmt_idx + 1 < len(sys.argv) and sys.argv[fmt_idx + 1] == "env":
        os.environ.setdefault("LOG_TO_CONSOLE", "false")
        os.environ.setdefault("LOG_TO_FILE", "false")

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from data.iv_db import IVDatabase  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Print IV DB collection stats")
    parser.add_argument(
        "--format",
        choices=["human", "env"],
        default="human",
        help="human: readable lines; env: KEY=value for shell",
    )
    args = parser.parse_args()

    with IVDatabase() as db:
        stats = db.get_collection_stats(anchor_ticker="SPY")

    total = stats["total_days"]
    latest = stats["latest_date"]
    first = stats["first_date"]

    if args.format == "env":
        print(f"IV_SPY_DAYS={total}")
        print(f"IV_FIRST_DATE={first.isoformat() if first else ''}")
        print(f"IV_LATEST_DATE={latest.isoformat() if latest else ''}")
        print(f"IV_MISSING_GAPS={len(stats['missing_days'])}")
        return 0

    if total == 0:
        print("IV database: no SPY history stored yet")
        return 0

    print(f"IV database: {total} trading day(s) stored for SPY")
    print(f"  Range: {first} -> {latest}")
    print(f"  Gaps in range: {len(stats['missing_days'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
