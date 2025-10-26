from __future__ import annotations

import argparse
import configparser
import hashlib
"""
V13_DoctrineFeedbackLoop
Phase 8 Step 11 - Commander AI feedback loop.

Responsibilities
----------------
* Consolidate performance telemetry (Sharpe, win rate, drawdown, etc.).
* Emit daily doctrine reports under docs/DoctrineReports/.
* Provide dual-layer feedback (ACK + doctrine advice) for CommandMatrix.
* Track commander review decisions (accepted / rejected).
"""

import json
import math
import statistics
from dataclasses import dataclass
from datetime import datetime, date, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from core.V13_TelemetryFusion import TelemetryFeed
from core.V13_RiskSentinel import RiskMonitor
from core.V13_PerformanceTracker import PerformanceTracker
from .Doctrine_Loader import load_doctrines

PERFORMANCE_SNAPSHOT_PATH = Path("data/performance_snapshot.json")
PERFORMANCE_LOG_PATH = Path("logs/V13_performance_metrics.jsonl")
DOCTRINE_REPORT_DIR = Path("docs/DoctrineReports")
DOCTRINE_DECISIONS_DIR = Path("docs/DoctrineDecisions")
DOCTRINE_UPDATE_DIR = Path("docs/DoctrineUpdates")
GOVERNANCE_STATE_PATH = Path("data/governance_state.json")
DOCTRINE_HISTORY_DIR = Path("docs/DoctrineHistory")
DOCTRINE_HISTORY_LOG = Path("logs/DoctrineHistory.log")


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _safe_stddev(values: Iterable[float]) -> float:
    values = list(values)
    if len(values) < 2:
        return 0.0
    return statistics.stdev(values)


def _safe_mean(values: Iterable[float]) -> float:
    values = list(values)
    if not values:
        return 0.0
    return statistics.fmean(values)


def _max_drawdown(sequence: Iterable[float]) -> float:
    cummax = -math.inf
    worst = 0.0
    cumulative = 0.0
    for value in sequence:
        cumulative += value
        cummax = max(cummax, cumulative)
        drawdown = cumulative - cummax
        worst = min(worst, drawdown)
    return abs(worst)


