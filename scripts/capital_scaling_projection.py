"""
capital_scaling_projection.py

Utility to generate Phase 8 scaling projections based on V13 block config.
Outputs the same metrics referenced in the Phase 8 runbook:
  - Gross capital
  - Daily PnL target (1%)
  - Max drawdown cap (-2%)
  - Network risk per trade (declining percentage)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Tuple

DEFAULT_BASE_CAPITAL = 5000.0
SCALING_RULES: List[Tuple[int, float]] = [
    (1, 0.01),
    (3, 0.0075),
    (5, 0.006),
    (10, 0.005),
]


def resolve_risk_pct(block_count: int) -> float:
    for threshold, pct in SCALING_RULES:
        if block_count <= threshold:
            return pct
    return SCALING_RULES[-1][1]


def projection(block_count: int, capital_per_block: float) -> dict:
    gross = block_count * capital_per_block
    risk_pct = resolve_risk_pct(block_count)
    return {
        "blocks": block_count,
        "gross_capital": round(gross, 2),
        "target_daily_pnl": round(gross * 0.01, 2),
        "max_drawdown": round(-gross * 0.02, 2),
        "risk_per_trade_usd": round(gross * risk_pct, 2),
        "risk_per_trade_pct": round(risk_pct * 100, 3),
    }


def render_table(rows: List[dict]) -> str:
    headers = [
        "# Blocks",
        "Gross Capital",
        "Target Day PnL (1%)",
        "Max DD (-2%)",
        "Risk per Trade",
        "Risk %",
    ]
    col_widths = [len(h) for h in headers]
    for row in rows:
        values = [
            str(row["blocks"]),
            f"{row['gross_capital']:.2f}",
            f"{row['target_daily_pnl']:.2f}",
            f"{row['max_drawdown']:.2f}",
            f"{row['risk_per_trade_usd']:.2f}",
            f"{row['risk_per_trade_pct']:.3f}%",
        ]
        for idx, value in enumerate(values):
            col_widths[idx] = max(col_widths[idx], len(value))
    lines = []
    header_line = " | ".join(h.ljust(col_widths[idx]) for idx, h in enumerate(headers))
    lines.append(header_line)
    lines.append("-+-".join("-" * w for w in col_widths))
    for row in rows:
        values = [
            str(row["blocks"]),
            f"{row['gross_capital']:.2f}",
            f"{row['target_daily_pnl']:.2f}",
            f"{row['max_drawdown']:.2f}",
            f"{row['risk_per_trade_usd']:.2f}",
            f"{row['risk_per_trade_pct']:.3f}%",
        ]
        lines.append(" | ".join(value.ljust(col_widths[idx]) for idx, value in enumerate(values)))
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Phase 8 scaling projection table.")
    parser.add_argument(
        "--blocks",
        type=int,
        nargs="+",
        default=[1, 3, 5, 10],
        help="Block counts to project (default: 1 3 5 10)",
    )
    parser.add_argument(
        "--base-capital",
        type=float,
        default=DEFAULT_BASE_CAPITAL,
        help="Capital per block (default: 5000)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON instead of table",
    )
    args = parser.parse_args()
    rows = [projection(count, args.base_capital) for count in sorted(set(args.blocks))]
    if args.json:
        print(json.dumps({"projections": rows}, indent=2))
    else:
        print(render_table(rows))


if __name__ == "__main__":
    main()
