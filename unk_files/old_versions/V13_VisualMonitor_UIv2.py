"""
V13_VisualMonitor_UIv2.py — Enhanced V13 Command Center
Build 2025-10-20 — Fusion Dark Aesthetic
Lightweight market feed integration (PAPER mode via alpaca_feed_core).
Displays real-time metrics with safe async threading.
"""

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel,
    QPushButton, QHBoxLayout, QFrame, QGridLayout, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QPalette, QColor
import sys
import core.V13_ManualOverride as manual_override
import sys
sys.path.append('..')
sys.path.append('../..')
import alpaca_feed_core
from pathlib import Path
import json, time, threading, random, datetime


# --- Enhanced Status Watcher Thread ------------------------------------------------
class V13EnhancedWatcher(threading.Thread):
    def __init__(self, gui_ref, interval=2.0):
        super().__init__(daemon=True)
        self.gui = gui_ref
        self.interval = interval
        self.running = True
        self.last_sync = datetime.datetime.now()

    def run(self):
        DATA = Path(__file__).resolve().parents[1] / "data"
        override_file = DATA / "V13_ManualOverride.json"
        kill_file = DATA / "V13_KillFlag.json"

        while self.running:
            try:
                # Manual Override State
                if override_file.exists():
                    data = json.loads(override_file.read_text())
                    self.gui.update_override_display(
                        data.get("phase", "AUTO"),
                        data.get("S_t", 0.0),
                        data.get("Drawdown", "0%"),
                        True,
                    )
                else:
                    self.gui.update_override_display("AUTO", 0.0, "0%", False)

                # Kill Switch State
                if kill_file.exists():
                    flag = json.loads(kill_file.read_text())
                    self.gui.update_kill_display(flag.get("reason", "Manual"))
                else:
                    self.gui.update_kill_display(None)

                # Real Market Data via Alpaca PAPER API
                snapshot = alpaca_feed_core.get_snapshot_stocks("SPY")
                if snapshot and snapshot.get("last_price"):
                    self.gui.update_market_info(
                        snapshot["symbol"],
                        snapshot["last_price"],
                        snapshot["percent_change"]
                    )
                    self.last_sync = datetime.datetime.now()
                    self.gui.update_time_sync(self.last_sync)
                else:
                    self.gui.update_market_info("SPY", 0.0, 0.0)
                    self.gui.update_time_sync(None)

                # Simulated Performance Summary
                self.gui.update_performance(random.uniform(-2, 5), random.uniform(40, 75))

            except Exception as e:
                print(f"Watcher error: {e}")

            time.sleep(self.interval)


# --- Enhanced GUI ---------------------------------------------------------------------
class V13EnhancedMonitor(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("V13 Command Center — Enhanced UI")
        self.setGeometry(100, 100, 1000, 600)

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
        header = QLabel("🧩 V13 Command Center — Enhanced")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        header.setStyleSheet("color: #00aaff; margin-bottom: 10px;")
        layout.addWidget(header)

        # Mode Indicator
        self.mode_label = QLabel("Mode: PAPER")
        self.mode_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mode_label.setFont(QFont("Segoe UI", 12))
        self.mode_label.setStyleSheet("color: #ffaa00; font-weight: bold;")
        layout.addWidget(self.mode_label)

        # Grid Layout for Metrics
        grid = QGridLayout()
        layout.addLayout(grid)

        # Market Info
        self.market_label = QLabel("Market: Waiting for data...")
        self.market_label.setFont(QFont("Segoe UI", 14))
        self.market_label.setStyleSheet("color: #ffffff;")
        grid.addWidget(self.market_label, 0, 0, 1, 2)

        # Time Sync
        self.sync_label = QLabel("Sync: Never")
        self.sync_label.setFont(QFont("Segoe UI", 10))
        self.sync_label.setStyleSheet("color: #888888;")
        grid.addWidget(self.sync_label, 0, 2)

        # Override Status
        self.override_label = QLabel("Override: AUTO MODE")
        self.override_label.setFont(QFont("Segoe UI", 12))
        self.override_label.setStyleSheet("color: #888888;")
        grid.addWidget(self.override_label, 1, 0)

        # Kill Switch Status
        self.kill_label = QLabel("Kill Switch: SAFE")
        self.kill_label.setFont(QFont("Segoe UI", 12))
        self.kill_label.setStyleSheet("color: #00ff00;")
        grid.addWidget(self.kill_label, 1, 1)

        # Performance Info
        self.perf_label = QLabel("PnL: 0.00% | Win Rate: 0.0%")
        self.perf_label.setFont(QFont("Segoe UI", 12))
        self.perf_label.setStyleSheet("color: #66ccff;")
        grid.addWidget(self.perf_label, 1, 2)

        # Buttons Row
        button_frame = QHBoxLayout()
        layout.addLayout(button_frame)

        btn_on = QPushButton("Enable Override")
        btn_off = QPushButton("Disable Override")
        btn_kill = QPushButton("EMERGENCY STOP")

        btn_on.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                color: #00ff00;
                border: 1px solid #00ff00;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #3a3a3a; }
        """)
        btn_off.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                color: #ffaa00;
                border: 1px solid #ffaa00;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #3a3a3a; }
        """)
        btn_kill.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                color: #ff0000;
                border: 2px solid #ff0000;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #3a3a3a; }
        """)

        btn_on.clicked.connect(lambda: manual_override.activate_override({
            "phase": "Avenger", "S_t": 0.0, "Drawdown": "0%", "mode": "PAPER"
        }))
        btn_off.clicked.connect(manual_override.clear_override)
        btn_kill.clicked.connect(lambda: manual_override.engage_kill_switch("Triggered via Monitor"))

        button_frame.addWidget(btn_on)
        button_frame.addWidget(btn_off)
        button_frame.addWidget(btn_kill)

        # Start watcher thread
        self.watcher = V13EnhancedWatcher(self)
        self.watcher.start()

    # --- Update Functions ----------------------------------------------------
    def update_override_display(self, phase, signal, drawdown, active):
        if active:
            self.override_label.setText(f"Override: ACTIVE ({phase})")
            self.override_label.setStyleSheet("color: #00ff00;")
        else:
            self.override_label.setText("Override: AUTO MODE")
            self.override_label.setStyleSheet("color: #888888;")

    def update_kill_display(self, reason):
        if reason:
            self.kill_label.setText(f"Kill Switch: ACTIVE")
            self.kill_label.setStyleSheet("color: #ff0000; font-weight: bold;")
        else:
            self.kill_label.setText("Kill Switch: SAFE")
            self.kill_label.setStyleSheet("color: #00ff00;")

    def update_market_info(self, symbol, price, change):
        color = "#00ff00" if change >= 0 else "#ff0000"
        self.market_label.setText(f"{symbol} @ {price:.2f} ({change:+.2f}%)")
        self.market_label.setStyleSheet(f"color: {color};")

    def update_performance(self, pnl, winrate):
        color = "#00ff00" if pnl >= 0 else "#ff0000"
        self.perf_label.setText(f"PnL: {pnl:+.2f}% | Win Rate: {winrate:.1f}%")
        self.perf_label.setStyleSheet(f"color: {color};")

    def update_time_sync(self, sync_time):
        if sync_time:
            self.sync_label.setText(f"Sync: {sync_time.strftime('%H:%M:%S')}")
            self.sync_label.setStyleSheet("color: #00ff00;")
        else:
            self.sync_label.setText("Sync: Failed")
            self.sync_label.setStyleSheet("color: #ff0000;")


# --- Main Launcher ---------------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = V13EnhancedMonitor()
    gui.show()
    sys.exit(app.exec())
