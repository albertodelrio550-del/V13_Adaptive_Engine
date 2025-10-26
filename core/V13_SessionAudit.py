"""
V13 Session Audit
-----------------
Rich session auditing utilities for V13, combining integrity checks,
runtime event capture, and post-session reporting so we can learn fast.
"""

import csv
import hashlib
import json
import time
from collections import Counter, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.V13_DoctrineFeedbackLoop import DoctrineFeedbackLoop
from core.V13_LogFormatter import log_event
from trade_core import get_account, get_account_activities

ROOT = Path(__file__).resolve().parents[1]
CORE_PATH = ROOT / "core"
LOG_PATH = ROOT / "logs"
DATA_PATH = ROOT / "data"
REPORT_FILE = LOG_PATH / "V13_session_audit_report.json"
SHADOW_LOG = LOG_PATH / "Audit_Shadow.log"
TRADE_REPORT_FILE = LOG_PATH / "trade_report.json"

MONITORED_MODULES = [
    "V13_LaunchSequence.py",
    "V13_TelemetryFusion.py",
    "V13_AdaptiveCycle.py",
    "V13_RiskSentinel.py",
    "V13_DoctrineFeedbackLoop.py",
    "V13_PerformanceTracker.py",
]

MONITORED_LOGS = [
    "V13_cycle_status.log",
    "V13_risk_status.log",
    "V13_commander_bridge.log",
    "V13_performance_tracker.log",
]


# ---------------------------------------------------------------------------
# Utility helpers for the legacy pre/post launch audits
# ---------------------------------------------------------------------------
def file_hash(path: Path) -> str:
    """Return a short SHA256 checksum for a file."""
    if not path.exists():
        return "MISSING"
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8192):
            digest.update(chunk)
    return digest.hexdigest()[:16]


def collect_hashes(base_path: Path, files: List[str]) -> Dict[str, str]:
    return {name: file_hash(base_path / name) for name in files}


def log_check() -> Dict[str, str]:
    status: Dict[str, str] = {}
    for log_name in MONITORED_LOGS:
        target = LOG_PATH / log_name
        if not target.exists():
            status[log_name] = "NOT FOUND"
        else:
            status[log_name] = f"{target.stat().st_size} bytes"
    return status


def _write_report_payload(payload: Dict[str, Any]) -> None:
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def pre_launch_audit() -> Dict[str, Any]:
    """Capture module hashes and log presence before boot."""
    print("=" * 62)
    print(" V13 SessionAudit :: PRE-LAUNCH VERIFICATION")
    print("=" * 62)

    module_hashes = collect_hashes(CORE_PATH, MONITORED_MODULES)
    log_status = log_check()
    audit_report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "module_hashes": module_hashes,
        "log_status": log_status,
        "status": "READY" if all(v != "MISSING" for v in module_hashes.values()) else "FAILED",
    }

    payload = {"pre_launch": audit_report}
    _write_report_payload(payload)

    for name, digest in module_hashes.items():
        print(f"  {name:<35} {digest}")
    for name, status in log_status.items():
        print(f"  {name:<35} {status}")

    print(f"\nSystem Integrity: {audit_report['status']}")
    print(f"Audit report saved -> {REPORT_FILE}")
    print("=" * 62)
    return audit_report


