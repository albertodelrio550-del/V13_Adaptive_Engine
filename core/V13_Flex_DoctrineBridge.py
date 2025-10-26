# ============================================================
#  V13_Flex_DoctrineBridge.py
#  Build: V13 — Manual Trading Engine (Flex–Doctrine Bridge)
#  Mode: Paper-Only Simulation
#  Purpose: Bridge CommanderFlex outputs to Doctrine Execution Layer.
# ============================================================

import datetime
from typing import Dict, List

# ============================================================
# SECTION 1 — FLEX–DOCTRINE BRIDGE CORE
# ============================================================

class FlexDoctrineBridge:
    """
    Connects CommanderFlex to the Doctrine Execution Layer.
    Handles signal routing, confirmation checks, and doctrine activation.
    """

    def __init__(self, commander):
        self.commander = commander
        self.active_doctrine = None
        self.bridge_log: List[Dict] = []
        self.bridge_state = "Idle"  # Idle | Linking | Active | Locked

    def evaluate_team(self):
        """
        Pulls the current active team from CommanderFlex and selects doctrine set.
        """
        flex_result = self.commander.flex_filter()
        self.active_doctrine = flex_result["lead"]
        self.bridge_state = "Linking"
        self.bridge_log.append({
            "timestamp": datetime.datetime.now(timezone.utc),
            "lead": flex_result["lead"],
            "support": flex_result["support"],
            "confidence": flex_result["confidence"]
        })
        return flex_result

    def activate_doctrine(self):
        """
        Activates the selected doctrine within the bridge.
        """
        if not self.active_doctrine:
            return "❌ No active doctrine to engage."
        self.bridge_state = "Active"
        msg = f"⚔️ Doctrine '{self.active_doctrine}' activated."
        self.bridge_log.append({
            "timestamp": datetime.datetime.now(timezone.utc),
            "action": "activate",
            "doctrine": self.active_doctrine
        })
        return msg

    def relay_order(self, order: str):
        """
        Relays new orders from CommanderFlex to Doctrine layer.
        """
        if self.bridge_state not in ("Linking", "Active"):
            return "❌ Bridge not ready for order relay."
        timestamp = datetime.datetime.now(timezone.utc)
        self.bridge_log.append({
            "timestamp": timestamp,
            "action": "relay_order",
            "order": order,
            "doctrine": self.active_doctrine
        })
        return f"📡 Order relayed to {self.active_doctrine}: '{order}'"

    def lock_bridge(self):
        """Lock the bridge to prevent any further updates (used during cooldown)."""
        self.bridge_state = "Locked"
        self.bridge_log.append({
            "timestamp": datetime.datetime.now(timezone.utc),
            "action": "lock",
            "doctrine": self.active_doctrine
        })
        return "🔒 Bridge locked — all doctrines held in current state."

    def reset_bridge(self):
        """Reset bridge to idle state."""
        self.bridge_state = "Idle"
        self.active_doctrine = None
        self.bridge_log.clear()
        return "🔄 Bridge reset to idle."

    def report(self) -> Dict:
        """Return current bridge status."""
        return {
            "state": self.bridge_state,
            "active_doctrine": self.active_doctrine,
            "log_count": len(self.bridge_log),
            "last_entry": self.bridge_log[-1] if self.bridge_log else None,
        }

# ============================================================
# SECTION 2 — MOCK DOCTRINE MANAGER (SIMULATION)
# ============================================================

class DoctrineManager:
    """
    Simulated Doctrine Layer (paper-only mode).
    Receives activation signals and executes dummy responses.
    """

    def __init__(self):
        self.active_strategy = None

    def deploy(self, doctrine_name: str):
        self.active_strategy = doctrine_name
        print(f"🛰️ DoctrineManager: Deploying strategy '{doctrine_name}'")

    def execute(self, command: str):
        if not self.active_strategy:
            return "❌ No doctrine deployed."
        print(f"🪶 Executing command '{command}' under {self.active_strategy}")
        return "✅ Execution logged."

# ============================================================
# SECTION 3 — LINKAGE TEST (MAIN EXECUTION)
# ============================================================

if __name__ == "__main__":
    from V13_CommanderFlex import initialize_commander_flex

    print("\n=== V13 Flex–Doctrine Bridge Test Run ===")
    commander = initialize_commander_flex()
    bridge = FlexDoctrineBridge(commander)
    doctrine_manager = DoctrineManager()

    # Simulate assignment of soldiers and filtering
    commander.assign("Tanja", "Engage AMD phase detection")
    commander.assign("Marco", "Precision Trap validation")
    commander.promote("Tanja", 10)
    team = bridge.evaluate_team()

    print(f"Selected Doctrine: {team['lead']} (Confidence: {team['confidence']})")

    # Activate doctrine
    print(bridge.activate_doctrine())
    doctrine_manager.deploy(bridge.active_doctrine)

    # Relay Commander order
    print(bridge.relay_order("Prepare entry conditions for confirmed signal"))
    doctrine_manager.execute("Confirm signal execution")

    # Lock and report
    print(bridge.lock_bridge())
    print(bridge.report())
    print("Status: ✅ V13 Flex–Doctrine Bridge operational.")
