from typing import Callable, Dict, Any, List

class Sentinel:
    """Out-of-band supervisor stub. Wire it later to Alpaca or your UI."""
    def __init__(self):
        self.handlers: Dict[str, List[Callable[[Any], None]]] = {}

    def subscribe(self, event: str, fn: Callable[[Any], None]):
        self.handlers.setdefault(event, []).append(fn)

    def emit(self, event: str, payload: Any):
        for fn in self.handlers.get(event, []):
            fn(payload)
