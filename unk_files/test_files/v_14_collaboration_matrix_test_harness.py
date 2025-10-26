# =============================================================
#  V14_CollaborationMatrix_TestHarness.py — V14 Adaptive Engine
#  Version: V14_Pre-Alpha (2025-10-19)
#  Purpose: Simulation harness for human ↔ AI collaboration tests
#  Mode: Paper-only Simulation — Multi-Scenario Fusion Testing
# =============================================================

import time
import random
import json
from V14_CollaborationMatrix import V14CollaborationMatrix

# -------------------------------------------------------------
#  SIMULATED COMPONENTS
# -------------------------------------------------------------
class CommanderFlexSim:
    def generate_signal(self):
        return {
            "signal_strength": round(random.uniform(-1.0, 1.0), 3),
            "confidence": round(random.uniform(0.5, 1.0), 2)
        }

class AISchemaSim:
    def generate_signal(self):
        # Simulate AI signal with smaller random bias
        return {
            "signal_strength": round(random.uniform(-1.0, 1.0), 3),
            "confidence": round(random.uniform(0.6, 0.95), 2)
        }

class RiskSentinelSim:
    def get_status(self):
        roll = random.random()
        if roll < 0.85:
            return "SAFE"
        elif roll < 0.95:
            return "LIMITED"
        else:
            return "LOCK"

# -------------------------------------------------------------
#  TEST HARNESS
# -------------------------------------------------------------
def run_collaboration_test(iterations: int = 20, delay: float = 0.4):
    print("\n🤝 V14 Collaboration Matrix Test Harness — Simulation Start")
    print("-------------------------------------------------------------")

    fusion_engine = V14CollaborationMatrix()
    commander = CommanderFlexSim()
    ai_schema = AISchemaSim()
    risk_sentinel = RiskSentinelSim()

    results = []

    for i in range(iterations):
        h_input = commander.generate_signal()
        a_input = ai_schema.generate_signal()
        risk_status = risk_sentinel.get_status()

        fused_output = fusion_engine.fuse(h_input, a_input, risk_status)
        results.append(fused_output)

        print(f"\nCycle {i+1}/{iterations} → Status: {risk_status}")
        print(json.dumps(fused_output, indent=2))
        time.sleep(delay)

    # Summary statistics
    valid = sum(1 for r in results if not r["divergent"])
    divergent = len(results) - valid
    avg_fused = sum(r["fused_signal"] for r in results) / len(results)

    print("\n-------------------------------------------------------------")
    print(f"✅ Non-divergent fusions: {valid}")
    print(f"⚠️ Divergent fusions: {divergent}")
    print(f"📊 Avg fused signal: {avg_fused:.4f}")
    print("📘 Collaboration Matrix simulation complete.")

# -------------------------------------------------------------
#  MAIN ENTRY POINT
# -------------------------------------------------------------
if __name__ == "__main__":
    run_collaboration_test(iterations=15, delay=0.5)