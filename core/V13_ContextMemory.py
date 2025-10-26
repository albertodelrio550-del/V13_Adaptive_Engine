# ============================================================
#  V13_ContextMemory.py
#  Build: V13 — Manual Trading Engine (Context Memory Layer)
#  Mode: Paper-Only Simulation
#  Purpose: Maintain historical volatility, session bias,
#           and event trend memory for CommanderFlex.
# ============================================================

import os
import json
import datetime
from statistics import mean
from typing import Dict, List, Optional


class ContextMemory:
    """
    Tracks rolling session data such as volatility, event impact,
    and directional bias to create a persistent context memory.
    """

    def __init__(self, log_dir: str = "../logs", filename: str = "V13_ContextMemory.json"):
        self.log_dir = os.path.abspath(log_dir)
        os.makedirs(self.log_dir, exist_ok=True)
        self.path = os.path.join(self.log_dir, filename)
        self.memory: Dict[str, List[Dict]] = self._load_memory()

    # --------------------------------------------------------
    # INTERNAL HANDLERS
    # --------------------------------------------------------
    def _load_memory(self) -> Dict:
        if not os.path.exists(self.path):
            return {"London": [], "New York": [], "Asia": [], "Events": []}
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_memory(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.memory, f, indent=4)

    # --------------------------------------------------------
    # SESSION RECORDING
    # --------------------------------------------------------
    def record_session(self, session: str, volatility: float, event: Optional[str], outcome_bias: float):
        """
        Record volatility and directional bias for a given session.
        :param session: e.g., 'London', 'New York', 'Asia'
        :param volatility: volatility index at snapshot
        :param event: macro event (CPI, NFP, FOMC, etc.)
        :param outcome_bias: simulated directional bias (+1 bull, -1 bear, 0 neutral)
        """
        if session not in self.memory:
            self.memory[session] = []
        entry = {
            "timestamp": datetime.datetime.now(timezone.utc).isoformat(),
            "volatility": round(volatility, 2),
            "event": event,
            "bias": outcome_bias
        }
        self.memory[session].append(entry)

        if event:
            self.memory["Events"].append({
                "timestamp": entry["timestamp"],
                "event": event,
                "session": session,
                "volatility": volatility,
                "bias": outcome_bias
            })

        # Keep memory window manageable (last 50 sessions)
        self.memory[session] = self.memory[session][-50:]
        self.memory["Events"] = self.memory["Events"][-100:]

        self._save_memory()
        return entry

    # --------------------------------------------------------
    # ANALYTICS
    # --------------------------------------------------------
    def get_average_volatility(self, session: str) -> float:
        data = self.memory.get(session, [])
        if not data:
            return 0.0
        return round(mean(d["volatility"] for d in data), 2)

    def get_average_bias(self, session: str) -> float:
        data = self.memory.get(session, [])
        if not data:
            return 0.0
        return round(mean(d["bias"] for d in data), 2)

    def get_event_impact(self, event_name: str) -> Dict:
        impacts = [e for e in self.memory.get("Events", []) if e["event"] == event_name]
        if not impacts:
            return {"count": 0, "avg_volatility": 0.0, "avg_bias": 0.0}
        return {
            "count": len(impacts),
            "avg_volatility": round(mean(e["volatility"] for e in impacts), 2),
            "avg_bias": round(mean(e["bias"] for e in impacts), 2)
        }

    # --------------------------------------------------------
    # CONTEXT SYNTHESIS
    # --------------------------------------------------------
    def synthesize_context(self, current_session: str) -> Dict:
        """
        Combines memory of volatility, bias, and event impact to create
        a contextual weighting profile for Commander decision logic.
        """
        avg_vol = self.get_average_volatility(current_session)
        avg_bias = self.get_average_bias(current_session)

        # Simplified market tone classification
        if avg_bias > 0.3:
            tone = "Bullish"
        elif avg_bias < -0.3:
            tone = "Bearish"
        else:
            tone = "Neutral"

        return {
            "session": current_session,
            "average_volatility": avg_vol,
            "average_bias": avg_bias,
            "market_tone": tone,
            "timestamp": datetime.datetime.now(timezone.utc).isoformat()
        }

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------
    def summary(self):
        print("\n=== V13 Context Memory Summary ===")
        for s in ["Asia", "London", "New York"]:
            avg_vol = self.get_average_volatility(s)
            avg_bias = self.get_average_bias(s)
            print(f"{s:<10} | Volatility: {avg_vol:>5} | Bias: {avg_bias:+.2f}")
        print("==================================\n")
        return {s: self.get_average_volatility(s) for s in ["Asia", "London", "New York"]}


# ============================================================
# SECTION 2 — DEMO EXECUTION
# ============================================================

if __name__ == "__main__":
    cm = ContextMemory()

    print("\n=== V13 Context Memory Demo ===")

    # Simulated recording of several sessions
    sessions = ["Asia", "London", "New York"]
    events = [None, "CPI", "FOMC", None]
    import random

    for _ in range(10):
        s = random.choice(sessions)
        e = random.choice(events)
        v = round(random.uniform(30, 85), 2)
        b = round(random.uniform(-1.0, 1.0), 2)
        cm.record_session(s, v, e, b)

    cm.summary()

    # Show synthesized context for London
    print(cm.synthesize_context("London"))
