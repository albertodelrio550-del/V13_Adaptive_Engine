"""PerformanceTracker — simplified implementation without numpy.

This file provides the PerformanceTracker class used by the launch
sequence and other components. It removes the dependency on numpy and
implements a small pure-Python correlation fallback for diagnostics.
"""

import os
import time
import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from core.V13_RiskSentinel import RiskMonitor


# Configuration
RISK_LOG = os.path.join('logs', 'V13_risk_status.log')
TELEMETRY_FILE = os.path.join('data', 'telemetry_signal.json')
OUTPUT_LOG = os.path.join('logs', 'V13_performance_tracker.log')
REPORT_FILE = os.path.join('logs', 'V13_daily_report.json')

UPDATE_INTERVAL = 30
LADDER_LEVELS = [50, 100, 150, 250]
LOCK_STEPS = [0.2, 0.5, 0.8, 0.9]
CAPITAL_BASE = 10000.0

LOCK_ASSASSINS_THRESHOLD = -CAPITAL_BASE * 0.005   # -0.5%
SUSPEND_AVENGERS_THRESHOLD = -CAPITAL_BASE * 0.01  # -1%
GLOBAL_LOCK_THRESHOLD = -CAPITAL_BASE * 0.02       # -2%


def _safe_correlation(x, y):
    # pure-Python Pearson correlation fallback
    if len(x) < 2 or len(y) < 2:
        return 0.0
    n = min(len(x), len(y))
    x_slice = x[-n:]
    y_slice = y[-n:]
    mean_x = sum(x_slice) / n
    mean_y = sum(y_slice) / n
    cov = sum((a - mean_x) * (b - mean_y) for a, b in zip(x_slice, y_slice))
    var_x = sum((a - mean_x) ** 2 for a in x_slice)
    var_y = sum((b - mean_y) ** 2 for b in y_slice)
    try:
        return cov / (var_x ** 0.5 * var_y ** 0.5)
    except Exception:
        return 0.0


