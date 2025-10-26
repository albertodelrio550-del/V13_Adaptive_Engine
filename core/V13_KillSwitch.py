"""
V13_KillSwitch.py — Global Kill Switch
Build: 2025-10-20 | V13_Stable_Release

Purpose:
    Provides a single broadcast signal to stop all runtime loops.
    Global KILL_FLAG, event subscription, and override mechanism.

Dependencies:
    - core.V13_LogFormatter for logging
"""

import threading
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from core.V13_LogFormatter import log_event

# Global Kill Flag
KILL_FLAG = False
kill_lock = threading.Lock()

# Event Bus (simple in-memory for simulation)
event_bus = {}
subscribers = {}

def subscribe(event, callback):
    """Subscribe to an event."""
    if event not in subscribers:
        subscribers[event] = []
    subscribers[event].append(callback)

def emit(event, data):
    """Emit an event to subscribers."""
    if event in subscribers:
        for callback in subscribers[event]:
            callback(data)

def engage_kill_switch(origin="Commander"):
    """Engage the global kill switch."""
    global KILL_FLAG
    with kill_lock:
        if KILL_FLAG:
            log_event("KillSwitch", "WARN", "KillSwitch already engaged.")
            return
        KILL_FLAG = True
        log_event("KillSwitch", "CRITICAL", f"KillSwitch engaged by {origin}. Terminating loops...")
        emit("KILL_SIGNAL", {"origin": origin, "event": "TERMINATED", "modules": 8})  # Assuming 8 modules

def check_kill_flag():
    """Check if kill switch is engaged."""
    with kill_lock:
        return KILL_FLAG

def reset_kill_switch():
    """Reset kill switch (for testing only, not allowed in production)."""
    global KILL_FLAG
    with kill_lock:
        KILL_FLAG = False
        log_event("KillSwitch", "INFO", "KillSwitch reset (testing only).")

# Example subscriber for modules
def example_module_handler(data):
    log_event("Module", "INFO", f"Received KILL_SIGNAL: {data}")

# Subscribe example
subscribe("KILL_SIGNAL", example_module_handler)

if __name__ == "__main__":
    # Test engagement
    engage_kill_switch("Test")
    print(f"Kill flag: {check_kill_flag()}")
    # Reset for testing
    reset_kill_switch()
