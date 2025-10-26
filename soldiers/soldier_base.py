"""
soldier_base.py — V13 Manual Trading Framework
Build: 2025-10-18
Phase: 4 — Soldier Diagnostics & Signal Health

Purpose
-------
Provide a common base class for all Ball soldiers (Ball1–Ball10).
Adds diagnostics, heartbeat tracking, and signal-validity reporting
for Commander telemetry integration.
"""

import time
import random
from typing import Dict, Optional


# ─────────────────────────────────────────────────────────────
# ⚙️ BASE CLASS
# ─────────────────────────────────────────────────────────────
class SoldierBase:
    """Base soldier class providing diagnostics and signal output."""

    def __init__(self, name: str, capital_pct: float):
        self.name = name
        self.capital_pct = capital_pct
        self.last_signal: Optional[float] = None
        self.last_heartbeat: float = time.time()
        self.error_count = 0
        self.uptime_start = time.time()
        self.active = True

    # ─────────────────────────────────────────
    # SIGNAL GENERATION
    # ─────────────────────────────────────────
    def generate_signal(self, market_ctx: Dict) -> float:
        """
        Placeholder logic for derived classes.
        Should return a float in [-1, +1].
        Positive = OFFENSE bias, Negative = DEFENSE.
        """
        try:
            # Mock logic — replace with actual strategy per soldier
            volatility = market_ctx.get("volatility", 0.02)
            bias = random.uniform(-1, 1) * (1 + volatility)
            self.last_signal = max(-1.0, min(1.0, bias))
            self.last_heartbeat = time.time()
            return self.last_signal
        except Exception as e:
            self.error_count += 1
            print(f"[{self.name}] Error generating signal: {e}")
            return 0.0

    # ─────────────────────────────────────────
    # DIAGNOSTICS
    # ─────────────────────────────────────────
    def diagnostics(self) -> Dict:
        """Return soldier status summary."""
        uptime_sec = time.time() - self.uptime_start
        heartbeat_age = time.time() - self.last_heartbeat
        healthy = heartbeat_age < 10.0 and self.error_count < 3

        return {
            "name": self.name,
            "capital_pct": self.capital_pct,
            "signal": self.last_signal,
            "last_heartbeat_sec": round(heartbeat_age, 2),
            "uptime_sec": round(uptime_sec, 2),
            "errors": self.error_count,
            "healthy": healthy,
        }

    # ─────────────────────────────────────────
    # RESET / CONTROL
    # ─────────────────────────────────────────
    def reset(self):
        """Reset runtime stats without losing configuration."""
        self.last_signal = None
        self.error_count = 0
        self.last_heartbeat = time.time()
        print(f"[{self.name}] diagnostics reset.")


# ─────────────────────────────────────────────────────────────
# 🧩 DEMONSTRATION (RUN STANDALONE)
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    s = SoldierBase("Ball-1", 0.05)
    for i in range(3):
        ctx = {"volatility": 0.03}
        sig = s.generate_signal(ctx)
        print(f"Cycle {i+1} → Signal: {sig:.3f}")
        time.sleep(1)

    print("\nDiagnostics snapshot:")
    print(s.diagnostics())
