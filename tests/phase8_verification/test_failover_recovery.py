import json
import time
import unittest
from pathlib import Path

from core import V13_SyncLoop


class FailoverRecoveryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.orders_path = Path("data/orders_snapshot.json")
        self.positions_path = Path("data/positions.json")
        self.logs_dir = Path("logs")
        self._cleanup_logs()
        self.orders_path.parent.mkdir(parents=True, exist_ok=True)
        self.orders_path.write_text(
            json.dumps(
                [
                    {
                        "id": "TEST-ORDER-1",
                        "status": "new",
                        "symbol": "SPY",
                        "qty": 1,
                        "side": "buy",
                    }
                ]
            ),
            encoding="utf-8",
        )
        self.positions_path.write_text(
            json.dumps(
                [
                    {
                        "symbol": "SPY",
                        "qty": 1,
                        "market_price": 420.5,
                        "market_value": 420.5,
                    }
                ]
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        if self.orders_path.exists():
            self.orders_path.unlink()
        if self.positions_path.exists():
            self.positions_path.unlink()
        self._cleanup_logs()

    def _cleanup_logs(self) -> None:
        for path in self.logs_dir.glob("recover_*.log"):
            path.unlink()

    def test_sync_loop_recovery_executes_under_fifteen_seconds(self) -> None:
        start = time.time()
        V13_SyncLoop.restore_runtime_state()
        elapsed = time.time() - start
        self.assertLess(elapsed, 15.0, "Recovery exceeded expected timeframe")

        recover_logs = list(self.logs_dir.glob("recover_*.log"))
        self.assertTrue(recover_logs, "Recovery log not written")
        payload = json.loads(recover_logs[0].read_text(encoding="utf-8"))
        self.assertIn("orders_restored", payload)
        self.assertIn("positions_restored", payload)
        self.assertIn("TEST-ORDER-1", payload["orders_restored"])


if __name__ == "__main__":
    unittest.main()
