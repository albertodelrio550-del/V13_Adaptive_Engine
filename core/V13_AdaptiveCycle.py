class AdaptiveCycle:
    def __init__(self):
        self.mode = 'PAPER'
        self.telemetry = type('T', (), {'refresh_rate': 1})()
        print("[AdaptiveCycle] initialized (stub)")

    def start(self):
        print("[AdaptiveCycle] start called (stub)")
# ==============================================================
# V13_AdaptiveCycle.py — Dynamic Phase Engine
# Build: 2025-10-20 | Version: V13_Stable_Release
# --------------------------------------------------------------
# Function: Manages Assassin⇄Avenger switching based on
# TelemetryFusion signal S_t (sentiment-volatility fusion).
# Hybrid-ready: paper mode simulation with live timing hooks.
# ==============================================================

import time, random, json, os
from pathlib import Path
from collections import deque
from collections import deque

# =========================================================================== #
#  V13 MANUAL OVERRIDE + SAFETY MONITORING INTEGRATION
# =========================================================================== #
import sys
sys.path.append('..')
sys.path.append('../..')
from core import V13_ManualOverride as manual_override
import traceback

# -- Startup Safety Check ----------------------------------------------------
KILL_STATE = manual_override.safety_status()
if KILL_STATE.get("kill"):
    print("\n🛑 V13 Kill Switch is ACTIVE — Launch aborted.")
    print(f"Reason: {KILL_STATE.get('reason', 'Unknown')}")
    print(f"Timestamp: {KILL_STATE.get('timestamp', 'N/A')}\n")
    exit(1)

print("✅ Safety check passed — Adaptive Cycle ready.\n")

# --------------------------------------------------------------
# CONFIGURATION
# --------------------------------------------------------------
REFRESH_INTERVAL = 15        # seconds between cycle updates
S_THRESHOLD = 0.35           # Assassin < 0.35, Avenger ≥ 0.35
LOG_PATH = "../logs/V13_cycle_status.log"
HYBRID_MODE = True           # enables live feed compatibility

# Placeholder for telemetry feed (normally from TelemetryFusion)
def get_signal_from_telemetry():
    """Simulate or import TelemetryFusion output."""
    try:
        # If TelemetryFusion writes to /data/telemetry_signal.json
        if os.path.exists("../data/telemetry_signal.json"):
            with open("../data/telemetry_signal.json", "r") as f:
                data = json.load(f)
            return float(data.get("S_t", 0))
        # Otherwise simulate signal for paper mode
        return round(random.uniform(-1.0, 1.0), 3)
    except Exception:
        return 0.0


def get_price_for_metric():
    try:
        path = Path("../data/telemetry_signal.json")
        if path.exists():
            data = json.loads(path.read_text())
            price = data.get("price") or data.get("last_price")
            if price is not None:
                return float(price)
    except Exception:
        pass
    return None


def compute_realized_vol(prices: deque):
    series = list(prices)
    if len(series) < 10:
        return 0.0
    deltas = [series[i] - series[i - 1] for i in range(1, len(series))]
    mean = sum(deltas) / len(deltas)
    variance = sum((d - mean) ** 2 for d in deltas) / len(deltas)
    return float(abs(variance) ** 0.5)


def compute_tsi(prices: deque):
    series = list(prices)
    if len(series) < 15:
        return 0.0
    short = sum(series[-5:]) / 5
    long = sum(series[-15:]) / 15
    price = series[-1]
    return float(abs(short - long) / price) if price else 0.0


def compute_allocation(vol_score: float, tsi: float):
    assassin_bias = min(max(vol_score, 0.0), 1.0)
    avenger_bias = min(max(tsi * 2, 0.0), 1.0)
    total = assassin_bias + avenger_bias
    if total <= 0:
        return {"Assassins": 0.5, "Avengers": 0.5}
    return {
        "Assassins": round(assassin_bias / total, 3),
        "Avengers": round(avenger_bias / total, 3),
    }


def export_allocation_snapshot(path: Path, allocation: dict, vol_score: float, tsi: float):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "volatility": round(vol_score, 4),
            "tsi": round(tsi, 4),
            "allocation": allocation,
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception:
        pass


def compute_realized_vol(prices: deque):
    if len(prices) < 20:
        return 0.0
    deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    mean = sum(deltas) / len(deltas)
    variance = sum((d - mean) ** 2 for d in deltas) / len(deltas)
    return float(abs(variance) ** 0.5)


