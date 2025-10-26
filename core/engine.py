from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import math, time, json, pathlib

from .ball import BallSpec, BallRuntime, EntrySpec, ExitSpec, TrailSpec, try_entry, manage_exit
from .risk import RiskManager, RiskLimits, Ladder, LadderRule

@dataclass
class SessionConfig:
    mode_name: str
    symbol: str = "BTC/USDT"
    capital_usd: float = 5000.0
    supports: List[float] = field(default_factory=list)
    resistances: List[float] = field(default_factory=list)
    entry_threshold_usd: float = 10.0

@dataclass
class SessionState:
    t_now: float = 0.0
    last_price: float = 0.0
    one_min_change_pct: float = 0.0
    realized_usd: float = 0.0
    balls: Dict[int, BallRuntime] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)

    def total_floating(self) -> float:
        return sum(b.floating_pnl for b in self.balls.values())

    def total(self) -> float:
        return self.realized_usd + self.total_floating()

class AssassinEngine:
    def __init__(self, cfg: SessionConfig, risk: RiskManager, balls: List[BallSpec]):
        self.cfg = cfg
        self.risk = risk
        self.state = SessionState()
        for bs in balls:
            self.state.balls[bs.id] = BallRuntime(spec=bs)

    @staticmethod
    def load_from_preset(cfg: SessionConfig, presets_path: str) -> "AssassinEngine":
        data = json.loads(pathlib.Path(presets_path).read_text())
        p = data[cfg.mode_name]
        # Risk & Ladder
        limits = RiskLimits(**p["risk"])
        ladder = Ladder(
            base_floor_usd=p["ladder"]["base_floor_usd"],
            steps=[LadderRule(**s) for s in p["ladder"]["steps"]],
        )
        risk = RiskManager(limits, ladder)
        # Balls
        balls: List[BallSpec] = []
        for b in p["balls"]:
            bs = BallSpec(
                id=b["id"], role=b["role"], side=b.get("side", "long"), capital_frac=b["capital_frac"],
                entry=EntrySpec(**b["entry"]), exit=ExitSpec(**b["exit"]), trail=TrailSpec(**b["trail"])
            )
            balls.append(bs)
        return AssassinEngine(cfg, risk, balls)

    def _nearest_level_dist(self, price: float, levels: List[float]) -> float:
        return min((abs(price - lv) for lv in levels), default=float('inf'))

    def _entry_gate(self, role: str, price: float) -> bool:
        near_sup = self._nearest_level_dist(price, self.cfg.supports) <= self.cfg.entry_threshold_usd
        near_res = self._nearest_level_dist(price, self.cfg.resistances) <= self.cfg.entry_threshold_usd
        return (near_sup or near_res) or (not self.cfg.supports and not self.cfg.resistances)

    def _position_qty(self, capital_frac: float, price: float) -> float:
        usd = max(self.cfg.capital_usd * capital_frac, 1e-6)
        return math.floor((usd / max(price, 1e-9)) * 1_000_000) / 1_000_000

    def on_price(self, price: float, one_min_change_pct: float = 0.0, ts: Optional[float] = None):
        ts = ts or time.time()
        s = self.state
        s.t_now = ts
        s.last_price = price
        s.one_min_change_pct = one_min_change_pct

        # CrashGuard
        if self.risk.crashguard(one_min_change_pct):
            self.cmd_lock_all(reason="CRASHGUARD")
            s.notes.append(f"[CRASHGUARD] pct={one_min_change_pct:.2f}")
            return

        for b_id, br in s.balls.items():
            if br.state == "IDLE" and self._entry_gate(br.spec.role, price):
                qty = self._position_qty(br.spec.capital_frac, price)
                if try_entry(br, price, ts, qty):
                    s.notes.append(f"Ball {b_id} ENTRY role={br.spec.role} qty={qty} @ {price:.2f}")
            else:
                evt = manage_exit(br, price, ts)
                if evt:
                    s.notes.append(f"Ball {b_id} EXIT {evt} realized={br.realized_pnl:.2f}")
                    s.realized_usd += br.realized_pnl
                    br.realized_pnl = 0.0

        self.risk.update_pnl(s.realized_usd, s.total_floating())
        if self.risk.dd_breach():
            self.cmd_lock_all(reason="DD_BREACH")

    def cmd_lock_all(self, reason: str = "LOCK"):
        s = self.state
        realized_gain = s.total_floating()
        s.realized_usd += realized_gain
        for b in s.balls.values():
            b.floating_pnl = 0.0
            b.trail_floor = 0.0
            b.state = "COOLDOWN"
        self.risk.update_pnl(s.realized_usd, 0.0)
        s.notes.append(f"[{reason}] Flattened all; realized += {realized_gain:.2f}")

    def snapshot(self) -> Dict:
        s = self.state
        return {
            "time": s.t_now,
            "last": s.last_price,
            "pnl": {"realized": s.realized_usd, "floating": s.total_floating(), "total": s.total()},
            "protection": {"floor": self.risk.state.session_floor, "peak": self.risk.state.session_peak},
            "balls": {
                b_id: {
                    "state": br.state, "float": br.floating_pnl, "trail_floor": br.trail_floor,
                    "qty": br.qty, "entry": br.entry_price, "role": br.spec.role, "side": br.spec.side
                } for b_id, br in s.balls.items()
            },
            "notes": s.notes[-12:]
        }
