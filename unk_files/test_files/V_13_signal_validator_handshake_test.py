# =============================================================
#  V13_SignalValidator_HandshakeTest.py — V13 Adaptive Engine
#  Version: V13_Stable_Release (2025-10-19)
#  Purpose: Simulation test for CommanderFlex ↔ TelemetryFusion ↔ SignalValidator handshake
#  Mode: Paper-only, simulation
# =============================================================

import time
import random
import json
from V13_SignalValidator import V13SignalValidator

# -------------------------------------------------------------
#  SIMULATED COMPONENTS
# -------------------------------------------------------------
class CommanderFlexSim:
    def generate_packet(self):
        return {
            "timestamp": time.time(),
            "price_delta": round(random.uniform(-0.005, 0.005), 5),
            "command_id": random.randint(1000, 9999)
        }

class TelemetryFusionSim:
    def generate_snapshot(self):
        base_delta = round(random.uniform(-0.005, 0.005), 5)
        return {
            "timestamp": time.time(),
            "price_delta": base_delta + random.uniform(-0.0001, 0.0001),
            "volatility": abs(random.uniform(0.01, 0.06))  # 1%–6%
        }

class RiskSentinelSim:
    def get_status(self):
        # 90% SAFE, 8% LIMITED, 2% LOCK
        roll = random.random()
        if roll < 0.9:
            return "SAFE"
        elif roll < 0.98:
            return "LIMITED"
        else:
            return "LOCK"

class BridgeGuardianSim:
    def get_sync_flag(self):
        # 97% chance of true sync
        return random.random() < 0.97

# -------------------------------------------------------------
#  HANDSHAKE TEST HARNESS
# -------------------------------------------------------------
def run_handshake_test(iterations: int = 25, delay: float = 0.3):
    print("\n🚦 V13 Signal Validator Handshake Test — Simulation Start")
    print("-------------------------------------------------------------")

    validator = V13SignalValidator()
    commander = CommanderFlexSim()
    fusion = TelemetryFusionSim()
    risk = RiskSentinelSim()
    bridge = BridgeGuardianSim()

    valid_count = 0
    invalid_count = 0

    for i in range(iterations):
        cmd_packet = commander.generate_packet()
        market_snapshot = fusion.generate_snapshot()
        risk_status = risk.get_status()
        sync_flag = bridge.get_sync_flag()

        result = validator.validate(cmd_packet, market_snapshot, risk_status, sync_flag)

        status = result.get("status", "?")
        if status == "VALID":
            valid_count += 1
        else:
            invalid_count += 1

        print(f"\nIteration {i+1}/{iterations} → Status: {status}")
        print(json.dumps(result, indent=2))

        time.sleep(delay)

    print("\n-------------------------------------------------------------")
    print(f"✅ Valid signals:   {valid_count}")
    print(f"⚠️  Invalid signals: {invalid_count}")
    print("📘 Handshake simulation complete. Review log above.")

# -------------------------------------------------------------
#  MAIN ENTRY POINT
# -------------------------------------------------------------
if __name__ == "__main__":
    run_handshake_test(iterations=15, delay=0.4)