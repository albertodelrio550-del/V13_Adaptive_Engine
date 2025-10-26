"""
V13_EventBus.py
Central event routing system for safe GUI interactions.
Build: PAPER Simulation Mode

Responsibilities:
- Route GUI events to modules without direct thread access
- Emit and subscribe to events
- Thread-safe operations
"""

import threading
from collections import defaultdict

class V13_EventBus:
    def __init__(self):
        self.subscribers = defaultdict(list)
        self.lock = threading.Lock()

    def subscribe(self, event_type, callback):
        with self.lock:
            self.subscribers[event_type].append(callback)

    def emit(self, event_type, data=None):
        with self.lock:
            for callback in self.subscribers[event_type]:
                try:
                    callback(data)
                except Exception as e:
                    print(f"EventBus error in callback for {event_type}: {e}")

# Global instance
event_bus = V13_EventBus()
