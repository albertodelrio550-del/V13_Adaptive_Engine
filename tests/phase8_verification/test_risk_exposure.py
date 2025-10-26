import unittest

from tests.phase8_verification import utils


class RiskExposureTest(unittest.TestCase):
    def setUp(self) -> None:
        self.matrix = utils.create_matrix(utils.ExposureRiskGate(cap=180.0))

    def _queue_order(self, tag: str, symbol: str, qty: float, price: float) -> None:
        intent = {
            "client_order_tag": tag,
            "symbol": symbol,
            "side": "buy",
            "qty": qty,
            "order_type": "limit",
            "limit_price": price,
            "strategy": "assassin",
        }
        self.matrix.receive_order_intent(intent)

    def test_cross_symbol_exposure_denied(self) -> None:
        self._queue_order("EXP-SPY-1", "SPY", 2, 100)   # ~100 exposure after allocation
        self._queue_order("EXP-AAPL-1", "AAPL", 1, 80)    # ~40 (total ~140)
        self._queue_order("EXP-TSLA-1", "TSLA", 1, 70)   # pushes above cap
        self._queue_order("EXP-SPY-2", "SPY", 1, 60)     # should be blocked

        self.matrix.process_order_intents()

        rejected = self.matrix.orders["EXP-SPY-2"]
        self.assertEqual(rejected.state, "ACK_REJECTED")
        # The first three should be closed (filled)
        for tag in ["EXP-SPY-1", "EXP-AAPL-1", "EXP-TSLA-1"]:
            self.assertEqual(self.matrix.orders[tag].state, "CLOSED")

        rejection_meta = next(
            (entry for entry in rejected.history if entry["state"] == "ACK_REJECTED"), None
        )
        self.assertIsNotNone(rejection_meta)
        meta = rejection_meta.get("meta", {})
        self.assertEqual(meta.get("source"), "risk_gate")
        self.assertGreater(meta.get("gross_now", 0), 0)
        self.assertGreater(meta.get("max_gross", 0), 0)


if __name__ == "__main__":
    unittest.main()