@dataclass
class DoctrineMetrics:
    sharpe: float = 0.0
    win_rate: float = 0.0
    average_lock_profit: float = 0.0
    correlation: float = 0.0
    mean_latency_ms: float = 0.0
    max_drawdown: float = 0.0
    slippage_mean: float = 0.0
    slippage_p95: float = 0.0
    trades: int = 0

    def as_dict(self) -> Dict[str, float]:
        return {
            "sharpe": round(self.sharpe, 4),
            "win_rate": round(self.win_rate, 2),
            "average_lock_profit": round(self.average_lock_profit, 4),
            "correlation": round(self.correlation, 4),
            "mean_latency_ms": round(self.mean_latency_ms, 2),
            "max_drawdown": round(self.max_drawdown, 4),
            "slippage_mean": round(self.slippage_mean, 4),
            "slippage_p95": round(self.slippage_p95, 4),
            "trades": self.trades,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "DoctrineMetrics":
        return cls(
            sharpe=float(payload.get("sharpe", 0.0) or 0.0),
            win_rate=float(payload.get("win_rate", 0.0) or 0.0),
            average_lock_profit=float(payload.get("average_lock_profit", 0.0) or 0.0),
            correlation=float(payload.get("correlation", 0.0) or 0.0),
            mean_latency_ms=float(payload.get("mean_latency_ms", 0.0) or 0.0),
            max_drawdown=float(payload.get("max_drawdown", 0.0) or 0.0),
            slippage_mean=float(payload.get("slippage_mean", 0.0) or 0.0),
            slippage_p95=float(payload.get("slippage_p95", 0.0) or 0.0),
            trades=int(payload.get("trades", 0) or 0),
        )




def _load_governance_state() -> dict:
    if GOVERNANCE_STATE_PATH.exists():
        try:
            return json.loads(GOVERNANCE_STATE_PATH.read_text(encoding='utf-8'))
        except Exception:
            pass
    return {
        'learning_mode': True,
        'consecutive_failures': 0,
        'last_parameters': {},
        'last_accepted_date': None,
        'changes_today': {}
    }


def _save_governance_state(state: dict) -> None:
    GOVERNANCE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    GOVERNANCE_STATE_PATH.write_text(json.dumps(state, indent=2), encoding='utf-8')


def _prune_change_history(changes: Dict[str, int], keep: int = 14) -> Dict[str, int]:
    if len(changes) <= keep:
        return changes
    ordered_keys = sorted(changes.keys())
    for stale_key in ordered_keys[:-keep]:
        changes.pop(stale_key, None)
    return changes


def _record_history(payload: dict) -> None:
    DOCTRINE_HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    history_path = DOCTRINE_HISTORY_DIR / f"{payload.get('date', 'unknown')}.json"
    history_path.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    digest = hashlib.sha256(history_path.read_bytes()).hexdigest()
    DOCTRINE_HISTORY_LOG.parent.mkdir(parents=True, exist_ok=True)
    with DOCTRINE_HISTORY_LOG.open('a', encoding='utf-8') as handle:
        handle.write(f"{payload.get('date')} {digest}\n")



class DoctrineFeedbackLoop:
    def __init__(
        self,
        snapshot_path: Path = PERFORMANCE_SNAPSHOT_PATH,
        report_dir: Path = DOCTRINE_REPORT_DIR,
        decisions_dir: Path = DOCTRINE_DECISIONS_DIR,
        update_dir: Path = DOCTRINE_UPDATE_DIR,
        load_doctrines_flag: bool = True,
    ):
        self.snapshot_path = snapshot_path
        self.report_dir = report_dir
        self.decisions_dir = decisions_dir
        self.update_dir = update_dir
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.decisions_dir.mkdir(parents=True, exist_ok=True)
        self.update_dir.mkdir(parents=True, exist_ok=True)
        self.governance_state = _load_governance_state()
        self.doctrines = load_doctrines() if load_doctrines_flag else {}
        self.doctrines = self.doctrines or {}
        self.telemetry = TelemetryFeed()
        self.risk_monitor = RiskMonitor()
        self.performance_tracker = PerformanceTracker()

    # ------------------------------------------------------------------
    # Context helpers
    # ------------------------------------------------------------------
    def _extract_config_context(self) -> Dict[str, str]:
        context = {
            "mode": "Unknown",
            "run_env": "UNKNOWN",
            "feed": "Unknown",
        }
        cfg_path = Path("config/V13_Config.ini")
        if cfg_path.exists():
            try:
                cfg = configparser.ConfigParser(inline_comment_prefixes=(";", "#"))
                cfg.read(cfg_path)
                safe_mode = cfg.get("Risk", "Safe_Mode", fallback="Balanced")
                run_env = cfg.get("MODE", "RUN_ENV", fallback="PAPER")
                feed_source = cfg.get("Telemetry", "Feed_Source", fallback="PAPER_FEED")
                context["mode"] = safe_mode.strip().title()
                context["run_env"] = run_env.strip().upper()
                context["feed"] = feed_source.replace("_", " ").title()
            except Exception:
                pass
        return context

    def _load_commander_decision(self, target_date: date) -> Optional[Dict[str, Any]]:
        decision_path = self.decisions_dir / f"{target_date:%Y-%m-%d}.json"
        if not decision_path.exists():
            return None
        try:
            return json.loads(decision_path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _load_doctrine_update(self, target_date: date) -> Optional[Dict[str, Any]]:
        update_path = self.update_dir / f"doctrine_update_{target_date:%Y-%m-%d}.json"
        if not update_path.exists():
            return None
        try:
            return json.loads(update_path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _load_metric_history(
        self,
        limit: int,
        up_to: Optional[date] = None,
    ) -> List[Tuple[date, DoctrineMetrics]]:
        if not PERFORMANCE_LOG_PATH.exists():
            return []
        history: List[Tuple[date, DoctrineMetrics]] = []
        for line in PERFORMANCE_LOG_PATH.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            try:
                entry_date = datetime.fromisoformat(payload["date"]).date()
            except Exception:
                continue
            if up_to and entry_date > up_to:
                continue
            metrics_payload = payload.get("metrics") or {}
            history.append((entry_date, DoctrineMetrics.from_dict(metrics_payload)))
        history.sort(key=lambda item: item[0])
        if limit > 0:
            history = history[-limit:]
        return history

    def _previous_metrics(self, current_date: date) -> Optional[DoctrineMetrics]:
        history = self._load_metric_history(limit=7, up_to=current_date - timedelta(days=1))
        if not history:
            return None
        return history[-1][1]

    def _describe_trend(
        self,
        values: List[float],
        unit: str = "",
        scale: float = 1.0,
        precision: int = 2,
    ) -> str:
        if not values:
            return "n/a"
        start_value = values[0] * scale
        end_value = values[-1] * scale
        delta = end_value - start_value
        suffix = unit or ""
        if suffix and not suffix.startswith(" "):
            suffix = f" {suffix}"
        if delta > 0:
            direction = "UP"
        elif delta < 0:
            direction = "DOWN"
        else:
            direction = "FLAT"
        return (
            f"{direction} {delta:+.{precision}f}{suffix} "
            f"({start_value:.{precision}f}{suffix} -> {end_value:.{precision}f}{suffix})"
        )

    def _emit_alert_notice(self, target_date: date, messages: List[str]) -> None:
        if not messages:
            return
        alert_path = Path("logs/DoctrineAlerts.log")
        alert_path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).isoformat()
        joined = "; ".join(messages)
        with alert_path.open("a", encoding="utf-8") as handle:
            handle.write(f"{timestamp} [{target_date:%Y-%m-%d}] {joined}\n")
        try:
            print(f"[DoctrineFeedbackLoop] ALERT {target_date:%Y-%m-%d}: {joined}")
        except Exception:
            pass

    def _humanize_key(self, key: str) -> str:
        parts = []
        for fragment in key.split("_"):
            if fragment.upper() in {"USD", "MS", "PNL"}:
                parts.append(fragment.upper())
            else:
                parts.append(fragment.capitalize())
        return " ".join(parts)

    def _format_value(self, key: str, value: float) -> str:
        if key.endswith("_percent"):
            return f"{value:.2f} %"
        if key.endswith("_usd"):
            return f"{value:.2f} USD"
        if float(value).is_integer():
            return f"{int(value)}"
        return f"{value:.2f}"

    def _format_delta(self, key: str, delta: float) -> str:
        if key.endswith("_percent"):
            return f"{delta:+.2f} %"
        if key.endswith("_usd"):
            return f"{delta:+.2f} USD"
        return f"{delta:+.2f}"

    def _build_adaptive_shift_line(
        self,
        suggestions: Dict[str, float],
        previous_parameters: Dict[str, Any],
    ) -> str:
        if not suggestions:
            return "Adaptive Shift: None"
        parts: List[str] = []
        for key, value in suggestions.items():
            label = self._humanize_key(key)
            prev_value = previous_parameters.get(key)
            if isinstance(prev_value, (int, float)):
                delta = value - float(prev_value)
                parts.append(f"{label} {self._format_delta(key, delta)}")
            else:
                parts.append(f"{label} -> {self._format_value(key, value)}")
        return "Adaptive Shift: " + " | ".join(parts)

    def _build_proposal_summary(
        self,
        suggestions: Dict[str, float],
        reasoning: Dict[str, str],
    ) -> str:
        if not suggestions:
            return "AI Proposal -> Hold doctrine parameters"
        key, value = next(iter(suggestions.items()))
        label = self._humanize_key(key)
        reason = reasoning.get(key, "").strip()
        change = self._format_value(key, value)
        summary = f"AI Proposal -> Adjust {label} to {change}"
        if reason:
            summary += f" ({reason})"
        return summary

    def _next_day_recommendation(
        self,
        suggestions: Dict[str, float],
        reasoning: Dict[str, str],
    ) -> str:
        if not suggestions:
            return "Next Day Recommendation:\nHold current doctrine; monitor key metrics."
        lines = ["Next Day Recommendation:"]
        for key, value in suggestions.items():
            reason = reasoning.get(key, "Monitor outcome.")
            lines.append(f"- {self._humanize_key(key)} -> {self._format_value(key, value)} :: {reason}")
        return "\n".join(lines)

    def _build_notes(
        self,
        metrics: DoctrineMetrics,
        previous: Optional[DoctrineMetrics],
        alerts: List[str],
    ) -> List[str]:
        notes: List[str] = []
        if previous:
            delta_sharpe = metrics.sharpe - previous.sharpe
            if abs(delta_sharpe) >= 0.05:
                direction = "improved" if delta_sharpe > 0 else "declined"
                notes.append(f"Sharpe {direction} by {delta_sharpe:+.2f} vs prior doctrine.")
            delta_win = metrics.win_rate - previous.win_rate
            if abs(delta_win) >= 1.0:
                direction = "higher" if delta_win > 0 else "lower"
                notes.append(f"Win rate {direction} at {metrics.win_rate:.1f} % ({delta_win:+.1f} pts).")
        if metrics.mean_latency_ms >= 600.0:
            notes.append(f"Latency elevated at {metrics.mean_latency_ms:.0f} ms; consider load shed.")
        if metrics.max_drawdown * 100 >= 2.0:
            notes.append(f"Drawdown registered at {metrics.max_drawdown*100:.1f} %; verify risk ladders.")
        for alert in alerts:
            notes.append(f"ALERT :: {alert}")
        if not notes:
            notes.append("System operating within expected bands.")
        return notes



    def learning_enabled(self) -> bool:
        return bool(self.governance_state.get("learning_mode", True))

    def record_health_result(self, passed: bool) -> None:
        state = self.governance_state
        if passed:
            state["consecutive_failures"] = 0
        else:
            state["consecutive_failures"] = state.get("consecutive_failures", 0) + 1
            if state["consecutive_failures"] >= 3:
                state["learning_mode"] = False
        self.governance_state = state
        _save_governance_state(state)

    def reset_learning(self) -> None:
        state = self.governance_state
        state["learning_mode"] = True
        state["consecutive_failures"] = 0
        _save_governance_state(state)

    @staticmethod
    def record_accepted_update(payload: dict) -> None:
        state = _load_governance_state()
        state['learning_mode'] = True
        state['consecutive_failures'] = 0
        suggestions = payload.get('suggestions') or {}
        state['last_parameters'] = suggestions
        state['last_accepted_date'] = payload.get('date')

        changes_today = state.get('changes_today') or {}
        date_key = payload.get('date')
        if date_key:
            changes_today[date_key] = changes_today.get(date_key, 0) + len(suggestions)
            state['changes_today'] = _prune_change_history(changes_today)
        else:
            state['changes_today'] = changes_today

        _save_governance_state(state)
        _record_history(payload)

    @staticmethod
    def get_last_good_doctrine() -> Optional[dict]:
        history_files = sorted(DOCTRINE_HISTORY_DIR.glob('*.json'))
        for history_path in reversed(history_files):
            try:
                payload = json.loads(history_path.read_text(encoding='utf-8'))
            except Exception:
                continue
            if payload.get('accepted'):
                payload['_history_path'] = str(history_path)
                return payload
        return None

    @staticmethod
    def rollback_last_good() -> Path:
        payload = DoctrineFeedbackLoop.get_last_good_doctrine()
        if not payload:
            raise FileNotFoundError('No doctrine history available for rollback.')
        payload = dict(payload)
        payload.pop('_history_path', None)
        payload['accepted'] = True
        payload['reviewed_at'] = datetime.now(timezone.utc).isoformat()
        payload['reviewer'] = payload.get('reviewer') or 'rollback'
        update_path = DOCTRINE_UPDATE_DIR / f"doctrine_update_{payload['date']}_rollback.json"
        update_path.write_text(json.dumps(payload, indent=2), encoding='utf-8')
        DoctrineFeedbackLoop.record_accepted_update(payload)
        return update_path

    # ------------------------------------------------------------------
    # Metric consolidation
    # ------------------------------------------------------------------
    def _load_snapshot(self) -> Dict[str, Any]:
        payload = _read_json(self.snapshot_path) or {}
        if "blocks" not in payload:
            payload["blocks"] = {}
        return payload

    def _collect_latencies(self) -> List[float]:
        latency_log = Path("logs/V13_Latency.log")
        if not latency_log.exists():
            return []
        latencies: List[float] = []
        for line in latency_log.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("event") == "FILLED":
                latency = entry.get("since_ack_ms")
                try:
                    latencies.append(float(latency))
                except (TypeError, ValueError):
                    continue
        return latencies

    def _validate_audit_seal(self) -> None:
        seal_path = Path("logs/GLOBAL_SEAL.txt")
        if not seal_path.exists():
            raise FileNotFoundError("Audit seal file missing.")
        lines = [line.strip() for line in seal_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        entries: List[bytes] = []
        composite_expected: Optional[str] = None
        for line in lines:
            if line.startswith("COMPOSITE "):
                composite_expected = line.split(" ", 1)[1]
                continue
            parts = line.rsplit(" ", 1)
            if len(parts) != 2:
                raise ValueError("Malformed audit seal entry.")
            file_path = Path(parts[0])
            digest_expected = parts[1]
            if not file_path.exists():
                raise FileNotFoundError(f"Audit log missing: {file_path}")
            data = file_path.read_bytes()
            digest_actual = hashlib.sha256(data).hexdigest()
            if digest_expected != digest_actual:
                raise ValueError(f"Audit seal mismatch for {file_path}")
            entries.append(data)
        if composite_expected is not None:
            composite = hashlib.sha256()
            for blob in entries:
                composite.update(blob)
            if composite.hexdigest() != composite_expected:
                raise ValueError("Composite audit seal mismatch.")

    def _compile_metrics_from_snapshot(self, snapshot: Dict[str, Any]) -> DoctrineMetrics:
        trades: List[Dict[str, Any]] = []
        returns: List[float] = []
        lock_profits: List[float] = []
        correlations: List[float] = []

        for block_data in (snapshot.get("blocks") or {}).values():
            trades.extend(block_data.get("trades", []))
            returns.extend(block_data.get("returns", []))
            lock_profits.extend(block_data.get("lock_profits", []))
            if "correlation" in block_data:
                correlations.append(block_data["correlation"])

        wins = [1 for trade in trades if trade.get("win") or trade.get("pnl", 0) > 0]
        durations = [float(trade.get("duration", 0)) for trade in trades if trade.get("duration") is not None]
        slippage = [float(trade.get("slippage", 0)) for trade in trades if trade.get("slippage") is not None]
        latency_samples = self._collect_latencies()

        sharpe = 0.0
        if returns:
            mean_return = _safe_mean(returns)
            std_return = _safe_stddev(returns)
            if std_return > 0:
                sharpe = mean_return / std_return

        max_dd = _max_drawdown(returns) if returns else 0.0
        win_rate = (sum(wins) / len(trades) * 100.0) if trades else 0.0
        avg_lock_profit = _safe_mean(lock_profits)
        correlation = _safe_mean(correlations)
        mean_latency = _safe_mean(latency_samples)

        slippage_mean = _safe_mean(slippage)
        slippage_p95 = 0.0
        if slippage:
            sorted_slippage = sorted(slippage)
            index = min(len(sorted_slippage) - 1, int(len(sorted_slippage) * 0.95))
            slippage_p95 = sorted_slippage[index]

        metrics = DoctrineMetrics(
            sharpe=sharpe,
            win_rate=win_rate,
            average_lock_profit=avg_lock_profit,
            correlation=correlation,
            mean_latency_ms=mean_latency,
            max_drawdown=max_dd,
            slippage_mean=slippage_mean,
            slippage_p95=slippage_p95,
            trades=len(trades),
        )
        return metrics

    def collect_daily_metrics(self, target_date: Optional[date] = None) -> DoctrineMetrics:
        snapshot = self._load_snapshot()
        metrics = self._compile_metrics_from_snapshot(snapshot)
        self._persist_metrics_snapshot(metrics, target_date)
        return metrics

    def _persist_metrics_snapshot(self, metrics: DoctrineMetrics, target_date: Optional[date]) -> None:
        payload = {
            "date": (target_date or date.today()).isoformat(),
            "metrics": metrics.as_dict(),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        PERFORMANCE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with PERFORMANCE_LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")

    # ------------------------------------------------------------------
    # Doctrine reporting
    # ------------------------------------------------------------------
    def _report_path(self, target_date: Optional[date]) -> Path:
        day = (target_date or date.today()).strftime("%Y-%m-%d")
        return self.report_dir / f"{day}.txt"

    def generate_doctrine_report(
        self,
        metrics: Optional[DoctrineMetrics] = None,
        target_date: Optional[date] = None,
    ) -> Path:
        report_date = target_date or date.today()
        metrics = metrics or self.collect_daily_metrics(report_date)
        report_path = self._report_path(report_date)
        report_path.parent.mkdir(parents=True, exist_ok=True)

        context = self._extract_config_context()
        snapshot = self._load_snapshot()
        blocks = len(snapshot.get('blocks', {}))

        update_payload = self._load_doctrine_update(report_date)
        if update_payload:
            suggestions = {k: float(v) for k, v in (update_payload.get('suggestions') or {}).items()}
            reasoning = update_payload.get('reasoning') or {}
        else:
            suggestions, reasoning = self._compute_suggestions(metrics)

        previous_metrics = self._previous_metrics(report_date)

        audit_status = 'Verified'
        alerts: List[str] = []
        try:
            self._validate_audit_seal()
        except FileNotFoundError:
            audit_status = 'Missing'
            alerts.append('Audit seal file missing')
        except Exception as exc:
            audit_status = 'FAILED'
            alerts.append(f'Audit seal check failed ({exc})')

        if previous_metrics and previous_metrics.sharpe:
            sharpe_drop = ((previous_metrics.sharpe - metrics.sharpe) / abs(previous_metrics.sharpe)) * 100
            if sharpe_drop > 25.0:
                alerts.append(f'Sharpe drop {sharpe_drop:.1f} % vs prior day')

        drawdown_limit = None
        cfg_path = Path('config/V13_Config.ini')
        if cfg_path.exists():
            try:
                cfg = configparser.ConfigParser(inline_comment_prefixes=(';', '#'))
                cfg.read(cfg_path)
                drawdown_limit = cfg.getfloat('Risk', 'Max_Drawdown_Percent', fallback=None)
            except Exception:
                drawdown_limit = None
        if drawdown_limit is not None and metrics.max_drawdown * 100 > drawdown_limit:
            alerts.append(f'Drawdown exceeded limit ({metrics.max_drawdown*100:.1f} % > {drawdown_limit:.1f} %)')

        header = f"Doctrine Report - {report_date:%Y-%m-%d}"
        if alerts:
            header = f"[ALERT] {header}"

        border = '-' * 80
        sharpe_vs_prev = 'n/a'
        if previous_metrics:
            if previous_metrics.sharpe == 0:
                sharpe_vs_prev = 'n/a'
            else:
                delta_pct = ((metrics.sharpe - previous_metrics.sharpe) / abs(previous_metrics.sharpe)) * 100
                sharpe_vs_prev = f'{delta_pct:+.1f} %'

        commander_decision = self._load_commander_decision(report_date)
        if commander_decision is None:
            verdict = 'Pending review'
        else:
            verdict = 'Approved' if commander_decision.get('accepted') else 'Rejected'

        adaptive_shift_line = self._build_adaptive_shift_line(suggestions, self.governance_state.get('last_parameters', {}))
        proposal_summary = self._build_proposal_summary(suggestions, reasoning)

        notes = self._build_notes(metrics, previous_metrics, alerts)
        recommendation_block = self._next_day_recommendation(suggestions, reasoning)

        content: List[str] = [
            border,
            header,
            border,
            f"Mode: {context['mode']:<12} Blocks: {blocks:<3} Feed: {context['feed']} ({context['run_env']})",
            f"Sharpe Ratio: {metrics.sharpe:>7.4f}   Win Rate: {metrics.win_rate:>6.2f} %   Avg DD: {-metrics.max_drawdown*100:>6.2f} %",
            f"Avg Latency: {metrics.mean_latency_ms:>7.2f} ms   Avg Slippage: {metrics.slippage_mean*100:>5.2f} %   Trades: {metrics.trades}",
            adaptive_shift_line,
            proposal_summary,
            f"Commander Verdict -> {verdict}",
            f"Performance vs Previous Doctrine: {sharpe_vs_prev}",
            f"Audit Seal: {audit_status}",
            border,
            'Notes:',
        ]

        content.extend(f'- {line}' for line in notes)
        content.append(border)
        content.append(recommendation_block)
        content.append(border)

        report_path.write_text("\n".join(content) + "\n", encoding="utf-8")

        self._emit_alert_notice(report_date, alerts)
        self._maybe_generate_weekly_summary(report_date)
        return report_path

    def _maybe_generate_weekly_summary(self, report_date: date) -> Optional[Path]:
        iso_year, iso_week, _ = report_date.isocalendar()
        summary_path = self.report_dir / f"weekly_summary_{iso_year}-W{iso_week:02d}.txt"
        history = self._load_metric_history(7, up_to=report_date)
        if summary_path.exists():
            return summary_path
        if len(history) < 7:
            return None
        if (report_date - history[0][0]).days < 6:
            return None
        return self.generate_weekly_summary(report_date, history)

    def generate_weekly_summary(
        self,
        report_date: Optional[date] = None,
        history: Optional[List[Tuple[date, DoctrineMetrics]]] = None,
    ) -> Path:
        report_date = report_date or date.today()
        history = history or self._load_metric_history(7, up_to=report_date)
        if not history:
            raise ValueError("No daily doctrine reports available for weekly summary.")
        history.sort(key=lambda item: item[0])
        start_day = history[0][0]
        end_day = history[-1][0]
        iso_year, iso_week, _ = report_date.isocalendar()
        summary_path = self.report_dir / f"weekly_summary_{iso_year}-W{iso_week:02d}.txt"
        summary_path.parent.mkdir(parents=True, exist_ok=True)

        sharpe_values = [m.sharpe for _, m in history]
        win_values = [m.win_rate for _, m in history]
        drawdown_values = [m.max_drawdown * 100 for _, m in history]
        lock_profit_values = [m.average_lock_profit for _, m in history]
        correlation_values = [m.correlation for _, m in history]

        border = "-" * 88
        lines = [
            border,
            f"Weekly Doctrine Summary - {iso_year}-W{iso_week:02d}",
            border,
            f"Span: {start_day:%Y-%m-%d} -> {end_day:%Y-%m-%d} ({len(history)} days)",
            f"Sharpe Trend: {self._describe_trend(sharpe_values, precision=3)}",
            f"Win Rate Trend: {self._describe_trend(win_values, unit='%', precision=2)}",
            f"Drawdown Trend: {self._describe_trend(drawdown_values, unit='%', precision=2)}",
            f"AI Update Impact (avg lock profit): {self._describe_trend(lock_profit_values, precision=4)}",
            f"Block Correlation Trend: {self._describe_trend(correlation_values, precision=3)}",
            border,
            "Daily Snapshots:",
        ]

        for day, metric in history:
            lines.append(
                f"- {day:%Y-%m-%d} | Sharpe {metric.sharpe:.3f} | Win {metric.win_rate:.2f} % "
                f"| DD {metric.max_drawdown*100:.2f} % | Corr {metric.correlation:.3f}"
            )

        lines.append(border)
        lines.append("Notes:")
        if len(history) < 7:
            lines.append("- Fewer than seven daily reports available; trend precision limited.")
        if sharpe_values and max(sharpe_values) - min(sharpe_values) <= 0.05:
            lines.append("- Sharpe remained stable across the period.")
        if drawdown_values and max(drawdown_values) > 3.0:
            lines.append("- Drawdown breached 3% threshold; review risk posture.")
        if correlation_values and min(correlation_values) < 0.3:
            lines.append("- Block correlation dipped below 0.30; investigate block alignment.")
        if lines[-1] == "Notes:":
            lines.append("- No anomalies detected across the sampled week.")
        lines.append(border)

        summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return summary_path

    def _compute_suggestions(self, metrics: DoctrineMetrics) -> tuple[Dict[str, float], Dict[str, str]]:
        suggestions: Dict[str, float] = {}
        reasoning: Dict[str, str] = {}

        if metrics.sharpe < 1.0:
            suggested_stop = round(max(1.0, 3.0 * metrics.sharpe), 2)
            suggestions["Assassin_stop_usd"] = suggested_stop
            reasoning["Assassin_stop_usd"] = "Sharpe < 1.0 with elevated volatility"

        if metrics.win_rate < 55.0:
            suggested_trail = round(max(4.0, min(8.0, 5.0 + (55.0 - metrics.win_rate) / 5.0)), 2)
            suggestions["Avenger_trail_percent"] = suggested_trail
            reasoning["Avenger_trail_percent"] = "Win rate below 55%; extend trail to protect profits"

        if metrics.mean_latency_ms > 600.0:
            concurrency = max(1, int(6 - (metrics.mean_latency_ms / 200.0)))
            suggestions["Block_concurrency"] = concurrency
            reasoning["Block_concurrency"] = "Latency drift above 600ms; reduce load"

        if not suggestions:
            reasoning["Doctrine"] = "Metrics within targets; hold parameters"

        # enforce maximum of three suggestions
        if len(suggestions) > 3:
            limited = dict(list(suggestions.items())[:3])
            suggestions = limited
        if len(reasoning) > 3:
            reasoning = dict(list(reasoning.items())[:3])
        return suggestions, reasoning

    def _enforce_rate_limits(self, day: str, suggestions: Dict[str, float], reasoning: Dict[str, str]) -> Dict[str, float]:
        state = self.governance_state
        if "changes_today" not in state:
            state["changes_today"] = {}
        changes_today = state["changes_today"]
        already = int(changes_today.get(day, 0) or 0)
        allowance = max(0, 3 - already)

        limited: Dict[str, float] = {}
        if allowance <= 0:
            if suggestions:
                reasoning["rate_limit"] = "Daily parameter change limit reached; holding doctrine parameters."
            self.governance_state = state
            return limited

        last_params = state.get("last_parameters", {})
        for key, value in suggestions.items():
            if len(limited) >= allowance:
                break
            prev = last_params.get(key)
            if prev is not None:
                max_delta = max(abs(prev) * 0.25, 0.25)
                delta = value - prev
                if abs(delta) > max_delta:
                    value = round(prev + (max_delta if delta > 0 else -max_delta), 4)
                    note = reasoning.get(key, "")
                    reasoning[key] = (note + " (clamped to 25%)").strip()
            limited[key] = value

        if len(suggestions) > allowance:
            reasoning["rate_limit"] = f"Daily limit allows {allowance} change(s); additional suggestions deferred."

        self.governance_state = state
        return limited

    def _generate_suggestions(self, metrics: DoctrineMetrics) -> List[str]:
        suggestions, reasoning = self._compute_suggestions(metrics)
        lines: List[str] = []
        for key, value in suggestions.items():
            reason = reasoning.get(key, "")
            label = key.replace('_', ' ').title()
            lines.append(f"{label} -> {value} ({reason})")
        if not lines:
            lines.append("Metrics healthy :: maintain doctrine parameters")
        return lines

    def record_commander_decision(self, accepted: bool, notes: str = "", target_date: Optional[date] = None) -> Path:
        path = self.decisions_dir / f"{(target_date or date.today()):%Y-%m-%d}.json"
        payload = {
            "date": (target_date or date.today()).isoformat(),
            "accepted": bool(accepted),
            "notes": notes,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    def generate_doctrine_update(
        self,
        metrics: Optional[DoctrineMetrics] = None,
        target_date: Optional[date] = None,
    ) -> Path:
        metrics = metrics or self.collect_daily_metrics(target_date)
        self._validate_audit_seal()
        day = (target_date or date.today()).isoformat()
        suggestions, reasoning = self._compute_suggestions(metrics)
        suggestions = self._enforce_rate_limits(day, suggestions, reasoning)
        payload = {
            "date": day,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "suggestions": suggestions,
            "reasoning": reasoning,
            "accepted": False,
            "reviewed_at": None,
            "reviewer": None,
            "source": "V13_DoctrineFeedbackLoop",
        }
        update_path = self.update_dir / f"doctrine_update_{day}.json"
        update_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return update_path

    # ------------------------------------------------------------------
    # Dual-layer feedback (legacy interface)
    # ------------------------------------------------------------------
    def generate_dual_feedback(self, command: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        ack = {
            "layer": "ACK",
            "command": command,
            "status": "ACK OK",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "origin": "CommandMatrix",
        }
        doctrine = {
            "doctrine_name": self._resolve_doctrine_name(command),
            "advice": self._contextual_advice(command, params),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        feedback = {
            "dual_layer": True,
            "ack": ack,
            "doctrine": doctrine,
            "full_response": f"{ack['status']} | {doctrine['advice']}",
        }
        self._emit_feedback_event(feedback)
        return feedback

    def analyze(self, packet: Dict[str, Any]) -> Dict[str, Any]:
        command = packet.get("cmd_text", "")
        feedback = {
            "command": command,
            "advice": self._contextual_advice(command, packet),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._emit_feedback_event({"analysis": feedback})
        return feedback

    def _emit_feedback_event(self, payload: Dict[str, Any]) -> None:
        try:
            from core.V13_SyncLoop import emit_event
            emit_event("CMD_FEEDBACK", payload)
        except ImportError:
            pass

    def _resolve_doctrine_name(self, command: str) -> str:
        for doctrine in self.doctrines.values():
            doc_name = doctrine["data"].get("Doctrine_Name")
            if not doc_name:
                continue
            if "Assassin" in doc_name and command in {"tighten B", "lock A"}:
                return doc_name
            if "Avenger" in doc_name and command in {"redeploy A", "unlock B"}:
                return doc_name
        if self.doctrines:
            return next(iter(self.doctrines.values()))["data"].get("Doctrine_Name", "Unknown")
        return "Unknown"

    def _contextual_advice(self, command: str, params: Optional[Dict[str, Any]]) -> str:
        match command:
            case "tighten B":
                return "Assassins tighten trail by 0.5% and monitor volatility."
            case "lock A":
                return "Locking positions :: hold Avengers until trend resumes."
            case "redeploy A":
                return "Avengers redeployed with extended trail."
            case "unlock B":
                return "Unlocking Assassin flank :: restore base allocation."
            case _:
                return "Command acknowledged. Doctrine standing by."


def _cli() -> None:
    parser = argparse.ArgumentParser(description='Doctrine feedback governance utilities.')
    parser.add_argument('--reset', action='store_true', help='Reset learning lockout.')
    parser.add_argument('--authorize', action='store_true', help='Authorize learning after reset.')
    parser.add_argument('--rollback', choices=['last_good'], help='Rollback to last accepted doctrine.')
    args = parser.parse_args()
    if args.reset and not args.authorize:
        raise SystemExit('Use --reset with --authorize to re-enable learning.')
    if args.reset and args.authorize:
        loop = DoctrineFeedbackLoop(load_doctrines_flag=False)
        loop.reset_learning()
        print('Learning mode re-enabled.')
        return
    if args.rollback == 'last_good':
        path = DoctrineFeedbackLoop.rollback_last_good()
        print(f'Rollback update created: {path}')
        return
    parser.print_help()


if __name__ == '__main__':
    _cli()
