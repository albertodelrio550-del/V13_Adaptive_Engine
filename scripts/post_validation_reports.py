from __future__ import annotations

import argparse
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.V13_DoctrineFeedbackLoop import DoctrineFeedbackLoop, DoctrineMetrics

DECISIONS_DIR = Path("docs/DoctrineDecisions")
HEALTH_DIR = Path("reports/health")
ALERT_LOG = Path("logs/DoctrineAlerts.log")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run post-validation doctrine reporting once approval and safety checks finish.",
    )
    parser.add_argument(
        "--date",
        help="Date to report (YYYY-MM-DD). Defaults to the previous trading day.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip commander approval and safety validation checks.",
    )
    parser.add_argument(
        "--allow-warn",
        action="store_true",
        help="Treat WARN health status as acceptable for safety validation.",
    )
    parser.add_argument(
        "--notify",
        action="store_true",
        help="Echo newly created alerts to the CLI (adds an audible bell).",
    )
    parser.add_argument(
        "--recompute-metrics",
        action="store_true",
        help="Recalculate daily metrics instead of reusing prior snapshot entries.",
    )
    return parser.parse_args()


def parse_day(raw: Optional[str]) -> date:
    if raw:
        try:
            return date.fromisoformat(raw)
        except ValueError as exc:
            raise SystemExit(f"Invalid date value {raw!r}: {exc}") from exc
    # default to previous calendar day to cover overnight batch execution
    return date.today() - timedelta(days=1)


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        raise RuntimeError(f"Failed to parse JSON payload: {path} :: {exc}") from exc


def ensure_commander_approval(day: date) -> Path:
    decision_path = DECISIONS_DIR / f"{day:%Y-%m-%d}.json"
    payload = load_json(decision_path)
    if not payload.get("accepted"):
        raise RuntimeError(
            f"Commander decision for {day:%Y-%m-%d} not approved "
            f"({decision_path})."
        )
    return decision_path


def ensure_safety_validation(day: date, allow_warn: bool) -> Path:
    health_path = HEALTH_DIR / f"health_{day:%Y%m%d}.json"
    payload = load_json(health_path)
    status = (payload.get("status") or "").upper()
    allowed = {"PASS"}
    if allow_warn:
        allowed.add("WARN")
    if status not in allowed:
        raise RuntimeError(
            f"Safety validation for {day:%Y-%m-%d} has status {status or 'UNKNOWN'} "
            f"({health_path})."
        )
    return health_path


def load_alert_lines() -> List[str]:
    if not ALERT_LOG.exists():
        return []
    lines = []
    for raw in ALERT_LOG.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if stripped:
            lines.append(stripped)
    return lines


def announce_alerts(lines: Iterable[str]) -> None:
    for line in lines:
        print(f"[DOCTRINE ALERT] {line}")
    if lines:
        # simple audible bell for terminals that support it
        print("\a", end="")


def reuse_metrics(
    loop: DoctrineFeedbackLoop,
    day: date,
) -> Optional[DoctrineMetrics]:
    history: List[Tuple[date, DoctrineMetrics]] = loop._load_metric_history(limit=14, up_to=day)  # type: ignore[attr-defined]
    for entry_day, metrics in reversed(history):
        if entry_day == day:
            return metrics
    return None


def main() -> None:
    args = parse_args()
    target_day = parse_day(args.date)
    if not args.force:
        try:
            approval_path = ensure_commander_approval(target_day)
        except FileNotFoundError:
            raise SystemExit(
                f"Commander decision missing for {target_day:%Y-%m-%d}. "
                "Run doctrine_review.py to record approval first."
            )
        except RuntimeError as exc:
            raise SystemExit(exc)
        try:
            safety_path = ensure_safety_validation(target_day, args.allow_warn)
        except FileNotFoundError:
            raise SystemExit(
                f"Safety validation report missing for {target_day:%Y-%m-%d}. "
                "Run tests/phase8_healthcheck/run_all.py before generating reports."
            )
        except RuntimeError as exc:
            raise SystemExit(exc)
    else:
        approval_path = None
        safety_path = None

    loop = DoctrineFeedbackLoop(load_doctrines_flag=False)
    metrics: Optional[DoctrineMetrics] = None
    if not args.recompute_metrics:
        metrics = reuse_metrics(loop, target_day)
    if metrics is None:
        metrics = loop.collect_daily_metrics(target_day)

    before_alerts = load_alert_lines()
    report_path = loop.generate_doctrine_report(metrics, target_day)
    weekly_path = loop._maybe_generate_weekly_summary(target_day)  # type: ignore[attr-defined]
    after_alerts = load_alert_lines()

    new_alerts = after_alerts[len(before_alerts) :]
    if args.notify and new_alerts:
        announce_alerts(new_alerts)

    print("Doctrine reporting complete.")
    print(f" - Target day              : {target_day:%Y-%m-%d}")
    if approval_path:
        print(f" - Commander approval file : {approval_path}")
    if safety_path:
        print(f" - Safety validation file  : {safety_path}")
    print(f" - Daily report path       : {report_path}")
    if weekly_path:
        print(f" - Weekly summary path     : {weekly_path}")
    else:
        print(" - Weekly summary path     : (not generated today)")
    if new_alerts:
        print(f" - Alerts emitted          : {len(new_alerts)}")
    else:
        print(" - Alerts emitted          : none")


if __name__ == "__main__":
    main()
