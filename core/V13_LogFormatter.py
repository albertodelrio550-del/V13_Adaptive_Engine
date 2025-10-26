"""
V13_LogFormatter.py — Unified Log Schema for V13 Engine
Build: 2025-10-20 | Standardized Logging Kernel

Purpose:
    Provides a unified log_event function for consistent JSON logging across all modules.
    Handles file locking to prevent IO collisions in async environments.

Dependencies:
    - json, time, fcntl (Unix-like systems) or msvcrt (Windows) for file locking.
"""

import json
import time
import os
from pathlib import Path

LOG_PATH = Path("logs/V13_unified.log")

def log_event(origin, level, message):
    """
    Unified log event function.
    Writes JSON-formatted log entry to V13_unified.log.
    Handles file locking for thread safety.

    Args:
        origin (str): Module or component name (e.g., "CommandMatrix").
        level (str): Log level (e.g., "INFO", "WARN", "ERROR").
        message (str): Log message.
    """
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    log_entry = {
        "time": int(time.time()),
        "origin": origin,
        "level": level,
        "msg": message
    }

    # File locking for thread safety
    try:
        import fcntl  # Unix-like systems
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            f.write(json.dumps(log_entry) + "\n")
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except ImportError:
        # Windows fallback using msvcrt
        import msvcrt
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
            f.write(json.dumps(log_entry) + "\n")
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)

if __name__ == "__main__":
    # Test the logger
    log_event("LogFormatter", "INFO", "LogFormatter initialized.")
    log_event("TestModule", "WARN", "Test warning message.")
    print("Log entries written to logs/V13_unified.log")
