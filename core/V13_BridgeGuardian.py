# ============================================================
#  V13_BridgeGuardian.py
#  Build: V13 — Manual Trading Engine (Command Relay Safety Layer)
#  Mode: Paper-Only Simulation
#  Purpose: Monitors, verifies, and secures all command transmissions
#           between CommanderFlex and DoctrineBridge.
# ============================================================

import datetime
import time
import random
from typing import Dict, List


class BridgeGuardian:
    """
    Supervises command transmissions to prevent duplicate relays,
    ensure confirmation, and handle timeout or failure scenarios.
    """

    def __init__(self, bridge, timeout_seconds: int = 5):
        self.bridge = bridge
        self.timeout = timeout_seconds
        self.active_relays: Dict[str, Dict] = {}
        self.confirmed_relays: List[Dict] = []
        self.failed_relays: List[Dict] = []
        self.guardian_log: List[Dict] = []

    # --------------------------------------------------------
    # COMMAND RELAY VALIDATION
    # --------------------------------------------------------
    def verify_before_relay(self, doctrine_name: str) -> bool:
        """Prevents duplicate activation or overlapping relay."""
        if doctrine_name in self.active_relays:
            print(f"⚠️ BridgeGuardian: Duplicate relay attempt blocked for {doctrine_name}.")
            return False
        return True

    def relay_command(self, doctrine_name: str, order: str):
        """Send relay with validation and monitoring."""
        if not self.verify_before_relay(doctrine_name):
            return "❌ Relay blocked by Guardian."

        timestamp = datetime.datetime.now(timezone.utc)
        self.active_relays[doctrine_name] = {
            "order": order,
            "timestamp": timestamp,
            "status": "pending"
        }
        self.guardian_log.append({
            "timestamp": timestamp.isoformat(),
            "doctrine": doctrine_name,
            "action": "relay_init",
            "order": order
        })
        print(f"🛰️ BridgeGuardian: Relaying command → {doctrine_name}: '{order}'")

        # Simulated transmission delay
        time.sleep(random.uniform(0.2, 0.8))

        # Execute relay via bridge
        result = self.bridge.relay_order(order)
        confirmation = self.await_confirmation(doctrine_name, result)
        return confirmation

    # --------------------------------------------------------
    # CONFIRMATION & TIMEOUT HANDLING
    # --------------------------------------------------------
    def await_confirmation(self, doctrine_name: str, result: str):
        """Wait for relay confirmation within timeout window."""
        start = datetime.datetime.now(timezone.utc)
        confirmed = False

        for _ in range(self.timeout * 2):  # check every 0.5 sec
            time.sleep(0.5)
            # Simulation: random confirmation pass/fail
            confirmed = random.random() > 0.1
            if confirmed:
                break

        end = datetime.datetime.now(timezone.utc)
        elapsed = (end - start).total_seconds()

        if confirmed:
            print(f"✅ BridgeGuardian: {doctrine_name} acknowledged in {elapsed:.2f}s.")
            self._finalize_relay(doctrine_name, "confirmed", elapsed)
            return f"✅ Relay confirmed for {doctrine_name}"
        else:
            print(f"❌ BridgeGuardian: {doctrine_name} failed to confirm within {self.timeout}s.")
            self._finalize_relay(doctrine_name, "failed", elapsed)
            return f"⚠️ Relay timeout for {doctrine_name}"

    # --------------------------------------------------------
    # INTERNAL HANDLERS
    # --------------------------------------------------------
    def _finalize_relay(self, doctrine_name: str, status: str, elapsed: float):
        entry = self.active_relays.pop(doctrine_name, None)
        if not entry:
            return

        entry["status"] = status
        entry["elapsed"] = elapsed
        entry["timestamp_closed"] = datetime.datetime.now(timezone.utc).isoformat()

        if status == "confirmed":
            self.confirmed_relays.append(entry)
        else:
            self.failed_relays.append(entry)

        self.guardian_log.append({
            "timestamp": entry["timestamp_closed"],
            "doctrine": doctrine_name,
            "action": "relay_complete",
            "status": status,
            "elapsed": round(elapsed, 2)
        })

    # --------------------------------------------------------
    # DIAGNOSTICS
    # --------------------------------------------------------
    def guardian_report(self) -> Dict:
        return {
            "active_relays": len(self.active_relays),
            "confirmed_relays": len(self.confirmed_relays),
            "failed_relays": len(self.failed_relays),
            "last_event": self.guardian_log[-1] if self.guardian_log else None
        }

    def purge_failed_relays(self):
        """Clean failed relays for next cycle."""
        count = len(self.failed_relays)
        self.failed_relays.clear()
        print(f"🧹 BridgeGuardian: Purged {count} failed relay records.")

    def diagnostics(self):
        report = self.guardian_report()
        print("\n=== Bridge Guardian Report ===")
        print(f"Active Relays: {report['active_relays']}")
        print(f"Confirmed: {report['confirmed_relays']} | Failed: {report['failed_relays']}")
        print(f"Last Event: {report['last_event']}")
        print("==============================\n")
        return report


# ============================================================
# SECTION 2 — DEMO EXECUTION
# ============================================================

if __name__ == "__main__":
    from V13_Flex_DoctrineBridge import FlexDoctrineBridge
    from V13_CommanderFlex import initialize_commander_flex

    commander = initialize_commander_flex()
    bridge = FlexDoctrineBridge(commander)
    guardian = BridgeGuardian(bridge)

    print("\n=== V13 BridgeGuardian Demo ===")
    bridge.evaluate_team()
    bridge.activate_doctrine()

    # Simulate multiple relays
    orders = [
        "Prepare entry validation",
        "Deploy precision confirmation",
        "Adjust stop alignment",
        "Close all signals"
    ]

    for o in orders:
        doctrine_name = bridge.active_doctrine or "Unknown"
        guardian.relay_command(doctrine_name, o)
        guardian.diagnostics()
        time.sleep(1)
