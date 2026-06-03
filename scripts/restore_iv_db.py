#!/usr/bin/env python3
"""Restore IV database from latest local backup."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

DEFAULT_DB = Path("data/volatility/iv_data.db")
LATEST_BACKUP = Path("data/volatility/iv_data.latest_backup.db")


def main() -> int:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DB
    source = Path(sys.argv[2]) if len(sys.argv) > 2 else LATEST_BACKUP

    if not source.exists():
        print(f"No backup found at {source}")
        print("Create one with: python scripts/backup_iv_db.py")
        return 1

    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        pre_restore = target.with_name(f"{target.stem}.pre_restore{target.suffix}")
        shutil.copy2(target, pre_restore)
        print(f"Current DB preserved at: {pre_restore}")

    shutil.copy2(source, target)
    print(f"Restored {source} -> {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
