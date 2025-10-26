import json
from pathlib import Path
from typing import Dict

DEFAULT_ALLOCATION = {"Assassins": 0.5, "Avengers": 0.5}
ALLOCATION_PATH = Path("data/allocation.json")


def get_current_allocation() -> Dict[str, float]:
    if not ALLOCATION_PATH.exists():
        return DEFAULT_ALLOCATION.copy()
    try:
        data = json.loads(ALLOCATION_PATH.read_text(encoding="utf-8"))
        alloc = data.get("allocation", {})
        merged = DEFAULT_ALLOCATION.copy()
        for key, value in alloc.items():
            try:
                merged[key] = float(value)
            except (TypeError, ValueError):
                continue
        return merged
    except Exception:
        return DEFAULT_ALLOCATION.copy()
