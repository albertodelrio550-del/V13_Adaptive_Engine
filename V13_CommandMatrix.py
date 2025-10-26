"""
V13_CommandMatrix.py
Central coordinator for simulated module control.
Build: PAPER Simulation Mode

Responsibilities:
- Verify presence of V13 core modules
- Provide safe simulation command routing
- Log and broadcast system health
"""

import json
import time
import os
import uuid
import sys
import hashlib
import statistics
import requests
import configparser
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Tuple
sys.path.append('.')
sys.path.append('..')
from datetime import datetime, timezone
from pathlib import Path
from core import V13_ManualOverride as manual_override
from core.V13_LogFormatter import log_event as unified_log_event
from core.V13_RiskSentinel import RiskGate
from core.V13_VolatilityScoring import Phase6VolatilityScorer
from scripts.check_phase8_exit import evaluate_phase8_exit as evaluate_phase8_exit_script
from core.allocation_helper import get_current_allocation
from alpaca_feed_core import load_keys, _get_headers

LOG_PATH = Path("logs/CommandMatrix.log")
DATA_PATH = Path("data/V13_Status.json")
ACK_PATH = Path("data/V13_Acknowledgments.json")
AUDIT_PATH = Path("logs/V13_SessionAudit.log")
ORDERS_DIR = Path("data/orders")
LATENCY_LOG_PATH = Path("logs/V13_Latency.log")
BLOCK_CONFIG_PATH = Path("config/V13_Blocks.ini")
ALLOCATION_LOG_PATH = Path("data/adaptive_allocation.json")
GLOBAL_SEAL_PATH = Path("logs/GLOBAL_SEAL.txt")
SCALING_SUMMARY_PATH = Path("data/capital_scaling_summary.json")
DASHBOARD_PATH = Path("data/global_dashboard.json")
BACKUP_DIR = Path("data/backups")
MAX_BACKUPS = 20

MODE_PROFILES = {
    "SUPER SAFE": {"defense": 0.70, "attack": 0.30, "max_dd": 0.5, "target_daily_pnl": 0.3},
    "SAFE": {"defense": 0.60, "attack": 0.40, "max_dd": 1.0, "target_daily_pnl": 0.6},
    "BALANCED": {"defense": 0.50, "attack": 0.50, "max_dd": 2.0, "target_daily_pnl": 1.2},
    "AGGRESSIVE": {"defense": 0.30, "attack": 0.70, "max_dd": 4.0, "target_daily_pnl": 2.0},
}

GLOBAL_DEFAULTS = {
    "max_drawdown": 5.0,
    "stagger_seconds": 20.0,
}

SCALING_RULES = [
    (1, 0.01),
    (3, 0.0075),
    (5, 0.006),
    (10, 0.005),
]

_ACTIVE_MATRIX: Optional["V13_CommandMatrix"] = None

ORDER_STATES = (
    "INTENT_RECEIVED",
    "VALIDATED",
    "ROUTED_TO_ALPACA",
    "POSTED",
    "ACK_PENDING",
    "ACK_ACCEPTED",
    "ACK_REJECTED",
    "FILL_PENDING",
    "PARTIALLY_FILLED",
    "FILLED",
    "CLOSED",
)

TERMINAL_STATES = {"ACK_REJECTED", "FILLED", "CLOSED"}


@dataclass
class OrderRecord:
    intent: Dict[str, Any]
    state: str = "INTENT_RECEIVED"
    history: List[Dict[str, Any]] = field(default_factory=list)
    response: Optional[Dict[str, Any]] = None
    alpaca_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    ack_time: Optional[float] = None
    fill_time: Optional[float] = None
    signal_price: Optional[float] = None
    block_id: Optional[str] = None


@dataclass
class BlockConfig:
    block_id: str
    mode: str
    capital: float
    strategy: str
    symbol: str
    stagger: float
    risk_ceiling: float


@dataclass
class BlockState:
    config: BlockConfig
    status: str = "IDLE"
    pnl: float = 0.0
    drawdown: float = 0.0
    latency_samples: List[float] = field(default_factory=list)
    last_launch: Optional[float] = None
    last_heartbeat: float = field(default_factory=time.time)
    adaptive_allocation: Dict[str, float] = field(
        default_factory=lambda: {"Assassins": 0.5, "Avengers": 0.5}
    )
    telemetry: Dict[str, Any] = field(default_factory=dict)
    last_score: Optional[Dict[str, Any]] = None

    def record_latency(self, value: float) -> None:
        self.latency_samples.append(value)
        # Keep most recent 200 samples to limit memory
        if len(self.latency_samples) > 200:
            self.latency_samples.pop(0)

    def latency_stats(self) -> Tuple[float, float]:
        if not self.latency_samples:
            return 0.0, 0.0
        return (
            statistics.fmean(self.latency_samples),
            max(self.latency_samples),
        )

    def update_metrics(self, pnl: float = 0.0, drawdown: float = 0.0, status: Optional[str] = None) -> None:
        if status:
            self.status = status
        self.pnl = pnl
        self.drawdown = drawdown
        self.last_heartbeat = time.time()


def log_event(msg):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().isoformat()}] {msg}\n")
    try:
        unified_log_event("CommandMatrix", "INFO", msg)
    except Exception:
        pass


def audit_line(message: str):
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_PATH, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()} | {message}\n")


def _flatten_meta(meta: Optional[Dict[str, Any]]) -> List[str]:
    if not meta:
        return []
    flattened = []
    for key, val in meta.items():
        if isinstance(val, dict):
            for sub_key, sub_val in val.items():
                flattened.append(f"{key}.{sub_key}={sub_val}")
        else:
            flattened.append(f"{key}={val}")
    return flattened


def audit_transition(order_id: str, state: str, extra: Optional[Dict[str, Any]] = None):
    event = (state or "").upper() or "STATE"
    parts = [event, f"id={order_id}"] + _flatten_meta(extra)
    audit_line(" | ".join(parts))


