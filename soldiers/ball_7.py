from soldiers.soldier_base import SoldierBase
import time

class Ball7(SoldierBase):
    """
    Ball-7  →  TRAIL
    -----------------
    Role:
        Profit follower / position manager.
        Monitors unrealized PnL or price distance and signals when to tighten
        stops or partially exit to secure gains.

    Input expectations (info_pack):
        {
            "symbol": "BTC/USD",
            "entry_price": <float>,
            "current_price": <float>,
            "trail_step": 0.002,        # 0.2% move between adjustments
            "lock_trigger": 0.005,      # 0.5% profit before locking
            "direction": "long" or "short"
        }
    """

    def decide(self):
        info = getattr(self, "info", {})
        entry = info.get("entry_price")
        price = info.get("current_price")
        direction = info.get("direction", "long")

        if not entry or not price:
            self.last_decision = "hold"
            return self.last_decision

        change = (price - entry) / entry if direction == "long" else (entry - price) / entry
        lock_trigger = info.get("lock_trigger", 0.005)
        trail_step = info.get("trail_step", 0.002)

        # profit reached → tighten stop
        if change >= lock_trigger:
            self.state = "lock_gain"
            self.last_decision = "adjust"
        elif change >= trail_step:
            self.state = "trail_follow"
            self.last_decision = "hold"
        else:
            self.state = "neutral"
            self.last_decision = "hold"

        self.last_update = time.time()
        return self.last_decision
