import os, sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.append(os.getcwd())
from core.V13_RiskSentinel import RiskGate
from pathlib import Path

rg = RiskGate()
print('RUN_ENV:', rg.cfg.get('MODE','RUN_ENV'))
print('EXECUTION_CHANNEL:', rg.cfg.get('MODE','EXECUTION_CHANNEL'))
print('DRY_RUN_POST:', rg.cfg.get('MODE','DRY_RUN_POST'))
print('live_arm flag:', getattr(RiskGate, 'live_arm', False))
print('live_arm file present:', Path('core/.live_armed').exists())
