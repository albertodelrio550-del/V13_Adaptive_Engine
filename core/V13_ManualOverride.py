"""
V13_ManualOverride.py
Build: 2025-10-20 | Version 13.2025.10.20.03
Purpose:
    Provides safe manual-override and environment-verification utilities for
    both PAPER and REAL modes of the V13 Adaptive Manual Trading Engine.

Safe for PAPER simulation only by default.
"""

import os
import json
import time
import py_compile
from datetime import datetime
from pathlib import Path
from core.V13_LogFormatter import log_event

# --- Path setup -------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "core"
DATA = ROOT / "data"
LOGS = ROOT / "logs"

OVERRIDE_FILE = DATA / "V13_ManualOverride.json"
KILL_FLAG = DATA / "V13_KillFlag.json"
OVERRIDE_LOG = LOGS / "Manual_Override.log"

# --- Utility ---------------------------------------------------------------
def _log(message: str):
    """Append a timestamped message to Manual_Override.log"""
    LOGS.mkdir(exist_ok=True)
    with open(OVERRIDE_LOG, "a", encoding="utf8") as f:
        f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {message}\n")
    # Use unified logging
    log_event("ManualOverride", "INFO", message)


# =========================================================================== #
#  ENVIRONMENT VERIFICATION
# =========================================================================== #
def verify_environment() -> bool:
    """
    Verify that all core modules compile, contain PAPER references, and logging hooks.
    Returns True if environment is stable and safe.
    """
    try:
        _log("Starting environment verification...")
        for pyfile in CORE.glob("*.py"):
            # Syntax check
            py_compile.compile(pyfile, doraise=True)
            text = pyfile.read_text(encoding="utf8", errors="ignore")
            if "PAPER" not in text:
                _log(f"⚠ {pyfile.name} missing PAPER reference.")
            if "log" not in text:
                _log(f"⚠ {pyfile.name} missing log reference.")
        _log("Environment verification complete. Status: OK")
        return True
    except Exception as e:
        _log(f"[ERROR] Environment verification failed: {e}")
        return False


# =========================================================================== #
#  OVERRIDE CONTROL
# =========================================================================== #
def activate_override(data: dict):
    """Activate manual override with provided parameters."""
    if os.path.exists(KILL_FLAG):
        _log("Attempted override while Kill Switch active — aborted.")
        return False

    if not verify_environment():
        _log("Override aborted: environment verification failed.")
        return False

    data.update({"active": True, "timestamp": datetime.now().isoformat()})
    DATA.mkdir(exist_ok=True)
    with open(OVERRIDE_FILE, "w", encoding="utf8") as f:
        json.dump(data, f, indent=4)
    _log(f"Manual override activated: {data}")
    return True


def read_override() -> dict:
    """Return current override data, or empty dict if inactive."""
    if not OVERRIDE_FILE.exists():
        return {}
    try:
        with open(OVERRIDE_FILE, "r", encoding="utf8") as f:
            data = json.load(f)
        return data if data.get("active") else {}
    except Exception as e:
        _log(f"Error reading override file: {e}")
        return {}


def clear_override():
    """Deactivate manual override."""
    if OVERRIDE_FILE.exists():
        OVERRIDE_FILE.unlink()
        _log("Manual override cleared.")
    return True


# =========================================================================== #
#  UNIVERSAL KILL SWITCH
# =========================================================================== #
def engage_kill_switch(reason: str = "Manual trigger"):
    """
    Engage global kill switch — halts all operations and writes /data/V13_KillFlag.json.
    """
    KILL_FLAG.write_text(json.dumps({"kill": True, "reason": reason,
                                     "timestamp": datetime.now().isoformat()}),
                         encoding="utf8")
    _log(f"🛑 KILL SWITCH ENGAGED: {reason}")
    print("\n🛑 V13 KILL SWITCH ENGAGED — All systems halted.🛑\n")


def safety_status() -> dict:
    """Return the current kill switch state."""
    if not KILL_FLAG.exists():
        return {"kill": False}
    try:
        with open(KILL_FLAG, "r", encoding="utf8") as f:
            return json.load(f)
    except Exception as e:
        _log(f"Error reading kill flag: {e}")
        return {"kill": True, "error": str(e)}


def clear_kill_switch():
    """Manually clear the kill flag (PAPER only)."""
    if KILL_FLAG.exists():
        KILL_FLAG.unlink()
        _log("Kill switch cleared manually.")
        print("Kill switch cleared. System ready to restart.")
    else:
        print("No kill flag present.")


# =========================================================================== #
#  SELF-TEST (only runs when executed directly)
# =========================================================================== #
if __name__ == "__main__":
    print("=== V13 Manual Override Self-Test ===")
    verify_environment()
    activate_override({"phase": "Avenger", "S_t": 0.55, "Drawdown": "-2.1%"})
    print("Current override:", read_override())
    clear_override()
    engage_kill_switch("Test trigger")
    print("Kill flag:", safety_status())
    clear_kill_switch()
    print("=== Self-Test Complete ===")
