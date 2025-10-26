from soldiers.soldier_base import SoldierBase
import statistics
import time

class Ball4(SoldierBase):
    """
    Ball-4  →  REVERB
    ------------------
    Role:
        Counter-trend / mean-reversion specialist.
        Detects overextended price deviations and signals fade entries
        when price is statistically far from the mean.

    Input expectations (info_pack):
        {
            "symbol": "BTC/USD",
            "recent_prices": [float, float, ...],
            "window": 20,
            "reversion_sigma": 2.0,     # standard deviation multiplier
        }
    """

    def decide(self):
        info = getattr(self, "info", {})
        prices = info.get("recent_prices", [])
        if len(prices) < 5:
            self.last_decision = "hold"
            return self.last_decision

        window = info.get("window", 20)
        if len(prices) < window:
            window = len(prices)

        segment = prices[-window:]
        mean_price = statistics.mean(segment)
        stdev = statistics.pstdev(segment)
        current = segment[-1]
        upper = mean_price + stdev * info.get("reversion_sigma", 2.0)
        lower = mean_price - stdev * info.get("reversion_sigma", 2.0)

        if current > upper:
            # Price stretched high → short bias
            self.state = "overbought"
            self.last_decision = "exit"
        elif current < lower:
            # Price stretched low → long bias
            self.state = "oversold"
            self.last_decision = "enter"
        else:
            self.state = "neutral"
            self.last_decision = "hold"

        self.last_update = time.time()
        return self.last_decision
