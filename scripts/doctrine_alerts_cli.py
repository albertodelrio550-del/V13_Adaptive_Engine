from __future__ import annotations

import argparse
import subprocess
import time
from pathlib import Path
from typing import Iterable, List

ALERT_LOG = Path("logs/DoctrineAlerts.log")
STATE_PATH = Path("logs/DoctrineAlerts.cursor")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="CLI notifier for Doctrine alert log events.",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Continuously watch the alert log for new entries.",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=15.0,
        help="Polling interval in seconds when --watch is used (default: 15s).",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Ignore stored cursor and replay the entire log on next read.",
    )
    parser.add_argument(
        "--beep",
        action="store_true",
        help="Emit a terminal bell when new alerts are detected.",
    )
    parser.add_argument(
        "--exec",
        dest="exec_command",
        help="Optional shell command to execute once per detected alert.",
    )
    return parser.parse_args()


def ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def read_alerts() -> List[str]:
    if not ALERT_LOG.exists():
        return []
    lines: List[str] = []
    for raw in ALERT_LOG.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if stripped:
            lines.append(stripped)
    return lines


def read_cursor() -> int:
    if not STATE_PATH.exists():
        return 0
    try:
        return int(STATE_PATH.read_text(encoding="utf-8").strip() or "0")
    except Exception:  # pragma: no cover - defensive
        return 0


def write_cursor(value: int) -> None:
    ensure_dir(STATE_PATH)
    STATE_PATH.write_text(str(value), encoding="utf-8")


def emit_alerts(lines: Iterable[str], beep: bool, exec_command: str | None) -> None:
    for line in lines:
        print(f"[DOCTRINE ALERT] {line}")
        if exec_command:
            try:
                subprocess.run(exec_command, shell=True, check=False)
            except Exception:  # pragma: no cover - defensive
                pass
    if beep and lines:
        print("\a", end="")


def process_once(beep: bool, exec_command: str | None, reset_cursor: bool) -> int:
    alerts = read_alerts()
    if reset_cursor:
        start_index = 0
    else:
        start_index = min(read_cursor(), len(alerts))
    new_entries = alerts[start_index:]
    emit_alerts(new_entries, beep, exec_command)
    write_cursor(len(alerts))
    return len(new_entries)


def main() -> None:
    args = parse_args()
    if args.reset:
        write_cursor(0)

    if not args.watch:
        count = process_once(args.beep, args.exec_command, args.reset)
        if count == 0:
            print("No new doctrine alerts.")
        return

    print("Watching Doctrine alerts. Press Ctrl+C to stop.")
    try:
        while True:
            process_once(args.beep, args.exec_command, False)
            time.sleep(max(args.interval, 1.0))
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()

