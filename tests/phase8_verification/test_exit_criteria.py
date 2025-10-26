from pathlib import Path
import hashlib
import json
from core.V13_DoctrineFeedbackLoop import DoctrineFeedbackLoop
from scripts.check_phase8_exit import evaluate_phase8_exit
import unittest
import shutil
import os

class Phase8ExitCriteriaTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_root = Path("tmp_exit_check")
        if self.temp_root.exists():
            shutil.rmtree(self.temp_root)
        self.temp_root.mkdir()
        (self.temp_root / "reports" / "health").mkdir(parents=True)
        (self.temp_root / "logs" / "block_01").mkdir(parents=True)
        (self.temp_root / "logs" / "block_02").mkdir(parents=True)
        (self.temp_root / "data").mkdir(parents=True)
        (self.temp_root / "docs" / "DoctrineDecisions").mkdir(parents=True)
        # metrics
        metrics = []
        for i in range(28):
            metrics.append({"date": f"2025-09-{i+1:02d}", "status": "PASS"})
        metrics_path = self.temp_root / "reports" / "health" / "metrics_daily.jsonl"
        metrics_path.write_text("\n".join(json.dumps(e) for e in metrics) + "\n", encoding="utf-8")
        # global seal
        entries = []
        composite = hashlib.sha256()
        for idx in (1, 2):
            block_path = self.temp_root / "logs" / f"block_0{idx}" / "V13_SessionAudit.log"
            data = f"block{idx} line\n".encode("utf-8")
            block_path.write_bytes(data)
            digest = hashlib.sha256(data).hexdigest()
            entries.append((block_path, digest, data))
        seal_lines = []
        for path, digest, data in entries:
            seal_lines.append(f"{path} {digest}")
            composite.update(data)
        seal_lines.append(f"COMPOSITE {composite.hexdigest()}")
        (self.temp_root / "logs" / "GLOBAL_SEAL.txt").write_text("\n".join(seal_lines) + "\n", encoding="utf-8")
        # status
        status_payload = {
            "global": {
                "total_capital": 10000,
                "pnl": 980,
                "weighted_drawdown": 2.0,
                "max_cap": 5.0,
            }
        }
        (self.temp_root / "data" / "V13_Status.json").write_text(json.dumps(status_payload), encoding="utf-8")
        # baseline
        baseline_payload = {
            "expected_pnl": 1000,
            "sealed_pnl": 980,
            "tolerance_pct": 5.0,
        }
        (self.temp_root / "data" / "performance_baseline.json").write_text(json.dumps(baseline_payload), encoding="utf-8")
        # doctrine decision
        decision_payload = {
            "date": "2025-10-22",
            "accepted": True,
            "notes": "All good",
            "recorded_at": "2025-10-22T00:00:00"
        }
        (self.temp_root / "docs" / "DoctrineDecisions" / "2025-10-22.json").write_text(json.dumps(decision_payload), encoding="utf-8")

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_root)

    def test_exit_evaluation_passes(self):
        status, results = evaluate_phase8_exit(self.temp_root)
        self.assertTrue(status)
        self.assertTrue(all(r.passed for r in results))

if __name__ == '__main__':
    unittest.main()
