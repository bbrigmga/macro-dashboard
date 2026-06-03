#!/usr/bin/env python3
"""Create a timestamped backup of the IV SQLite database."""

from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_DB = Path("data/volatility/iv_data.db")


def main() -> int:
    db_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DB
    if not db_path.exists():
        print(f"No database found at {db_path}")
        return 1

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.with_name(f"{db_path.stem}.backup_{stamp}{db_path.suffix}")
    shutil.copy2(db_path, backup_path)

    # Also refresh a stable "latest backup" pointer for quick restore
    latest_backup = db_path.with_name(f"{db_path.stem}.latest_backup{db_path.suffix}")
    shutil.copy2(db_path, latest_backup)

    print(f"Backup created: {backup_path}")
    print(f"Latest backup:  {latest_backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