class PerformanceTracker:
    def __init__(self):
        base_path = os.path.join(os.getcwd(), 'logs')
        os.makedirs(base_path, exist_ok=True)
        self.log_path = os.path.join(base_path, 'Performance_Log.txt')
        self.risk = RiskMonitor()
        self.session_profit = 0.0
        self.peak_profit = 0.0
        self.floor_lock = 0.0
        self.ladder_state = 'INIT'
        self.entries = []
        self.profit_history = []
        self.signal_history = []
        self.safety_flags = {
            'assassins_locked': False,
            'avengers_suspended': False,
            'global_lock': False,
            'emergency_exit': False,
        }
        self.safety_path = Path('data') / 'safety_flags.json'
        self.volatility_spike_triggered = False
        # Start performance summary stream
        self.status_file = os.path.join(os.getcwd(), 'data', 'V13_Status.json')
        os.makedirs(os.path.dirname(self.status_file), exist_ok=True)
        self.stream_thread = threading.Thread(target=self._export_status_loop, daemon=True)
        self.stream_thread.start()

    def track(self, feed: dict):
        pnl = feed.get('pnl', 0)
        delta = feed.get('delta', 0)
        self.session_profit += pnl
        self.peak_profit = max(self.peak_profit, self.session_profit)

        self.ladder_state = self._check_ladder(self.session_profit)
        self._update_safety(self.session_profit)
        self._check_volatility(feed)

        entry = {
            'time': datetime.now().strftime('%H:%M:%S'),
            'pnl': pnl,
            'delta': delta,
            'session_profit': round(self.session_profit, 2),
            'ladder': self.ladder_state,
        }
        self.entries.append(entry)
        self._log_entry(entry)

        # update histories
        self.profit_history.append(self.session_profit)
        self.signal_history.append(feed.get('s_t', 0.0))

        corr = _safe_correlation(self.signal_history, self.profit_history)

        return {
            'profit': self.session_profit,
            'peak': self.peak_profit,
            'ladder': self.ladder_state,
            'correlation': corr,
        }

    def _check_ladder(self, pnl):
        if pnl >= LOCK_STEPS[1]:
            self.floor_lock = pnl * LOCK_STEPS[1]
            return f"TIGHTEN {int(LOCK_STEPS[1]*100)}% | Floor={self.floor_lock:.2f}"
        elif pnl >= LOCK_STEPS[0]:
            self.floor_lock = pnl * LOCK_STEPS[0]
            return f"LOCK {int(LOCK_STEPS[0]*100)}% | Floor={self.floor_lock:.2f}"
        else:
            return 'NORMAL'

    def _log_entry(self, entry):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{timestamp}] Δ={entry['delta']:.3f} PnL={entry['pnl']:+.2f} Session={entry['session_profit']:+.2f} Ladder={entry['ladder']}\n"
        with open(self.log_path, 'a', encoding='utf-8') as f:
            f.write(log_line)

    def _export_status_loop(self):
        while True:
            self._export_status()
            time.sleep(10)

    def _export_status(self):
        # Calculate WinRate
        if self.entries:
            positive_pnl = sum(1 for e in self.entries if e['pnl'] > 0)
            winrate = (positive_pnl / len(self.entries)) * 100
        else:
            winrate = 0.0
        status = {
            "symbol": "BTCUSDT",
            "PnL": round(self.session_profit, 2),
            "WinRate": round(winrate, 2),
            "Updated": int(time.time())
        }
        with open(self.status_file, 'w') as f:
            json.dump(status, f, indent=4)

    def _update_safety(self, session_profit: float):
        updated = False
        if session_profit <= GLOBAL_LOCK_THRESHOLD and not self.safety_flags['global_lock']:
            self.safety_flags['global_lock'] = True
            self._log_safety_event('GLOBAL_LOCK', session_profit)
            updated = True
        elif session_profit <= SUSPEND_AVENGERS_THRESHOLD and not self.safety_flags['avengers_suspended']:
            self.safety_flags['avengers_suspended'] = True
            self._log_safety_event('SUSPEND_AVENGERS', session_profit)
            updated = True
        elif session_profit <= LOCK_ASSASSINS_THRESHOLD and not self.safety_flags['assassins_locked']:
            self.safety_flags['assassins_locked'] = True
            self._log_safety_event('LOCK_ASSASSINS', session_profit)
            updated = True

        # Clear flags when recovering above thresholds (except global lock; requires manual reset)
        if session_profit > LOCK_ASSASSINS_THRESHOLD and self.safety_flags['assassins_locked'] and session_profit > 0:
            self.safety_flags['assassins_locked'] = False
            self._log_safety_event('ASSASSINS_UNLOCK', session_profit)
            updated = True
        if session_profit > SUSPEND_AVENGERS_THRESHOLD and self.safety_flags['avengers_suspended'] and session_profit > 0:
            self.safety_flags['avengers_suspended'] = False
            self._log_safety_event('AVENGERS_RESUME', session_profit)
            updated = True

        if updated:
            self._write_safety_flags()

    def _check_volatility(self, feed: dict):
        vol = feed.get('volatility')
        if vol is None:
            return
        if vol >= 0.05 and not self.safety_flags['emergency_exit']:
            self.safety_flags['emergency_exit'] = True
            self._log_safety_event('EMERGENCY_EXIT', self.session_profit, extra={'volatility': round(vol, 4)})
            self._write_safety_flags()
        elif vol < 0.05 and self.safety_flags['emergency_exit']:
            self.safety_flags['emergency_exit'] = False
            self._log_safety_event('EMERGENCY_CLEAR', self.session_profit)
            self._write_safety_flags()

    def _log_safety_event(self, event: str, session_profit: float, extra: dict | None = None):
        payload = extra.copy() if extra else {}
        payload['session_profit'] = round(session_profit, 2)
        log_event('PerformanceTracker', 'WARN', f'{event} | {payload}')
        audit_path = Path('logs') / 'V13_SessionAudit.log'
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        with open(audit_path, 'a', encoding='utf-8') as f:
            f.write(f"{datetime.now(timezone.utc).isoformat()} | SAFETY_EVENT | {event} | {json.dumps(payload)}\n")

    def _write_safety_flags(self):
        self.safety_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'flags': self.safety_flags,
        }
        self.safety_path.write_text(json.dumps(payload, indent=2), encoding='utf-8')

    def summarize(self):
        report = {
            'Total Profit': round(self.session_profit, 2),
            'Peak Profit': round(self.peak_profit, 2),
            'Lock Floor': round(self.floor_lock, 2),
            'Entries Logged': len(self.entries),
        }
        print('\n📊 [Performance Summary]')
        for k, v in report.items():
            print(f"   {k}: {v}")
        return report
