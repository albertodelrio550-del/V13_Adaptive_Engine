import json
import unittest
import shutil
from pathlib import Path

from core.V13_PerformanceAnalytics import PerformanceAnalytics


class PerformanceAnalyticsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_root = Path('tmp_perf_analytics')
        if self.temp_root.exists():
            shutil.rmtree(self.temp_root)
        (self.temp_root / 'data').mkdir(parents=True)
        snapshot = {
            'blocks': {
                'BLOCK1': {
                    'returns': [0.02, -0.01, 0.015],
                    'trades': [
                        {'pnl': 12.0, 'win': True, 'duration': 45, 'slippage': 0.02},
                        {'pnl': -3.0, 'win': False, 'duration': 30, 'slippage': 0.015},
                        {'pnl': 5.0, 'win': True, 'duration': 25, 'slippage': 0.01},
                    ],
                    'latencies': [320, 410, 390],
                },
                'BLOCK2': {
                    'returns': [0.01, 0.03],
                    'trades': [
                        {'pnl': 8.0, 'win': True, 'duration': 35, 'slippage': 0.01},
                        {'pnl': 4.0, 'win': True, 'duration': 40, 'slippage': 0.012},
                    ],
                    'latencies': [280, 300],
                },
            }
        }
        snapshot_path = self.temp_root / 'data' / 'performance_snapshot.json'
        snapshot_path.write_text(json.dumps(snapshot, indent=2), encoding='utf-8')
        self.analytics = PerformanceAnalytics(snapshot_path=snapshot_path)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_root)
        summary_path = Path('data/performance_summary.json')
        if summary_path.exists():
            summary_path.unlink()

    def test_performance_summary_generated(self):
        results = self.analytics.analyse()
        self.assertEqual(len(results), 2)
        summary_path = Path('data/performance_summary.json')
        self.assertTrue(summary_path.exists())
        payload = json.loads(summary_path.read_text(encoding='utf-8'))
        self.assertIn('blocks', payload)
        self.assertEqual(len(payload['blocks']), 2)
        block_entry = payload['blocks'][0]
        self.assertIn('sharpe', block_entry)
        self.assertIn('win_rate', block_entry)


if __name__ == '__main__':
    unittest.main()
