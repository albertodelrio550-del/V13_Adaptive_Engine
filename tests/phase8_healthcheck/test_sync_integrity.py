from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import utils


def _parse_iso(ts: str) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def main() -> None:
    status_path = Path("data/V13_Status.json")
    payload = utils.load_json(status_path)
    if not payload:
        utils.exit_with_status(
            "WARN",
            f"Status payload missing at {status_path}",
            "test_sync_integrity",
            {"status_path": str(status_path)},
        )

    history = payload.get("history", [])
    last_timestamp = payload.get("timestamp")
    parsed_last = _parse_iso(last_timestamp) if last_timestamp else None
    now = datetime.now(timezone.utc)
    stale = False
    if parsed_last:
        stale = now - parsed_last > timedelta(minutes=15)

    issues = []
    if len(history) > 10:
        issues.append("History length exceeds rolling window (10)")
    if stale:
        issues.append("Last status update is older than 15 minutes")

    status = "PASS"
    message = "SyncLoop status within tolerance"
    if issues:
        status = "FAIL"
        message = "; ".join(issues)

    details = {
        "history_length": len(history),
        "last_timestamp": last_timestamp,
        "stale": stale,
        "issues": issues,
    }
    utils.exit_with_status(status, message, "test_sync_integrity", details)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover
        utils.exit_with_status("FAIL", f"Unhandled exception: {exc}", "test_sync_integrity", {})
