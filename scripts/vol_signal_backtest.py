#!/usr/bin/env python3
"""Run IV/RV contrarian signal backtest and print summary tables."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from data.vol_signal_backtest import (  # noqa: E402
    FORWARD_HORIZONS,
    format_backtest_summary_table,
    run_vol_signal_backtest,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="IV/RV contrarian signal backtest")
    parser.add_argument(
        "--ticker",
        action="append",
        help="Limit to ticker(s); repeatable. Default: full ETF universe",
    )
    parser.add_argument(
        "--horizon",
        type=int,
        default=21,
        choices=FORWARD_HORIZONS,
        help="Forward return horizon in trading days (default: 21)",
    )
    args = parser.parse_args()

    result = run_vol_signal_backtest(tickers=args.ticker)
    meta = result.get("metadata", {})

    if meta.get("n_events", 0) == 0:
        print(
            "No backtest events — need more history in iv_data.db "
            "(~27+ trading days per ticker; 85+ for full 63D horizon)."
        )
        return 1

    print(
        f"Events: {meta['n_events']} | "
        f"Range: {meta.get('date_start')} -> {meta.get('date_end')} | "
        f"Tickers: {', '.join(meta.get('tickers', []))}"
    )

    ic = result.get("ic_by_horizon", {}).get(args.horizon)
    if ic is not None:
        print(
            f"Information coefficient (Spearman, net score vs fwd {args.horizon}d return): "
            f"{ic:.4f}"
        )

    calibration = result.get("calibration_by_horizon", {}).get(args.horizon, {})
    if calibration:
        ic_neg = calibration.get("ic_negated_net_score")
        if ic_neg is not None:
            print(
                f"Information coefficient (Spearman, negated net score vs fwd "
                f"{args.horizon}d return): {ic_neg:.4f}"
            )
        ic_by_bucket = calibration.get("ic_by_bucket") or {}
        if ic_by_bucket:
            print(f"\n=== Per-bucket Spearman IC ({args.horizon}d) ===")
            for bucket, bucket_ic in sorted(ic_by_bucket.items()):
                print(f"  {bucket}: {bucket_ic:.4f}")
        ic_ensemble = calibration.get("ic_ensemble_score")
        if ic_ensemble is not None:
            print(
                f"Information coefficient (Spearman, ensemble score vs fwd "
                f"{args.horizon}d return): {ic_ensemble:.4f}"
            )
        ic_velocity = calibration.get("ic_prem_z_velocity")
        if ic_velocity is not None:
            print(
                f"Information coefficient (Spearman, prem_z_velocity vs fwd "
                f"{args.horizon}d return): {ic_velocity:.4f}"
            )

    table = format_backtest_summary_table(result, horizon=args.horizon)
    if table.empty:
        print("No summary rows for this horizon.")
        return 1

    print(f"\n=== Forward {args.horizon}-day outcomes ===\n")
    print(table.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
