import os, sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.append(os.getcwd())
from collections import deque
from core.V13_AdaptiveCycle import (
    AdaptiveCycle,
    compute_realized_vol,
    compute_tsi,
    compute_allocation,
    export_allocation_snapshot,
)

cycle = AdaptiveCycle()
cycle.price_window = deque([100 + i for i in range(60)], maxlen=60)
vol = compute_realized_vol(cycle.price_window)
tsi = compute_tsi(cycle.price_window)
allocation = compute_allocation(vol, tsi)
export_allocation_snapshot(cycle.allocation_path, allocation, vol, tsi)
print('Allocation snapshot written:', cycle.allocation_path)