def compute_tsi(prices: deque):
    if len(prices) < 25:
        return 0.0
    length = len(prices)
    price = prices[-1]
    series = list(prices)
    short = sum(series[-8:]) / 8
    long = sum(series[-25:]) / 25
    return float(abs(short - long) / price) if price else 0.0


def compute_allocation(vol_score: float, tsi: float):
    # Higher volatility → favor Assassins; stable trend + high TSI → favor Avengers
    assassin_bias = min(max(vol_score * 10, 0), 1)
    avenger_bias = min(max(tsi * 10, 0), 1)
    total = assassin_bias + avenger_bias
    if total == 0:
        return {"Assassins": 0.5, "Avengers": 0.5}
    return {
        "Assassins": round(assassin_bias / total, 3),
        "Avengers": round(avenger_bias / total, 3),
    }


def export_allocation(allocation: dict):
    path = Path("../data/allocation.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    snapshot = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "allocation": allocation,
    }
    path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")

# --------------------------------------------------------------
# LOGGING
# --------------------------------------------------------------
def log_cycle(phase, S_t, mode, allocation=None, vol=None, tsi=None):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    alloc_repr = allocation or {}
    msg = (
        f"{ts} | MODE={mode} | PHASE={phase} | SIGNAL={S_t:.3f} "
        f"| VOL={vol if vol is not None else 'n/a'} "
        f"| TSI={tsi if tsi is not None else 'n/a'} "
        f"| ALLOC={alloc_repr}"
    )
    print(msg)
    with open(LOG_PATH, "a") as f:
        f.write(msg + "\n")

# --------------------------------------------------------------
# CORE LOGIC
# --------------------------------------------------------------
def run_cycle(mode="PAPER"):
    print("==============================================================")
    print(" V13 AdaptiveCycle — ACTIVE")
    print(f" Mode: {mode} | Hybrid Mode: {HYBRID_MODE}")
    print("--------------------------------------------------------------")

    phase = "INIT"
    counter = 0

    while True:
        # =========================================================================== #
        #  RUNTIME SAFETY MONITORING
        # =========================================================================== #
        if manual_override.safety_status().get("kill"):
            print("\n🛑 Kill switch engaged mid-cycle — aborting safely.")
            break

        # Check for manual override
        override = manual_override.read_override()
        if override:
            phase = override.get("phase", phase)
            S_t = override.get("S_t", S_t)
            print(f"⚠️  Manual Override Active: Phase={phase}, S_t={S_t:.3f}")

        S_t = get_signal_from_telemetry()
        prev_phase = phase

        price = get_price_for_metric()
        if price is not None:
            self.price_window.append(price)
        vol_score = compute_realized_vol(self.price_window)
        tsi = compute_tsi(self.price_window)
        allocation = compute_allocation(vol_score, tsi)
        export_allocation_snapshot(self.allocation_path, allocation, vol_score, tsi)

        # Phase determination logic
        if abs(S_t) < 0.05:
            phase = "HOLD"
        elif S_t < S_THRESHOLD:
            phase = "ASSASSIN"
        else:
            phase = "AVENGER"

        # Logging
        if phase != prev_phase:
            print(f"→ Phase Switch: {prev_phase} → {phase} (Signal={S_t:.3f})")
        log_cycle(phase, S_t, mode, allocation, vol_score, tsi)

        # Optional real-time feedback
        if counter % 4 == 0:  # every 4 cycles (~1 min)
            print(f"[Cycle Update] Phase={phase} S_t={S_t:.3f} vol={vol_score:.4f} tsi={tsi:.4f} alloc={allocation}")

        time.sleep(REFRESH_INTERVAL)
        counter += 1

# --------------------------------------------------------------
# ENTRY POINT
# --------------------------------------------------------------
if __name__ == "__main__":
    run_cycle("PAPER")
"""
============================================================
V13_AdaptiveCycle.py — Mode Controller & Runtime Adjuster
Build: 2025-10-20 | DDS Integration (Phase 4-Step 21)
============================================================

Purpose:
    Defines dynamic behavior presets:
        SAFE → Low frequency / tight risk
        BALANCED → Normal DDS baseline
        AGGRESSIVE → High telemetry frequency / loose stops
    Reads parameters from V13_Config.ini on startup.

Dependencies:
    - config/V13_Config.ini
    - V13_RiskSentinel.py
    - V13_TelemetryFusion.py
    - V13_PerformanceTracker.py
"""

