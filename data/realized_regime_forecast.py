"""Load quarter-ahead realized macro regime forecasts from the backtester export."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_FORECAST_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "GDP_Inflation_Proxy-Backtester"
    / "results"
    / "regime_forecast.json"
)


def load_realized_regime_forecast(
    path: Path | str | None = None,
) -> dict[str, Any] | None:
    """
    Load regime_forecast.json produced by GDP_Inflation_Proxy-Backtester.

    Returns None if the file is missing or invalid.
    """
    forecast_path = Path(path) if path is not None else DEFAULT_FORECAST_PATH
    if not forecast_path.is_file():
        logger.debug("Realized regime forecast not found: %s", forecast_path)
        return None

    try:
        payload = json.loads(forecast_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Failed to read realized regime forecast (%s): %s", forecast_path, exc)
        return None

    if not isinstance(payload, dict) or "horizons" not in payload:
        logger.warning("Invalid realized regime forecast schema: %s", forecast_path)
        return None

    payload["_source_path"] = str(forecast_path)
    return payload


def attach_realized_regime_forecast(
    regime_data: dict[str, Any],
    path: Path | str | None = None,
) -> dict[str, Any]:
    """Attach backtester realized macro forecast to regime quadrant payload."""
    forecast = load_realized_regime_forecast(path)
    regime_data["realized_macro_forecast"] = forecast
    return regime_data
