import unittest

from tests.phase8_verification import utils


class AdaptiveReallocationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.matrix = utils.create_matrix(utils.AllowAllRiskGate())
        self.block_id = next(iter(self.matrix.blocks.keys()))

    def test_low_volatility_increases_assassin_allocation(self) -> None:
        state = self.matrix.blocks[self.block_id]
        self.assertAlmostEqual(state.adaptive_allocation["Assassins"], 0.5, places=4)

        telemetry = {
            "pnl": 0.0,
            "drawdown": 0.1,
            "delta": 0.15,
            "volatility": 0.25,
            "trend_strength": 0.05,
        }
        self.matrix.ingest_block_telemetry(self.block_id, telemetry)

        updated = self.matrix.blocks[self.block_id].adaptive_allocation
        self.assertGreater(updated["Assassins"], 0.55)
        self.assertLess(updated["Avengers"], 0.45)


if __name__ == "__main__":
    unittest.main()
