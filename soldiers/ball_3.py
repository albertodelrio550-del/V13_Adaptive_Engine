from soldiers.soldier_base import SoldierBase
import statistics
import time

class Ball3(SoldierBase):
    """
    Ball-3  →  ANCHOR
    -----------------
    Role:
        Track mean / equilibrium value and measure distance from it.
        Helps define when price is in balance (hold) or out of balance (enter/exit).

    Input expectations (info_pack):
        {
            "symbol": "BTC/USD",
            "recent_prices": [float, float, ...],
            "anchor_window": 20,
            "deviation_threshold": 0.0015,   # 0.15%
        }
    """

    def decide(self):
        info = getattr(self, "info", {})
        prices = info.get("recent_prices", [])
        if len(prices) < 3:
            self.last_decision = "hold"
            return self.last_decision

        window = info.get("anchor_window", 20)
        if len(prices) < window:
            window = len(prices)

        segment = prices[-window:]
        mean_price = statistics.mean(segment)
        current_price = segment[-1]
        deviation = (current_price - mean_price) / mean_price
        threshold = info.get("deviation_threshold", 0.0015)

        # decide balance state
        if deviation > threshold:
            self.state = "above_balance"
            self.last_decision = "enter"   # market breaking above balance
        elif deviation < -threshold:
            self.state = "below_balance"
            self.last_decision = "exit"    # market below balance
        else:
            self.state = "balanced"
            self.last_decision = "hold"

        self.last_update = time.time()
        return self.last_decision
