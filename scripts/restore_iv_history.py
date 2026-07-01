#!/usr/bin/env python3
"""Restore IV database history from last good git commit and merge newer rows."""

from __future__ import annotations

import shutil
import sqlite3
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data/volatility/iv_data.db"
GOOD_REF = "ba0d85d:data/volatility/iv_data.db"
TMP_GOOD = ROOT / "data/volatility/iv_data.good_tmp.db"


def export_good_db() -> None:
    blob = subprocess.check_output(["git", "show", GOOD_REF], cwd=ROOT)
    TMP_GOOD.write_bytes(blob)


def merge_newer_rows(source_db: Path, target_db: Path, after: date) -> int:
    src = sqlite3.connect(source_db)
    dst = sqlite3.connect(target_db)
    rows = src.execute(
        """
        SELECT date, ticker, close_price, iv_30d, rv_30d, iv_premium, ytd_return
        FROM daily_iv
        WHERE date > ?
        ORDER BY date, ticker
        """,
        (after.isoformat(),),
    ).fetchall()
    dst.executemany(
        """
        INSERT OR REPLACE INTO daily_iv
        (date, ticker, close_price, iv_30d, rv_30d, iv_premium, ytd_return)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    dst.commit()
    src.close()
    dst.close()
    return len(rows)


def stats(db_path: Path) -> tuple[int, str, str]:
    conn = sqlite3.connect(db_path)
    spy_days = conn.execute(
        "SELECT COUNT(DISTINCT date) FROM daily_iv WHERE ticker='SPY'"
    ).fetchone()[0]
    row = conn.execute(
        "SELECT MIN(date), MAX(date) FROM daily_iv WHERE ticker='SPY'"
    ).fetchone()
    conn.close()
    return spy_days, row[0][:10], row[1][:10]


def main() -> int:
    if not DB.exists():
        print(f"No database at {DB}")
        return 1

    backup = DB.with_name(f"{DB.stem}.pre_restore{DB.suffix}")
    shutil.copy2(DB, backup)
    print(f"Backed up current DB to {backup}")

    export_good_db()
    good_days, good_first, good_last = stats(TMP_GOOD)
    print(f"Good git snapshot: {good_days} SPY days ({good_first} -> {good_last})")

    shutil.copy2(TMP_GOOD, DB)
    merged = merge_newer_rows(backup, DB, date.fromisoformat(good_last))
    print(f"Merged {merged} row(s) newer than {good_last}")

    final_days, first, last = stats(DB)
    print(f"Restored DB: {final_days} SPY days ({first} -> {last})")
    TMP_GOOD.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
