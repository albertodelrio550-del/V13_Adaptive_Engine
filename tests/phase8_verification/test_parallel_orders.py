import json
import json
import os
import time
import unittest
from pathlib import Path

from tests.phase8_verification import utils


class ParallelOrderStressTest(unittest.TestCase):
    def setUp(self) -> None:
        latency_log = Path("logs/V13_Latency.log")
        if latency_log.exists():
            latency_log.unlink()
        self.matrix = utils.create_matrix(utils.AllowAllRiskGate())
        # Ensure a predictable number of blocks for the stress scenario
        for idx in range(1, 6):
            utils.ensure_block(self.matrix, f"BLOCK{idx}")

    def test_parallel_order_latency_under_five_hundred_ms(self) -> None:
        full_stress = os.getenv("V13_FULL_STRESS", "").lower() in {"1", "true", "yes", "on"}
        blocks_to_use = 5 if full_stress else 3
        orders_per_block = 20 if full_stress else 10

        blocks = list(self.matrix.blocks.keys())[:blocks_to_use]
        counter = 0
        for block_id in blocks:
            for i in range(orders_per_block):
                counter += 1
                intent = {
                    "client_order_tag": f"TEST-{block_id}-{i}",
                    "symbol": "SPY",
                    "side": "buy",
                    "qty": 1,
                    "order_type": "limit",
                    "limit_price": 50 + i,
                    "strategy": "assassin",
                    "block_id": block_id,
                }
                self.matrix.receive_order_intent(intent)

        # Synchronize created_at to emulate simultaneous intent arrival
        sync_time = time.time()
        for record in self.matrix.orders.values():
            record.created_at = sync_time

        start = time.time()
        self.matrix.process_order_intents()
        duration = time.time() - start

        self.assertEqual(len(self.matrix.orders), counter)
        self.assertTrue(all(record.state == "CLOSED" for record in self.matrix.orders.values()))
        self.assertLess(duration, 15, "Order processing took unexpectedly long")

        latency_log = Path("logs/V13_Latency.log")
        self.assertTrue(latency_log.exists())
        with latency_log.open("r", encoding="utf-8") as fh:
            entries = [json.loads(line) for line in fh if line.strip()]
        ack_events = [entry for entry in entries if entry.get("event") == "ACK_ACCEPTED"]
        fill_events = [entry for entry in entries if entry.get("event") == "FILLED"]
        self.assertEqual(len(fill_events), len(ack_events))
        fill_latencies = [entry.get("since_ack_ms", 0) for entry in fill_events]
        self.assertTrue(fill_latencies, "No fill latency metrics captured")
        self.assertTrue(all(lat < 500 for lat in fill_latencies))


if __name__ == "__main__":
    unittest.main()
