# ============================================================
#  V13_SessionLogger.py
#  Build: V13 — Manual Trading Engine (Session Logging Layer)
#  Mode: Paper-Only Simulation
#  Purpose: Record each adaptive cycle's telemetry, commander
#           state, doctrine decisions, and feedback results.
# ============================================================

import json
import os
import datetime
from typing import Dict, Any, List

# ============================================================
# SECTION 1 — LOGGER CORE
# ============================================================

class SessionLogger:
    """Handles persistent logging for V13 adaptive cycles."""

    def __init__(self, log_dir: str = "../logs", filename: str = "V13_SessionLog.json"):
        self.log_dir = os.path.abspath(log_dir)
        os.makedirs(self.log_dir, exist_ok=True)
        self.log_path = os.path.join(self.log_dir, filename)
        self.records: List[Dict[str, Any]] = []

    # --------------------------------------------------------
    # APPEND NEW CYCLE ENTRY
    # --------------------------------------------------------
    def log_cycle(self, cycle_index: int, telemetry: Dict, decision: Dict, feedback_summary: List[Dict]):
        """Store telemetry, commander decision, and feedback summary."""
        entry = {
            "cycle": cycle_index,
            "timestamp": datetime.datetime.now(timezone.utc).isoformat(),
            "telemetry": telemetry,
            "decision": decision,
            "feedback_summary": feedback_summary,
        }
        self.records.append(entry)
        return entry

    # --------------------------------------------------------
    # SAVE SESSION DATA
    # --------------------------------------------------------
    def save_session(self):
        """Write log entries to persistent JSON file."""
        data = {
            "session_timestamp": datetime.datetime.now(timezone.utc).isoformat(),
            "entries": self.records,
        }
        with open(self.log_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        print(f"💾 Session saved to {self.log_path}")
        return self.log_path

    # --------------------------------------------------------
    # LOAD PREVIOUS LOG
    # --------------------------------------------------------
    def load_previous(self) -> Dict:
        """Load the most recent saved log (if any)."""
        if not os.path.exists(self.log_path):
            return {"status": "no_previous_log"}
        with open(self.log_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # --------------------------------------------------------
    # QUICK SUMMARY
    # --------------------------------------------------------
    def summary(self):
        total = len(self.records)
        print(f"\n=== V13 Session Summary ===")
        print(f"Total Cycles Recorded: {total}")
        if total:
            print(f"Start Time: {self.records[0]['timestamp']}")
            print(f"End Time:   {self.records[-1]['timestamp']}")
            print(f"File: {self.log_path}")
        print("===========================\n")
        return total

# ============================================================
# SECTION 2 — DEMO / TEST
# ============================================================

if __name__ == "__main__":
    from random import randint
    logger = SessionLogger()

    # Simulated demo entry
    telemetry = {"session": "New York", "volatility_index": 61.2, "event": "CPI"}
    decision = {"lead": "Tanja", "support": ["Marco"], "confidence": 0.72}
    feedback = [
        {"soldier": "Tanja", "win_rate": 80.0, "net_pnl": 2.1, "current_priority": 9},
        {"soldier": "Marco", "win_rate": 60.0, "net_pnl": 0.8, "current_priority": 6},
    ]

    for i in range(3):
        logger.log_cycle(i + 1, telemetry, decision, feedback)

    logger.save_session()
    logger.summary()
