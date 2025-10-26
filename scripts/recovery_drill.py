import os, sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.append(os.getcwd())
import json
from pathlib import Path
from importlib import reload

import V13_CommandMatrix
reload(V13_CommandMatrix)
from V13_CommandMatrix import V13_CommandMatrix
from core.V13_SyncLoop import restore_runtime_state

print('--- Recovery Drill (Phase 7 Step 6) ---')

matrix = V13_CommandMatrix()
matrix.cfg.set('MODE', 'DRY_RUN_POST', 'true')
order_ids = []
for i in range(5):
    intent = {
        'ts': f'2025-10-21T22:0{i}:00Z',
        'strategy': 'Assassin',
        'reason': 'recovery.drill',
        'symbol': 'SPY',
        'side': 'buy' if i % 2 == 0 else 'sell',
        'qty': 0.05,
        'order_type': 'market',
        'time_in_force': 'day',
        'client_order_tag': f'RECOVERY-{i}'
    }
    oid = matrix.receive_order_intent(intent)
    matrix.process_order_intents()
    order_ids.append(oid)
print('Orders before simulated crash:', order_ids)

restore_runtime_state()
print('restore_runtime_state invoked; check logs/recover_* for summary.')

recover_logs = sorted(Path('logs').glob('recover_*.log'))
if recover_logs:
    latest = recover_logs[-1]
    data = json.loads(latest.read_text())
    print('Latest recovery log:', latest.name)
    print(json.dumps(data, indent=2))
else:
    print('No recovery log found.')

print('--- Recovery drill complete ---')
