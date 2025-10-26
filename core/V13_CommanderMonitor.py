"""
V13_CommanderMonitor.py — Commander Monitor GUI
Build: 2025-10-20 | GUI with EventBus Integration

Purpose:
    GUI interface for V13 system control, launching CommandMatrix and SyncLoop threads,
    displaying system states, audit logs, and command input.

Features:
    - Launches CommandMatrix and SyncLoop threads
    - Displays system states: RUNNING, PAUSED, STOPPED, KILLED
    - Shows last 10 lines from logs/Audit_DB.json
    - Command input box routing via EventBus
"""

import os
import sys
import threading
import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QTextEdit, QHBoxLayout, QFrame, QGridLayout
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QPalette, QColor

from core.V13_EventBus import event_bus
from V13_CommandMatrix import V13_CommandMatrix
from core.V13_SyncLoop import run_sync_loop
import core.V13_ManualOverride as manual_override

# ---------------------------------------------------------------------
# COMMANDER MONITOR GUI CLASS
# ---------------------------------------------------------------------
class CommanderMonitorGUI(QWidget):
    update_signal = pyqtSignal(str)  # For thread-safe updates

    def __init__(self):
        super().__init__()
        self.setWindowTitle("V13 Commander Monitor — GUI")
        self.setGeometry(200, 200, 1200, 800)

        # Fusion Dark Theme
        app = QApplication.instance()
        app.setStyle("Fusion")
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
        dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        dark_palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
        app.setPalette(dark_palette)

        self.setStyleSheet("font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;")

        layout = QVBoxLayout()
        self.setLayout(layout)

        # Header
        header = QLabel("🧩 V13 Commander Monitor — GUI")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        header.setStyleSheet("color: #00aaff; margin-bottom: 10px;")
        layout.addWidget(header)

        # System State Display
        self.state_label = QLabel("System State: STOPPED")
        self.state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.state_label.setFont(QFont("Segoe UI", 14))
        self.state_label.setStyleSheet("color: #ffaa00; font-weight: bold;")
        layout.addWidget(self.state_label)

        # Grid for Audit Logs and Status
        grid = QGridLayout()
        layout.addLayout(grid)

        # Audit Logs Display
        audit_label = QLabel("Last 10 Audit Logs:")
        audit_label.setFont(QFont("Segoe UI", 12))
        audit_label.setStyleSheet("color: #ffffff;")
        grid.addWidget(audit_label, 0, 0)

        self.audit_display = QTextEdit()
        self.audit_display.setReadOnly(True)
        self.audit_display.setFont(QFont("Segoe UI", 10))
        self.audit_display.setStyleSheet("background-color: #1a1a1a; color: #ffffff; border: 1px solid #333;")
        grid.addWidget(self.audit_display, 1, 0)

        # Status Display
        status_label = QLabel("System Status:")
        status_label.setFont(QFont("Segoe UI", 12))
        status_label.setStyleSheet("color: #ffffff;")
        grid.addWidget(status_label, 0, 1)

        self.status_display = QTextEdit()
        self.status_display.setReadOnly(True)
        self.status_display.setFont(QFont("Segoe UI", 10))
        self.status_display.setStyleSheet("background-color: #1a1a1a; color: #ffffff; border: 1px solid #333;")
        grid.addWidget(self.status_display, 1, 1)

        # Command Input
        command_layout = QHBoxLayout()
        layout.addLayout(command_layout)

        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Enter command (e.g., /sync, /status, deploy, tighten B, kill)")
        self.command_input.setFont(QFont("Segoe UI", 12))
        self.command_input.setStyleSheet("background-color: #2a2a2a; color: #ffffff; border: 1px solid #555; padding: 5px;")
        command_layout.addWidget(self.command_input)

        send_button = QPushButton("Send Command")
        send_button.setFont(QFont("Segoe UI", 12))
        send_button.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                color: #00ff00;
                border: 1px solid #00ff00;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #3a3a3a; }
        """)
        send_button.clicked.connect(self.send_command)
        command_layout.addWidget(send_button)

        # Control Buttons
        button_layout = QHBoxLayout()
        layout.addLayout(button_layout)

        start_button = QPushButton("Start System")
        start_button.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                color: #00ff00;
                border: 1px solid #00ff00;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #3a3a3a; }
        """)
        start_button.clicked.connect(self.start_system)
        button_layout.addWidget(start_button)

        stop_button = QPushButton("Stop System")
        stop_button.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                color: #ffaa00;
                border: 1px solid #ffaa00;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #3a3a3a; }
        """)
        stop_button.clicked.connect(self.stop_system)
        button_layout.addWidget(stop_button)

        kill_button = QPushButton("Kill System")
        kill_button.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                color: #ff0000;
                border: 2px solid #ff0000;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #3a3a3a; }
        """)
        kill_button.clicked.connect(self.kill_system)
        button_layout.addWidget(kill_button)

        # Threads and State
        self.matrix = None
        self.sync_thread = None
        self.system_state = "STOPPED"
        self.running = False

        # EventBus subscriptions
        event_bus.subscribe("CMD_ACK", self.handle_cmd_ack)
        event_bus.subscribe("RISK_ALERT", self.handle_risk_alert)
        event_bus.subscribe("KILL_SIGNAL", self.handle_kill_signal)

        # Timer for updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_displays)
        self.timer.start(2000)  # Update every 2 seconds

        # Connect signal
        self.update_signal.connect(self.update_state_label)

    def start_system(self):
        if self.running:
            return
        self.running = True
        self.system_state = "RUNNING"
        self.update_signal.emit("System State: RUNNING")

        # Launch CommandMatrix
        self.matrix = V13_CommandMatrix()
        if not self.matrix.verify_core_modules():
            self.update_signal.emit("System State: FAILED (Modules missing)")
            return

        # Launch SyncLoop in thread
        self.sync_thread = threading.Thread(target=self.run_sync_loop_thread, daemon=True)
        self.sync_thread.start()

    def stop_system(self):
        self.running = False
        self.system_state = "STOPPED"
        self.update_signal.emit("System State: STOPPED")
        # Stop threads gracefully

    def kill_system(self):
        manual_override.engage_kill_switch("GUI Kill")
        self.system_state = "KILLED"
        self.update_signal.emit("System State: KILLED")

    def run_sync_loop_thread(self):
        while self.running:
            run_sync_loop(interval=10, max_cycles=1)  # Run one cycle every 10s

    def send_command(self):
        command = self.command_input.text().strip()
        if command:
            event_bus.emit("COMMAND", command)
            self.command_input.clear()

    def handle_cmd_ack(self, data):
        self.update_signal.emit(f"CMD_ACK: {data}")

    def handle_risk_alert(self, data):
        self.update_signal.emit(f"RISK_ALERT: {data}")

    def handle_kill_signal(self, data):
        self.system_state = "KILLED"
        self.update_signal.emit("System State: KILLED")

    def update_displays(self):
        # Update audit logs
        audit_path = Path("logs/Audit_DB.json")
        if audit_path.exists():
            try:
                with open(audit_path, "r") as f:
                    data = json.load(f)
                    sessions = data.get("sessions", [])
                    last_10 = sessions[-10:]
                    audit_text = "\n".join([f"{s['Timestamp']} - {s['Event']}: {s['Details']}" for s in last_10])
                    self.audit_display.setPlainText(audit_text)
            except:
                self.audit_display.setPlainText("Error loading audit logs")

        # Update status
        status_text = f"State: {self.system_state}\n"
        if self.matrix:
            status_text += f"Modules Verified: {len(self.matrix.verified_modules)}\n"
        safety = manual_override.safety_status()
        status_text += f"Kill Active: {safety.get('kill', False)}\n"
        status_text += f"Override Active: {bool(manual_override.read_override())}"
        self.status_display.setPlainText(status_text)

    def update_state_label(self, text):
        self.state_label.setText(text)

# ---------------------------------------------------------------------
# MAIN LAUNCHER
# ---------------------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = CommanderMonitorGUI()
    gui.show()
    sys.exit(app.exec())
