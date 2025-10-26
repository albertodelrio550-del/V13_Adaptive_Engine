"""
============================================================
Doctrine_Heartbeat.py — V13 Dynamic Doctrine Runtime Sentinel
Build: 2025-10-20 | Log Stream Integrated
============================================================
"""

import os
import time
import json
import hashlib
from datetime import datetime
from core.V13_RiskSentinel import RiskMonitor
from core.V13_TelemetryFusion import TelemetryFeed
from core.V13_DoctrineFeedbackLoop import DoctrineFeedbackLoop

# ---------------------------------------------------------------------
# HEARTBEAT CLASS
# ---------------------------------------------------------------------
class DoctrineHeartbeat:
    def __init__(self, interval=60):
        self.interval = interval
        self.telemetry = TelemetryFeed()
        self.risk = RiskMonitor()
        self.feedback = DoctrineFeedbackLoop()
        self.last_hash_check = None
        self.last_telemetry_check = None
        self.last_feedback_pulse = None
        self.alerts = []

        # log path setup
        base_path = os.path.join(
            os.getcwd(), "Videos", "bohrn 2025", "trade", "V13", "logs"
        )
        os.makedirs(base_path, exist_ok=True)
        self.log_file = os.path.join(base_path, "Heartbeat_Log.txt")

    # ---------------------------------------------------------------
    def _calculate_md5(self, path):
        hash_md5 = hashlib.md5()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def _write_log(self, message):
        """Append timestamped message to Heartbeat_Log.txt"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")

    # ---------------------------------------------------------------
    def verify_doctrine_hashes(self):
        hash_list_path = os.path.join(
            os.getcwd(), "Videos", "bohrn 2025", "trade", "V13", "docs",
            "Doctrine_V13", "Integrity_HashList.md5"
        )

        if not os.path.exists(hash_list_path):
            self.alerts.append("❌ Integrity HashList missing.")
            self._write_log("❌ Integrity HashList missing.")
            return

        with open(hash_list_path, "r", encoding="utf-8") as f:
            logged_hashes = f.read()

        for doctrine_id, data in self.feedback.doctrines.items():
            file_name = f"{data['data']['Doctrine_Name']}.json"
            file_path = os.path.join(
                os.getcwd(), "Videos", "bohrn 2025", "trade", "V13",
                "docs", "Doctrine_V13", file_name
            )

            if not os.path.exists(file_path):
                msg = f"⚠️ Missing file: {file_name}"
                self.alerts.append(msg)
                self._write_log(msg)
                continue

            active_hash = self._calculate_md5(file_path)
            if active_hash not in logged_hashes:
                msg = f"⚠️ Hash drift detected for {file_name}"
                self.alerts.append(msg)
                self._write_log(msg)

        self.last_hash_check = datetime.now().strftime("%H:%M:%S")

    # ---------------------------------------------------------------
    def check_telemetry(self):
        sample = self.telemetry.get_market_snapshot("Trade A")
        if not sample or "price" not in sample:
            msg = "⚠️ Telemetry feed inactive or invalid."
            self.alerts.append(msg)
            self._write_log(msg)
        self.last_telemetry_check = datetime.now().strftime("%H:%M:%S")

    # ---------------------------------------------------------------
    def pulse_feedback(self):
        try:
            self.feedback.run_cycle()
            self.last_feedback_pulse = datetime.now().strftime("%H:%M:%S")
        except Exception as e:
            msg = f"❌ Feedback loop error: {e}"
            self.alerts.append(msg)
            self._write_log(msg)

    # ---------------------------------------------------------------
    def run_heartbeat(self):
        """Main heartbeat loop with persistent logging."""
        print(f"💓 [DDS] Doctrine Heartbeat online (interval = {self.interval}s)")
        self._write_log("💓 Heartbeat started.")
        while True:
            self.alerts.clear()

            self.verify_doctrine_hashes()
            self.check_telemetry()
            self.pulse_feedback()

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cycle_summary = (
                f"Heartbeat @ {timestamp} | "
                f"Hash: {self.last_hash_check} | "
                f"Telemetry: {self.last_telemetry_check} | "
                f"Feedback: {self.last_feedback_pulse}"
            )
            print("\n[⏱] " + cycle_summary)
            self._write_log(cycle_summary)

            if self.alerts:
                print("🚨 Alerts:")
                for alert in self.alerts:
                    print(f"   • {alert}")
                self._write_log(f"⚠️ Alerts triggered: {len(self.alerts)} issue(s)")
            else:
                print("✅ All systems nominal.")
                self._write_log("✅ All systems nominal.")

            time.sleep(self.interval)