import os
import configparser
from datetime import datetime, timezone
import sys
sys.path.append('..')
sys.path.append('../..')
from core.V13_RiskSentinel import RiskMonitor
from core.V13_PerformanceTracker import PerformanceTracker
from core.V13_TelemetryFusion import TelemetryFeed
from core import V13_ManualOverride as manual_override
from collections import deque

# ---------------------------------------------------------------------
# ADAPTIVE CYCLE CONTROLLER
# ---------------------------------------------------------------------
class AdaptiveCycle:
    def __init__(self):
        self.config = self._load_config()
        self.mode = self.config.get("Risk", "Safe_Mode", fallback="Balanced").upper()
        self.telemetry = TelemetryFeed()
        self.risk = RiskMonitor()
        self.performance = PerformanceTracker()
        self.cycle_interval = 2.0
        self.last_mode_switch = None
        self.price_window = deque(maxlen=60)
        self.allocation_path = Path('data') / 'allocation.json'
        self._apply_mode()

    # ---------------------------------------------------------------
    def _load_config(self):
        cfg_path = os.path.join(
            os.getcwd(), "Videos", "bohrn 2025", "trade", "V13", "config", "V13_Config.ini"
        )
        config = configparser.ConfigParser()
        config.read(cfg_path)
        return config

    # ---------------------------------------------------------------
    def _apply_mode(self):
        """Apply operational parameters based on selected mode."""
        mode = self.mode
        if mode == "SAFE":
            self.risk.max_dd = 1.0
            self.telemetry.refresh_rate = 2.5
            self.performance_lock = 0.9
            self.cycle_interval = 3.0
        elif mode == "BALANCED":
            self.risk.max_dd = 2.0
            self.telemetry.refresh_rate = 1.5
            self.performance_lock = 0.8
            self.cycle_interval = 2.0
        elif mode == "AGGRESSIVE":
            self.risk.max_dd = 3.0
            self.telemetry.refresh_rate = 0.8
            self.performance_lock = 0.7
            self.cycle_interval = 1.0
        else:
            self.mode = "BALANCED"
            self._apply_mode()
            return

        self.last_mode_switch = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"⚙️ [AdaptiveCycle] Mode set → {self.mode}")
        print(f"   ↳ MaxDD={self.risk.max_dd}% | Telemetry={self.telemetry.refresh_rate}s | Cycle={self.cycle_interval}s")

    # ---------------------------------------------------------------
    def switch_mode(self, new_mode):
        """Manually switch operational mode."""
        self.mode = new_mode.upper()
        self._apply_mode()

    # ---------------------------------------------------------------
    def execute_cycle(self, feed):
        """Perform adaptive feedback iteration (telemetry + risk + performance)."""
        # Safety validation hook: Check kill switch before execution
        if manual_override.safety_status().get("kill"):
            print("\n🛑 Kill switch active — cycle execution aborted.")
            return {"error": "Kill switch engaged"}

        # Override logic hook: Apply manual override if active
        override = manual_override.read_override()
        if override:
            print(f"⚠️  Manual Override Active: Adjusting cycle parameters.")
            # Example: Override mode or parameters based on override data
            if "phase" in override:
                self.mode = override["phase"].upper()
                self._apply_mode()

        print(f"\n🌀 [AdaptiveCycle] Executing {self.mode} cycle...")
        risk_state = self.risk.assess(feed)
        perf_state = self.performance.track(feed)
        print(f"   → Risk: {risk_state} | PnL: {perf_state['profit']:+.2f} | Ladder: {perf_state['ladder']}")
        return {
            "mode": self.mode,
            "risk": risk_state,
            "performance": perf_state,
        }

# ---------------------------------------------------------------------
# DIAGNOSTIC EXECUTION
# ---------------------------------------------------------------------
if __name__ == "__main__":
    ac = AdaptiveCycle()
    mock_feed = {"pnl": +45, "delta": +0.15}
    ac.execute_cycle(mock_feed)
    ac.switch_mode("Aggressive")
    ac.execute_cycle({"pnl": +75, "delta": +0.20})

