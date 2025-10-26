import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import utils

from core.V13_PerformanceAnalytics import PerformanceAnalytics, SUMMARY_PATH
from core.V13_DoctrineFeedbackLoop import DoctrineFeedbackLoop
from core.V13_ReplayEngine import ReplayEngine, _default_parameter_sets
from core.V13_RLAgent import ReinforcementLearner
from V13_CommandMatrix import V13_CommandMatrix


TEST_MODULES = [
    "test_latency",
    "test_risk_caps",
    "test_sync_integrity",
    "test_adaptive_weights",
    "test_audit_hash",
]


def run_tests() -> dict:
    results: dict[str, dict] = {}
    python_exe = sys.executable
    for module in TEST_MODULES:
        module_name = f"tests.phase8_healthcheck.{module}"
        proc = subprocess.run(
            [python_exe, "-m", module_name],
            capture_output=True,
            text=True,
        )
        report_path = utils.REPORTS_DIR / f"{module}.json"
        report_payload = utils.load_json(report_path) or {}
        results[module] = {
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            "report": report_payload,
        }
    return results


def summarise(results: dict) -> dict:
    status_priority = {"FAIL": 2, "WARN": 1, "PASS": 0}
    aggregate_status = "PASS"
    for report in results.values():
        status = (report.get("report") or {}).get("status")
        if status and status_priority.get(status, 0) > status_priority.get(aggregate_status, 0):
            aggregate_status = status
    now_utc = datetime.now(timezone.utc)
    return {
        "status": aggregate_status,
        "as_of": now_utc.isoformat(),
        "tests": results,
    }


def run_performance_analytics(summary: dict) -> None:
    try:
        analytics = PerformanceAnalytics()
        results = analytics.analyse()
        summary['performance_summary'] = {
            'blocks': len(results),
            'path': str(SUMMARY_PATH),
        }
    except FileNotFoundError as exc:
        summary['performance_summary_error'] = f'snapshot missing: {exc}'
    except Exception as exc:  # pragma: no cover - defensive
        summary['performance_summary_error'] = f'analytics failed: {exc}'


def run_replay_engine(summary: dict) -> None:
    try:
        engine = ReplayEngine()
        results = engine.run_replay(_default_parameter_sets())
        summary['replay_results'] = {
            'count': len(results),
            'path': str(engine.results_path),
        }
    except FileNotFoundError as exc:
        summary['replay_error'] = f'analytics missing: {exc}'
    except Exception as exc:
        summary['replay_error'] = f'replay failed: {exc}'



def run_reinforcement_learning(summary: dict, metrics: dict | None) -> None:
    if not metrics:
        summary['rl_error'] = 'metrics unavailable'
        return
    try:
        agent = ReinforcementLearner()
        result = agent.learn_from_metrics(metrics)
        summary['rl_actions'] = result.actions
        summary['rl_reward'] = round(result.reward, 4)
        summary['rl_policy'] = str(agent.policy_path)
    except Exception as exc:
        summary['rl_error'] = f'rl failed: {exc}'

def run_doctrine_feedback(summary: dict, status: str) -> dict | None:
    try:
        loop = DoctrineFeedbackLoop(load_doctrines_flag=False)
        loop.record_health_result(status == "PASS")
        summary['learning_mode'] = loop.learning_enabled()
        summary['consecutive_failures'] = loop.governance_state.get('consecutive_failures', 0)
        today_key = datetime.now(timezone.utc).date().isoformat()
        changes_today = int(loop.governance_state.get('changes_today', {}).get(today_key, 0) or 0)
        summary['daily_changes'] = changes_today
        summary['daily_change_allowance'] = max(0, 3 - changes_today)
        summary['last_accepted_date'] = loop.governance_state.get('last_accepted_date')
        if not loop.learning_enabled():
            summary["doctrine_feedback"] = "learning disabled"
            return None
        metrics = loop.collect_daily_metrics()
        report_path = loop.generate_doctrine_report(metrics)
        update_path = loop.generate_doctrine_update(metrics)
        summary['doctrine_report'] = str(report_path)
        summary['doctrine_update'] = str(update_path)
        return {
            'sharpe': metrics.sharpe,
            'win_rate': metrics.win_rate,
            'mean_latency_ms': metrics.mean_latency_ms,
            'max_drawdown': metrics.max_drawdown,
            'correlation': metrics.correlation,
        }
    except FileNotFoundError as exc:
        summary['doctrine_feedback_error'] = f'snapshot missing: {exc}'
    except Exception as exc:  # pragma: no cover - defensive
        summary['doctrine_feedback_error'] = f'doctrine feedback failed: {exc}'
    return None


def main() -> None:
    utils.ensure_reports_dir()
    try:
        matrix = V13_CommandMatrix()
        matrix._write_global_audit_seal()
    except Exception:
        pass
    results = run_tests()
    summary = summarise(results)
    run_performance_analytics(summary)
    run_replay_engine(summary)
    doctrine_metrics = run_doctrine_feedback(summary, summary["status"])
    run_reinforcement_learning(summary, doctrine_metrics)

    metrics_path = utils.todays_report_path('health')
    metrics_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    now_utc = datetime.now(timezone.utc)
    condensed = {
        "date": now_utc.strftime("%Y-%m-%d"),
        "status": summary["status"],
        "tests": {name: data.get("report", {}).get("status") for name, data in results.items()},
    }
    utils.append_daily_metrics(condensed)
    print(summary["status"])


if __name__ == "__main__":
    main()
