from __future__ import annotations

import json
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional

SNAPSHOT_PATH = Path('data/performance_snapshot.json')
SUMMARY_PATH = Path('data/performance_summary.json')


@dataclass
class BlockAnalytics:
    block_id: str
    sharpe: float
    win_rate: float
    average_trade_duration: float
    mean_latency: float
    max_drawdown: float
    slippage_mean: float
    slippage_p95: float

    def as_dict(self) -> Dict[str, float | str]:
        return {
            'block_id': self.block_id,
            'sharpe': round(self.sharpe, 4),
            'win_rate': round(self.win_rate, 2),
            'average_trade_duration': round(self.average_trade_duration, 2),
            'mean_latency': round(self.mean_latency, 2),
            'max_drawdown': round(self.max_drawdown, 4),
            'slippage_mean': round(self.slippage_mean, 4),
            'slippage_p95': round(self.slippage_p95, 4),
        }


class PerformanceAnalytics:
    def __init__(self, snapshot_path: Path = SNAPSHOT_PATH):
        self.snapshot_path = snapshot_path

    def load_snapshot(self) -> Dict[str, any]:
        if not self.snapshot_path.exists():
            raise FileNotFoundError(f'Performance snapshot missing: {self.snapshot_path}')
        return json.loads(self.snapshot_path.read_text(encoding='utf-8'))

    def analyse(self) -> List[BlockAnalytics]:
        snapshot = self.load_snapshot()
        blocks = snapshot.get('blocks') or {}
        results: List[BlockAnalytics] = []
        for block_id, data in blocks.items():
            trades = data.get('trades', [])
            returns = data.get('returns', [])
            latencies = data.get('latencies', [])
            slippages = [float(t.get('slippage', 0)) for t in trades if t.get('slippage') is not None]
            durations = [float(t.get('duration', 0)) for t in trades if t.get('duration') is not None]

            sharpe = self._sharpe_ratio(returns)
            win_rate = self._win_rate(trades)
            avg_duration = statistics.fmean(durations) if durations else 0.0
            mean_latency = statistics.fmean(latencies) if latencies else 0.0
            max_drawdown = self._max_drawdown(returns)
            slippage_mean = statistics.fmean(slippages) if slippages else 0.0
            slippage_p95 = self._percentile(slippages, 0.95)

            results.append(BlockAnalytics(
                block_id=block_id,
                sharpe=sharpe,
                win_rate=win_rate,
                average_trade_duration=avg_duration,
                mean_latency=mean_latency,
                max_drawdown=max_drawdown,
                slippage_mean=slippage_mean,
                slippage_p95=slippage_p95,
            ))
        self._write_summary(results)
        return results

    def _sharpe_ratio(self, returns: Iterable[float]) -> float:
        returns = list(returns)
        if not returns:
            return 0.0
        mean = statistics.fmean(returns)
        std = statistics.pstdev(returns) if len(returns) > 1 else 0.0
        return mean / std if std > 0 else 0.0

    def _win_rate(self, trades: Iterable[Dict[str, any]]) -> float:
        trades = list(trades)
        if not trades:
            return 0.0
        wins = sum(1 for trade in trades if trade.get('win') or trade.get('pnl', 0) > 0)
        return wins / len(trades) * 100.0

    def _max_drawdown(self, returns: Iterable[float]) -> float:
        peak = 0.0
        drawdown = 0.0
        cumulative = 0.0
        for value in returns:
            cumulative += value
            peak = max(peak, cumulative)
            drawdown = min(drawdown, cumulative - peak)
        return abs(drawdown)

    def _percentile(self, values: List[float], pct: float) -> float:
        if not values:
            return 0.0
        values = sorted(values)
        index = min(len(values) - 1, int(len(values) * pct))
        return values[index]

    def _write_summary(self, results: List[BlockAnalytics]) -> None:
        payload = {
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'blocks': [item.as_dict() for item in results],
        }
        SUMMARY_PATH.write_text(json.dumps(payload, indent=2), encoding='utf-8')
