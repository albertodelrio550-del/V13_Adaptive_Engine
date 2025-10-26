import unittest

from tests.phase8_verification import utils


class CapitalGrowthDoctrineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.matrix = utils.create_matrix(utils.AllowAllRiskGate())

    def test_compounding_reinvests_into_smallest_block(self) -> None:
        # Make block 1 slightly under-funded
        self.matrix.blocks["BLOCK1"].config.capital = 4800.0
        self.matrix.blocks["BLOCK2"].config.capital = 5200.0
        self.matrix.blocks["BLOCK3"].config.capital = 5100.0
        self.matrix._update_baseline()

        target = self.matrix.apply_compounding(200.0)
        self.assertEqual(target, "BLOCK1")
        self.assertAlmostEqual(self.matrix.blocks["BLOCK1"].config.capital, 5000.0, places=3)
        self.assertAlmostEqual(self.matrix._baseline_capital["BLOCK1"], 5000.0, places=3)

    def test_block_splitting_creates_child(self) -> None:
        block_id = next(iter(self.matrix.blocks))
        self.matrix.blocks[block_id].config.capital = self.matrix.base_block_capital * 1.6
        created = self.matrix.maybe_split_blocks()
        self.assertTrue(created)
        child_id = created[0]
        self.assertIn(child_id, self.matrix.blocks)
        self.assertAlmostEqual(self.matrix.blocks[block_id].config.capital, self.matrix.blocks[child_id].config.capital)

    def test_performance_scaling_and_reset(self) -> None:
        initial = {bid: state.config.capital for bid, state in self.matrix.blocks.items()}
        self.matrix.record_weekly_performance("green")
        self.matrix.record_weekly_performance("green")
        self.matrix.record_weekly_performance("green")
        scaled = {bid: state.config.capital for bid, state in self.matrix.blocks.items()}
        for bid in initial:
            self.assertAlmostEqual(scaled[bid], initial[bid] * 1.1, places=3)
        self.matrix.record_weekly_performance("red")
        reset = {bid: state.config.capital for bid, state in self.matrix.blocks.items()}
        for bid in initial:
            self.assertAlmostEqual(reset[bid], self.matrix._baseline_capital[bid], places=3)


if __name__ == "__main__":
    unittest.main()
