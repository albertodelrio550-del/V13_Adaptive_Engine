"""
telemetry_schema_v13.py — V13 Manual Trading Framework
Build: 2025-10-18
Phase: 2 — Telemetry Schema Standardization

Purpose
-------
Defines the JSON structure used across Commander, Aggregator,
and Bridge layers for consistent runtime logging.

Each tactical cycle produces one log entry appended to:
    /logs/session_log.json
"""

# ─────────────────────────────────────────────────────────────
# 🧾 TELEMETRY SCHEMA
# ─────────────────────────────────────────────────────────────
TELEMETRY_SCHEMA = {
    "timestamp": "ISO-8601 UTC",
    "cycle": "int — Commander cycle counter",
    "mode": "str — OFFENSE | HOLD | DEFENSE",
    "weighted_score": "float (-1.0..+1.0)",
    "confidence": "float (0.0..1.0)",
    "participation": "float (0.0..1.0)",

    "soldier_breakdown": {
        "Ball-1": {"score": 0.72, "weight": 0.05, "ok": True},
        "Ball-2": {"score": 0.31, "weight": 0.05, "ok": True},
        "...": {}
    },

    "superupdate": "bool — tightening event triggered",
    "crashguard": "bool — volatility defense active",

    "virtual_pnl": "float — total net profit/loss",
    "positions": [
        {
            "symbol": "BTC/USD",
            "side": "LONG | SHORT",
            "entry_price": "float",
            "current_price": "float",
            "pnl": "float"
        }
    ],

    "runtime_mode": "Safe | Balanced | Aggressive",
    "uptime_sec": "float — commander uptime seconds",
    "errors": ["list of any runtime warnings"]
}


# ─────────────────────────────────────────────────────────────
# ⚙️ LOG WRITER HELPER
# ─────────────────────────────────────────────────────────────
def write_log(entry: dict, path: str = "logs/session_log.json"):
    """
    Append a telemetry entry to session_log.json
    Creates /logs/ if it does not exist.
    """
    import os, json, time
    os.makedirs(os.path.dirname(path), exist_ok=True)
    entry["timestamp"] = entry.get("timestamp") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ─────────────────────────────────────────────────────────────
# 🧩 EXAMPLE USAGE
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    sample_entry = {
        "cycle": 1,
        "mode": "OFFENSE",
        "weighted_score": 0.54,
        "confidence": 0.81,
        "participation": 0.9,
        "superupdate": True,
        "crashguard": False,
        "virtual_pnl": 125.4,
        "runtime_mode": "Balanced",
        "errors": []
    }
    write_log(sample_entry)
    print("Sample telemetry entry appended → logs/session_log.json")

# ============================================================
