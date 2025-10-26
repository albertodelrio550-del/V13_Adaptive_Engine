from soldiers.soldier_base import SoldierBase
import statistics
import time

class Ball5(SoldierBase):
    """
    Ball-5  →  SHIELD
    -----------------
    Role:
        Risk stabilizer and noise filter.
        Evaluates current market stability and signals 'defend' (exit/hold)
        when volatility or spread exceeds tolerance.

    Input expectations (info_pack):
        {
            "symbol": "BTC/USD",
            "recent_prices": [float, float, ...],
            "bid": <float>,
            "ask": <float>,
            "spread_limit": 5.0,          # max allowed spread in USD
            "volatility_window": 10,
            "volatility_limit": 0.0025,   # 0.25% stddev / mean
        }
    """

    def decide(self):
        info = getattr(self, "info", {})
        prices = info.get("recent_prices", [])
        bid = info.get("bid")
        ask = info.get("ask")

        if not prices or not bid or not ask:
            self.last_decision = "hold"
            return self.last_decision

        # 1. Spread check
        spread = abs(ask - bid)
        if spread > info.get("spread_limit", 5.0):
            self.state = "wide_spread"
            self.last_decision = "exit"
            return self.last_decision

        # 2. Volatility check
        window = info.get("volatility_window", 10)
        if len(prices) < window:
            window = len(prices)
        segment = prices[-window:]
        mean_price = statistics.mean(segment)
        stdev = statistics.pstdev(segment)
        vol_ratio = stdev / mean_price if mean_price else 0

        if vol_ratio > info.get("volatility_limit", 0.0025):
            self.state = "high_volatility"
            self.last_decision = "exit"
        else:
            self.state = "calm"
            self.last_decision = "hold"

        self.last_update = time.time()
        return self.last_decision
