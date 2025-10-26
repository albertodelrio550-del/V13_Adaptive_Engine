"""
V13_SyncLoop.py
Simulation-only coordination loop for monitoring core module health.
Does not place or execute trades.

Purpose:
  - Poll each module’s diagnostic / summary function
  - Write combined status snapshot to /data/V13_Status.json
  - Append activity to /logs/SyncLoop.log
"""

import json, time, os, sys
import configparser
from typing import Dict, Any, List

import requests
from datetime import datetime, timezone
from pathlib import Path

# Add path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from core.V13_LogFormatter import log_event
from core.V13_KillSwitch import check_kill_flag, subscribe
from alpaca_feed_core import load_keys, _get_headers

# safe paths
LOG_PATH  = Path("logs/SyncLoop.log")
DATA_PATH = Path("data/V13_Status.json")
ORDERS_SNAPSHOT_PATH = Path("data/orders_snapshot.json")
POSITIONS_PATH = Path("data/positions.json")
ACCOUNT_PATH = Path("data/account.json")

STATUS_MAP = {
    "accepted": "ACK_ACCEPTED",
    "new": "ACK_ACCEPTED",
    "pending_new": "ACK_PENDING",
    "partially_filled": "PARTIALLY_FILLED",
    "filled": "FILLED",
    "canceled": "CANCELED",
    "replaced": "REPLACED",
    "rejected": "ACK_REJECTED",
    "expired": "EXPIRED",
}

_sync_state = {
    "orders": {},  # order_id -> status
    "last_snapshot_ts": 0.0,
}


def restore_runtime_state():
    """Rehydrate open orders and positions when V13 boots with existing PAPER exposure."""
    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "orders_restored": [],
        "positions_restored": [],
        "notes": []
    }

    orders = _read_json_file(ORDERS_SNAPSHOT_PATH)
    restored_orders = []
    if isinstance(orders, list):
        for order in orders:
            if not isinstance(order, dict):
                continue
            status = order.get("status", "")
            if status in {"filled", "canceled", "expired"}:
                continue
            order_id = order.get("id") or order.get("client_order_id")
            if not order_id:
                continue
            order = dict(order)
            order["restored_at"] = datetime.now(timezone.utc).isoformat()
            order["restored"] = True
            restored_orders.append(order)
            summary["orders_restored"].append(order_id)
            # Mark in in-memory state for latency/status tracking
            _sync_state["orders"][order_id] = _map_order_status(order.get("status"))
            emit_event("ORDER_RESTORED", {
                "order_id": order_id,
                "status": order.get("status"),
                "symbol": order.get("symbol"),
                "qty": order.get("qty"),
                "side": order.get("side"),
                "restored_at": order["restored_at"],
            })

    positions = _read_json_file(POSITIONS_PATH)
    restored_positions = []
    if isinstance(positions, list):
        for pos in positions:
            if not isinstance(pos, dict):
                continue
            pos = dict(pos)
            pos["restored_at"] = datetime.now(timezone.utc).isoformat()
            restored_positions.append(pos)
            summary["positions_restored"].append(pos.get("symbol"))

    if restored_orders:
        _persist_snapshot(ORDERS_SNAPSHOT_PATH, restored_orders)
    if restored_positions:
        _persist_snapshot(POSITIONS_PATH, restored_positions)

    if restored_positions or restored_orders:
        emit_event("RESTORE_SUMMARY", {
            "orders": summary["orders_restored"],
            "positions": summary["positions_restored"],
            "timestamp": summary["timestamp"],
        })
        _write_recovery_log(summary)


def _read_json_file(path: Path):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        _log(f"Failed to read snapshot {path}: {exc}")
    return None


def _write_recovery_log(summary: Dict[str, Any]):
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    recover_path = log_dir / f"recover_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.log"
    try:
        recover_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    except Exception as exc:
        _log(f"Failed to write recovery log: {exc}")

# ---- simple helpers ---------------------------------------------------------
def _log(msg: str):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().isoformat()}] {msg}\n")
    # Use unified logging
    log_event("SyncLoop", "INFO", msg)

