from soldiers.soldier_base import SoldierBase
import time

class Ball10(SoldierBase):
    """
    Ball-10  →  JOKER
    ------------------
    Role:
        Recovery sniper / crisis specialist.
        Activates only after a drawdown event (triggered by Guardian).
        Executes a single, high-confidence re-entry once stability returns.

    Input expectations (info_pack):
        {
            "symbol": "BTC/USD",
            "crash_flag": <bool>,              # from Guardian (True if crash triggered)
            "recovery_signal": <bool>,         # indicates re-entry opportunity
            "volatility": <float>,             # optional — confirm stability
            "volatility_max": 0.002,           # max allowed volatility
            "cooldown": 300                    # seconds between activations
        }
    """

    def __init__(self, name: str, capital: float):
        super().__init__(name, capital)
        self.last_fire_time = 0

    def decide(self):
        info = getattr(self, "info", {})
        crash_flag = info.get("crash_flag", False)
        recovery_signal = info.get("recovery_signal", False)
        volatility = info.get("volatility", 0.0)
        vol_max = info.get("volatility_max", 0.002)
        cooldown = info.get("cooldown", 300)  # 5 min cooldown

        now = time.time()
        time_since_last = now - self.last_fire_time

        # only engage post-crash + stability + cooldown met
        if crash_flag and recovery_signal and volatility < vol_max and time_since_last > cooldown:
            self.state = "recovery_attack"
            self.last_decision = "enter"
            self.last_fire_time = now
        else:
            if crash_flag and not recovery_signal:
                self.state = "waiting_recovery"
            elif not crash_flag:
                self.state = "standby"
            else:
                self.state = "cooldown"
            self.last_decision = "hold"

        self.last_update = now
        return self.last_decision
