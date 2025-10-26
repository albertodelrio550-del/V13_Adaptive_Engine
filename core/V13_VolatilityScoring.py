"""
V13_VolatilityScoring.py
Phase 6 volatility classifier used by CommandMatrix adaptive allocation.

The scorer maintains a rolling history of per-block telemetry deltas and
produces a normalized volatility/trend signal. The CommandMatrix consumes
the signal to adjust capital splits (Assassins vs Avengers) and logs each
decision for later audit/learning.
"""

from __future__ import annotations

import statistics
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, Optional


@dataclass
class VolatilityScore:
    block_id: str
    samples: int
    volatility: float
    trend_strength: float
    classification: str

    def as_dict(self) -> Dict[str, float | int | str]:
        return {
            "block_id": self.block_id,
            "samples": self.samples,
            "volatility": round(self.volatility, 4),
            "trend_strength": round(self.trend_strength, 4),
            "classification": self.classification,
        }


class Phase6VolatilityScorer:
    """
    Lightweight rolling volatility scorer.

    The input telemetry is expected to provide either `delta` (percentage)
    or `price`. When only price is available, pseudo-delta is computed as
    the percent change between successive prices.
    """

    def __init__(
        self,
        window: int = 30,
        low_threshold: float = 0.35,
        high_threshold: float = 0.9,
        trend_threshold: float = -0.05,
    ) -> None:
        self.window = max(window, 5)
        self.low_threshold = low_threshold
        self.high_threshold = high_threshold
        self.trend_threshold = trend_threshold
        self._delta_history: Dict[str, Deque[float]] = {}
        self._last_price: Dict[str, float] = {}

    # ------------------------------------------------------------------
    def _compute_delta(self, block_id: str, telemetry: Dict[str, float]) -> Optional[float]:
        raw_delta = telemetry.get("delta")
        if raw_delta is not None:
            try:
                return float(raw_delta)
            except (TypeError, ValueError):
                return None
        price = telemetry.get("price")
        if price is None:
            return None
        try:
            price = float(price)
        except (TypeError, ValueError):
            return None
        last_price = self._last_price.get(block_id)
        self._last_price[block_id] = price
        if last_price is None or last_price == 0:
            return None
        return ((price - last_price) / last_price) * 100

    def update(self, block_id: str, telemetry: Dict[str, float]) -> VolatilityScore:
        block_key = block_id.upper()
        delta = self._compute_delta(block_key, telemetry)
        history = self._delta_history.setdefault(block_key, deque(maxlen=self.window))
        if delta is not None:
            history.append(delta)
        samples = len(history)
        if samples < 2:
            volatility = abs(delta or 0.0)
            trend_strength = delta or 0.0
        else:
            volatility = statistics.pstdev(history)
            trend_strength = statistics.fmean(history)

        classification = self._classify(volatility, trend_strength)
        return VolatilityScore(
            block_id=block_key,
            samples=samples,
            volatility=volatility,
            trend_strength=trend_strength,
            classification=classification,
        )

    def _classify(self, volatility: float, trend_strength: float) -> str:
        if volatility <= self.low_threshold:
            return "LOW_VOL"
        if volatility >= self.high_threshold and trend_strength <= self.trend_threshold:
            return "HIGH_VOL_NEG_TREND"
        return "NEUTRAL"
