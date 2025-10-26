"""
V13_ReplayEngine.py
Historical replay sandbox for doctrine evaluation (Phase 8 Step 4).

Responsibilities
----------------
* Load the most recent 30 days of archived tick/telemetry data.
* Apply one or more doctrine parameter sets against that feed.
* Compute counterfactual PnL and fitness metrics per configuration.
* Persist replay artefacts for downstream Doctrine Feedback analysis.

Notes
-----
This module intentionally avoids heavy dependencies so the sandbox can
run inside constrained PAPER environments. Tick archives are expected
under data/analytics/YYYYMMDD/ with either ticks.jsonl or ticks.csv.
Missing days are tolerated and surfaced in the replay report.
"""

from __future__ import annotations

import csv
import json
import statistics
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

ANALYTICS_ROOT = Path("data/analytics")
RESULTS_PATH = Path("data/replay_results.json")
LOG_PATH = Path("logs/replay_engine.log")
DEFAULT_LOOKBACK_DAYS = 30


# pathlib.Path.write_text does not offer append; helper wrapper.
def _append_log(message: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(f"{timestamp} | {message}\n")


log_event = _append_log  # alias for clarity


@dataclass
class ReplayResult:
    doctrine_id: str
    parameters: Dict[str, float]
    total_pnl: float
    daily_pnl: Dict[str, float]
    sharpe: float
    max_drawdown: float
    volatility: float
    fitness: float
    missing_days: List[str]

    def as_dict(self) -> Dict[str, object]:
        return {
            "doctrine_id": self.doctrine_id,
            "parameters": self.parameters,
            "total_pnl": round(self.total_pnl, 4),
            "daily_pnl": {k: round(v, 4) for k, v in self.daily_pnl.items()},
            "sharpe": round(self.sharpe, 4),
            "max_drawdown": round(self.max_drawdown, 4),
            "volatility": round(self.volatility, 4),
            "fitness": round(self.fitness, 4),
            "missing_days": self.missing_days,
        }


class ReplayEngine:
    def __init__(
        self,
        analytics_root: Path = ANALYTICS_ROOT,
        results_path: Path = RESULTS_PATH,
        lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    ) -> None:
        self.analytics_root = analytics_root
        self.results_path = results_path
        self.lookback_days = lookback_days
        self.analytics_root.mkdir(parents=True, exist_ok=True)
        self.results_path.parent.mkdir(parents=True, exist_ok=True)
        log_event(f"ReplayEngine initialized | root={analytics_root} lookback={lookback_days}")

    # ------------------------------------------------------------------
    # Data discovery helpers
    # ------------------------------------------------------------------
    def list_available_days(self) -> List[str]:
        if not self.analytics_root.exists():
            return []
        days = [
            p.name
            for p in self.analytics_root.iterdir()
            if p.is_dir() and p.name.isdigit() and len(p.name) == 8
        ]
        days.sort(reverse=True)
        return days[: self.lookback_days]

    def _load_ticks_jsonl(self, path: Path) -> List[Dict[str, float]]:
        entries: List[Dict[str, float]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                entries.append(payload)
        return entries

    def _load_ticks_csv(self, path: Path) -> List[Dict[str, float]]:
        entries: List[Dict[str, float]] = []
        with path.open("r", newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                entries.append(row)
        return entries

    def load_ticks_for_day(self, day: str) -> List[Dict[str, float]]:
        day_path = self.analytics_root / day
        if not day_path.exists():
            return []
        jsonl_path = day_path / "ticks.jsonl"
        csv_path = day_path / "ticks.csv"
        if jsonl_path.exists():
            return self._load_ticks_jsonl(jsonl_path)
        if csv_path.exists():
            return self._load_ticks_csv(csv_path)
        log_event(f"No tick archive for {day}")
        return []

    # ------------------------------------------------------------------
    # Simulation / metrics
    # ------------------------------------------------------------------
    def _simulate_day(
        self,
        ticks: Sequence[Dict[str, object]],
        parameters: Dict[str, float],
    ) -> float:
        if not ticks:
            return 0.0
        risk_factor = float(parameters.get("risk_factor", 1.0))
        assassin_bias = float(parameters.get("assassin_bias", 0.5))
        avenger_bias = float(parameters.get("avenger_bias", 0.5))
        pnl = 0.0
        inventory = 0.0
        last_price = None
        for tick in ticks:
            price = tick.get("price") or tick.get("close") or tick.get("last")
            try:
                price = float(price)
            except (TypeError, ValueError):
                price = last_price
            if price is None:
                continue
            last_price = price
            signal = str(tick.get("signal") or tick.get("side") or "HOLD").upper()
            momentum = float(tick.get("delta") or tick.get("momentum") or 0.0)
            volatility = abs(float(tick.get("volatility") or 0.0))
            position_delta = 0.0
            if signal == "BUY":
                position_delta = 1.0 * assassin_bias
            elif signal == "SELL":
                position_delta = -1.0 * avenger_bias
            # inventory update
            inventory += position_delta
            pnl += (inventory * momentum * risk_factor) - (volatility * 0.01 * abs(inventory))
        return pnl

    def _compute_drawdown(self, pnl_series: Iterable[float]) -> float:
        peak = 0.0
        drawdown = 0.0
        cumulative = 0.0
        for value in pnl_series:
            cumulative += value
            peak = max(peak, cumulative)
            drawdown = min(drawdown, cumulative - peak)
        return abs(drawdown)

    def _compute_metrics(self, daily_values: Dict[str, float]) -> Dict[str, float]:
        if not daily_values:
            return {"total_pnl": 0.0, "sharpe": 0.0, "volatility": 0.0, "max_drawdown": 0.0}
        pnl_list = list(daily_values.values())
        total = sum(pnl_list)
        avg = statistics.fmean(pnl_list) if pnl_list else 0.0
        volatility = statistics.pstdev(pnl_list) if len(pnl_list) > 1 else 0.0
        sharpe = avg / volatility if volatility > 0 else 0.0
        max_drawdown = self._compute_drawdown(pnl_list)
        return {
            "total_pnl": total,
            "sharpe": sharpe,
            "volatility": volatility,
            "max_drawdown": max_drawdown,
        }

    def _fitness_score(self, metrics: Dict[str, float]) -> float:
        sharpe = metrics.get("sharpe", 0.0)
        drawdown = metrics.get("max_drawdown", 0.0)
        volatility = metrics.get("volatility", 0.0)
        return sharpe - (drawdown * 0.1) - (volatility * 0.05)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run_replay(
        self,
        parameter_sets: Sequence[Dict[str, object]],
        lookback_days: Optional[int] = None,
    ) -> List[ReplayResult]:
        lookback = lookback_days or self.lookback_days
        target_days = self.list_available_days()[:lookback]
        prepared_days = list(reversed(target_days))  # chronological
        log_event(f"Running replay across {len(prepared_days)} days: {prepared_days}")
        results: List[ReplayResult] = []
        for params in parameter_sets:
            doctrine_id = str(params.get("doctrine_id") or params.get("name") or "UNNAMED")
            settings = {
                key: float(value)
                for key, value in params.items()
                if isinstance(value, (int, float)) or key in {"risk_factor", "assassin_bias", "avenger_bias"}
            }
            daily_pnl: Dict[str, float] = {}
            missing_days: List[str] = []
            for day in prepared_days:
                ticks = self.load_ticks_for_day(day)
                if not ticks:
                    missing_days.append(day)
                    continue
                pnl = self._simulate_day(ticks, settings)
                daily_pnl[day] = pnl
            metrics = self._compute_metrics(daily_pnl)
            fitness = self._fitness_score(metrics)
            result = ReplayResult(
                doctrine_id=doctrine_id,
                parameters=settings,
                total_pnl=metrics["total_pnl"],
                daily_pnl=daily_pnl,
                sharpe=metrics["sharpe"],
                max_drawdown=metrics["max_drawdown"],
                volatility=metrics["volatility"],
                fitness=fitness,
                missing_days=missing_days,
            )
            results.append(result)
            log_event(
                f"Replay complete | doctrine={doctrine_id} pnl={metrics['total_pnl']:.2f} "
                f"sharpe={metrics['sharpe']:.2f} fitness={fitness:.2f} missing={len(missing_days)}"
            )
        self._persist_results(results)
        return results

    def _persist_results(self, results: Sequence[ReplayResult]) -> None:
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "lookback_days": self.lookback_days,
            "results": [item.as_dict() for item in results],
        }
        self.results_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # Convenience CLI -----------------------------------------------------------------
    def run_from_file(self, parameter_file: Path) -> List[ReplayResult]:
        if not parameter_file.exists():
            raise FileNotFoundError(f"Parameter file not found: {parameter_file}")
        params_payload = json.loads(parameter_file.read_text(encoding="utf-8"))
        if isinstance(params_payload, dict):
            parameter_sets = params_payload.get("parameter_sets") or [params_payload]
        elif isinstance(params_payload, list):
            parameter_sets = params_payload
        else:
            raise ValueError("Parameter file must contain dict or list payload.")
        if not isinstance(parameter_sets, list):
            raise ValueError("Parameter sets must be a list.")
        return self.run_replay(parameter_sets)


def _default_parameter_sets() -> List[Dict[str, object]]:
    return [
        {
            "doctrine_id": "ASSASSIN_BASELINE",
            "risk_factor": 1.0,
            "assassin_bias": 0.7,
            "avenger_bias": 0.3,
        },
        {
            "doctrine_id": "AVENGER_EXTENDED",
            "risk_factor": 0.8,
            "assassin_bias": 0.4,
            "avenger_bias": 0.6,
        },
    ]


def main(argv: Optional[Sequence[str]] = None) -> None:
    argv = list(argv or sys.argv[1:])
    engine = ReplayEngine()
    try:
        if argv:
            param_file = Path(argv[0])
            results = engine.run_from_file(param_file)
        else:
            results = engine.run_replay(_default_parameter_sets())
        summary = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "results": [res.as_dict() for res in results],
            "output_path": str(engine.results_path),
        }
        print(json.dumps(summary, indent=2))
    except Exception as exc:  # pragma: no cover
        log_event(f"ReplayEngine failed: {exc}")
        raise


if __name__ == "__main__":  # pragma: no cover
    main()
