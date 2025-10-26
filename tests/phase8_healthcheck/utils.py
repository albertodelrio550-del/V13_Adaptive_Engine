import configparser
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

REPORTS_DIR = Path("reports/health")
LOGS_DIR = Path("logs")
DATA_DIR = Path("data")
CONFIG_DIR = Path("config")


def ensure_reports_dir() -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return REPORTS_DIR


def write_report(name: str, payload: Dict[str, Any]) -> Path:
    ensure_reports_dir()
    path = REPORTS_DIR / f"{name}.json"
    payload = dict(payload)
    payload.setdefault("generated_at", datetime.now(timezone.utc).isoformat())
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except Exception as exc:
        raise RuntimeError(f"Failed to parse JSON file {path}: {exc}") from exc


def load_json_lines(path: Path) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    if not path.exists():
        return entries
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    if isinstance(value, str):
        cleaned = value.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(cleaned)
        except ValueError:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    return None


def block_config_map() -> Dict[str, Dict[str, Any]]:
    config_path = CONFIG_DIR / "V13_Blocks.ini"
    parser = configparser.ConfigParser()
    parser.optionxform = str
    if not config_path.exists():
        return {}
    parser.read(config_path, encoding="utf-8")
    cfg: Dict[str, Dict[str, Any]] = {}
    for section in parser.sections():
        if section.upper() == "GLOBAL":
            continue
        entry = parser[section]
        block_id = section.strip().upper()
        cfg[block_id] = {
            "mode": entry.get("MODE", "Balanced"),
            "capital": float(entry.get("CAPITAL", 5000)),
            "risk_ceiling": float(entry.get("RISK_CEILING_PCT", 2.0)),
        }
    return cfg


def summarise_latency(
    entries: Iterable[Dict[str, Any]],
    max_age_seconds: int = 24 * 60 * 60,
) -> Dict[str, Any]:
    per_block: Dict[str, List[float]] = {}
    totals: List[float] = []
    cutoff = None
    if max_age_seconds is not None:
        cutoff = datetime.now(timezone.utc).timestamp() - max_age_seconds
    for entry in entries:
        if cutoff is not None:
            ts = _parse_timestamp(entry.get("timestamp"))
            if ts and ts.timestamp() < cutoff:
                continue
        event_type = (entry.get("event") or "").upper()
        if event_type and event_type != "FILLED":
            continue
        latency = entry.get("since_ack_ms")
        if latency is None:
            latency = entry.get("since_intent_ms")
        if latency is None:
            continue
        try:
            latency = float(latency)
        except (TypeError, ValueError):
            continue
        block_id = str(entry.get("block_id") or "UNASSIGNED").upper()
        per_block.setdefault(block_id, []).append(latency)
        totals.append(latency)
    summary: Dict[str, Any] = {"per_block": {}}
    if totals:
        summary["avg_latency_ms"] = statistics.fmean(totals)
        summary["max_latency_ms"] = max(totals)
    for block_id, values in per_block.items():
        summary["per_block"][block_id] = {
            "count": len(values),
            "avg": statistics.fmean(values),
            "max": max(values),
        }
    summary["sample_count"] = len(totals)
    return summary


def todays_report_path(suffix: str) -> Path:
    ensure_reports_dir()
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    return REPORTS_DIR / f"{suffix}_{day}.json"


def append_daily_metrics(payload: Dict[str, Any]) -> None:
    ensure_reports_dir()
    log_path = REPORTS_DIR / "metrics_daily.jsonl"
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload) + "\n")


def exit_with_status(status: str, message: str, report_name: str, details: Dict[str, Any]) -> None:
    payload = {
        "status": status,
        "message": message,
        "details": details,
    }
    write_report(report_name, payload)
    if status == "FAIL":
        sys.exit(1)
    sys.exit(0)
