"""
signal_aggregator.py  — V13 Manual
Build: 2025-10-18

Purpose
-------
Merge autonomous soldier outputs (Ball1..Ball10) into a single tactical bias:
  - OFFENSE  (aggressive / buy bias)
  - DEFENSE  (protect / sell bias)
  - HOLD     (neutral / wait)

Design goals
------------
1. Deterministic weighted aggregation using soldier-provided numeric scores.
2. Respect capital-weighting when available.
3. Hysteresis + cooldown to avoid flappy mode changes.
4. Read doctrine overrides from `config/doctrine_overrides.json` if present.
5. Produce diagnostics/telemetry-friendly output for logging by Commander.

Input format (expected)
-----------------------
soldier_signals: list of dicts, each dict contains:
  {
    "name": "Ball-1",
    "score":  0.65,        # float in [-1.0, +1.0], positive=OFFENSE, negative=DEFENSE
    "capital_pct": 0.05    # optional relative weight (0..1) — defaults to equal-weighting
  }

Market context (optional) — consumer-defined dict for additional biasing (volatility, spread, mode)

Output
------
{
  "mode": "OFFENSE" | "DEFENSE" | "HOLD",
  "weighted_score": float,        # aggregated score in [-1,1]
  "confidence": float,            # 0..1 derived from abs(weighted_score) & participation
  "breakdown": { <per-soldier diagnostics> },
  "timestamp": <iso8601>,
}

"""

from __future__ import annotations

import json
import math
import os
import time
from typing import Dict, List, Optional, Tuple

