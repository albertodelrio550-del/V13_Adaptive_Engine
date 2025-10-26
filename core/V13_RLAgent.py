from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone, timezone
from pathlib import Path
from typing import Dict, List

STATE_KEYS = ["volatility", "trend_strength", "latency", "win_rate"]
ACTION_KEYS = ["trail_pct", "stop_pct", "capital_split"]


@dataclass
class RLResult:
    actions: Dict[str, float]
    reward: float


class ReinforcementLearner:
    def __init__(self, policy_path: Path | None = None, learning_rate: float = 0.05):
        self.policy_path = policy_path or Path("data/policy.json")
        self.learning_rate = learning_rate
        self.policy = self._load_policy()

    def _load_policy(self) -> Dict[str, List[float]]:
        if self.policy_path.exists():
            try:
                payload = json.loads(self.policy_path.read_text(encoding="utf-8"))
                payload.pop("updated_at", None)
                if all(len(payload.get(action, [])) == len(STATE_KEYS) for action in ACTION_KEYS):
                    return payload
            except Exception:
                pass
        return {action: [0.0 for _ in STATE_KEYS] for action in ACTION_KEYS}

    def _save_policy(self) -> None:
        self.policy_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {action: weights for action, weights in self.policy.items()}
        payload["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.policy_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def evaluate(self, state: Dict[str, float]) -> Dict[str, float]:
        features = [float(state.get(key, 0.0)) for key in STATE_KEYS]
        actions = {}
        for action, weights in self.policy.items():
            value = sum(float(w) * float(f) for w, f in zip(weights, features))
            actions[action] = round(value, 4)
        return actions

    def update(self, state: Dict[str, float], reward: float) -> RLResult:
        features = [float(state.get(key, 0.0)) for key in STATE_KEYS]
        for action in ACTION_KEYS:
            weights = self.policy[action]
            for idx, feature in enumerate(features):
                try:
                    feature_val = float(feature)
                except (TypeError, ValueError):
                    feature_val = 0.0
                weights[idx] += self.learning_rate * reward * feature_val
        self._save_policy()
        actions = self.evaluate(state)
        return RLResult(actions=actions, reward=reward)

    def learn_from_metrics(self, metrics: Dict[str, float]) -> RLResult:
        state = self._build_state(metrics)
        reward = metrics.get("sharpe", 0.0) - metrics.get("max_drawdown", 0.0)
        return self.update(state, reward)

    def _build_state(self, metrics: Dict[str, float]) -> Dict[str, float]:
        return {
            "volatility": float(metrics.get("max_drawdown", 0.0) or 0.0),
            "trend_strength": float(metrics.get("correlation", 0.0) or 0.0),
            "latency": float(metrics.get("mean_latency_ms", 0.0) or 0.0) / 1000.0,
            "win_rate": float(metrics.get("win_rate", 0.0) or 0.0) / 100.0,
        }