def _read_json():
    if DATA_PATH.exists():
        try:
            return json.loads(DATA_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def _write_json(payload: dict):
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _load_cfg() -> configparser.ConfigParser:
    cfg = configparser.ConfigParser(inline_comment_prefixes=(';', '#'))
    cfg.optionxform = str
    cfg.read('config/V13_Config.ini')
    return cfg


def _alpaca_base_url(cfg: configparser.ConfigParser) -> str:
    return cfg.get('BROKER_ALPACA', 'BASE_URL', fallback='https://paper-api.alpaca.markets')


def _alpaca_get(endpoint: str, params: Dict[str, Any] | None = None) -> Dict[str, Any] | List[Any] | None:
    try:
        keys = load_keys()
    except Exception as exc:
        _log(f"Alpaca keys missing: {exc}")
        return None

    cfg = _load_cfg()
    base_url = _alpaca_base_url(cfg)
    url = f"{base_url}{endpoint}"
    headers = _get_headers(keys)
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        _log(f"Alpaca GET error [{endpoint}]: {exc}")
        return None

# ---- simulated module stubs -------------------------------------------------
def refresh_feed():
    # Simulated TelemetryFusion output
    return {"symbol": "SPY", "price": 4315.2, "delta": 0.25}

def audit_risk():
    # Simulated RiskSentinel output
    return {"max_dd": -2.4, "exposure": 0.63}

def summary_performance():
    # Simulated PerformanceTracker output
    return {"PnL": 2.3, "WinRate": 61}

def adaptive_status():
    # Simulated AdaptiveCycle output
    return {"phase": "stabilize", "cycle": 147}

def doctrine_check():
    # Simulated DoctrineFeedbackLoop output
    return {"status": "synced"}

def safety_status():
    # Simulated ManualOverride / kill switch
    return {"override": False, "kill": False}

# ---- coordination logic for triggering trading modules ----------------------
def evaluate_trade_signals(snapshot: dict) -> list:
    """Evaluate snapshot for trade signals (simulation template)."""
    signals = []
    # Placeholder logic: Trigger based on simulated conditions
    if snapshot["modules"]["TelemetryFusion"]["delta"] > 0.1:
        signals.append({"action": "buy", "symbol": "SPY", "quantity": 10})
    if snapshot["modules"]["RiskSentinel"]["exposure"] > 0.5:
        signals.append({"action": "reduce_exposure", "symbol": "SPY"})
    return signals

def execute_trade_signal(signal: dict, simulation: bool = True):
    """Execute or simulate trade signal."""
    if simulation:
        _log(f"Simulated trade: {signal}")
        # Placeholder: In real mode, integrate with trading API
        # e.g., alpaca_api.submit_order(signal)
    else:
        _log(f"Executing trade: {signal}")
        # Insert real execution code here, e.g., call trading module


def _map_order_status(status: str) -> str:
    if not status:
        return "UNKNOWN"
    normalized = status.lower()
    return STATUS_MAP.get(normalized, normalized.upper())

# ---- event emission and relay -----------------------------------------------
def emit_event(event_type: str, payload: dict):
    """Emit event to be relayed by SyncLoop."""
    event = {
        "event_type": event_type,
        "payload": payload,
        "timestamp": datetime.now().isoformat(),
        "origin": "SyncLoop"
    }
    _log(f"Event emitted: {event_type} - {payload}")
    # Placeholder: In real implementation, broadcast to EventBus or queue
    # For now, write to a shared event file
    event_path = Path("data/V13_Events.json")
    event_path.parent.mkdir(parents=True, exist_ok=True)
    with open(event_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")

def relay_cmd_ack(ack: dict):
    """Relay CMD_ACK event from CommandMatrix and log to SessionAudit."""
    emit_event("CMD_ACK", ack)
    # Log to SessionAudit if available
    try:
        from core.V13_SessionAudit import SessionAudit
        audit = SessionAudit()
        if audit.active:
            audit.log_cmd_ack(ack)
    except ImportError:
        pass  # SessionAudit not available, skip logging


def relay_order_update(order_payload: dict):
    """Relay ORDER_UPDATE events for live tracking (Stage 5)."""
    emit_event("ORDER_UPDATE", order_payload)
    try:
        from core.V13_SessionAudit import SessionAudit
        audit = SessionAudit()
        if audit.active:
            audit.log_runtime_event("ORDER_UPDATE", json.dumps(order_payload))
    except ImportError:
        pass
    except Exception as exc:
        _log(f"Failed to record ORDER_UPDATE audit: {exc}")

def relay_dual_feedback(dual_feedback: dict):
    """Relay DUAL_FEEDBACK event from DoctrineFeedbackLoop to VisualMonitor."""
    emit_event("DUAL_FEEDBACK", dual_feedback)
    # Placeholder: Integrate with VisualMonitor for UI updates
    # For now, log the full response
    _log(f"Dual feedback relayed: {dual_feedback.get('full_response', 'N/A')}")


def _persist_snapshot(path: Path, payload: Any):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception as exc:
        _log(f"Failed to persist snapshot {path}: {exc}")


def _emit_visual_update(orders: List[Dict[str, Any]], positions: List[Dict[str, Any]]):
    visual_payload = {
        "orders": [
            {
                "id": o.get("id"),
                "client_order_id": o.get("client_order_id"),
                "symbol": o.get("symbol"),
                "qty": o.get("qty"),
                "side": o.get("side"),
                "type": o.get("type"),
                "status": o.get("v13_status"),
                "submitted_at": o.get("submitted_at") or o.get("created_at"),
                "filled_qty": o.get("filled_qty"),
                "filled_avg_price": o.get("filled_avg_price"),
            }
            for o in orders
        ],
        "positions": [
            {
                "symbol": p.get("symbol"),
                "qty": p.get("qty"),
                "market_value": p.get("market_value"),
                "unrealized_pl": p.get("unrealized_pl"),
            }
            for p in positions
        ],
    }
    emit_event("VISUAL_UPDATE", visual_payload)


def _emit_performance_update(account: Dict[str, Any], positions: List[Dict[str, Any]]):
    pnl_payload = {
        "equity": account.get("equity"),
        "cash": account.get("cash"),
        "buying_power": account.get("buying_power"),
        "unrealized_pl": sum(float(p.get("unrealized_pl", 0) or 0) for p in positions),
        "unrealized_plpc": sum(float(p.get("unrealized_plpc", 0) or 0) for p in positions),
    }
    emit_event("PERFORMANCE_UPDATE", pnl_payload)


def poll_alpaca_reconciliation(force: bool = False):
    now = time.time()
    if not force and now - _sync_state.get("last_snapshot_ts", 0) < 60:
        return

    orders_raw = _alpaca_get('/v2/orders', params={"status": "all", "limit": 50})
    if isinstance(orders_raw, dict) and "orders" in orders_raw:
        orders_list = orders_raw.get("orders", [])
    else:
        orders_list = orders_raw or []

    enriched_orders = []
    if isinstance(orders_list, list):
        for order in orders_list:
            if not isinstance(order, dict):
                continue
            status = _map_order_status(order.get("status"))
            order_id = order.get("id") or order.get("client_order_id")
            if order_id:
                previous = _sync_state["orders"].get(order_id)
                if previous != status:
                    event_payload = {
                        "order_id": order_id,
                        "status": status,
                        "alpaca_status": order.get("status"),
                        "symbol": order.get("symbol"),
                        "side": order.get("side"),
                        "qty": order.get("qty"),
                        "filled_qty": order.get("filled_qty"),
                        "filled_avg_price": order.get("filled_avg_price"),
                        "submitted_at": order.get("submitted_at") or order.get("created_at"),
                    }
                    emit_event("ORDER_STATUS", event_payload)
                _sync_state["orders"][order_id] = status
            # attach mapped status for visual snapshot
            order = dict(order)
            order["v13_status"] = status
            enriched_orders.append(order)

    positions_raw = _alpaca_get('/v2/positions') or []
    positions_list = positions_raw if isinstance(positions_raw, list) else []

    account_raw = _alpaca_get('/v2/account') or {}

    if enriched_orders:
        _persist_snapshot(ORDERS_SNAPSHOT_PATH, enriched_orders)
    if positions_list:
        _persist_snapshot(POSITIONS_PATH, positions_list)
    if account_raw:
        _persist_snapshot(ACCOUNT_PATH, account_raw)

    if account_raw or positions_list:
        _emit_performance_update(account_raw, positions_list)
    if enriched_orders or positions_list:
        _emit_visual_update(enriched_orders, positions_list)

    _sync_state["last_snapshot_ts"] = now

# ---- main heartbeat ---------------------------------------------------------
def run_sync_loop(interval: int = 10, max_cycles: int = 30, enable_trading: bool = False):
    """Simulation heartbeat that polls module stubs and optionally coordinates trading."""
    _log("V13 SyncLoop started (simulation).")
    for i in range(max_cycles):
        if check_kill_flag():
            _log("KillSwitch engaged — SyncLoop halted.")
            break

        # Emit SYNC_TICK every 10s
        emit_event("SYNC_TICK", {"heartbeat": i + 1})

        # Simulate commands for PAPER TEST 1
        if i + 1 == 5:
            # Simulate "deploy"
            _log("Simulating command: deploy")
            emit_event("CMD_ACK", {"command": "deploy", "status": "ACK", "doctrine": "Visible"})
        elif i + 1 == 10:
            # Simulate "tighten B"
            _log("Simulating command: tighten B")
            emit_event("RISK_ALERT", {"alert": "Exposure tightened", "level": "B"})
        elif i + 1 == 15:
            # Simulate "kill"
            _log("Simulating command: kill")
            from core.V13_KillSwitch import engage_kill_switch
            engage_kill_switch("PAPER_TEST")

        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "heartbeat": i + 1,
            "modules": {
                "TelemetryFusion": refresh_feed(),
                "RiskSentinel": audit_risk(),
                "PerformanceTracker": summary_performance(),
                "AdaptiveCycle": adaptive_status(),
                "DoctrineFeedbackLoop": doctrine_check(),
            },
            "safety": safety_status(),
        }

        # Evaluate and execute trade signals if enabled
        if enable_trading:
            signals = evaluate_trade_signals(snapshot)
            for signal in signals:
                execute_trade_signal(signal, simulation=True)  # Always simulation for safety

        try:
            poll_alpaca_reconciliation()
        except Exception as exc:
            _log(f"Reconciliation error: {exc}")

        _write_json(snapshot)
        _log(f"Heartbeat {i+1} complete.")
        time.sleep(interval)

    _log("V13 SyncLoop finished (simulation).")

# ---- run standalone (safe) --------------------------------------------------
if __name__ == "__main__":
    print("Running V13 SyncLoop (simulation mode)...")
    run_sync_loop()
    print("Simulation complete.  Check logs/ and data/ folders.")