# --- Defaults / Tunables -------------------------------------------------
DEFAULT_MIN_PARTICIPATION = 0.3  # fraction of total capital that must report to consider the aggregate valid
DEFAULT_THRESHOLD = 0.15         # |weighted_score| must exceed this for OFFENSE/DEFENSE (otherwise HOLD)
DEFAULT_HYSTERESIS = 0.05        # extra margin required to flip from previous mode
DEFAULT_COOLDOWN_SEC = 3.0       # seconds to wait before accepting a different mode (simple temporal debounce)
DOCTRINE_OVERRIDES_PATH = os.path.join("config", "doctrine_overrides.json")


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class SignalAggregator:
    """Aggregator with stateful hysteresis and optional doctrine overrides.

    Usage:
        agg = SignalAggregator()         # uses defaults and reads doctrine_overrides.json if present
        out = agg.aggregate(soldier_signals)
        # out contains mode, weighted_score, confidence, breakdown

    The aggregator is intentionally conservative: it requires reasonable participation
    and a small margin before flipping modes to reduce thrashing in noisy markets.
    """

    def __init__(self,
                 min_participation: float = DEFAULT_MIN_PARTICIPATION,
                 threshold: float = DEFAULT_THRESHOLD,
                 hysteresis: float = DEFAULT_HYSTERESIS,
                 cooldown_sec: float = DEFAULT_COOLDOWN_SEC,
                 doctrine_path: Optional[str] = DOCTRINE_OVERRIDES_PATH):
        self.min_participation = min_participation
        self.threshold = threshold
        self.hysteresis = hysteresis
        self.cooldown_sec = cooldown_sec

        self.last_mode: Optional[str] = None
        self.last_switch_ts: float = 0.0
        self.last_weighted_score: float = 0.0

        self.doctrine = self._load_doctrine(doctrine_path) if doctrine_path else {}

    def _load_doctrine(self, path: str) -> Dict:
        try:
            with open(path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except Exception as e:
            # don't crash the runtime because doctrine parsing failed; fall back to empty
            print(f"[SignalAggregator] failed to load doctrine overrides: {e}")
            return {}

    def _apply_doctrine_bias(self, weighted_score: float, market_context: Optional[Dict]) -> float:
        """If doctrine overrides specify a bias multiplier or floor/ceiling, apply them.

        Example overrides (doctrine_overrides.json):
        {
          "bias_multiplier": 0.9,       # damp overall signal by 10%
          "force_mode": null,          # e.g. "HOLD" or "OFFENSE" to force
          "min_confidence": 0.2
        }
        """
        if not self.doctrine:
            return weighted_score

        score = weighted_score
        mult = self.doctrine.get("bias_multiplier")
        if isinstance(mult, (int, float)):
            score *= float(mult)

        # forced mode handling is done upstream (we don't change the numeric score here)
        return max(-1.0, min(1.0, score))

    def _determine_mode_from_score(self, weighted_score: float, participation: float) -> Tuple[str, float]:
        """Return (mode, confidence)

        - If participation below minimum → HOLD with low confidence
        - If |weighted_score| below threshold → HOLD
        - Otherwise OFFENSE if score>0 else DEFENSE
        Confidence is a simple mapping of abs(score) * participation
        """
        if participation < self.min_participation:
            return "HOLD", float(participation)

        abs_score = abs(weighted_score)
        if abs_score < self.threshold:
            return "HOLD", abs_score * participation

        mode = "OFFENSE" if weighted_score > 0 else "DEFENSE"
        confidence = min(1.0, abs_score * (0.5 + 0.5 * participation))
        return mode, confidence

    def aggregate(self, soldier_signals: List[Dict], market_context: Optional[Dict] = None) -> Dict:
        """Aggregate a single cycle of soldier signals into a unified mode.

        soldier_signals: see top-of-file format. Missing/invalid scores are ignored but participation is tracked.
        market_context: optional dict passed through to doctrine adjustments.
        """
        if not isinstance(soldier_signals, list):
            raise TypeError("soldier_signals must be a list of dicts")

        # Normalize and compute capital weights
        breakdown = {}
        total_weight = 0.0
        weighted_sum = 0.0
        participating_capital = 0.0
        reported_count = 0

        # Default equal weight if no capital_pct provided
        default_weight = 1.0

        for s in soldier_signals:
            name = s.get("name", "unknown")
            raw_score = s.get("score")
            if raw_score is None:
                breakdown[name] = {"ok": False, "reason": "no score"}
                continue

            try:
                score = float(raw_score)
            except Exception:
                breakdown[name] = {"ok": False, "reason": "bad score"}
                continue

            cap = s.get("capital_pct")
            weight = float(cap) if (cap is not None and cap > 0) else default_weight

            breakdown[name] = {"ok": True, "score": score, "weight": weight}
            reported_count += 1
            total_weight += weight
            weighted_sum += (score * weight)
            participating_capital += weight

        # if nobody reported, return HOLD
        if reported_count == 0 or total_weight == 0.0:
            return {
                "mode": "HOLD",
                "weighted_score": 0.0,
                "confidence": 0.0,
                "breakdown": breakdown,
                "timestamp": _now_iso(),
            }

        # participation fraction — interpreted relative to sum of declared weights if the commander/registry
        # cannot provide a true total capital figure; this is coarse but effective for simulations.
        # If doctrine supplies an expected_total_capital, use it.
        expected_total_capital = None
        if isinstance(self.doctrine.get("expected_total_capital"), (int, float)):
            expected_total_capital = float(self.doctrine["expected_total_capital"])

        if expected_total_capital and expected_total_capital > 0:
            participation = min(1.0, participating_capital / expected_total_capital)
        else:
            # participation relative to number of soldiers (fallback)
            participation = min(1.0, reported_count / 10.0)

        weighted_score = weighted_sum / total_weight

        # apply doctrine multipliers or damping
        weighted_score = self._apply_doctrine_bias(weighted_score, market_context)

        # hysteresis: require additional margin to flip away from last_mode
        proposed_mode, base_confidence = self._determine_mode_from_score(weighted_score, participation)

        now_ts = time.time()
        mode = proposed_mode
        confidence = base_confidence

        # Forced mode via doctrine (highest precedence)
        forced = self.doctrine.get("force_mode")
        if isinstance(forced, str) and forced.upper() in ("OFFENSE", "DEFENSE", "HOLD"):
            mode = forced.upper()
            confidence = max(confidence, float(self.doctrine.get("min_confidence", confidence)))

        else:
            # only consider hysteresis/cooldown if we had a previous mode
            if self.last_mode is not None and mode != self.last_mode:
                # compute required margin to flip based on hysteresis
                # e.g., if last_mode was OFFENSE, weighted_score must be < -(threshold + hysteresis) to go DEFENSE
                # symmetric for opposite direction
                flip_required = self.threshold + self.hysteresis
                if abs(weighted_score) < flip_required:
                    # not enough magnitude to change mode — stay in last_mode
                    mode = self.last_mode
                    # degrade confidence slightly since underlying signal is weak
                    confidence = base_confidence * 0.5
                else:
                    # respect cooldown
                    if (now_ts - self.last_switch_ts) < self.cooldown_sec:
                        # still cooling down — ignore flip
                        mode = self.last_mode
                        confidence = base_confidence * 0.6
                    else:
                        # allow mode flip
                        pass

        # commit state if the mode changed
        if mode != self.last_mode:
            self.last_mode = mode
            self.last_switch_ts = now_ts

        self.last_weighted_score = weighted_score

        out = {
            "mode": mode,
            "weighted_score": float(max(-1.0, min(1.0, weighted_score))),
            "confidence": float(max(0.0, min(1.0, confidence))),
            "participation": float(participation),
            "breakdown": breakdown,
            "timestamp": _now_iso(),
        }

        return out


# --------------------------- Example / Unit Test ----------------------------------
if __name__ == "__main__":
    # Mock soldiers with various signals
    mock = [
        {"name": "Ball-1", "score": 0.8, "capital_pct": 0.05},
        {"name": "Ball-2", "score": 0.6, "capital_pct": 0.05},
        {"name": "Ball-3", "score": 0.1, "capital_pct": 0.05},
        {"name": "Ball-4", "score": -0.3, "capital_pct": 0.10},
        {"name": "Ball-9", "score": -0.9, "capital_pct": 0.20},
    ]

    agg = SignalAggregator()
    out1 = agg.aggregate(mock)
    print("Cycle 1 ->", out1)

    # flip case: more OFFENSE votes
    mock2 = [
        {"name": "Ball-1", "score": 0.8, "capital_pct": 0.05},
        {"name": "Ball-2", "score": 0.7, "capital_pct": 0.05},
        {"name": "Ball-6", "score": 0.9, "capital_pct": 0.10},
        {"name": "Ball-9", "score": 0.4, "capital_pct": 0.20},
    ]

    time.sleep(1)
    out2 = agg.aggregate(mock2)
    print("Cycle 2 ->", out2)

    # quick weak opposite signal — should stay in last_mode due to hysteresis/cooldown
    mock3 = [
        {"name": "Ball-1", "score": -0.2, "capital_pct": 0.05},
        {"name": "Ball-2", "score": -0.1, "capital_pct": 0.05},
    ]

    out3 = agg.aggregate(mock3)
    print("Cycle 3 ->", out3)


# --------------------------- Integration Snippet ----------------------------------
# In commander_v13_manual.py (example):
#
# from signal_aggregator import SignalAggregator
#
# agg = SignalAggregator()
#
# while running:
#     soldier_signals = commander.collect_soldier_signals()  # list of dicts (see format)
#     market_ctx = commander.market_snapshot()
#     aggregate_out = agg.aggregate(soldier_signals, market_ctx)
#     commander.apply_tactical_mode(aggregate_out)
#
# Telemetry: commander should log aggregate_out at INFO level every cycle.