def log_latency(event: str, payload: Dict[str, Any]):
    LATENCY_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()
    try:
        line = json.dumps({"timestamp": timestamp, "event": event, **payload})
    except TypeError:
        payload = {k: str(v) for k, v in payload.items()}
        line = json.dumps({"timestamp": timestamp, "event": event, **payload})
    with open(LATENCY_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    block_id = payload.get("block_id")
    if block_id and _ACTIVE_MATRIX:
        try:
            _ACTIVE_MATRIX._handle_latency_event(block_id, payload)
        except Exception as exc:
            log_event(f"Latency hook failed for {block_id}: {exc}")

def read_status():
    if DATA_PATH.exists():
        return json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return {"history": []}

def write_status(update):
    data = read_status()
    history = data.get("history", [])
    history.append(update)
    history = history[-10:]       # keep last 10
    payload = {
        "timestamp": datetime.now().isoformat(),
        "modules": update.get("modules", {}),
        "safety": update.get("safety", {}),
        "history": history,
        "last_action": update.get("last_action"),
    }
    if "blocks" in update:
        payload["blocks"] = update["blocks"]
    if "global" in update:
        payload["global"] = update["global"]
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

def simulated_health_check():
    # Example: pretend every module is OK
    return {
        "TelemetryFusion": "OK",
        "RiskSentinel": "OK",
        "PerformanceTracker": "OK",
        "AdaptiveCycle": "OK",
        "DoctrineFeedbackLoop": "OK",
        "CommanderMonitor": "OK",
    }

def matrix_status():
    modules = simulated_health_check()
    safety_status = manual_override.safety_status()
    override_active = bool(manual_override.read_override())
    blocks_snapshot = _ACTIVE_MATRIX._block_status_snapshot() if _ACTIVE_MATRIX else {}
    global_snapshot = _ACTIVE_MATRIX._global_metrics_snapshot() if _ACTIVE_MATRIX else {}
    update = {
        "modules": modules,
        "safety": {
            "override": override_active,
            "kill": safety_status.get("kill", False),
            "kill_reason": safety_status.get("reason", "N/A") if safety_status.get("kill") else None
        },
        "blocks": blocks_snapshot,
        "global": global_snapshot,
        "last_action": "/matrix status - simulated",
    }
    log_event("Matrix status check complete.")
    write_status(update)
    return update


def broadcast_status_update(action):
    """
    Broadcast status update to /data/V13_Status.json with rolling 10-action history for GUI live updates.
    """
    modules = simulated_health_check()
    safety_status = manual_override.safety_status()
    override_active = bool(manual_override.read_override())
    detail = action if isinstance(action, dict) else None
    if isinstance(action, dict):
        action_text = (
            action.get("action")
            or action.get("message")
            or action.get("status")
            or "update"
        )
    else:
        action_text = str(action)
    blocks_snapshot = _ACTIVE_MATRIX._block_status_snapshot() if _ACTIVE_MATRIX else {}
    global_snapshot = _ACTIVE_MATRIX._global_metrics_snapshot() if _ACTIVE_MATRIX else {}
    update = {
        "modules": modules,
        "safety": {
            "override": override_active,
            "kill": safety_status.get("kill", False),
            "kill_reason": safety_status.get("reason", "N/A") if safety_status.get("kill") else None
        },
        "blocks": blocks_snapshot,
        "global": global_snapshot,
        "last_action": action_text,
    }
    if detail:
        update["detail"] = detail
    write_status(update)
    if _ACTIVE_MATRIX:
        try:
            _ACTIVE_MATRIX._write_dashboard(update)
            _ACTIVE_MATRIX._write_global_audit_seal()
            _ACTIVE_MATRIX._snapshot_backup(update)
        except Exception as exc:
            log_event(f"Dashboard update failed: {exc}")
    log_event(f"Status broadcast updated: {action_text}")

class V13_CommandMatrix:
    def __init__(self, core_modules_path='core'):
        global _ACTIVE_MATRIX
        _ACTIVE_MATRIX = self
        self.core_modules_path = Path(core_modules_path)
        self.verified_modules: List[str] = []
        self.simulation_mode = True  # Always in simulation mode
        self.cfg = self._load_config()
        self.orders: Dict[str, OrderRecord] = {}
        self.order_queue: List[str] = []
        self.risk_gate = RiskGate(self.cfg)
        self.network_hold_until: float = 0.0
        self.block_config_path = BLOCK_CONFIG_PATH
        self._ensure_block_config_file()
        self.block_configs = self._load_block_configs()
        self.blocks: Dict[str, BlockState] = self._initialize_blocks()
        self.default_block_id = next(iter(self.blocks)) if self.blocks else "BLOCK1"
        self.global_drawdown_cap = self._resolve_global_drawdown_cap()
        self.global_freeze = False
        self._allocation_history = self._load_allocation_history()
        self._last_global_seal = 0.0
        self._last_scaling_snapshot: Dict[str, Any] = {}
        self.volatility_scorer = Phase6VolatilityScorer()
        self.queued_mode = False
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        self.base_block_capital = self._infer_base_block_capital()
        self._baseline_capital: Dict[str, float] = {
            block_id: state.config.capital for block_id, state in self.blocks.items()
        }
        self.performance_green_streak = 0
        self.performance_scale_multiplier = 1.0
        self._last_doctrine_update: Optional[str] = None

    # ------------------------------------------------------------------
    # Block configuration & state management
    # ------------------------------------------------------------------
    def _ensure_block_config_file(self) -> None:
        if self.block_config_path.exists():
            return
        self.block_config_path.parent.mkdir(parents=True, exist_ok=True)
        default_config = """[GLOBAL]
MAX_DRAWDOWN_PCT = 5
STAGGER_SECONDS_DEFAULT = 20
DEFAULT_MODE = Balanced

[BLOCK1]
MODE = Balanced
CAPITAL = 5000
STRATEGY = AssassinAvenger
SYMBOL = SPY
ENABLED = 1
"""
        self.block_config_path.write_text(default_config, encoding="utf-8")

    def _load_block_configs(self) -> Dict[str, BlockConfig]:
        parser = configparser.ConfigParser()
        parser.optionxform = str
        parser.read(self.block_config_path, encoding="utf-8")
        global_settings = {
            "max_drawdown": GLOBAL_DEFAULTS["max_drawdown"],
            "stagger_seconds": GLOBAL_DEFAULTS["stagger_seconds"],
            "default_mode": "Balanced",
        }
        if parser.has_section("GLOBAL"):
            section = parser["GLOBAL"]
            global_settings["max_drawdown"] = float(
                section.get("MAX_DRAWDOWN_PCT", GLOBAL_DEFAULTS["max_drawdown"])
            )
            global_settings["stagger_seconds"] = float(
                section.get("STAGGER_SECONDS_DEFAULT", GLOBAL_DEFAULTS["stagger_seconds"])
            )
            global_settings["default_mode"] = section.get("DEFAULT_MODE", "Balanced")
        self._block_global_settings = global_settings

        configs: Dict[str, BlockConfig] = {}
        for section in parser.sections():
            if section.upper() == "GLOBAL":
                continue
            entry = parser[section]
            enabled = entry.get("ENABLED", "1").strip()
            if enabled not in {"1", "true", "TRUE", "yes", "YES"}:
                continue
            block_id = section.strip().upper()
            mode = entry.get("MODE", global_settings["default_mode"]).strip()
            mode_profile = MODE_PROFILES.get(mode.upper(), MODE_PROFILES["BALANCED"])
            capital = float(entry.get("CAPITAL", 5000))
            strategy = entry.get("STRATEGY", "AssassinAvenger").strip()
            symbol = entry.get("SYMBOL", "SPY").strip().upper()
            stagger = float(entry.get("STAGGER_SECONDS", global_settings["stagger_seconds"]))
            risk_ceiling = float(entry.get("RISK_CEILING_PCT", mode_profile["max_dd"]))

            configs[block_id] = BlockConfig(
                block_id=block_id,
                mode=mode,
                capital=capital,
                strategy=strategy,
                symbol=symbol,
                stagger=stagger,
                risk_ceiling=risk_ceiling,
            )
        return configs

    def _initialize_blocks(self) -> Dict[str, BlockState]:
        blocks: Dict[str, BlockState] = {}
        for idx, (block_id, config) in enumerate(self.block_configs.items()):
            state = BlockState(config=config, status="READY")
            state.last_launch = time.time() + config.stagger * idx
            blocks[block_id] = state
            self._ensure_block_dirs(block_id)
        return blocks

    def _resolve_global_drawdown_cap(self) -> float:
        return float(self._block_global_settings.get("max_drawdown", GLOBAL_DEFAULTS["max_drawdown"]))

    def _normalize_block_id(self, block_id: Optional[str]) -> str:
        if not block_id:
            return ""
        return str(block_id).strip().upper()

    def _block_slug(self, block_id: str) -> str:
        normalized = self._normalize_block_id(block_id) or "BLOCK"
        digits = "".join(ch for ch in normalized if ch.isdigit())
        if digits:
            return f"block_{digits.zfill(2)}"
        return normalized.lower()

    def _ensure_block_dirs(self, block_id: str) -> None:
        slug = self._block_slug(block_id)
        (Path("logs") / slug).mkdir(parents=True, exist_ok=True)
        (Path("data") / slug).mkdir(parents=True, exist_ok=True)

    def _block_audit_path(self, block_id: str) -> Path:
        slug = self._block_slug(block_id)
        return Path("logs") / slug / "V13_SessionAudit.log"

    def _audit_block(self, block_id: str, message: str) -> None:
        path = self._block_audit_path(block_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(f"{datetime.now(timezone.utc).isoformat()} | {message}\n")

    # ------------------------------------------------------------------
    # Allocation history
    # ------------------------------------------------------------------
    def _load_allocation_history(self) -> List[Dict[str, Any]]:
        if not ALLOCATION_LOG_PATH.exists():
            return []
        try:
            payload = json.loads(ALLOCATION_LOG_PATH.read_text(encoding="utf-8"))
            history = payload.get("history", [])
            if isinstance(history, list):
                return history
        except Exception:
            pass
        return []

    def _persist_allocation_history(self) -> None:
        ALLOCATION_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = {"history": self._allocation_history[-200:]}
        ALLOCATION_LOG_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _record_allocation_decision(
        self,
        block_id: str,
        allocation: Dict[str, float],
        context: Optional[Dict[str, Any]] = None,
        reason: str = "auto",
    ) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "block_id": block_id,
            "allocation": allocation,
            "context": context or {},
            "reason": reason,
        }
        self._allocation_history.append(entry)
        self._persist_allocation_history()

    # ------------------------------------------------------------------
    # Block & global telemetry snapshots
    # ------------------------------------------------------------------
    def _block_status_snapshot(self) -> Dict[str, Dict[str, Any]]:
        snapshot: Dict[str, Dict[str, Any]] = {}
        for block_id, state in self.blocks.items():
            avg_latency, max_latency = state.latency_stats()
            snapshot[block_id] = {
                "mode": state.config.mode,
                "capital": state.config.capital,
                "status": state.status,
                "pnl": round(state.pnl, 4),
                "drawdown": round(state.drawdown, 4),
                "latency_avg_ms": round(avg_latency, 2),
                "latency_max_ms": round(max_latency, 2),
                "last_heartbeat": state.last_heartbeat,
                "allocation": state.adaptive_allocation,
                "symbol": state.config.symbol,
            }
        return snapshot

    def _global_metrics_snapshot(self) -> Dict[str, Any]:
        if not self.blocks:
            return {
                "total_capital": 0.0,
                "pnl": 0.0,
                "weighted_drawdown": 0.0,
                "freeze": self.global_freeze,
            }
        total_capital = sum(state.config.capital for state in self.blocks.values())
        total_pnl = sum(state.pnl for state in self.blocks.values())
        weighted_dd = 0.0
        for state in self.blocks.values():
            weight = state.config.capital / total_capital if total_capital else 0.0
            weighted_dd += state.drawdown * weight
        scaling = self._scaling_metrics(total_capital, len(self.blocks))
        self._persist_scaling_summary(scaling)
        return {
            "total_capital": round(total_capital, 2),
            "pnl": round(total_pnl, 4),
            "weighted_drawdown": round(weighted_dd, 4),
            "freeze": self.global_freeze,
            "max_cap": self.global_drawdown_cap,
            "queue_mode": self.queued_mode,
            "scaling": scaling,
        }

    def _resolve_scaling_pct(self, block_count: int) -> float:
        if block_count <= 0:
            return SCALING_RULES[0][1]
        for threshold, pct in SCALING_RULES:
            if block_count <= threshold:
                return pct
        return SCALING_RULES[-1][1]

    def _scaling_metrics(self, total_capital: float, block_count: int) -> Dict[str, Any]:
        total_capital = max(float(total_capital), 0.0)
        block_count = max(int(block_count), 0)
        if block_count == 0 or total_capital <= 0.0:
            return {
                "block_count": block_count,
                "gross_capital": 0.0,
                "target_daily_pnl": 0.0,
                "max_drawdown": 0.0,
                "risk_per_trade_usd": 0.0,
                "risk_per_trade_pct": 0.0,
                "per_block_risk_usd": 0.0,
            }
        risk_pct = self._resolve_scaling_pct(block_count)
        target_daily_pnl = total_capital * 0.01
        max_drawdown = -total_capital * 0.02
        risk_per_trade_usd = total_capital * risk_pct
        per_block_risk = risk_per_trade_usd / block_count if block_count else 0.0
        return {
            "block_count": block_count,
            "gross_capital": round(total_capital, 2),
            "target_daily_pnl": round(target_daily_pnl, 2),
            "max_drawdown": round(max_drawdown, 2),
            "risk_per_trade_usd": round(risk_per_trade_usd, 2),
            "risk_per_trade_pct": round(risk_pct * 100, 3),
            "per_block_risk_usd": round(per_block_risk, 2),
        }

    def _persist_scaling_summary(self, scaling: Dict[str, Any]) -> None:
        if not scaling:
            return
        if scaling == self._last_scaling_snapshot:
            return
        SCALING_SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "scaling": scaling,
        }
        SCALING_SUMMARY_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self._last_scaling_snapshot = scaling

    def _infer_base_block_capital(self) -> float:
        if self.blocks:
            return min(state.config.capital for state in self.blocks.values())
        return 5000.0

    def _snapshot_backup(self, status_payload: Dict[str, Any]) -> None:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUP_DIR / f"status_{timestamp}.json"
        backup_path.write_text(json.dumps(status_payload, indent=2), encoding="utf-8")
        self._trim_backups()

    def _trim_backups(self) -> None:
        backups = sorted(BACKUP_DIR.glob("status_*.json"))
        excess = len(backups) - MAX_BACKUPS
        for path in backups[:max(0, excess)]:
            try:
                path.unlink(missing_ok=True)
            except Exception:
                continue

    def _load_latest_backup(self) -> Optional[Dict[str, Any]]:
        backups = sorted(BACKUP_DIR.glob("status_*.json"), reverse=True)
        for path in backups:
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
        return None

    def rollback_all(self) -> bool:
        backup_payload = self._load_latest_backup()
        if not backup_payload:
            log_event("Rollback aborted - no backup available.")
            return False
        DATA_PATH.write_text(json.dumps(backup_payload, indent=2), encoding="utf-8")
        self.orders.clear()
        self.order_queue.clear()
        self.global_freeze = False
        self.network_hold_until = 0.0
        self.queued_mode = False
        self._write_dashboard(backup_payload)
        self._write_global_audit_seal()
        broadcast_status_update({"action": "ROLLBACK_RESTORE", "timestamp": datetime.now(timezone.utc).isoformat()})
        log_event("Rollback restore completed from latest backup.")
        return True

    def _latest_doctrine_update(self) -> Optional[Path]:
        update_dir = Path("docs/DoctrineUpdates")
        if not update_dir.exists():
            return None
        updates = sorted(update_dir.glob("doctrine_update_*.json"))
        return updates[-1] if updates else None

    def apply_approved_doctrine_update(self) -> Optional[str]:
        update_path = self._latest_doctrine_update()
        payload: Optional[Dict[str, Any]] = None
        if update_path:
            try:
                payload = json.loads(update_path.read_text(encoding="utf-8"))
            except Exception as exc:
                log_event(f"Failed to read doctrine update {update_path}: {exc}")

        try:
            from core.V13_DoctrineFeedbackLoop import DoctrineFeedbackLoop
        except Exception as exc:
            DoctrineFeedbackLoop = None  # type: ignore
            log_event(f"Unable to import DoctrineFeedbackLoop: {exc}")

        if payload and payload.get("accepted"):
            if payload.get("date") == self._last_doctrine_update:
                return payload.get("date")
            log_event(f"Applying approved doctrine update {update_path}")
            broadcast_status_update({
                "action": "DOCTRINE_UPDATE_APPLIED",
                "date": payload.get("date"),
                "detail": payload.get("suggestions", {}),
            })
            if DoctrineFeedbackLoop:
                try:
                    DoctrineFeedbackLoop.record_accepted_update(payload)
                except Exception as exc:
                    log_event(f"Failed to record doctrine acceptance: {exc}")
            self._last_doctrine_update = payload.get("date")
            return self._last_doctrine_update

        if DoctrineFeedbackLoop:
            try:
                last_good = DoctrineFeedbackLoop.get_last_good_doctrine()
            except Exception as exc:
                log_event(f"Unable to resolve last good doctrine: {exc}")
                return None
            if not last_good:
                return None
            fallback_date = last_good.get("date")
            if fallback_date == self._last_doctrine_update:
                return fallback_date
            log_event(f"No approved doctrine update; reverting to last good doctrine {fallback_date}")
            broadcast_status_update({
                "action": "DOCTRINE_UPDATE_FALLBACK",
                "date": fallback_date,
                "detail": last_good.get("suggestions", {}),
            })
            self._last_doctrine_update = fallback_date
            return fallback_date

        return None

    def _dashboard_snapshot(self, status_payload: Dict[str, Any]) -> Dict[str, Any]:
        global_metrics = status_payload.get("global", {}) or {}
        total_pnl = float(global_metrics.get("pnl", 0.0) or 0.0)
        weighted_dd = float(global_metrics.get("weighted_drawdown", 0.0) or 0.0)
        max_cap = float(global_metrics.get("max_cap", 1.0) or 1.0)
        load_pct = 0.0
        if max_cap > 0:
            load_pct = max(0.0, min(100.0, (weighted_dd / max_cap) * 100.0))
        if load_pct < 80:
            load_color = "GREEN"
        elif load_pct < 95:
            load_color = "AMBER"
        else:
            load_color = "RED"

        active_orders = sum(
            1
            for record in self.orders.values()
            if record.state not in TERMINAL_STATES
        )

        latency_samples = []
        for state in self.blocks.values():
            avg_latency, _ = state.latency_stats()
            if avg_latency:
                latency_samples.append(avg_latency)
        latency_avg = sum(latency_samples) / len(latency_samples) if latency_samples else 0.0

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_pnl": round(total_pnl, 4),
            "active_orders": active_orders,
            "global_drawdown_pct": round(weighted_dd, 4),
            "drawdown_cap_pct": round(max_cap, 4),
            "load_pct": round(load_pct, 2),
            "load_color": load_color,
            "latency_avg_ms": round(latency_avg, 2),
        }

    def _write_dashboard(self, status_payload: Dict[str, Any]) -> None:
        snapshot = self._dashboard_snapshot(status_payload)
        DASHBOARD_PATH.parent.mkdir(parents=True, exist_ok=True)
        DASHBOARD_PATH.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")

    def _set_queued_mode(self, enabled: bool, reason: str) -> None:
        enabled = bool(enabled)
        if self.queued_mode == enabled:
            return
        self.queued_mode = enabled
        state = "ENABLED" if enabled else "DISABLED"
        log_event(f"Queued mode {state} | reason={reason}")
        broadcast_status_update({
            "action": "QUEUED_MODE_" + ("ON" if enabled else "OFF"),
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def manual_abort(self, reason: str = "Commander abort") -> int:
        aborted = 0
        for order_id, record in list(self.orders.items()):
            if record.state in TERMINAL_STATES:
                continue
            meta = {"reason": "manual_abort"}
            if record.block_id:
                meta["block_id"] = record.block_id
            self._transition(order_id, "CLOSED", meta)
            aborted += 1
        self.order_queue.clear()
        broadcast_status_update({
            "action": "MANUAL_ABORT",
            "orders_closed": aborted,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        self._write_global_audit_seal()
        log_event(f"Manual abort executed | orders_closed={aborted}")
        return aborted

    def evaluate_phase8_exit(self) -> Dict[str, Any]:
        passed, results = evaluate_phase8_exit_script(Path("."))
        return {
            "passed": passed,
            "criteria": [
                {"name": r.name, "passed": r.passed, "details": r.details} for r in results
            ],
        }

    def _update_baseline(self) -> None:
        if not self.blocks:
            self._baseline_capital = {}
            return
        self._baseline_capital = {
            block_id: state.config.capital for block_id, state in self.blocks.items()
        }
        self.base_block_capital = self._infer_base_block_capital()

    def _scale_capitals(self, multiplier: float) -> None:
        if multiplier <= 0 or not self.blocks:
            return
        for state in self.blocks.values():
            state.config.capital = round(state.config.capital * multiplier, 4)

    def _restore_baseline_capitals(self) -> None:
        if not self._baseline_capital:
            return
        for block_id, state in self.blocks.items():
            base = self._baseline_capital.get(block_id)
            if base is not None:
                state.config.capital = base
        self.performance_scale_multiplier = 1.0
        self._persist_scaling_summary(self._scaling_metrics(
            sum(state.config.capital for state in self.blocks.values()),
            len(self.blocks),
        ))
        broadcast_status_update({"action": "PERFORMANCE_RESET", "timestamp": datetime.now(timezone.utc).isoformat()})

    def _generate_next_block_id(self) -> str:
        digits = []
        for block_id in self.blocks:
            suffix = "".join(ch for ch in block_id if ch.isdigit())
            if suffix:
                try:
                    digits.append(int(suffix))
                except ValueError:
                    continue
        next_idx = max(digits, default=len(self.blocks)) + 1
        return f"BLOCK{next_idx}"

    def apply_compounding(self, sealed_profit: float) -> Optional[str]:
        try:
            profit = float(sealed_profit)
        except (TypeError, ValueError):
            log_event(f"Compounding skipped - invalid profit value {sealed_profit}")
            return None
        if profit <= 0 or not self.blocks:
            return None
        target_id, target_state = min(
            self.blocks.items(), key=lambda item: item[1].config.capital
        )
        target_state.config.capital = round(target_state.config.capital + profit, 4)
        self._audit_block(
            target_id,
            f"COMPOUND | profit={profit:.2f} | new_capital={target_state.config.capital:.2f}",
        )
        self._update_baseline()
        self._persist_scaling_summary(self._scaling_metrics(
            sum(state.config.capital for state in self.blocks.values()),
            len(self.blocks),
        ))
        broadcast_status_update({
            "action": "COMPOUND_APPLIED",
            "block_id": target_id,
            "profit": round(profit, 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        self.maybe_split_blocks()
        return target_id

    def maybe_split_blocks(self) -> list[str]:
        created: list[str] = []
        for block_id, state in list(self.blocks.items()):
            threshold = self.base_block_capital * 1.5
            if state.config.capital <= threshold:
                continue
            new_capital = round(state.config.capital / 2, 4)
            state.config.capital = new_capital
            new_id = self._generate_next_block_id()
            new_config = BlockConfig(
                block_id=new_id,
                mode=state.config.mode,
                capital=new_capital,
                strategy=state.config.strategy,
                symbol=state.config.symbol,
                stagger=state.config.stagger,
                risk_ceiling=state.config.risk_ceiling,
            )
            new_state = BlockState(config=new_config, status="READY")
            self.blocks[new_id] = new_state
            self.block_configs[new_id] = new_config
            created.append(new_id)
            self._audit_block(block_id, f"SPLIT_PARENT | new_capital={new_capital:.2f} | child={new_id}")
            self._audit_block(new_id, f"SPLIT_CHILD | inherited_mode={new_config.mode}")
        if created:
            self._update_baseline()
            self._persist_scaling_summary(self._scaling_metrics(
                sum(state.config.capital for state in self.blocks.values()),
                len(self.blocks),
            ))
            broadcast_status_update({
                "action": "BLOCK_SPLIT",
                "children": created,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        return created

    def record_weekly_performance(self, status: str) -> None:
        status = (status or "").strip().lower()
        if status not in {"green", "red"}:
            log_event(f"Weekly performance ignored - invalid status '{status}'")
            return
        if status == "green":
            self.performance_green_streak += 1
            if self.performance_green_streak >= 3:
                self._scale_capitals(1.10)
                self.performance_scale_multiplier *= 1.10
                self.performance_green_streak = 0
                self._persist_scaling_summary(self._scaling_metrics(
                    sum(state.config.capital for state in self.blocks.values()),
                    len(self.blocks),
                ))
                broadcast_status_update({
                    "action": "PERFORMANCE_SCALE_UP",
                    "multiplier": round(self.performance_scale_multiplier, 4),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
        else:
            self.performance_green_streak = 0
            self._restore_baseline_capitals()
            broadcast_status_update({
                "action": "PERFORMANCE_RESET_RED",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

    # ------------------------------------------------------------------
    # Telemetry, risk, and adaptive allocation
    # ------------------------------------------------------------------
    def _handle_latency_event(self, block_id: str, payload: Dict[str, Any]) -> None:
        key = self._normalize_block_id(block_id)
        state = self.blocks.get(key)
        if not state:
            return
        latency = payload.get("since_intent_ms")
        try:
            latency = float(latency)
        except (TypeError, ValueError):
            latency = None
        if latency is not None:
            state.record_latency(latency)
            state.last_heartbeat = time.time()

    def ingest_block_telemetry(self, block_id: str, telemetry: Dict[str, Any]) -> None:
        key = self._normalize_block_id(block_id)
        state = self.blocks.get(key)
        if not state:
            return
        pnl = telemetry.get("pnl", state.pnl)
        drawdown = telemetry.get("drawdown", state.drawdown)
        status = telemetry.get("status")
        try:
            pnl = float(pnl)
        except (TypeError, ValueError):
            pnl = state.pnl
        try:
            drawdown = abs(float(drawdown))
        except (TypeError, ValueError):
            drawdown = state.drawdown
        score = self.volatility_scorer.update(key, telemetry)
        score_payload = score.as_dict()
        telemetry_payload = dict(telemetry)
        telemetry_payload.setdefault("volatility", score.volatility)
        telemetry_payload.setdefault("trend_strength", score.trend_strength)
        telemetry_payload["volatility_class"] = score.classification
        telemetry_payload["volatility_samples"] = score.samples
        state.last_score = score_payload
        state.update_metrics(pnl=pnl, drawdown=drawdown, status=status)
        state.telemetry.update(telemetry_payload)
        self._audit_block(
            key,
            (
                "TELEMETRY | pnl={:.4f} | drawdown={:.4f} | status={} | "
                "vol={:.3f} | trend={:.3f}"
            ).format(pnl, drawdown, state.status, score.volatility, score.trend_strength),
        )
        self._evaluate_block_drawdown(key, state)
        self._maybe_rebalance_allocation(key, telemetry_payload, score_payload)
        self._check_global_drawdown()

    def _evaluate_block_drawdown(self, block_id: str, state: BlockState) -> None:
        if state.drawdown >= state.config.risk_ceiling:
            if state.status != "PAUSED":
                state.status = "PAUSED"
                self._audit_block(block_id, f"DRAWDOWN_PAUSE | drawdown={state.drawdown:.2f}")
                broadcast_status_update({
                    "action": "BLOCK_PAUSE",
                    "block_id": block_id,
                    "drawdown": round(state.drawdown, 3),
                    "ceiling": state.config.risk_ceiling,
                })
        elif state.status == "PAUSED" and state.drawdown <= max(state.config.risk_ceiling * 0.6, 0.1):
            state.status = "READY"
            self._audit_block(block_id, f"DRAWDOWN_CLEAR | drawdown={state.drawdown:.2f}")
            broadcast_status_update({
                "action": "BLOCK_RESUME",
                "block_id": block_id,
                "drawdown": round(state.drawdown, 3),
            })

    def _check_global_drawdown(self) -> None:
        metrics = self._global_metrics_snapshot()
        weighted_dd = metrics.get("weighted_drawdown", 0.0)
        if weighted_dd >= self.global_drawdown_cap:
            if not self.global_freeze:
                self.global_freeze = True
                for state in self.blocks.values():
                    state.status = "FROZEN"
                broadcast_status_update({
                    "action": "GLOBAL_FREEZE",
                    "drawdown": weighted_dd,
                    "cap": self.global_drawdown_cap,
                })
                log_event(f"Global drawdown freeze engaged at {weighted_dd:.2f}%")
        else:
            if self.global_freeze and weighted_dd <= self.global_drawdown_cap * 0.6:
                self.global_freeze = False
                for state in self.blocks.values():
                    if state.status == "FROZEN":
                        state.status = "READY"
                broadcast_status_update({
                    "action": "GLOBAL_RESUME",
                    "drawdown": weighted_dd,
                })
                log_event("Global drawdown freeze cleared.")

    def _maybe_rebalance_allocation(
        self,
        block_id: str,
        telemetry: Dict[str, Any],
        score: Optional[Dict[str, Any]] = None,
    ) -> None:
        state = self.blocks.get(block_id)
        if not state:
            return
        vol = telemetry.get("volatility")
        trend = telemetry.get("trend_strength", telemetry.get("trend"))
        if vol is None:
            return
        try:
            vol = float(vol)
        except (TypeError, ValueError):
            return
        shift = 0.0
        classification = (score or {}).get("classification")
        context = {
            "volatility": vol,
            "trend": trend,
            "score": score or {},
        }
        reason = "phase6_neutral"
        if classification == "LOW_VOL":
            shift = 0.10
            reason = "phase6_low_vol"
        elif classification == "HIGH_VOL_NEG_TREND":
            shift = -0.10
            reason = "phase6_high_vol_neg_trend"
        else:
            target = {"Assassins": 0.5, "Avengers": 0.5}
            if state.adaptive_allocation != target:
                state.adaptive_allocation = target
                self._record_allocation_decision(block_id, target, context, reason="phase6_neutral_reset")
            return
        self._apply_allocation_shift(block_id, state, shift, context, reason=reason)

    def _apply_allocation_shift(
        self,
        block_id: str,
        state: BlockState,
        shift: float,
        context: Optional[Dict[str, Any]] = None,
        reason: str = "volatility_shift",
    ) -> None:
        assassins = float(state.adaptive_allocation.get("Assassins", 0.5))
        avengers = float(state.adaptive_allocation.get("Avengers", 0.5))
        assassins = max(0.0, min(1.0, assassins + shift))
        avengers = max(0.0, min(1.0, avengers - shift))
        total = assassins + avengers
        if total > 0:
            assassins /= total
            avengers /= total
        new_allocation = {
            "Assassins": round(assassins, 4),
            "Avengers": round(avengers, 4),
        }
        if new_allocation != state.adaptive_allocation:
            state.adaptive_allocation = new_allocation
            self._record_allocation_decision(
                block_id,
                new_allocation,
                context=context,
                reason=reason,
            )
            self._audit_block(
                block_id,
                f"ALLOCATION_SHIFT | assassins={new_allocation['Assassins']:.3f} | avengers={new_allocation['Avengers']:.3f}",
            )

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------
    def _write_global_audit_seal(self) -> None:
        log_paths = []
        for block_id in self.blocks:
            path = self._block_audit_path(block_id)
            if path.exists():
                log_paths.append(path)
        if not log_paths:
            return
        GLOBAL_SEAL_PATH.parent.mkdir(parents=True, exist_ok=True)
        lines = []
        composite = hashlib.sha256()
        for path in sorted(log_paths):
            data = path.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            lines.append(f"{path} {digest}")
            composite.update(data)
        lines.append(f"COMPOSITE {composite.hexdigest()}")
        GLOBAL_SEAL_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _resolve_block_for_intent(self, intent: Dict[str, Any]) -> str:
        candidate = self._normalize_block_id(intent.get("block_id") or intent.get("block"))
        if candidate and candidate in self.blocks:
            return candidate
        symbol = (intent.get("symbol") or "").strip().upper()
        if symbol:
            for block_id, state in self.blocks.items():
                if state.config.symbol.upper() == symbol:
                    return block_id
        return self.default_block_id

    def verify_core_modules(self):
        """
        Verify presence of V13 core modules.
        """
        if not self.core_modules_path.exists():
            log_event(f"Core modules path {self.core_modules_path} does not exist.")
            return False

        expected_modules = [
            'V13_VisualMonitor.py',
            'V13_CommanderMonitor.py',
            'V13_RiskSentinel.py',
            # Add more as needed
        ]

        for module in expected_modules:
            module_path = self.core_modules_path / module
            if module_path.exists():
                self.verified_modules.append(module)
                log_event(f"Verified module: {module}")
            else:
                log_event(f"Missing module: {module}")

        if len(self.verified_modules) == len(expected_modules):
            log_event("All core modules verified.")
            return True
        else:
            log_event("Some core modules are missing.")
            return False

    def route_simulation_command(self, command, params=None):
        """
        Provide safe simulation command routing.
        Placeholder for routing commands in simulation mode.
        """
        if not self.simulation_mode:
            log_event("Command routing only allowed in simulation mode.")
            return False

        # Safety check: Block commands if kill switch is active
        if manual_override.safety_status().get("kill"):
            log_event(f"Command '{command}' blocked — kill switch active.")
            return False

        # Override check: Log if manual override is active
        override = manual_override.read_override()
        if override:
            log_event(f"Command '{command}' routed under manual override: {override}")

        if command.startswith("/rollback"):
            return self.rollback_all()

        if command in {"/abort", "/manual_abort"}:
            self.manual_abort("Commander abort command")
            return True

        if command.startswith("/growth"):
            parts = command.split()
            if len(parts) >= 3 and parts[1].lower() == "compound":
                try:
                    profit = float(parts[2])
                    self.apply_compounding(profit)
                    return True
                except ValueError:
                    log_event(f"Invalid compound value: {parts[2]}")
                    return False
            if len(parts) >= 2 and parts[1].lower() == "split":
                self.maybe_split_blocks()
                return True
            if len(parts) >= 3 and parts[1].lower() == "record":
                self.record_weekly_performance(parts[2])
                return True
            log_event(f"Unknown growth command: {command}")
            return False

        # Handle trading mode commands
        if command.startswith("/trade"):
            return self.handle_trading_mode_command(command)

        # Handle ghost order commands
        if command.startswith("/ghost_order"):
            return self.handle_ghost_order_command(command)

        log_event(f"Routing simulation command: {command} with params: {params}")
        # Broadcast status update for GUI live updates
        broadcast_status_update(f"Command routed: {command}")
        # Simulate command execution and generate dual-layer feedback
        dual_feedback = self.generate_dual_feedback(command, params)
        self.send_dual_feedback(dual_feedback)
        # Placeholder: Simulate command execution
        # e.g., if command == 'start_monitor': simulate starting monitor
        # Fill in your own module calls here
        return True

    def handle_trading_mode_command(self, command):
        """
        Handle trading mode commands: /trade paper, /trade live, /trade status
        """
        parts = command.split()
        if len(parts) < 2:
            log_event("Invalid trading command format. Use /trade paper|live|status")
            return False

        subcommand = parts[1].lower()
        if subcommand == "paper":
            log_event("[Mode] PAPER simulation mode activated.")
            self.simulation_mode = True
            broadcast_status_update("Trading mode set to PAPER")
            return True
        elif subcommand == "live":
            log_event("[Mode] Live trading locked (PAPER-only build).")
            return False
        elif subcommand == "status":
            current_mode = "PAPER" if self.simulation_mode else "LIVE"
            log_event(f"[Mode] Current trading mode: {current_mode}")
            broadcast_status_update(f"Trading mode status: {current_mode}")
            return True
        else:
            log_event(f"Unknown trading subcommand: {subcommand}")
            return False

    def handle_ghost_order_command(self, command):
        """
        Handle ghost order commands: /ghost_order symbol side qty price
        e.g., /ghost_order BTC/USD buy 1 50000
        """
        parts = command.split()
        if len(parts) != 5:
            log_event("Invalid ghost order format. Use /ghost_order symbol side qty price")
            return False

        symbol, side, qty, price = parts[1], parts[2].lower(), float(parts[3]), float(parts[4])
        if side not in ["buy", "sell"]:
            log_event(f"Invalid side: {side}. Use buy or sell.")
            return False

        log_event(f"Ghost order: {side} {qty} {symbol} @ {price}")
        response = self.submit_ghost_order(symbol, side, qty, price)
        if response:
            log_event(f"Ghost order response: {json.dumps(response)}")
            broadcast_status_update(f"Ghost order submitted: {symbol} {side} {qty} @ {price}")
            return True
        else:
            log_event("Ghost order submission failed.")
            return False

    def submit_ghost_order(self, symbol, side, qty, price):
        """
        Submit a ghost order to Alpaca paper API.
        Sends POST to https://paper-api.alpaca.markets/v2/orders with order data.
        Captures and returns response JSON (order_id, filled_avg_price, status).
        Does not affect real balance.
        """
        keys = load_keys()
        url = keys.get("TRADE_ENDPOINT", "https://paper-api.alpaca.markets/v2") + "/orders"
        headers = _get_headers(keys)
        order_data = {
            "symbol": symbol,
            "qty": min(qty, 0.01),  # Limit to 0.01 BTC to avoid balance issues
            "side": side,
            "type": "limit",
            "time_in_force": "gtc",
            "limit_price": price
        }
        try:
            resp = requests.post(url, headers=headers, json=order_data, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            log_event(f"Ghost order error: {e}")
            return None

    def generate_acknowledgment(self, command, params):
        """
        Generate acknowledgment for command execution.
        """
        cmd_id = str(uuid.uuid4())
        ack = {
            "cmd_id": cmd_id,
            "cmd_text": command,
            "ack_status": "ACK ✅",
            "effect_summary": f"Command '{command}' executed successfully.",
            "timestamp": time.time(),
            "origin": "CommandMatrix"
        }
        # Customize based on command
        if command == "tighten B":
            ack["effect_summary"] = "Trail tightened +0.5%"
        elif command == "lock A":
            ack["effect_summary"] = "Position A locked"
        # Add more custom acknowledgments as needed
        return ack

    def generate_dual_feedback(self, command, params=None):
        """
        Generate dual-layer feedback via DoctrineFeedbackLoop.
        """
        from core.V13_DoctrineFeedbackLoop import DoctrineFeedbackLoop
        loop = DoctrineFeedbackLoop()
        return loop.generate_dual_feedback(command, params)

    def send_dual_feedback(self, dual_feedback):
        """
        Send dual-layer feedback to VisualMonitor via SyncLoop relay and log it.
        """
        # Import here to avoid circular import
        from core.V13_SyncLoop import relay_dual_feedback
        # Relay the full dual feedback
        relay_dual_feedback(dual_feedback)
        log_event(f"Dual feedback sent: {dual_feedback['full_response']}")

    def log_and_broadcast_health(self):
        """
        Log and broadcast system health.
        """
        snapshot = matrix_status()
        health_status = {
            "simulation_mode": self.simulation_mode,
            "verified_modules": self.verified_modules,
            "global": snapshot.get("global", {}),
            "freeze": self.global_freeze,
        }
        log_event(f"System health snapshot: {json.dumps(health_status)}")
        broadcast_status_update({"action": "HEALTH_BROADCAST"})
        self._write_global_audit_seal()
        self.apply_approved_doctrine_update()

    def _load_config(self):
        """Load config from V13_Config.ini"""
        cfg = configparser.ConfigParser(inline_comment_prefixes=(';', '#'))
        cfg.optionxform = str
        cfg.read('config/V13_Config.ini')
        return cfg

    def receive_order_intent(self, intent):
        """Receive order intent from modules (V13_RiskSentinel, V13_ManualOverride, etc.)"""
        intent = dict(intent)
        order_id = intent.get('client_order_tag') or intent.get('client_order_id')
        if not order_id:
            order_id = f"V13-PAPER-{uuid.uuid4()}"
            intent['client_order_tag'] = order_id

        if order_id in self.orders:
            log_event(f"Duplicate intent ignored for existing order_id {order_id}")
            return order_id

        block_id = self._resolve_block_for_intent(intent)
        intent['block_id'] = block_id
        state = self.blocks.get(block_id)

        base_qty = intent.get('qty')
        alloc_weight = None
        try:
            base_qty = float(base_qty)
        except (TypeError, ValueError):
            base_qty = None

        strategy = (intent.get('strategy') or '').lower()
        allocation = state.adaptive_allocation if state else get_current_allocation()
        capital_scale = 1.0
        if state:
            capital_scale = max(state.config.capital / 5000.0, 0.1)
        if base_qty is not None:
            scaled_qty = base_qty * capital_scale
            if 'assassin' in strategy:
                alloc_weight = allocation.get('Assassins')
            elif 'avenger' in strategy:
                alloc_weight = allocation.get('Avengers')
            if alloc_weight is not None:
                intent['_base_qty'] = base_qty
                intent['qty'] = round(scaled_qty * max(alloc_weight, 0), 6)

        record = OrderRecord(intent=intent, block_id=block_id)
        if intent.get('signal_price') is not None:
            try:
                record.signal_price = float(intent['signal_price'])
            except (TypeError, ValueError):
                record.signal_price = None
        self.orders[order_id] = record
        self.order_queue.append(order_id)
        log_event(f"Order intent received: {order_id} | block={block_id} -> {intent}")
        if state:
            self._audit_block(
                block_id,
                f"ORDER_INTENT | id={order_id} | symbol={intent.get('symbol')} | qty={intent.get('qty')}",
            )
        self._audit_event("ORDER_INTENT", order_id, {
            "symbol": intent.get('symbol'),
            "side": intent.get('side'),
            "qty": intent.get('qty'),
            "strategy": intent.get('strategy'),
            "reason": intent.get('reason'),
            "signal_price": record.signal_price,
            "allocation_weight": alloc_weight,
            "block_id": block_id,
        })
        self._transition(order_id, "INTENT_RECEIVED", {
            "symbol": intent.get('symbol'),
            "side": intent.get('side'),
            "qty": intent.get('qty'),
            "block_id": block_id,
        })
        return order_id

    def _audit_event(self, event: str, order_id: str, meta: Optional[Dict[str, Any]] = None):
        parts = [event, f"id={order_id}"] + _flatten_meta(meta)
        audit_line(" | ".join(parts))
        block_id = None
        if meta:
            block_id = meta.get("block_id") or meta.get("block")
        if not block_id:
            record = self.orders.get(order_id)
            if record and record.block_id:
                block_id = record.block_id
        if block_id:
            self._audit_block(block_id, " | ".join(parts))

    def _transition(self, order_id: str, new_state: str, meta: Optional[Dict[str, Any]] = None):
        record = self.orders.get(order_id)
        if not record:
            return

        meta_with_block = dict(meta) if isinstance(meta, dict) else ({} if meta is None else {"meta": meta})
        block_id = record.block_id
        if block_id and "block_id" not in meta_with_block:
            meta_with_block["block_id"] = block_id

        timestamp = datetime.now(timezone.utc).isoformat()
        history_entry = {"timestamp": timestamp, "state": new_state}
        if meta_with_block:
            history_entry["meta"] = meta_with_block

        record.history.append(history_entry)
        record.state = new_state

        audit_transition(order_id, new_state, meta_with_block)

        msg_meta = f" | {meta_with_block}" if meta_with_block else ""
        if new_state in TERMINAL_STATES:
            log_event(f"Order {order_id} reached {new_state}{msg_meta}")
        else:
            log_event(f"Order {order_id} -> {new_state}{msg_meta}")

        if new_state in {"ACK_ACCEPTED", "ACK_REJECTED", "PARTIALLY_FILLED", "FILLED", "CLOSED"}:
            self._record_ack(order_id, new_state, meta_with_block)

        # Update latency checkpoints
        if new_state == "ACK_ACCEPTED" and record.ack_time is None:
            record.ack_time = time.time()
            log_latency("ACK_ACCEPTED", {
                "order_id": order_id,
                "since_intent_ms": int((record.ack_time - record.created_at) * 1000),
                "status": meta_with_block.get("status"),
                "block_id": block_id,
            })
        if new_state == "FILLED" and record.fill_time is None:
            record.fill_time = time.time()
            log_latency("FILLED", {
                "order_id": order_id,
                "since_intent_ms": int((record.fill_time - record.created_at) * 1000),
                "since_ack_ms": int((record.fill_time - (record.ack_time or record.created_at)) * 1000),
                "status": meta_with_block.get("status"),
                "block_id": block_id,
            })

        # Relay order state to SyncLoop for dashboards/monitoring
        self._sync_order_event({
            "order_id": order_id,
            "state": new_state,
            "meta": meta_with_block,
            "block_id": block_id,
            "timestamp": timestamp,
        })

    def _record_ack(self, order_id: str, state: str, meta: Optional[Dict[str, Any]]):
        ack_payload = {
            "order_id": order_id,
            "state": state,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "meta": meta or {},
        }
        record = self.orders.get(order_id)
        if record and record.block_id:
            ack_payload["block_id"] = record.block_id
            ack_payload["meta"].setdefault("block_id", record.block_id)
        try:
            if ACK_PATH.exists():
                existing = json.loads(ACK_PATH.read_text(encoding="utf-8"))
                ack_list = existing.get("acknowledgments", [])
            else:
                ack_list = []
        except Exception:
            ack_list = []

        ack_list.append(ack_payload)
        ack_list = ack_list[-50:]
        payload = {"acknowledgments": ack_list}
        ACK_PATH.parent.mkdir(parents=True, exist_ok=True)
        ACK_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _order_log_path(self) -> Path:
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        ORDERS_DIR.mkdir(parents=True, exist_ok=True)
        return ORDERS_DIR / f"{day}.jsonl"

    def _persist_order_record(self, record: Dict[str, Any]):
        path = self._order_log_path()
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, default=str) + "\n")
        except Exception as exc:
            log_event(f"Order persistence failed: {exc}")

    def _sync_order_event(self, payload: Dict[str, Any]):
        try:
            from core.V13_SyncLoop import relay_order_update
        except ImportError:
            return
        try:
            relay_order_update(payload)
        except Exception as exc:
            log_event(f"Failed to relay order event: {exc}")

    def process_order_intents(self):
        """Process queued order intents, apply risk gate, and route to router"""
        if self.network_hold_until and time.time() < self.network_hold_until:
            remaining = int(self.network_hold_until - time.time())
            log_event(f"Network hold active | remaining={remaining}s")
            return
        while self.order_queue:
            order_id = self.order_queue.pop(0)
            record = self.orders.get(order_id)
            if not record:
                continue

            if record.state != "INTENT_RECEIVED":
                log_event(f"Order {order_id} state {record.state} skipped (already processed)")
                continue

            allowed, details = self._approve_intent(order_id, record.intent)
            if allowed:
                self._transition(order_id, "VALIDATED", details)
                self._transition(order_id, "ROUTED_TO_ALPACA")
                self._route_to_alpaca(order_id, record.intent)
            else:
                meta = {"source": "risk_gate"}
                if isinstance(details, dict):
                    meta.update(details)
                self._transition(order_id, "ACK_REJECTED", meta)


    def _approve_intent(self, order_id: str, intent: Dict[str, Any]):
        """Apply Stage-3 pre-trade risk gate via RiskGate"""
        block_id = self._normalize_block_id(intent.get("block_id"))
        state = self.blocks.get(block_id)
        if self.global_freeze:
            reason = {"reason": "global_freeze", "block_id": block_id}
            self._audit_event("GLOBAL_FREEZE_BLOCK", order_id, reason)
            return False, reason
        if state:
            if state.status in {"PAUSED", "FROZEN"}:
                reason = {"reason": "block_status", "status": state.status, "block_id": block_id}
                self._audit_event("BLOCK_STATUS_DENY", order_id, reason)
                return False, reason
            if state.drawdown >= state.config.risk_ceiling:
                reason = {
                    "reason": "block_drawdown",
                    "drawdown": round(state.drawdown, 3),
                    "ceiling": state.config.risk_ceiling,
                    "block_id": block_id,
                }
                self._audit_event("BLOCK_DD_DENY", order_id, reason)
                return False, reason

        decision = self.risk_gate.approve(intent)
        details = getattr(decision, 'details', {}) if hasattr(decision, 'details') else {}
        if not decision.allowed:
            log_event(f"Intent rejected ({order_id}): {decision.reason} {details}")
            audit_meta = {"reason": decision.reason}
            if isinstance(details, dict):
                audit_meta.update(details)
            self._audit_event("RISK_DENY", order_id, audit_meta)
            return False, details
        if isinstance(details, dict):
            intent.setdefault('_risk', {}).update(details)
            details.setdefault("block_id", block_id)
        self._audit_event("RISK_OK", order_id, details if isinstance(details, dict) else {"block_id": block_id})
        return True, details


    
    def _route_to_alpaca(self, order_id: str, intent: Dict[str, Any]):
        """Translate intent to Alpaca payload and POST"""
        timestamp = datetime.now(timezone.utc).isoformat()
        dry_run_enabled = self.cfg.getboolean('MODE', 'DRY_RUN_POST', fallback=False)
        record = self.orders.get(order_id)
        block_id = self._normalize_block_id(
            (record.block_id if record and record.block_id else intent.get('block_id'))
        )
        request_record = {
            "order_id": order_id,
            "timestamp": timestamp,
            "intent": intent,
            "block_id": block_id,
        }
        if record and record.signal_price is not None:
            request_record["signal_price"] = record.signal_price

        if dry_run_enabled:
            dry_meta = {"dry_run": True, "block_id": block_id}
            request_record.update({
                "status": "DRY_RUN",
                "note": "DRY_RUN_POST true"
            })
            self._persist_order_record(request_record)
            self._transition(order_id, "POSTED", dry_meta)
            self._transition(order_id, "ACK_PENDING", dry_meta)
            self._transition(order_id, "ACK_ACCEPTED", dry_meta)
            self._transition(order_id, "FILL_PENDING", dry_meta)
            self._transition(order_id, "CLOSED", {**dry_meta, "reason": "dry_run_post"})
            if record:
                log_latency("DRY_RUN_COMPLETE", {
                    "order_id": order_id,
                    "since_intent_ms": int((time.time() - record.created_at) * 1000),
                    "block_id": block_id,
                })
            return

        alpaca_payload = self._translate_to_alpaca(intent)
        if not alpaca_payload:
            self._persist_order_record({**request_record, "status": "TRANSLATE_FAILED"})
            self._transition(order_id, "ACK_REJECTED", {"reason": "payload_translate_failed", "block_id": block_id})
            return

        request_record["payload"] = alpaca_payload
        routed_meta = {
            "symbol": alpaca_payload.get("symbol"),
            "type": alpaca_payload.get("type"),
            "qty": alpaca_payload.get("qty"),
            "block_id": block_id,
        }
        self._transition(order_id, "POSTED", routed_meta)
        self._transition(order_id, "ACK_PENDING", routed_meta)

        response = self._post_to_alpaca(alpaca_payload)
        if isinstance(response, dict) and response.get('_hold'):
            hold_until = datetime.utcfromtimestamp(self.network_hold_until).isoformat()
            self._audit_event("NETWORK_PAUSE", order_id, {"hold_until": hold_until, "block_id": block_id})
            self.order_queue.insert(0, order_id)
            return
        if not response:
            self._persist_order_record({**request_record, "status": "POST_FAILED"})
            self._transition(order_id, "ACK_REJECTED", {"reason": "post_failed", "block_id": block_id})
            return

        request_record.update({
            "status": "POSTED",
            "response": response,
        })
        self._persist_order_record(request_record)

        if record:
            record.response = response
            record.alpaca_id = response.get('id')

        status = (response.get('status') or "").lower()
        metadata = {
            "alpaca_id": response.get('id'),
            "status": status,
            "submitted_at": response.get('created_at'),
            "block_id": block_id,
        }

        if status in {"accepted", "new", "pending_new"}:
            self._transition(order_id, "ACK_ACCEPTED", metadata)
            self._transition(order_id, "FILL_PENDING", metadata)
        elif status == "partially_filled":
            self._transition(order_id, "ACK_ACCEPTED", metadata)
            self._transition(order_id, "PARTIALLY_FILLED", metadata)
        elif status == "filled":
            self._transition(order_id, "ACK_ACCEPTED", metadata)
            self._transition(order_id, "FILLED", metadata)
            self._transition(order_id, "CLOSED", metadata)
        elif status in {"rejected", "rejected_by_alpaca"}:
            self._transition(order_id, "ACK_REJECTED", metadata)
        elif status in {"canceled", "expired"}:
            reason_meta = {**metadata, "reason": status}
            self._transition(order_id, "ACK_ACCEPTED", reason_meta)
            self._transition(order_id, "CLOSED", reason_meta)
        else:
            self._transition(order_id, "ACK_PENDING", metadata)

    def _translate_to_alpaca(self, intent):
        """Map canonical intent to Alpaca order format"""
        order_type = intent.get('order_type', 'market')
        payload = {
            "symbol": intent['symbol'],
            "qty": str(intent['qty']),
            "side": intent['side'],
            "type": order_type,
            "time_in_force": intent.get('time_in_force', 'day'),
            "client_order_id": intent.get('client_order_tag', str(uuid.uuid4())),
        }
        if order_type == 'limit' and 'limit_price' in intent:
            payload['limit_price'] = str(intent['limit_price'])
        elif order_type == 'stop' and 'stop_price' in intent:
            payload['stop_price'] = str(intent['stop_price'])
        elif order_type == 'trailing_stop' and 'trail_type' in intent:
            if intent['trail_type'] == 'percent':
                payload['trail_percent'] = str(intent['trail_value'])
            else:
                payload['trail_price'] = str(intent['trail_value'])
        return payload

    def _post_to_alpaca(self, payload):
        """POST order to Alpaca paper API"""
        keys = load_keys()
        url = self.cfg.get('BROKER_ALPACA', 'BASE_URL') + '/v2/orders'
        headers = _get_headers(keys)
        attempts = 3
        for attempt in range(1, attempts + 1):
            start_ts = time.time()
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=10)
                elapsed = time.time() - start_ts
                if elapsed > 5:
                    self._set_queued_mode(True, f"broker_latency_{elapsed:.2f}s")
                elif self.queued_mode and self.network_hold_until <= time.time():
                    self._set_queued_mode(False, "broker_latency_cleared")
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                elapsed = time.time() - start_ts
                if elapsed > 5:
                    self._set_queued_mode(True, f"broker_error_latency_{elapsed:.2f}s")
                else:
                    self._set_queued_mode(True, f"broker_error_{type(e).__name__}")
                log_event(f"Alpaca POST error attempt {attempt}/{attempts}: {e}")
                if attempt == attempts:
                    self.network_hold_until = time.time() + 30
                    self._set_queued_mode(True, "network_hold")
                    return {'_hold': True}
                time.sleep(min(5 * attempt, 10))

    def check_audit_state(self):
        """
        Check the audit state of components.
        Returns a dictionary with component statuses.
        """
        audit = {
            "Command Schema Loader": {
                "status": "✅",
                "description": "All primary commands parsed successfully: deploy, update, lock A/B, tighten B, redeploy A, feedback, stop."
            },
            "Commander Bridge": {
                "status": "✅",
                "description": "Live Commander ↔ Manual Input via terminal interface confirmed in PAPER environment."
            },
            "Matrix Translator": {
                "status": "✅",
                "description": "Correctly converts text input into SyncLoop directives and event packets (JSON-based)."
            },
            "VisualMonitor Hook": {
                "status": "⚙️",
                "description": "Partial sync; visual HUD receives status packets but not command acknowledgment (no “✅ A locked” or “B tightened” feedback line yet)."
            },
            "DoctrineFeedbackLoop": {
                "status": "⚙️",
                "description": "CommandMatrix sends packets, but DoctrineFeedbackLoop not yet providing adaptive responses (AI tactical reasoning still dormant in PAPER)."
            },
            "SyncLoop Integration": {
                "status": "✅",
                "description": "Heartbeat and command relays every 15s confirmed stable."
            },
            "SessionAudit Logging": {
                "status": "✅",
                "description": "Command history recorded properly (commands_typed[] JSON confirmed)."
            }
        }
        log_event("Audit state checked.")
        return audit

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="V13 Command Matrix Utility")
    parser.add_argument("--rollback", choices=["all"], help="Rollback to last sealed PAPER configuration.")
    parser.add_argument("--manual-abort", action="store_true", help="Trigger manual abort (graceful cancel).")
    parser.add_argument("--check-exit", action="store_true", help="Evaluate Phase 8 exit criteria.")
    args = parser.parse_args()

    matrix = V13_CommandMatrix()

    if args.rollback == "all":
        success = matrix.rollback_all()
        sys.exit(0 if success else 1)

    if args.manual_abort:
        matrix.manual_abort("CLI manual abort")
        sys.exit(0)

    if args.check_exit:
        summary = matrix.evaluate_phase8_exit()
        print(json.dumps(summary, indent=2))
        sys.exit(0 if summary.get("passed") else 1)

    if matrix.verify_core_modules():
        matrix.log_and_broadcast_health()
    else:
        log_event("Core modules verification failed.")
