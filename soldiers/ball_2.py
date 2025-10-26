from soldiers.soldier_base import SoldierBase
import statistics
import time

class Ball2(SoldierBase):
    """
    Ball-2  →  PULSE
    -----------------
    Role:
        Measure short-term momentum and directional bias.
        Confirms when the market’s pulse (velocity) sustains beyond threshold.

    Input expectations (info_pack):
        {
            "symbol": "BTC/USD",
            "recent_prices": [float, float, ...],
            "momentum_window": 5,
            "momentum_threshold": 0.001,   # 0.1%
        }
    """

    def decide(self):
        info = getattr(self, "info", {})
        prices = info.get("recent_prices", [])
        if len(prices) < 3:
            self.last_decision = "hold"
            return self.last_decision

        window = info.get("momentum_window", 5)
        if len(prices) < window:
            window = len(prices)

        # Simple linear momentum = last - first over window
        momentum = (prices[-1] - prices[-window]) / prices[-window]
        threshold = info.get("momentum_threshold", 0.001)

        if momentum > threshold:
            self.state = "bullish"
            self.last_decision = "enter"
        elif momentum < -threshold:
            self.state = "bearish"
            self.last_decision = "exit"
        else:
            self.state = "neutral"
            self.last_decision = "hold"

        self.last_update = time.time()
        return self.last_decision
