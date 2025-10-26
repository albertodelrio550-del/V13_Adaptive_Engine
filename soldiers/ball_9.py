from soldiers.soldier_base import SoldierBase
import time

class Ball9(SoldierBase):
    """
    Ball-9  →  GUARDIAN
    --------------------
    Role:
        Oversees overall equity health and session drawdown.
        Acts as the capital sentinel — triggers defensive or shutdown
        signals when thresholds are breached.

    Input expectations (info_pack):
        {
            "symbol": "BTC/USD",
            "equity": <float>,                 # current equity
            "peak_equity": <float>,            # highest recorded equity
            "max_drawdown_limit": -200.0,      # stop threshold in USD
            "recovery_threshold": -50.0,       # alert when nearing danger
        }
    """

    def decide(self):
        info = getattr(self, "info", {})
        equity = info.get("equity")
        peak = info.get("peak_equity", equity)
        max_dd = info.get("max_drawdown_limit", -200.0)
        recovery = info.get("recovery_threshold", -50.0)

        if equity is None:
            self.last_decision = "hold"
            return self.last_decision

        drawdown = equity - peak

        if drawdown <= max_dd:
            self.state = "crashguard"
            self.last_decision = "exit"   # emergency full stop
        elif drawdown <= recovery:
            self.state = "alert"
            self.last_decision = "defend" # early warning
        else:
            self.state = "safe"
            self.last_decision = "hold"

        self.last_update = time.time()
        return self.last_decision
