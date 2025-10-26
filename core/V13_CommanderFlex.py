# ============================================================
#  V13_CommanderFlex.py
#  Build: V13 — Manual Trading Engine (Commander Flex Layer)
#  Mode: Paper-Only Simulation
#  Purpose: Central command layer for managing all strategy
#           soldiers, overrides, priorities, and coordination.
# ============================================================

import datetime
from V13_DoctrineFeedbackLoop import DoctrineFeedbackLoop, FeedbackReport
from typing import List, Dict, Optional
from V13_PerformanceTracker import PerformanceTracker

# ============================================================
# SECTION 1 — STRATEGY SOLDIER BASE CLASS
# ============================================================

class StrategySoldier:
    """Base unit representing an individual strategy in the V13 system."""

    def __init__(self, soldier_id: str, name: str, role: str, priority: int):
        self.soldier_id = soldier_id
        self.name = name
        self.role = role
        self.priority = priority
        self.status = "Idle"          # Idle | Active | Standby | Override | Fault
        self.signal_strength = 0.0
        self.current_order = None
        self.last_action = None

    def receive_order(self, order: str):
        self.current_order = order
        self.status = "Active"
        self.last_action = datetime.datetime.now(timezone.utc)

    def set_status(self, new_status: str):
        self.status = new_status
        self.last_action = datetime.datetime.now(timezone.utc)

    def report(self) -> Dict:
        return {
            "soldier_id": self.soldier_id,
            "name": self.name,
            "role": self.role,
            "status": self.status,
            "priority": self.priority,
            "signal_strength": round(self.signal_strength, 2),
            "order": self.current_order,
            "last_action": self.last_action,
        }
# ============================================================
# SECTION 2 — COMMANDER FEEDBACK INTEGRATION
# ============================================================

class CommanderFeedbackIntegration:
    """
    Couples CommanderFlex with DoctrineFeedbackLoop.
    Handles automatic priority updates from feedback reports.
    """

    def __init__(self, commander):
        self.commander = commander
        self.feedback_loop = DoctrineFeedbackLoop(commander)
        self.last_update = None

    def ingest_feedback(self, soldier_name: str, result: str, pnl: float, accuracy: float, latency: float):
        """Collects and processes incoming feedback."""
        report = FeedbackReport(soldier_name, result, pnl, accuracy, latency)
        msg = self.feedback_loop.collect_feedback(report)
        self.last_update = datetime.datetime.now(timezone.utc)
        return msg

    def recalibrate_priorities(self):
        """Recalculate soldier priorities from feedback data."""
        updated = self.feedback_loop.adjust_priorities()
        report = self.feedback_loop.performance_report()
        self.commander.command_log.append({
            "action": "recalibration",
            "timestamp": datetime.datetime.now(timezone.utc),
            "updates": updated
        })
        return {"updated_priorities": updated, "performance_report": report}

    def print_summary(self):
        data = self.recalibrate_priorities()
        print("\n=== FEEDBACK LOOP SUMMARY ===")
        for r in data["performance_report"]:
            print(f"{r['soldier']}: {r['win_rate']}% win, PnL {r['net_pnl']}, Priority {r['current_priority']}")
        print("Updated Priorities:", data["updated_priorities"])
        print("==============================\n")

# ============================================================
# SECTION 3 — SOLDIER REGISTRY
# ============================================================

class SoldierRegistry:
    """Registry to manage all strategy soldiers and their statuses."""

    def __init__(self):
        self.soldiers: Dict[str, StrategySoldier] = {}

    def register(self, soldier: StrategySoldier):
        self.soldiers[soldier.name] = soldier

    def get(self, name: str) -> Optional[StrategySoldier]:
        return self.soldiers.get(name)

    def list_active(self) -> List[str]:
        return [s.name for s in self.soldiers.values() if s.status == "Active"]

    def all_reports(self) -> Dict[str, Dict]:
        return {name: soldier.report() for name, soldier in self.soldiers.items()}

# ============================================================
# SECTION 4 — COMMANDER FLEX CORE
# ============================================================

