"""
runtime_config.py — V13 Manual Trading Framework
Build : 2025-10-18
Phase : 5 — Runtime Config System

Purpose
-------
Provide Commander and subordinate modules with live-read configuration
for session mode, thresholds, and safety caps.
"""

import json
import os
from typing import Dict, Any

RUNTIME_CONFIG_PATH = os.path.join("config", "runtime_config.json")

# ─────────────────────────────────────────────────────────────
# ⚙️ DEFAULT CONFIGURATION
# ─────────────────────────────────────────────────────────────
DEFAULT_CONFIG: Dict[str, Any] = {
    "mode": "Balanced",               # Safe | Balanced | Aggressive
    "thresholds": {
        "aggregator_threshold": 0.15,
        "aggregator_hysteresis": 0.05
    },
    "risk": {
        "max_drawdown_usd": -150.0,
        "take_profit_usd": 10.0,
        "stop_loss_usd": 5.0
    },
    "session": {
        "duration_sec": 21600,       # 6 hours night session
        "goal_profit_usd": 20.0,
        "capital_usd": 10000.0
    },
    "telemetry": {
        "log_rotation": 1000,
        "enable_console_log": True
    }
}


# ─────────────────────────────────────────────────────────────
# 📖 CONFIG LOADER
# ─────────────────────────────────────────────────────────────
def load_runtime_config(path: str = RUNTIME_CONFIG_PATH) -> Dict[str, Any]:
    """
    Load runtime_config.json; if missing, create with defaults.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        print(f"[RuntimeConfig] Created default config at {path}")
        return DEFAULT_CONFIG

    try:
        with open(path, "r") as f:
            cfg = json.load(f)
            return _merge_defaults(cfg)
    except Exception as e:
        print(f"[RuntimeConfig] Error loading file ({e}); reverting to defaults.")
        return DEFAULT_CONFIG


# ─────────────────────────────────────────────────────────────
# 🔄 MERGE HELPER
# ─────────────────────────────────────────────────────────────
def _merge_defaults(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensures missing keys are filled with DEFAULT_CONFIG values.
    """
    def recursive_merge(base, incoming):
        for k, v in base.items():
            if k not in incoming:
                incoming[k] = v
            elif isinstance(v, dict):
                incoming[k] = recursive_merge(v, incoming.get(k, {}))
        return incoming
    return recursive_merge(DEFAULT_CONFIG, cfg)


# ─────────────────────────────────────────────────────────────
# 🧩 EXAMPLE USAGE
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    cfg = load_runtime_config()
    print("Runtime Config Loaded:")
    for k, v in cfg.items():
        print(f"  {k}: {v}")
