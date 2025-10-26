import json
import shutil
import unittest
from pathlib import Path

from core.V13_ReplayEngine import ReplayEngine, _default_parameter_sets


class ReplayEngineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_root = Path('tmp_replay')
        if self.temp_root.exists():
            shutil.rmtree(self.temp_root)
        (self.temp_root / 'analytics').mkdir(parents=True)
        (self.temp_root / 'results').mkdir(parents=True, exist_ok=True)
        for day in ['20251020', '20251021']:
            day_dir = self.temp_root / 'analytics' / day
            day_dir.mkdir(parents=True)
            ticks = [
                {'price': 100 + i, 'delta': 0.1 * i, 'signal': 'BUY' if i % 2 == 0 else 'SELL'}
                for i in range(1, 6)
            ]
            (day_dir / 'ticks.jsonl').write_text('\n'.join(json.dumps(t) for t in ticks), encoding='utf-8')

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_root)

    def test_run_replay(self) -> None:
        engine = ReplayEngine(
            analytics_root=self.temp_root / 'analytics',
            results_path=self.temp_root / 'results' / 'replay.json',
            lookback_days=5,
        )
        results = engine.run_replay(_default_parameter_sets())
        self.assertTrue(results)
        self.assertTrue((self.temp_root / 'results' / 'replay.json').exists())


if __name__ == '__main__':
    unittest.main()