class CommanderFlex:
    """Central command layer that issues orders, manages overrides, and applies FlexFilter logic."""

    def __init__(self, registry: SoldierRegistry):
        self.registry = registry
        self.active_team: List[str] = []
        self.command_log: List[Dict] = []

    # --- Order Control ---
    def assign(self, name: str, order: str):
        soldier = self.registry.get(name)
        if not soldier:
            return f"❌ Soldier {name} not found."
        soldier.receive_order(order)
        self.command_log.append({"action": "assign", "soldier": name, "order": order})
        return f"🪶 Order assigned to {name}: '{order}'"

    def stand_down(self, name: str):
        soldier = self.registry.get(name)
        if not soldier:
            return f"❌ Soldier {name} not found."
        soldier.set_status("Standby")
        self.command_log.append({"action": "stand_down", "soldier": name})
        return f"🟡 {name} moved to Standby."

    def override(self, target: str, replacement: str):
        t_soldier = self.registry.get(target)
        r_soldier = self.registry.get(replacement)
        if not t_soldier or not r_soldier:
            return "❌ Invalid override request."
        t_soldier.set_status("Override")
        r_soldier.set_status("Active")
        self.command_log.append({"action": "override", "target": target, "replacement": replacement})
        return f"🔁 Override: {replacement} replaces {target}"

    def promote(self, name: str, new_priority: int):
        soldier = self.registry.get(name)
        if not soldier:
            return f"❌ Soldier {name} not found."
        soldier.priority = new_priority
        self.command_log.append({"action": "promote", "soldier": name, "priority": new_priority})
        return f"🔺 {name} promoted to priority {new_priority}"

    def merge(self, group: List[str], mode: str):
        for s in group:
            soldier = self.registry.get(s)
            if soldier:
                soldier.set_status("Active")
        self.command_log.append({"action": "merge", "group": group, "mode": mode})
        return f"🧩 Merged team {group} under mode '{mode}'"

    # --- Filtering and Selection ---
    def flex_filter(self):
        """Core logic to select lead strategy and support confirmations."""
        active = [s for s in self.registry.soldiers.values() if s.status == "Active"]
        if not active:
            return {"lead": None, "support": [], "confidence": 0.0}

        # Sort by priority, then signal strength
        active.sort(key=lambda s: (s.priority, s.signal_strength), reverse=True)
        lead = active[0].name
        support = [s.name for s in active[1:3]]  # top 2 supports
        confidence = min(1.0, 0.5 + 0.05 * len(active))
        self.active_team = [lead] + support

        return {"lead": lead, "support": support, "confidence": round(confidence, 2)}

    # --- Reporting ---
    def commander_report(self) -> Dict:
        return {
            "timestamp": datetime.datetime.now(timezone.utc),
            "active_team": self.active_team,
            "all_status": self.registry.all_reports(),
            "log_entries": len(self.command_log),
        }

    def print_status(self):
        print("\n=== COMMANDER FLEX STATUS ===")
        data = self.commander_report()
        print(f"Active Team: {data['active_team']}")
        print(f"Total Soldiers: {len(data['all_status'])}")
        print(f"Command Log Entries: {data['log_entries']}")
        print("-------------------------------")
        for name, rep in data["all_status"].items():
            print(f"{name}: {rep['status']} | Order: {rep['order']} | Priority: {rep['priority']}")
        print("-------------------------------\n")
        return data

# ============================================================
# SECTION 5 — INITIALIZATION
# ============================================================

def initialize_commander_flex():
    registry = SoldierRegistry()
    registry.register(StrategySoldier("S01", "Fabio", "Auction Market", 5))
    registry.register(StrategySoldier("S02", "Mayne", "Structure / OTE", 5))
    registry.register(StrategySoldier("S03", "Umar", "Discipline / Process", 10))
    registry.register(StrategySoldier("S04", "Marco", "Liquidity Trap", 6))
    registry.register(StrategySoldier("S05", "Kane", "SMT / PO3", 7))
    registry.register(StrategySoldier("S06", "TG_Capital", "London Swing / Trident", 4))
    registry.register(StrategySoldier("S07", "Tanja", "AMD / Event Bias", 8))
    commander = CommanderFlex(registry)

    # 🔁 Attach feedback interface
    commander.feedback = CommanderFeedbackIntegration(commander)
    # 🔁 Attach feedback interface
    commander.feedback = CommanderFeedbackIntegration(commander)

    # 🧠 Auto-Bias soldiers from lifetime performance tracker
    tracker = PerformanceTracker()
    data = tracker.data

    if data:
        print(f"🧩 Applying lifetime bias from PerformanceTracker ({len(data)} records)")
        for name, stats in data.items():
            s = commander.registry.get(name)
            if s:
                win_rate = stats.get("win_rate", 50)
                net_pnl = stats.get("net_pnl", 0)
                # Bias formula: base priority + weighted performance boost
                bias_boost = (win_rate / 100) * 2 + (1 if net_pnl > 0 else 0)
                s.priority = min(10, int(s.priority + bias_boost))
                s.signal_strength = round(win_rate / 10, 2)
                print(f"   {s.name:<10} | WinRate: {win_rate:>5}% | PnL: {net_pnl:+6.2f} | Priority → {s.priority}")
    else:
        print("🆕 No performance data found — starting neutral priorities.")

    return commander

# ============================================================
# MAIN DEMO EXECUTION
# ============================================================

if __name__ == "__main__":
    commander = initialize_commander_flex()

    # Assign initial orders
    print(commander.assign("Fabio", "Monitor balance zones"))
    print(commander.assign("Tanja", "Prepare AMD confirmation"))
    print(commander.assign("Marco", "Scan liquidity traps"))
    print(commander.promote("Tanja", 9))

    # Override example
    print(commander.override("Fabio", "Mayne"))

    # Merge example
    print(commander.merge(["Tanja", "Marco"], mode="HybridPrecision"))

    # Run FlexFilter to choose lead & support
    decision = commander.flex_filter()
    print(f"FlexFilter Decision → Lead: {decision['lead']}, Support: {decision['support']}, Confidence: {decision['confidence']}")

    # Report full status
    commander.print_status()
    print("Status: ✅ Commander Flex Layer operational.")

    # === FEEDBACK TEST ===
    print("\nSimulating post-session feedback...")
    commander.feedback.ingest_feedback("Tanja", "WIN", +3.5, 0.9, 1.1)
    commander.feedback.ingest_feedback("Marco", "LOSS", -1.0, 0.6, 0.8)
    commander.feedback.ingest_feedback("Kane", "WIN", +1.8, 0.75, 1.0)

    commander.feedback.print_summary()

