from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Tuple


@dataclass
class CriterionResult:
    name: str
    passed: bool
    details: str


def _read_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _load_metrics(metrics_path: Path) -> List[dict]:
    if not metrics_path.exists():
        return []
    entries = []
    for line in metrics_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def check_health_streak(root: Path) -> CriterionResult:
    metrics_path = root / "reports" / "health" / "metrics_daily.jsonl"
    entries = _load_metrics(metrics_path)
    recent = entries[-28:]
    if len(recent) < 28:
        return CriterionResult(
            "health_streak",
            False,
            f"Found {len(recent)} health entries; need 28 consecutive PASS days.",
        )
    failed = [entry for entry in recent if entry.get("status") != "PASS"]
    if failed:
        return CriterionResult(
            "health_streak",
            False,
            f"{len(failed)} of last 28 days not PASS.",
        )
    return CriterionResult(
        "health_streak",
        True,
        "28 consecutive nightly health reports PASS.",
    )


def check_audit_integrity(root: Path) -> CriterionResult:
    seal_path = root / "logs" / "GLOBAL_SEAL.txt"
    if not seal_path.exists():
        return CriterionResult("audit_integrity", False, "GLOBAL_SEAL.txt missing.")
    lines = [
        line.strip()
        for line in seal_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not lines:
        return CriterionResult("audit_integrity", False, "Seal file empty.")
    composite_line = None
    for line in lines:
        if line.startswith("COMPOSITE "):
            composite_line = line
            break
    if not composite_line:
        return CriterionResult("audit_integrity", False, "Composite digest missing.")
    return CriterionResult("audit_integrity", True, "Global audit seal present.")


def check_drawdown_compliance(root: Path) -> CriterionResult:
    status_path = root / "data" / "V13_Status.json"
    status = _read_json(status_path) or {}
    global_state = status.get("global") or {}
    drawdown = float(global_state.get("weighted_drawdown", 0.0) or 0.0)
    cap = float(global_state.get("max_cap", 0.0) or 0.0)
    if cap <= 0:
        return CriterionResult(
            "drawdown_cap",
            False,
            "Max drawdown cap missing from status snapshot.",
        )
    if drawdown > cap:
        return CriterionResult(
            "drawdown_cap",
            False,
            f"Weighted drawdown {drawdown:.2f} exceeds cap {cap:.2f}.",
        )
    return CriterionResult(
        "drawdown_cap",
        True,
        f"Weighted drawdown {drawdown:.2f}% within cap {cap:.2f}%.",
    )


def check_pnl_consistency(root: Path) -> CriterionResult:
    baseline_path = root / "data" / "performance_baseline.json"
    baseline = _read_json(baseline_path)
    if not isinstance(baseline, dict):
        return CriterionResult(
            "pnl_consistency",
            False,
            "Baseline file data/performance_baseline.json missing.",
        )
    expected = float(baseline.get("expected_pnl", 0.0) or 0.0)
    sealed = float(baseline.get("sealed_pnl", 0.0) or 0.0)
    tolerance = baseline.get("tolerance_pct", 5.0)
    if expected == 0:
        delta = abs(sealed)
        threshold = tolerance
    else:
        delta = abs(sealed - expected)
        threshold = abs(expected) * (tolerance / 100.0)
    if delta > threshold:
        return CriterionResult(
            "pnl_consistency",
            False,
            f"Sealed PnL {sealed:.2f} deviates >{tolerance}% from expected {expected:.2f}.",
        )
    return CriterionResult(
        "pnl_consistency",
        True,
        f"Sealed PnL {sealed:.2f} within ±{tolerance}% of expected {expected:.2f}.",
    )


def check_commander_approval(root: Path) -> CriterionResult:
    decisions_dir = root / "docs" / "DoctrineDecisions"
    if not decisions_dir.exists():
        return CriterionResult(
            "commander_approval", False, "Doctrine decisions directory missing."
        )
    accepted = False
    for path in sorted(decisions_dir.glob("*.json")):
        payload = _read_json(path)
        if isinstance(payload, dict) and payload.get("accepted"):
            accepted = True
            break
    if not accepted:
        return CriterionResult(
            "commander_approval",
            False,
            "No accepted doctrine decision found.",
        )
    return CriterionResult(
        "commander_approval",
        True,
        "Commander approval recorded.",
    )


def evaluate_phase8_exit(root: Path = Path(".")) -> Tuple[bool, List[CriterionResult]]:
    root = root.resolve()
    results = [
        check_health_streak(root),
        check_audit_integrity(root),
        check_drawdown_compliance(root),
        check_pnl_consistency(root),
        check_commander_approval(root),
    ]
    passed = all(result.passed for result in results)
    return passed, results


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Phase 8 exit criteria.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("."),
        help="Path to project root (default: current directory).",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output.")
    args = parser.parse_args()

    status, results = evaluate_phase8_exit(args.root)
    stamp = datetime.now(timezone.utc).isoformat()
    header = "[PASS]" if status else "[FAIL]"
    print(f"{header} Phase 8 exit assessment :: {stamp}")
    for result in results:
        label = "OK" if result.passed else "FAIL"
        print(f" - {result.name:20s} [{label}] {result.details}")
    return 0 if status else 1


if __name__ == "__main__":
    raise SystemExit(main())
