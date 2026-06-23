"""CLI export for aligned daily ETF + macro spreadsheet."""
import argparse
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

# Project root on path when run as script
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

load_dotenv(_ROOT / ".env")

from data.market_macro_export import build_market_macro_export

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export aligned daily CPER/GLD/IEF/TIP + GDP/CPI spreadsheet (CSV)."
    )
    parser.add_argument(
        "--years",
        type=int,
        default=3,
        help="Lookback window in years (default: 3)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output CSV path (default: market_macro_analysis_<today>.csv)",
    )
    args = parser.parse_args()

    from datetime import date

    output = args.output or f"market_macro_analysis_{date.today().isoformat()}.csv"

    try:
        df = build_market_macro_export(years=args.years)
    except Exception as exc:
        logger.error("Export failed: %s", exc)
        return 1

    if df.empty:
        logger.error("No data to export")
        return 1

    df.to_csv(output, index=False)
    logger.info("Exported %d rows to %s", len(df), output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
