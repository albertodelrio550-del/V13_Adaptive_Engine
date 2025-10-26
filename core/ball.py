from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Literal, Dict

Role = Literal["private", "specialist", "major", "sniper"]
Side = Literal["long", "short"]
BallState = Literal["IDLE", "OPEN", "LOCKED", "COOLDOWN"]

@dataclass
class EntrySpec:
    use_support_resistance: bool = True
    use_pullback: bool = True
    allow_breakout: bool = False
    signal_confirm_bars: int = 1

@dataclass
class ExitSpec:
    tp_usd: Optional[float] = None
    sl_usd: Optional[float] = None
    time_limit_s: Optional[int] = None

@dataclass
class TrailSpec:
    enabled: bool = True
    step_usd: float = 1.0
    arm_after_profit_usd: float = 2.0
    hard_floor_usd: Optional[float] = None

@dataclass
class BallSpec:
    id: int
    role: Role
    side: Side = "long"
    capital_frac: float = 0.02
    entry: EntrySpec = field(default_factory=EntrySpec)
    exit: ExitSpec = field(default_factory=ExitSpec)
    trail: TrailSpec = field(default_factory=TrailSpec)
    cooldown_s: int = 30
    rearm_on_recovery: bool = True
    notes: str = ""

@dataclass
class BallRuntime:
    spec: BallSpec
    state: BallState = "IDLE"
    entry_price: Optional[float] = None
    qty: float = 0.0
    notional_usd: float = 0.0
    realized_pnl: float = 0.0
    floating_pnl: float = 0.0
    trail_floor: Optional[float] = None
    last_action_ts: Optional[float] = None

    def reset(self):
        self.state = "IDLE"
        self.entry_price = None
        self.qty = 0.0
        self.notional_usd = 0.0
        self.floating_pnl = 0.0
        self.trail_floor = None

def signed_pnl(spec: BallSpec, px_now: float, px_entry: float, qty: float) -> float:
    raw = (px_now - px_entry) * qty
    return raw if spec.side == "long" else -raw

def try_entry(br: BallRuntime, price: float, ts: float, qty: float) -> bool:
    if br.state != "IDLE" or qty <= 0:
        return False
    br.state = "OPEN"
    br.entry_price = price
    br.qty = qty
    br.notional_usd = qty * price
    br.last_action_ts = ts
    return True

def manage_exit(br: BallRuntime, price: float, ts: float) -> Optional[str]:
    if br.state != "OPEN" or br.entry_price is None or br.qty <= 0:
        return None
    pnl = signed_pnl(br.spec, price, br.entry_price, br.qty)
    br.floating_pnl = pnl
    ex = br.spec.exit

    # TP/SL
    if ex.tp_usd is not None and pnl >= ex.tp_usd:
        br.realized_pnl += pnl
        br.reset()
        return "TP"
    if ex.sl_usd is not None and pnl <= -abs(ex.sl_usd):
        br.realized_pnl += pnl
        br.reset()
        return "SL"

    # Age limit
    if ex.time_limit_s and br.last_action_ts and ts - br.last_action_ts >= ex.time_limit_s:
        br.realized_pnl += pnl
        br.reset()
        return "TIMEOUT"

    # Trail step (profit only)
    tr = br.spec.trail
    if tr.enabled and tr.step_usd > 0 and pnl >= (br.trail_floor or 0.0) + tr.step_usd:
        br.trail_floor = pnl
    return None
