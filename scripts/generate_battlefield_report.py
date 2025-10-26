"""
generate_battlefield_report.py

Summarize the last V13 night session without overloading runtime.
Parses lightweight per-cycle soldier telemetry and broker activities
to produce a concise battlefield report for review.
"""

from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Dict, List, Any

import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))

try:
    from trade_core import get_account_activities
except Exception:  # pragma: no cover
    get_account_activities = None  # type: ignore


LOGS = Path("logs")
REPORTS = Path("reports")


def _iso(t: int) -> str:
    return datetime.fromtimestamp(t, tz=timezone.utc).isoformat()


def load_soldier_ops(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out


def summarize_soldiers(cycles: List[Dict[str, Any]]) -> Dict[str, Any]:
    mode_counts = Counter(c.get("mode", "HOLD") for c in cycles)
    per_soldier_scores: Dict[str, List[float]] = defaultdict(list)
    for c in cycles:
        for s in c.get("soldiers", []):
            name = str(s.get("name", "?"))
            try:
                per_soldier_scores[name].append(float(s.get("score", 0.0)))
            except Exception:
                pass
    soldier_summary = {
        name: {
            "avg_score": round(mean(vals), 4) if vals else 0.0,
            "cycles": len(vals),
        }
        for name, vals in per_soldier_scores.items()
    }
    sorted_soldiers = dict(sorted(soldier_summary.items(), key=lambda kv: kv[1]["avg_score"], reverse=True))
    return {
        "mode_counts": dict(mode_counts),
        "soldiers": sorted_soldiers,
    }


def estimate_realized_pnl(start_ts: int, end_ts: int) -> float:
    if get_account_activities is None:
        return 0.0
    start_iso = datetime.fromtimestamp(start_ts, tz=timezone.utc).isoformat()
    end_iso = datetime.fromtimestamp(end_ts, tz=timezone.utc).isoformat()
    try:
        acts = get_account_activities(start_iso, end_iso)
    except Exception:
        return 0.0
    realized = 0.0
    for a in acts:
        if "realizedPnl" in a:
            try:
                realized += float(a.get("realizedPnl", 0))
            except Exception:
                continue
        elif a.get("activity_type") == "FILL":
            try:
                realized += float(a.get("net_amount", 0))
            except Exception:
                continue
    return realized


def main() -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)

    soldier_path = LOGS / "soldier_ops.jsonl"
    cycles = load_soldier_ops(soldier_path)
    if not cycles:
        print("No soldier_ops.jsonl found; nothing to report.")
        return

    start_ts = cycles[0]["ts"]
    end_ts = cycles[-1]["ts"]
    summary = summarize_soldiers(cycles)
    realized_pnl = estimate_realized_pnl(start_ts, end_ts)

    # Top spikes by absolute weighted score
    top_spikes = sorted(cycles, key=lambda c: abs(float(c.get("weighted_score", 0.0))), reverse=True)[:10]

    # Render Markdown
    now = datetime.now(timezone.utc)
    rpt_name = f"battlefield_{now.strftime('%Y%m%d_%H%M%S')}.md"
    out_path = REPORTS / rpt_name

    lines: List[str] = []
    lines.append(f"# V13 Battlefield Report — {now.strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("")
    lines.append("## Session Overview")
    lines.append(f"- Window: {_iso(start_ts)} → {_iso(end_ts)}")
    lines.append(f"- Cycles: {len(cycles)} (interval ~10s)")
    lines.append(f"- Estimated Realized PnL: {realized_pnl:.2f} (quote asset)")
    lines.append("")
    lines.append("## Tactical Modes")
    for mode, count in summary["mode_counts"].items():
        lines.append(f"- {mode}: {count}")
    lines.append("")
    lines.append("## Soldier Performance (avg score, cycles)")
    for name, stats in summary["soldiers"].items():
        lines.append(f"- {name}: avg={stats['avg_score']:.3f}, cycles={stats['cycles']}")
    lines.append("")
    lines.append("## Notable Spikes (|weighted_score|)")
    for c in top_spikes:
        lines.append(f"- {_iso(c['ts'])} | mode={c['mode']} | ws={float(c.get('weighted_score', 0.0)):.3f} | conf={float(c.get('confidence', 0.0)):.2f}")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Report written to {out_path}")


if __name__ == "__main__":
    main()

