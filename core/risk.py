from __future__ import annotations
from dataclasses import dataclass, field
from typing import List

@dataclass
class LadderRule:
    trigger_profit: float
    lock_fraction: float  # fraction of total (realized+floating)

@dataclass
class Ladder:
    base_floor_usd: float = 0.0
    steps: List[LadderRule] = field(default_factory=list)

@dataclass
class RiskLimits:
    per_trade_max_dd_usd: float
    session_max_dd_usd: float
    crashguard_vol_threshold: float

@dataclass
class RiskState:
    session_realized: float = 0.0
    session_floating: float = 0.0
    session_peak: float = 0.0
    session_floor: float = 0.0

class RiskManager:
    def __init__(self, limits: RiskLimits, ladder: Ladder):
        self.limits = limits
        self.ladder = ladder
        self.state = RiskState()

    def update_pnl(self, realized: float, floating: float):
        self.state.session_realized = realized
        self.state.session_floating = floating
        total = realized + floating
        if total > self.state.session_peak:
            self.state.session_peak = total

        # Compute floor
        floor = self.ladder.base_floor_usd
        for step in sorted(self.ladder.steps, key=lambda s: s.trigger_profit):
            if total >= step.trigger_profit:
                floor = max(floor, total * step.lock_fraction)
        self.state.session_floor = floor

    def dd_breach(self) -> bool:
        """Return True if drawdown from peak exceeds session_max_dd_usd."""
        total = self.state.session_realized + self.state.session_floating
        return (self.state.session_peak - total) >= abs(self.limits.session_max_dd_usd)

    def crashguard(self, pct_change_1m: float) -> bool:
        return abs(pct_change_1m) >= self.limits.crashguard_vol_threshold
