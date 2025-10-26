import json
import shutil
import unittest
from pathlib import Path

from core.V13_RLAgent import ReinforcementLearner


class RLAgentTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path('tmp_rl_policy')
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        self.temp_dir.mkdir()
        self.policy_path = self.temp_dir / 'policy.json'

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir)

    def test_rewards_update_weights(self) -> None:
        agent = ReinforcementLearner(policy_path=self.policy_path, learning_rate=0.1)
        metrics = {
            'sharpe': 1.2,
            'max_drawdown': 0.3,
            'mean_latency_ms': 400.0,
            'win_rate': 60.0,
            'correlation': 0.5,
        }
        result = agent.learn_from_metrics(metrics)
        self.assertTrue(self.policy_path.exists())
        payload = json.loads(self.policy_path.read_text())
        for action in ['trail_pct', 'stop_pct', 'capital_split']:
            self.assertTrue(any(abs(weight) > 0 for weight in payload[action]))
        self.assertIn('trail_pct', result.actions)


if __name__ == '__main__':
    unittest.main()