def post_session_audit() -> None:
    """Compare current hashes with the pre-launch snapshot."""
    print("=" * 62)
    print(" V13 SessionAudit :: POST-SESSION CHECK")
    print("=" * 62)

    if not REPORT_FILE.exists():
        print(" ! No pre-launch audit found. Run pre_launch_audit() first.")
        return

    try:
        payload = json.loads(REPORT_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print(" ! Audit report is malformed. Re-run pre_launch_audit().")
        return

    pre_data = payload.get("pre_launch") or {}
    module_snapshot = pre_data.get("module_hashes", {})
    current_hashes = collect_hashes(CORE_PATH, MONITORED_MODULES)

    mismatches = {}
    for name, original in module_snapshot.items():
        if original != current_hashes.get(name):
            mismatches[name] = {"before": original, "after": current_hashes.get(name)}

    if mismatches:
        print(" ! Module integrity mismatch detected:")
        for name, delta in mismatches.items():
            print(f"   {name}: {delta}")
    else:
        print(" . All modules verified identical since pre-launch.")

    print("Post-session audit complete.")
    print("=" * 62)


# ---------------------------------------------------------------------------
# SessionAudit class with enriched reporting
# ---------------------------------------------------------------------------
class SessionAudit:
    """Runtime session monitor that produces a detailed final report."""

    def __init__(self) -> None:
        self.logs_dir = LOG_PATH
        self.data_dir = DATA_PATH
        self.docs_dir = ROOT / "docs"

        self.audit_csv = self.logs_dir / "Audit_DB.csv"
        self.audit_json = self.logs_dir / "Audit_DB.json"
        self.summary_path = REPORT_FILE
        self.shadow_log = SHADOW_LOG
        self.hash_list = self.docs_dir / "Doctrine_V13" / "Integrity_HashList.md5"

        self.feedback = DoctrineFeedbackLoop()
        self.session_id = datetime.now().strftime("V13_%Y%m%d_%H%M%S")
        self.active = False
        self.records: List[Dict[str, Any]] = []
        self.started_at: Optional[datetime] = None
        self.ended_at: Optional[datetime] = None
        self.baseline_status: Dict[str, Any] = {}
        self.baseline_metrics: Optional[Dict[str, Any]] = None
        self.baseline_capital: Optional[float] = None
        self._ensure_headers()

    # ------------------------------------------------------------------
    # Housekeeping
    # ------------------------------------------------------------------
    def _ensure_headers(self) -> None:
        if not self.audit_csv.exists():
            self.audit_csv.parent.mkdir(parents=True, exist_ok=True)
            with self.audit_csv.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Timestamp", "Session_ID", "Event", "Status", "Details"])

        if not self.audit_json.exists():
            self.audit_json.write_text(json.dumps({"sessions": []}, indent=4), encoding="utf-8")

    def _record_event(self, event: str, status: str, details: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        record = {
            "Timestamp": timestamp,
            "Session_ID": self.session_id,
            "Event": event,
            "Status": status,
            "Details": details,
        }
        self.records.append(record)
        log_event("SessionAudit", "INFO", f"{event}: {details}")

        with self.audit_csv.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow([timestamp, self.session_id, event, status, details])

        try:
            data = json.loads(self.audit_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {"sessions": []}
        data.setdefault("sessions", []).append(record)
        self.audit_json.write_text(json.dumps(data, indent=4), encoding="utf-8")

        try:
            self.shadow_log.parent.mkdir(parents=True, exist_ok=True)
            with self.shadow_log.open("a", encoding="utf-8") as shadow_f:
                shadow_f.write(json.dumps(record) + "\n")
        except Exception as exc:
            log_event("SessionAudit", "WARN", f"Shadow log failure: {exc}")

    # ------------------------------------------------------------------
    # Data collection helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_iso(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        value = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(value)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            return None

    def _load_json(self, path: Path) -> Optional[Dict[str, Any]]:
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            log_event("SessionAudit", "WARN", f"Failed to parse JSON {path}: {exc}")
            return None

    def _latest_metric_entry(
        self, start: Optional[datetime] = None, end: Optional[datetime] = None
    ) -> Optional[Dict[str, Any]]:
        metrics_path = self.logs_dir / "V13_performance_metrics.jsonl"
        if not metrics_path.exists():
            return None
        lines = deque(maxlen=500)
        with metrics_path.open("r", encoding="utf-8") as handle:
            for raw in handle:
                raw = raw.strip()
                if raw:
                    lines.append(raw)
        for raw in reversed(lines):
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                continue
            stamp = self._parse_iso(payload.get("generated_at"))
            if start and stamp and stamp < start:
                continue
            if end and stamp and stamp > end:
                continue
            return payload
        if lines:
            try:
                return json.loads(lines[-1])
            except json.JSONDecodeError:
                return None
        return None

    def _collect_order_flow(self, start: Optional[datetime], end: Optional[datetime]) -> Dict[str, Any]:
        stats = {
            "orders": {
                "intents": 0,
                "validated": 0,
                "routed": 0,
                "posted": 0,
                "ack_pending": 0,
                "ack_accepted": 0,
                "ack_rejected": 0,
                "filled": 0,
                "closed": 0,
                "risk_ok": 0,
                "risk_denied": 0,
                "unique_order_ids": 0,
            },
            "symbols": [],
            "blocks": [],
            "recent": [],
            "notes": [],
        }
        if not start or not end:
            stats["notes"].append("Session window unavailable; order flow skipped.")
            return stats

        audit_path = self.logs_dir / "V13_SessionAudit.log"
        if not audit_path.exists():
            stats["notes"].append("V13_SessionAudit.log missing.")
            return stats

        symbols, blocks, recent = set(), set(), deque(maxlen=40)
        order_ids = set()
        with audit_path.open("r", encoding="utf-8") as handle:
            for raw in handle:
                row = raw.strip()
                if not row:
                    continue
                try:
                    stamp_part, payload_part = row.split(" | ", 1)
                except ValueError:
                    continue
                stamp = self._parse_iso(stamp_part)
                if not stamp or stamp < start or stamp > end:
                    continue
                tokens = payload_part.split(" | ")
                event_name = tokens[0]
                meta: Dict[str, str] = {}
                for token in tokens[1:]:
                    if "=" in token:
                        key, val = token.split("=", 1)
                        meta[key.strip()] = val.strip()
                order_id = meta.get("id") or meta.get("order_id")
                if order_id:
                    order_ids.add(order_id)
                symbol = meta.get("symbol")
                if symbol:
                    symbols.add(symbol)
                block_id = meta.get("block_id")
                if block_id:
                    blocks.add(block_id)

                event_key = event_name.lower()
                if event_key == "order_intent":
                    stats["orders"]["intents"] += 1
                elif event_key == "validated":
                    stats["orders"]["validated"] += 1
                elif event_key == "routed_to_alpaca":
                    stats["orders"]["routed"] += 1
                elif event_key == "posted":
                    stats["orders"]["posted"] += 1
                elif event_key == "ack_pending":
                    stats["orders"]["ack_pending"] += 1
                elif event_key == "ack_accepted":
                    stats["orders"]["ack_accepted"] += 1
                elif event_key == "ack_rejected":
                    stats["orders"]["ack_rejected"] += 1
                elif event_key == "filled":
                    stats["orders"]["filled"] += 1
                elif event_key == "closed":
                    stats["orders"]["closed"] += 1
                elif event_key == "risk_ok":
                    stats["orders"]["risk_ok"] += 1
                elif event_key == "risk_deny":
                    stats["orders"]["risk_denied"] += 1

                recent.append(
                    {
                        "timestamp": stamp.isoformat(),
                        "event": event_name,
                        "meta": meta,
                    }
                )

        stats["symbols"] = sorted(symbols)
        stats["blocks"] = sorted(blocks)
        stats["recent"] = list(recent)
        stats["orders"]["unique_order_ids"] = len(order_ids)
        if stats["orders"]["risk_denied"]:
            stats["notes"].append(
                f"Risk denied {stats['orders']['risk_denied']} intents; review exposure caps."
            )
        if not stats["recent"]:
            stats["notes"].append("No order flow detected during session window.")
        return stats

    def _collect_latency_stats(self, start: Optional[datetime], end: Optional[datetime]) -> Dict[str, Any]:
        stats = {
            "samples": 0,
            "since_intent_avg_ms": 0.0,
            "since_intent_max_ms": 0.0,
            "since_ack_avg_ms": 0.0,
            "since_ack_max_ms": 0.0,
            "notes": [],
        }
        if not start or not end:
            stats["notes"].append("Session window unavailable; latency analysis skipped.")
            return stats

        latency_path = self.logs_dir / "V13_Latency.log"
        if not latency_path.exists():
            stats["notes"].append("V13_Latency.log missing.")
            return stats

        intent_samples: List[float] = []
        ack_samples: List[float] = []
        with latency_path.open("r", encoding="utf-8") as handle:
            for raw in handle:
                row = raw.strip()
                if not row:
                    continue
                try:
                    payload = json.loads(row)
                except json.JSONDecodeError:
                    continue
                stamp = self._parse_iso(payload.get("timestamp"))
                if not stamp or stamp < start or stamp > end:
                    continue
                intent_val = payload.get("since_intent_ms")
                if isinstance(intent_val, (int, float)):
                    intent_samples.append(float(intent_val))
                ack_val = payload.get("since_ack_ms")
                if isinstance(ack_val, (int, float)):
                    ack_samples.append(float(ack_val))

        if intent_samples:
            stats["samples"] = len(intent_samples)
            stats["since_intent_avg_ms"] = round(sum(intent_samples) / len(intent_samples), 2)
            stats["since_intent_max_ms"] = round(max(intent_samples), 2)
        if ack_samples:
            stats["since_ack_avg_ms"] = round(sum(ack_samples) / len(ack_samples), 2)
            stats["since_ack_max_ms"] = round(max(ack_samples), 2)
        if not intent_samples and not ack_samples:
            stats["notes"].append("No latency samples captured within session window.")
        return stats

    def _collect_doctrine_alerts(
        self, start: Optional[datetime], end: Optional[datetime]
    ) -> Dict[str, Any]:
        alerts = {"count": 0, "entries": [], "notes": []}
        if not start or not end:
            alerts["notes"].append("Session window unavailable; doctrine alert scan skipped.")
            return alerts

        alerts_path = self.logs_dir / "DoctrineAlerts.log"
        if not alerts_path.exists():
            alerts["notes"].append("DoctrineAlerts.log missing.")
            return alerts

        entries: List[Dict[str, str]] = []
        with alerts_path.open("r", encoding="utf-8") as handle:
            for raw in handle:
                row = raw.strip()
                if not row:
                    continue
                parts = row.split(" ", 1)
                stamp = self._parse_iso(parts[0]) if parts else None
                if not stamp or stamp < start or stamp > end:
                    continue
                text = parts[1].strip() if len(parts) > 1 else ""
                entries.append({"timestamp": stamp.isoformat(), "text": text})
        alerts["count"] = len(entries)
        alerts["entries"] = entries[-20:]
        if alerts["count"] == 0:
            alerts["notes"].append("No doctrine alerts during session window.")
        return alerts

    def _collect_overrides(self) -> Dict[str, Any]:
        manual_path = self.data_dir / "V13_ManualOverride.json"
        kill_path = self.data_dir / "V13_KillFlag.json"
        manual_data = self._load_json(manual_path) or {}
        kill_data = self._load_json(kill_path) or {}
        return {
            "manual_override": {
                "active": bool(manual_data.get("active")),
                "payload": manual_data,
            },
            "kill_switch": {
                "armed": bool(kill_data.get("kill")),
                "payload": kill_data,
            },
        }

    def _collect_alpaca_capital_and_pnl(self, start: Optional[datetime], end: Optional[datetime]) -> Dict[str, Any]:
        alpaca_data = {"capital_start": None, "capital_end": None, "realized_pnl": 0.0, "activities": [], "notes": []}
        if not start or not end:
            alpaca_data["notes"].append("Session window unavailable; Alpaca data skipped.")
            return alpaca_data

        # Fetch capital at start and end
        if self.baseline_capital is not None:
            alpaca_data["capital_start"] = self.baseline_capital
        else:
            account_start = get_account()
            if account_start:
                alpaca_data["capital_start"] = float(account_start.get("equity", 0.0))

        account_end = get_account()
        if account_end:
            alpaca_data["capital_end"] = float(account_end.get("equity", 0.0))

        # Fetch all activities for learning and detailed report
        all_activities = get_account_activities()
        # Filter for session window for P&L calculation
        session_activities = [a for a in all_activities if start and end and self._parse_iso(a.get("transaction_time")) and start <= self._parse_iso(a.get("transaction_time")) <= end]
        for activity in session_activities:
            if activity.get("activity_type") == "FILL" and "net_amount" in activity:
                alpaca_data["realized_pnl"] += float(activity["net_amount"])
        # Include all activities for learning
        for activity in all_activities:
            if activity.get("activity_type") == "FILL":
                description = f"{activity.get('side', '').capitalize()} {activity.get('qty', 0)} {activity.get('symbol', '')}"
                activity_detail = {
                    "description": description,
                    "type": activity.get("activity_type", ""),
                    "qty": activity.get("qty", 0),
                    "amount": activity.get("net_amount", 0.0),
                    "date": activity.get("transaction_time", "")
                }
                alpaca_data["activities"].append(activity_detail)

        if not all_activities:
            alpaca_data["notes"].append("No account activities found in session window.")
        return alpaca_data

    def _collect_performance_summary(self, end: Optional[datetime]) -> Dict[str, Any]:
        status = self._load_json(self.data_dir / "V13_Status.json") or {}
        metrics = self._latest_metric_entry(None, end)
        summary: Dict[str, Any] = {"status": status, "latest_metrics": metrics}

        if status and self.baseline_status:
            pnl_now = status.get("PnL")
            pnl_before = self.baseline_status.get("PnL")
            win_now = status.get("WinRate")
            win_before = self.baseline_status.get("WinRate")
            delta: Dict[str, float] = {}
            if isinstance(pnl_now, (int, float)) and isinstance(pnl_before, (int, float)):
                delta["PnL"] = round(pnl_now - pnl_before, 4)
            if isinstance(win_now, (int, float)) and isinstance(win_before, (int, float)):
                delta["WinRate"] = round(win_now - win_before, 4)
            if delta:
                summary["delta_vs_start"] = delta

        if metrics and self.baseline_metrics and metrics is not self.baseline_metrics:
            try:
                trades_now = metrics.get("metrics", {}).get("trades", 0)
                trades_before = self.baseline_metrics.get("metrics", {}).get("trades", 0)
                summary.setdefault("delta_vs_start", {})
                summary["delta_vs_start"]["trades"] = trades_now - trades_before
            except Exception:
                pass
        return summary

    def _build_session_summary(self, ended_at: datetime, broker_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        started_iso = self.started_at.isoformat() if self.started_at else None
        duration_seconds = (
            int((ended_at - self.started_at).total_seconds()) if self.started_at else None
        )
        event_counter = Counter(record["Event"] for record in self.records)
        summary = {
            "session_id": self.session_id,
            "started_at": started_iso,
            "ended_at": ended_at.isoformat(),
            "duration_seconds": duration_seconds,
            "events": {
                "total": len(self.records),
                "by_type": dict(event_counter),
                "timeline": self.records[-50:],
            },
        }
        if broker_data:
            summary.update({
                "capital_start": broker_data.get("capital_start", 0.0),
                "capital_end": broker_data.get("capital_end", 0.0),
                "realized_pnl": broker_data.get("realized_pnl", 0.0),
            })

        order_flow = self._collect_order_flow(self.started_at, ended_at)
        latency = self._collect_latency_stats(self.started_at, ended_at)
        alerts = self._collect_doctrine_alerts(self.started_at, ended_at)
        overrides = self._collect_overrides()
        performance = self._collect_performance_summary(ended_at)
        alpaca_data = self._collect_alpaca_capital_and_pnl(self.started_at, ended_at)

        summary["order_flow"] = order_flow
        summary["latency"] = latency
        summary["doctrine_alerts"] = alerts
        summary["overrides"] = overrides
        summary["performance"] = performance
        summary["alpaca_data"] = alpaca_data

        notes: List[str] = []
        if order_flow["orders"]["intents"] == 0:
            notes.append("No order intents detected; confirm command pipeline.")
        if order_flow["orders"]["risk_denied"] > 0:
            notes.append("Risk denied intents; review exposure or caps.")
        if latency["since_intent_max_ms"] and latency["since_intent_max_ms"] > 200:
            notes.append("Latency exceeded 200 ms; inspect infrastructure or broker load.")
        if overrides["manual_override"]["active"]:
            notes.append("Manual override stayed active; capture operator rationale.")
        if overrides["kill_switch"]["armed"]:
            notes.append("Kill switch engaged; investigate cause before relaunch.")
        if alerts["count"] > 0:
            notes.append("Doctrine alerts fired; review doctrine feedback loop.")
        if not performance.get("latest_metrics"):
            notes.append("No performance metrics captured; confirm tracker is running.")
        summary["learning_notes"] = notes
        return summary

    def _write_summary(self, summary: Dict[str, Any]) -> None:
        payload: Dict[str, Any] = {}
        if self.summary_path.exists():
            try:
                payload = json.loads(self.summary_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                payload = {}

        payload.setdefault("pre_launch", payload.get("pre_launch"))
        sessions = payload.setdefault("sessions", [])
        if not isinstance(sessions, list):
            sessions = []
            payload["sessions"] = sessions
        sessions.append(summary)
        self.summary_path.parent.mkdir(parents=True, exist_ok=True)
        self.summary_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------
    # Trade report generation
    # ------------------------------------------------------------------
    def _collect_filled_order_ids(
        self, start: Optional[datetime], end: Optional[datetime]
    ) -> Dict[str, Dict[str, str]]:
        """Return mapping of order_id -> meta for FILLED events within window.

        Meta includes any parsed fields on the FILLED line (e.g., alpaca_id).
        """
        filled: Dict[str, Dict[str, str]] = {}
        if not start or not end:
            return filled
        audit_path = self.logs_dir / "V13_SessionAudit.log"
        if not audit_path.exists():
            return filled
        with audit_path.open("r", encoding="utf-8") as handle:
            for raw in handle:
                row = raw.strip()
                if not row:
                    continue
                try:
                    stamp_part, payload_part = row.split(" | ", 1)
                except ValueError:
                    continue
                stamp = self._parse_iso(stamp_part)
                if not stamp or stamp < start or stamp > end:
                    continue
                tokens = payload_part.split(" | ")
                event_name = tokens[0].strip().upper()
                if event_name != "FILLED":
                    continue
                meta: Dict[str, str] = {}
                for token in tokens[1:]:
                    if "=" in token:
                        key, val = token.split("=", 1)
                        meta[key.strip()] = val.strip()
                order_id = meta.get("id") or meta.get("order_id")
                if order_id:
                    filled[order_id] = meta
        return filled

    def _iter_order_files_between(self, start: Optional[datetime], end: Optional[datetime]):
        if not start or not end:
            return
        day = start.date()
        last = end.date()
        while True:
            path = self.data_dir / "orders" / f"{day.isoformat()}.jsonl"
            if path.exists():
                yield path
            if day >= last:
                break
            # advance by one day
            day = day.fromordinal(day.toordinal() + 1)

    def _load_order_records(self, start: Optional[datetime], end: Optional[datetime]) -> Dict[str, Dict[str, Any]]:
        """Load order records (by order_id) from data/orders/*.jsonl within window."""
        by_id: Dict[str, Dict[str, Any]] = {}
        for path in self._iter_order_files_between(start, end):
            try:
                with path.open("r", encoding="utf-8") as handle:
                    for raw in handle:
                        raw = raw.strip()
                        if not raw:
                            continue
                        try:
                            rec = json.loads(raw)
                        except json.JSONDecodeError:
                            continue
                        ts = self._parse_iso(rec.get("timestamp"))
                        if ts and start and end and (ts < start or ts > end):
                            continue
                        oid = rec.get("order_id") or rec.get("intent", {}).get("client_order_tag")
                        if not oid:
                            continue
                        by_id[oid] = rec
            except Exception:
                continue
        return by_id

    def _load_orders_snapshot(self) -> Optional[List[Dict[str, Any]]]:
        """Optional enriched Alpaca snapshot for filled_qty/avg_price, if present."""
        snap_path = self.data_dir / "orders_snapshot.json"
        if not snap_path.exists():
            return None
        try:
            snap = json.loads(snap_path.read_text(encoding="utf-8"))
            return snap if isinstance(snap, list) else None
        except Exception:
            return None

    def _generate_trade_report(self, ended_at: datetime) -> Dict[str, Any]:
        start = self.started_at
        end = ended_at
        filled_map = self._collect_filled_order_ids(start, end)
        orders_by_id = self._load_order_records(start, end)
        snapshot = self._load_orders_snapshot() or []
        snapshot_by_id: Dict[str, Dict[str, Any]] = {}
        for o in snapshot:
            if isinstance(o, dict):
                oid = o.get("id") or o.get("client_order_id")
                if oid:
                    snapshot_by_id[str(oid)] = o

        trades: List[Dict[str, Any]] = []
        for oid, filled_meta in filled_map.items():
            base: Dict[str, Any] = {"order_id": oid, "status": "FILLED"}
            if "alpaca_id" in filled_meta:
                base["alpaca_id"] = filled_meta.get("alpaca_id")
            if "submitted_at" in filled_meta:
                base["submitted_at"] = filled_meta.get("submitted_at")
            if "block_id" in filled_meta:
                base["block_id"] = filled_meta.get("block_id")

            order_rec = orders_by_id.get(oid) or {}
            payload = order_rec.get("payload") or {}
            intent = order_rec.get("intent") or {}
            response = order_rec.get("response") or {}

            base["symbol"] = payload.get("symbol") or intent.get("symbol")
            base["side"] = payload.get("side") or intent.get("side")
            base["qty"] = payload.get("qty") or intent.get("qty")
            base["order_type"] = payload.get("type") or intent.get("order_type")
            base["time_in_force"] = payload.get("time_in_force") or intent.get("time_in_force")
            for k in ("limit_price", "stop_price", "trail_price", "trail_percent"):
                if payload.get(k) is not None:
                    base[k] = payload.get(k)
                elif intent.get(k) is not None:
                    base[k] = intent.get(k)
            if intent:
                for k in ("strategy", "reason", "signal_price", "block_id"):
                    if intent.get(k) is not None and base.get(k) is None:
                        base[k] = intent.get(k)

            if response:
                base.setdefault("alpaca_id", response.get("id"))
                base.setdefault("submitted_at", response.get("created_at"))
                base["alpaca_status"] = response.get("status")

            snap_match = None
            if base.get("alpaca_id") and snapshot_by_id.get(str(base["alpaca_id"])):
                snap_match = snapshot_by_id.get(str(base["alpaca_id"]))
            elif snapshot_by_id.get(oid):
                snap_match = snapshot_by_id.get(oid)
            if snap_match:
                for k in ("filled_qty", "filled_avg_price", "filled_at", "submitted_at"):
                    val = snap_match.get(k)
                    if val is not None and not base.get(k):
                        base[k] = val

            trades.append(base)

        report = {
            "session_id": self.session_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": ended_at.isoformat(),
            "count": len(trades),
            "trades": trades,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        return report

    def _write_trade_report(self, report: Dict[str, Any]) -> None:
        TRADE_REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
        TRADE_REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------
    # Public control flow
    # ------------------------------------------------------------------
    def verify_doctrine_hashes(self) -> bool:
        print("[SessionAudit] Verifying doctrine integrity...")
        if not self.hash_list.exists():
            self._record_event("HASH_VALIDATION", "FAIL", "Integrity_HashList.md5 missing.")
            return False

        valid_hashes = self.hash_list.read_text(encoding="utf-8")
        all_valid = True
        for doctrine_id, data in self.feedback.doctrines.items():
            active_hash = data.get("hash")
            if active_hash not in valid_hashes:
                print(f"[SessionAudit] Hash mismatch detected for {doctrine_id}")
                self._record_event("HASH_MISMATCH", "FAIL", doctrine_id)
                all_valid = False
            else:
                self._record_event("HASH_VERIFIED", "OK", doctrine_id)
        return all_valid

    def start_session(self) -> bool:
        """Initialize audit logging for this runtime session."""
        self.active = True
        self.started_at = datetime.now(timezone.utc)
        self._record_event("SESSION_START", "OK", "Session initialized.")
        print(f"[SessionAudit] Session {self.session_id} started.")

        integrity_ok = self.verify_doctrine_hashes()
        if not integrity_ok:
            print("[SessionAudit] Integrity check failed -- aborting launch.")
            self._record_event("SESSION_ABORT", "FAIL", "Hash mismatch detected.")
            self.active = False
            return False

        print("[SessionAudit] All doctrines verified.")
        self.baseline_status = self._load_json(self.data_dir / "V13_Status.json") or {}
        self.baseline_metrics = self._latest_metric_entry()
        account = get_account()
        if account:
            self.baseline_capital = float(account.get("equity", 0.0))
        return True

    def log_runtime_event(self, event: str, detail: str) -> None:
        if self.active:
            self._record_event(event, "OK", detail)

    def log_cmd_ack(self, ack_payload: Dict[str, Any]) -> None:
        if not self.active:
            return
        cmd_text = ack_payload.get("cmd_text", "UNK")
        effect_summary = ack_payload.get("effect_summary", "No summary")
        self._record_event("CMD_ACK", "OK", f"{cmd_text}: {effect_summary}")

    def _seal_logs(self) -> None:
        log_path = self.logs_dir / "V13_SessionAudit.log"
        seal_path = self.logs_dir / "AUDIT_SEAL.txt"
        if not log_path.exists():
            self._record_event("AUDIT_SEAL", "FAIL", "V13_SessionAudit.log not found.")
            return
        digest = hashlib.sha256(log_path.read_bytes()).hexdigest()
        seal_payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session": self.session_id,
            "sha256": digest,
        }
        seal_path.parent.mkdir(parents=True, exist_ok=True)
        with seal_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(seal_payload) + "\n")
        self._record_event("AUDIT_SEAL", "OK", f"sha256={digest}")

    def end_session(self) -> None:
        if not self.active:
            print("[SessionAudit] No active session to close.")
            return
        self.ended_at = datetime.now(timezone.utc)
        self._record_event("SESSION_END", "OK", "Session completed successfully.")
        self._seal_logs()
        # Fetch capital and P&L from broker
        broker_data = self._fetch_session_capital_and_pnl()
        summary = self._build_session_summary(self.ended_at, broker_data)
        self._write_summary(summary)
        # Generate trade report with FILLED orders and Alpaca details
        try:
            trade_report = self._generate_trade_report(self.ended_at)
            self._write_trade_report(trade_report)
        except Exception as exc:
            log_event("SessionAudit", "WARN", f"Trade report generation failed: {exc}")
        print(f"[SessionAudit] Session {self.session_id} logged and closed.")
        self.active = False

    def _fetch_session_capital_and_pnl(self) -> Dict[str, Any]:
        """Fetch capital at start/end and aggregate realized P&L for session."""
        start_iso = self.started_at.isoformat() if self.started_at else None
        end_iso = self.ended_at.isoformat() if self.ended_at else None

        # Fetch account info for capital
        account_start = get_account()  # Current capital (assume start if no history)
        capital_start = 0.0
        if account_start:
            # Alpaca: 'equity' present; Binance Spot: balances list
            if isinstance(account_start, dict) and "equity" in account_start:
                capital_start = float(account_start.get("equity", 0))
            elif isinstance(account_start, dict) and "balances" in account_start:
                try:
                    bals = account_start.get("balances", [])
                    usdt = next((b for b in bals if b.get("asset") == "USDT"), None)
                    if usdt:
                        capital_start = float(usdt.get("free", 0)) + float(usdt.get("locked", 0))
                except Exception:
                    pass
        capital_end = capital_start  # For simplicity, use current; could fetch historical if available

        # Fetch activities for realized P&L
        activities = get_account_activities(start_time=start_iso, end_time=end_iso)
        realized_pnl = 0.0
        for activity in activities:
            if activity.get("activity_type") == "FILL":  # Alpaca
                pnl = float(activity.get("net_amount", 0))
                realized_pnl += pnl
            elif "realizedPnl" in activity:  # Binance
                pnl = float(activity.get("realizedPnl", 0))
                realized_pnl += pnl

        return {
            "capital_start": capital_start,
            "capital_end": capital_end,
            "realized_pnl": realized_pnl,
        }


# ---------------------------------------------------------------------------
# Diagnostic execution
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    audit = SessionAudit()
    if audit.start_session():
        audit.log_runtime_event("TELEMETRY_PING", "Live feed active.")
        audit.log_runtime_event("RISK_MONITOR", "Drawdown stable at 1.2%.")
        audit.end_session()
