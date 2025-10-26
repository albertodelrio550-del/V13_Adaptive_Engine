import json
import unittest
from datetime import date, timedelta
from pathlib import Path

import core.V13_DoctrineFeedbackLoop as loop_module
from core.V13_DoctrineFeedbackLoop import DoctrineFeedbackLoop, DoctrineMetrics
from V13_CommandMatrix import V13_CommandMatrix


class DoctrineFeedbackLoopTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path("tmp_doctrine")
        self.temp_dir.mkdir(exist_ok=True)
        self.snapshot_path = self.temp_dir / "performance_snapshot.json"
        snapshot = {
            "blocks": {
                "BLOCK1": {
                    "returns": [0.02, -0.01, 0.03],
                    "trades": [
                        {"pnl": 12.0, "win": True, "duration": 45, "slippage": 0.02},
                        {"pnl": -5.0, "win": False, "duration": 60, "slippage": 0.01},
                        {"pnl": 7.0, "win": True, "duration": 30, "slippage": 0.03},
                    ],
                    "lock_profits": [0.15, 0.1],
                    "correlation": 0.62,
                },
                "BLOCK2": {
                    "returns": [0.01, 0.015],
                    "trades": [
                        {"pnl": 5.0, "win": True, "duration": 40, "slippage": 0.015},
                        {"pnl": 4.0, "win": True, "duration": 35, "slippage": 0.02},
                    ],
                    "lock_profits": [0.08],
                    "correlation": 0.58,
                },
            }
        }
        self.snapshot_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
        self.original_perf_log = loop_module.PERFORMANCE_LOG_PATH
        self.original_governance_state = loop_module.GOVERNANCE_STATE_PATH
        loop_module.PERFORMANCE_LOG_PATH = self.temp_dir / "performance_metrics.jsonl"
        loop_module.GOVERNANCE_STATE_PATH = self.temp_dir / "governance_state.json"
        self.loop = DoctrineFeedbackLoop(
            snapshot_path=self.snapshot_path,
            report_dir=self.temp_dir / "reports",
            decisions_dir=self.temp_dir / "decisions",
            update_dir=self.temp_dir / "updates",
            load_doctrines_flag=False,
        )

    def tearDown(self) -> None:
        loop_module.PERFORMANCE_LOG_PATH = self.original_perf_log
        loop_module.GOVERNANCE_STATE_PATH = self.original_governance_state
        for path in sorted(self.temp_dir.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            else:
                path.rmdir()
        self.temp_dir.rmdir()

    def test_collect_daily_metrics(self) -> None:
        metrics = self.loop.collect_daily_metrics()
        self.assertIsInstance(metrics, DoctrineMetrics)
        self.assertGreater(metrics.sharpe, 0)
        self.assertGreater(metrics.win_rate, 0)
        self.assertAlmostEqual(metrics.trades, 5)

    def test_generate_doctrine_report(self) -> None:
        metrics = DoctrineMetrics(
            sharpe=1.23,
            win_rate=61.5,
            average_lock_profit=0.12,
            correlation=0.55,
            mean_latency_ms=350.0,
            max_drawdown=0.08,
            slippage_mean=0.01,
            slippage_p95=0.02,
            trades=20,
        )
        report_date = date(2025, 10, 22)
        report_path = self.loop.generate_doctrine_report(metrics, report_date)
        self.assertTrue(report_path.exists())
        content = report_path.read_text(encoding="utf-8")
        self.assertIn("Doctrine Report - 2025-10-22", content)
        self.assertIn("Sharpe Ratio", content)
        self.assertIn("Next Day Recommendation", content)

    def test_generate_doctrine_update(self) -> None:
        metrics = DoctrineMetrics(
            sharpe=0.8,
            win_rate=52.0,
            average_lock_profit=0.1,
            correlation=0.5,
            mean_latency_ms=700.0,
            max_drawdown=0.2,
            slippage_mean=0.01,
            slippage_p95=0.02,
            trades=15,
        )
        update_path = self.loop.generate_doctrine_update(metrics, date(2025, 10, 22))
        payload = json.loads(update_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["date"], "2025-10-22")
        self.assertFalse(payload["accepted"])
        self.assertIn("Assassin_stop_usd", payload["suggestions"])
        self.assertIn("Avenger_trail_percent", payload["suggestions"])
        self.assertIn("Block_concurrency", payload["suggestions"])
        self.assertIn("Assassin_stop_usd", payload["reasoning"])

    def test_weekly_summary_compilation(self) -> None:
        base_date = date(2025, 10, 16)
        for offset in range(7):
            day = base_date + timedelta(days=offset)
            metrics = DoctrineMetrics(
                sharpe=1.0 + offset * 0.05,
                win_rate=55.0 + offset,
                average_lock_profit=0.1 + offset * 0.005,
                correlation=0.4 + offset * 0.02,
                mean_latency_ms=400.0,
                max_drawdown=0.02 + offset * 0.001,
                slippage_mean=0.01,
                slippage_p95=0.02,
                trades=10 + offset,
            )
            self.loop._persist_metrics_snapshot(metrics, day)
            self.loop.generate_doctrine_report(metrics, day)
        summary_path = self.loop.generate_weekly_summary(date(2025, 10, 22))
        self.assertTrue(summary_path.exists())
        content = summary_path.read_text(encoding="utf-8")
        self.assertIn("Weekly Doctrine Summary", content)
        self.assertIn("Sharpe Trend", content)

    def test_record_commander_decision(self) -> None:
        decision_path = self.loop.record_commander_decision(True, "Looks good", date(2025, 10, 22))
        payload = json.loads(decision_path.read_text(encoding="utf-8"))
        self.assertTrue(payload["accepted"])
        self.assertEqual(payload["notes"], "Looks good")

    def test_dual_feedback_interface(self) -> None:
        feedback = self.loop.generate_dual_feedback("tighten B", {"symbol": "SPY"})
        self.assertTrue(feedback["dual_layer"])
        self.assertIn("ack", feedback)
        self.assertIn("doctrine", feedback)
        analysis = self.loop.analyze({"cmd_text": "lock A"})
        self.assertIn("advice", analysis)

    def test_command_matrix_applies_update(self) -> None:
        update_dir = Path("docs/DoctrineUpdates")
        update_dir.mkdir(parents=True, exist_ok=True)
        update_path = update_dir / "doctrine_update_2030-01-01.json"
        payload = {
            "date": "2030-01-01",
            "generated_at": "2030-01-01T00:00:00+00:00",
            "suggestions": {"Assassin_stop_usd": 2.5},
            "reasoning": {"Assassin_stop_usd": "test"},
            "accepted": True,
            "reviewed_at": "2025-10-22T01:00:00+00:00",
            "reviewer": "Tester",
            "source": "test",
        }
        update_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        try:
            matrix = V13_CommandMatrix()
            applied = matrix.apply_approved_doctrine_update()
            self.assertEqual(applied, "2030-01-01")
        finally:
            if update_path.exists():
                update_path.unlink()


if __name__ == "__main__":
    unittest.main()
