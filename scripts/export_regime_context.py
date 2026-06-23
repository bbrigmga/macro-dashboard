#!/usr/bin/env python3
"""Export regime_context.json for Moon Machine / LLM macro scoring."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import data.numpy_compat  # noqa: F401, E402

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_OUTPUT = ROOT / "data" / "macro_exports" / "regime_context.json"


def main() -> int:
    output = DEFAULT_OUTPUT
    if len(sys.argv) > 1:
        output = Path(sys.argv[1])

    try:
        from data.fred_client import FredClient
        from data.indicators import IndicatorData
        from data.regime_llm_export import write_regime_context_json

        fred = FredClient(cache_enabled=True)
        data = IndicatorData(fred).get_regime_quadrant_data(lookback_days=2520, trail_days=252)
        trail = data.get("trail_data")
        if data.get("current_regime") == "Unknown":
            logger.warning("Regime data may be empty or degraded")

        path = write_regime_context_json(output, data)
        as_of = "unknown"
        if trail is not None and hasattr(trail, "empty") and not trail.empty:
            as_of = str(trail["Date"].iloc[-1])[:10]
        logger.info("Wrote %s (regime=%s, as_of=%s)", path, data.get("current_regime"), as_of)
        return 0
    except Exception as exc:
        logger.error("Export failed: %s", exc, exc_info=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
