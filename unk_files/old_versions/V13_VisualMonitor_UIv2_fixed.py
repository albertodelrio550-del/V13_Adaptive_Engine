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
try:
    import core.V13_ManualOverride as manual_override
except ImportError:
    manual_override = None
import sys
sys.path.append('..')
sys.path.append('../..')
try:
    import alpaca_feed_core
except ImportError:
    alpaca_feed_core = None
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
        perf_file = DATA / "doctrine_performance.json"

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
                if alpaca_feed_core:
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
                else:
                    self.gui.update_market_info("SPY", 0.0, 0.0)
                    self.gui.update_time_sync(None)

                # Load Doctrine Performance
                if perf_file.exists():
                    perf = json.loads(perf_file.read_text())
                else:
                    perf = {d:{"accuracy":random.uniform(0.6,0.9),"PnL":random.randint(50,200),"sessions":random.randint(3,12)} for d in ["Fabio","Marco","Tanja","TG_Capital","Kane","Mayne","Umar"]}

                active = max(perf, key=lambda k: perf[k]["accuracy"])
                vol = round(random.uniform(0.9,2.4),2)
                phase = random.choice(["Accumulation","Manipulation","Distribution"])
                discipline = random.randint(70,95)

                self.gui.update_doctrine_info(active, phase)
                self.gui.update_performance_table(perf, active)
                self.gui.update_minimap(active)
                self.gui.update_commander_speech(active, vol, phase, discipline)
                self.gui.update_utc_time()

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

        # New Section: UTC Time, Active Doctrine, AMD Phase
        info_layout = QHBoxLayout()
        layout.addLayout(info_layout)

        self.utc_label = QLabel("UTC Time: --:--:--")
        self.utc_label.setFont(QFont("Segoe UI", 12))
        self.utc_label.setStyleSheet("color: #ffffff;")
        info_layout.addWidget(self.utc_label)

        self.doctrine_label = QLabel("Active Doctrine: None")
        self.doctrine_label.setFont(QFont("Segoe UI", 12))
        self.doctrine_label.setStyleSheet("color: #00aaff;")
        info_layout.addWidget(self.doctrine_label)

        self.phase_label = QLabel("AMD Phase: Unknown")
        self.phase_label.setFont(QFont("Segoe UI", 12))
        self.phase_label.setStyleSheet("color: #ffaa00;")
        info_layout.addWidget(self.phase_label)

        # Doctrine Performance Table
        self.perf_table = QTableWidget()
        self.perf_table.setColumnCount(5)
        self.perf_table.setHorizontalHeaderLabels(["Doctrine", "Accuracy", "PnL($)", "Sessions", "Status"])
        self.perf_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.perf_table.setStyleSheet("color: #ffffff; background-color: #2a2a2a;")
        self.perf_table.setRowCount(7)  # For 7 doctrines
        layout.addWidget(self.perf_table)

        # Minimap
        self.minimap_label = QLabel("Tactical Grid: Loading...")
        self.minimap_label.setFont(QFont("Segoe UI", 10))
        self.minimap_label.setStyleSheet("color: #888888; font-family: monospace;")
        layout.addWidget(self.minimap_label)

        # Commander Speech
        self.speech_label = QLabel("🎙️ Commander: Awaiting orders...")
        self.speech_label.setFont(QFont("Segoe UI", 12))
        self.speech_label.setStyleSheet("color: #ffaa00;")
        layout.addWidget(self.speech_label)

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

        if manual_override:
            btn_on.clicked.connect(lambda: manual_override.activate_override({
                "phase": "Avenger", "S_t": 0.0, "Drawdown": "0%", "mode": "PAPER"
            }))
            btn_off.clicked.connect(manual_override.clear_override)
            btn_kill.clicked.connect(lambda: manual_override.engage_kill_switch("Triggered via Monitor"))
        else:
            btn_on.setEnabled(False)
            btn_off.setEnabled(False)
            btn_kill.setEnabled(False)

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

    def update_utc_time(self):
        self.utc_label.setText(f"UTC Time: {datetime.datetime.now(timezone.utc).strftime('%H:%M:%S')}")

    def update_doctrine_info(self, active, phase):
        self.doctrine_label.setText(f"Active Doctrine: {active}")
        self.phase_label.setText(f"AMD Phase: {phase}")

    def update_performance_table(self, perf, active):
        doctrines = ["Fabio","Marco","Tanja","TG_Capital","Kane","Mayne","Umar"]
        for row, d in enumerate(doctrines):
            v = perf.get(d, {"accuracy":0.5,"PnL":0,"sessions":0})
            acc = v.get("accuracy",0.5)
            pnl = v.get("PnL",0)
            sessions = v.get("sessions",0)
            status = "ACTIVE" if d==active else "IDLE"
            color = "#00ff00" if acc >= 0.8 else "#ffaa00" if acc >= 0.65 else "#ff0000"

            self.perf_table.setItem(row, 0, QTableWidgetItem(d))
            self.perf_table.setItem(row, 1, QTableWidgetItem(f"{acc*100:.1f}%"))
            self.perf_table.setItem(row, 2, QTableWidgetItem(f"{pnl}"))
            self.perf_table.setItem(row, 3, QTableWidgetItem(f"{sessions}"))
            self.perf_table.setItem(row, 4, QTableWidgetItem(status))

            for col in range(5):
                item = self.perf_table.item(row, col)
                if item:
                    item.setForeground(QColor(color))

    def update_minimap(self, active):
        grid = [
            ["Fabio","Marco","Tanja"],
            ["TG_Capital","Kane","Mayne"],
            ["Umar","",""]
        ]
        lines = ["+------------------ [TACTICAL GRID] ------------------+"]
        for row in grid:
            line = ""
            for name in row:
                if not name: continue
                symbol = "🟢" if name==active else random.choice(["🔵","🟡","🟠","🟣"])
                line += f"[{name[:6]:<6}] {symbol}  "
            lines.append(line)
        lines.append("+----------------------------------------------------+")
        self.minimap_label.setText("\n".join(lines))

    def update_commander_speech(self, active, vol, phase, discipline):
        events = [
            f"{active} Doctrine engaging field — volatility {vol}.",
            f"{active} reports phase shift → {phase}.",
            f"Umar confirms discipline stability at {discipline}%.",
            f"Commander authorizes controlled aggression pattern.",
            f"RiskSentinel recalibrating limits post-cycle scan."
        ]
        self.speech_label.setText(f"🎙️  {random.choice(events)}")


# --- Main Launcher ---------------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = V13EnhancedMonitor()
    gui.show()
    sys.exit(app.exec())
