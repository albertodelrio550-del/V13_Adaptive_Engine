from soldiers.soldier_base import SoldierBase
import statistics
import time

class Ball1(SoldierBase):
    """
    Ball-1  →  SCOUT
    -----------------
    Role:
        Detect early volatility or directional breakout.
        Provides 'enter' signal when short-term price acceleration exceeds baseline.

    Input expectations (info_pack):
        {
            "symbol": "BTC/USD",
            "price": <float>,
            "recent_prices": [float, float, ...],
            "volatility_window": 14,
            "threshold": 0.002   # 0.2%
        }
    """

    def decide(self):
        info = getattr(self, "info", {})
        prices = info.get("recent_prices", [])
        if len(prices) < 5:
            self.last_decision = "hold"
            return self.last_decision

        # compute short-term volatility
        window = info.get("volatility_window", 14)
        recent = prices[-window:] if len(prices) >= window else prices
        stdev = statistics.pstdev(recent)
        mean = statistics.mean(recent)
        if mean == 0:
            self.last_decision = "hold"
            return self.last_decision

        vol_ratio = stdev / mean
        threshold = info.get("threshold", 0.002)

        # simple logic: if volatility > threshold → scout senses breakout
        if vol_ratio > threshold:
            self.state = "alert"
            self.last_decision = "enter"
        else:
            self.state = "standby"
            self.last_decision = "hold"

        # timestamp and report
        self.last_update = time.time()
        return self.last_decision
