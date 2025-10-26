from soldiers.soldier_base import SoldierBase
import statistics
import time

class Ball8(SoldierBase):
    """
    Ball-8  →  CORE
    -----------------
    Role:
        Trend carrier / structure maintainer.
        Holds medium-term directional exposure until the trend structure breaks.
        Acts as the backbone of sustained positioning.

    Input expectations (info_pack):
        {
            "symbol": "BTC/USD",
            "recent_prices": [float, float, ...],
            "ma_fast": 10,
            "ma_slow": 30,
            "trend_bias_threshold": 0.0015,   # 0.15% minimum bias
        }
    """

    def decide(self):
        info = getattr(self, "info", {})
        prices = info.get("recent_prices", [])
        if len(prices) < 5:
            self.last_decision = "hold"
            return self.last_decision

        ma_fast_len = info.get("ma_fast", 10)
        ma_slow_len = info.get("ma_slow", 30)

        # moving averages
        fast_segment = prices[-ma_fast_len:] if len(prices) >= ma_fast_len else prices
        slow_segment = prices[-ma_slow_len:] if len(prices) >= ma_slow_len else prices
        ma_fast_val = statistics.mean(fast_segment)
        ma_slow_val = statistics.mean(slow_segment)

        bias = (ma_fast_val - ma_slow_val) / ma_slow_val
        threshold = info.get("trend_bias_threshold", 0.0015)

        if bias > threshold:
            self.state = "trend_up"
            self.last_decision = "enter"
        elif bias < -threshold:
            self.state = "trend_down"
            self.last_decision = "exit"
        else:
            self.state = "neutral"
            self.last_decision = "hold"

        self.last_update = time.time()
        return self.last_decision
