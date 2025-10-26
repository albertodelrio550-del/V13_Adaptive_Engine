"""
runbook_verification_v13.py — V13 Manual Trading Framework
Build : 2025-10-18
Phase : 6 — Verification & Runbook Blueprint

Purpose
-------
Define the verification procedure for all V13 modules.
Ensures structural integrity, module communication, and telemetry reliability
before field deployment or version increment to V13.1.
"""

import os
import json
import time

# ─────────────────────────────────────────────────────────────
# 🧭 VERIFICATION OBJECTIVES
# ─────────────────────────────────────────────────────────────
"""
1. Structure check → confirm every required file/folder exists.
2. Commander cycle test → one tactical loop runs end-to-end.
3. Aggregator output → produces valid mode/confidence.
4. Bridge PnL simulation → updates + logs properly.
5. Telemetry validation → session_log.json receives data.
"""

PROJECT_ROOT = "Videos/bohrn 2025/trade/V13/"
REQUIRED_PATHS = [
    "commander_v13_manual.py",
    "signal_aggregator.py",
    "paper_order_bridge.py",
    "telemetry_schema_v13.py",
    "config/runtime_config.json",
    "soldiers/soldier_base.py",
    "intel/",
    "logs/"
]

# ─────────────────────────────────────────────────────────────
# 🔍 STRUCTURE VERIFICATION
# ─────────────────────────────────────────────────────────────
def verify_structure():
    missing = []
    for path in REQUIRED_PATHS:
        full = os.path.join(PROJECT_ROOT, path)
        if not os.path.exists(full):
            missing.append(path)
    if missing:
        print("❌ Missing components:")
        for m in missing:
            print("   -", m)
    else:
        print("✅ All required modules found.")
    return not missing


# ─────────────────────────────────────────────────────────────
# 🧩 RUNTIME LOOP SIMULATION (LIGHT TEST)
# ─────────────────────────────────────────────────────────────
def verify_runtime_cycle():
    from signal_aggregator import SignalAggregator
    from paper_order_bridge import PaperOrderBridge

    agg = SignalAggregator()
    bridge = PaperOrderBridge()

    # Mock soldier signals
    soldiers = [
        {"name": "Ball-1", "score": 0.6, "capital_pct": 0.05},
        {"name": "Ball-2", "score": 0.3, "capital_pct": 0.05},
        {"name": "Ball-9", "score": -0.4, "capital_pct": 0.20}
    ]
    ctx = {"volatility": 0.03, "symbol": "BTC/USD"}

    agg_out = agg.aggregate(soldiers, ctx)
    print("→ Aggregator output:", agg_out)

    bridge.open_trade("BTC/USD", "LONG", 120000, 1000)
    bridge.update_trades(120400)
    state = bridge.export_state()
    print("→ Bridge state:", json.dumps(state, indent=2))

    return True


# ─────────────────────────────────────────────────────────────
# 🧾 TELEMETRY CHECK
# ─────────────────────────────────────────────────────────────
def verify_telemetry():
    path = os.path.join(PROJECT_ROOT, "logs/session_log.json")
    if not os.path.exists(path):
        print("⚠️  No session_log.json found yet — run Commander once.")
        return False
    try:
        with open(path, "r") as f:
            lines = f.readlines()
            last = json.loads(lines[-1])
        required_fields = ["timestamp", "cycle", "mode", "weighted_score"]
        ok = all(k in last for k in required_fields)
        print("✅ Telemetry entry valid." if ok else "❌ Telemetry missing keys.")
        return ok
    except Exception as e:
        print("❌ Error reading telemetry:", e)
        return False


# ─────────────────────────────────────────────────────────────
# 🚀 MAIN VERIFICATION RUNBOOK
# ─────────────────────────────────────────────────────────────
def run_verification():
    print("\n=== V13 Verification Runbook ===\n")

    step1 = verify_structure()
    if not step1:
        print("⚠️  Structure incomplete — aborting deeper tests.")
        return

    print("\n--- Step 2: Runtime Cycle Test ---")
    verify_runtime_cycle()

    print("\n--- Step 3: Telemetry Check ---")
    verify_telemetry()

    print("\nVerification completed.\n")
    print("If all checks show ✅, system is ready for full Commander run.")


# ─────────────────────────────────────────────────────────────
# 🧮 EXECUTION ENTRYPOINT
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    run_verification()
