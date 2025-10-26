# ============================================================
# V13 CrashGuard Helper
# Provides event logging interface for system anomalies.
# ============================================================

import csv, datetime, os

def log_crash_event(module, event_type, severity, description, action, session_id="N/A"):
    """Append a new system event entry to CrashGuard_EventLog.csv."""
    ts = datetime.datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    log_path = os.path.join(os.path.dirname(__file__), "../logs/CrashGuard_EventLog.csv")
    with open(log_path, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([ts, module, event_type, severity, description, action, session_id])
# Example usage:
# log_crash_event("V13_RiskSentinel", "Volatility Spike", "HIGH", "Detected 5% price swing in 2 minutes", "Initiated protective measures", "SESSION12345")
# ============================================================