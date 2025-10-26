from soldiers.soldier_base import SoldierBase
import statistics
import time

class Ball6(SoldierBase):
    """
    Ball-6  →  STRIKE
    -----------------
    Role:
        Aggressive executioner.
        Fires only when breakout + momentum alignment occurs.
        Designed for controlled offensive trades with measured aggression.

    Input expectations (info_pack):
        {
            "symbol": "BTC/USD",
            "recent_prices": [float, float, ...],
            "momentum": <float>,              # external signal (from Pulse or Commander)
            "volatility": <float>,            # external signal (from Scout)
            "alignment_threshold": 0.0015,    # 0.15%
            "volatility_min": 0.002,          # 0.2%
        }
    """

    def decide(self):
        info = getattr(self, "info", {})
        prices = info.get("recent_prices", [])
        if len(prices) < 3:
            self.last_decision = "hold"
            return self.last_decision

        momentum = info.get("momentum", 0)
        volatility = info.get("volatility", 0)
        align_th = info.get("alignment_threshold", 0.0015)
        vol_min = info.get("volatility_min", 0.002)

        # Confirm both conditions: direction + sufficient volatility
        if abs(momentum) >= align_th and volatility >= vol_min:
            if momentum > 0:
                self.state = "attack_long"
                self.last_decision = "enter"
            else:
                self.state = "attack_short"
                self.last_decision = "exit"
        else:
            self.state = "idle"
            self.last_decision = "hold"

        self.last_update = time.time()
        return self.last_decision
