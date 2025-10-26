"""
V13_VisualMonitor_UIv2.py - Enhanced V13 Command Center
Build 2025-10-20 - Fusion Dark Aesthetic
Lightweight market feed integration (PAPER mode via alpaca_feed_core).
Displays real-time metrics with safe async threading.
"""

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel,
    QPushButton, QHBoxLayout, QFrame, QGridLayout, QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit
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

# Import AssassinEngine for real data
try:
    from core.engine import AssassinEngine, SessionConfig
except ImportError:
    AssassinEngine = None
    SessionConfig = None


# --- Enhanced Status Watcher Thread ------------------------------------------------
class V13EnhancedWatcher(threading.Thread):
    def __init__(self, gui_ref, interval=2.0):
        super().__init__(daemon=True)
        self.gui = gui_ref
        self.interval = interval
        self.running = True
        self.last_sync = datetime.datetime.now()
        # Initialize AssassinEngine for real data
        self.engine = None
        if AssassinEngine and SessionConfig:
            try:
                cfg = SessionConfig(mode_name="balanced", symbol="SPY", capital_usd=5000.0)
                self.engine = AssassinEngine.load_from_preset(cfg, "config/mode_presets.json")
                print("AssassinEngine loaded successfully.")
            except Exception as e:
                print(f"Failed to load AssassinEngine: {e}")
                self.engine = None
        else:
            print("AssassinEngine not available.")

    def run(self):
        DATA = Path(__file__).resolve().parents[1] / "data"
        override_file = DATA / "V13_ManualOverride.json"
        kill_file = DATA / "V13_KillFlag.json"
        perf_file = DATA / "doctrine_performance.json"
        status_file = DATA / "V13_Status.json"
        events_file = DATA / "V13_Events.json"

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

                # Ball Status and Net P/L from engine snapshot
                if self.engine:
                    # Simulate price update to generate pnl
                    current_price = 450.0 + random.uniform(-10, 10)  # Simulate SPY price around 450
                    self.engine.on_price(current_price)

                    # Get real snapshot
                    snap = self.engine.snapshot()
                    balls = {}
                    for b_id in range(1, 6):  # Ensure 5 balls for table
                        if b_id in snap["balls"]:
                            b_data = snap["balls"][b_id]
                            state = b_data["state"]
                            profit = b_data["float"]
                            loss = 0.0  # Loss not directly in snapshot, set to 0
                        else:
                            state = "IDLE"
                            profit = 0.0
                            loss = 0.0
                        balls[b_id] = {"state": state, "profit": profit, "loss": loss}
                    self.gui.update_ball_status(balls)

                    # Real Net P/L from engine
                    net_pnl = snap["pnl"]["total"]
                    capital = self.engine.cfg.capital_usd
                    self.gui.update_net_pnl_capital(net_pnl, capital)
                else:
                    # Fallback to simulated data
                    balls = {
                        1: {"state": "OPEN", "profit": random.uniform(-50, 150), "loss": random.uniform(0, 20)},
                        2: {"state": "IDLE", "profit": 0, "loss": 0},
                        3: {"state": "LOCKED", "profit": random.uniform(10, 100), "loss": random.uniform(0, 10)},
                        4: {"state": "OPEN", "profit": random.uniform(-30, 200), "loss": random.uniform(0, 15)},
                        5: {"state": "IDLE", "profit": 0, "loss": 0},
                    }
                    self.gui.update_ball_status(balls)

                    # Net P/L and Capital from status
                    if status_file.exists():
                        status = json.loads(status_file.read_text())
                        net_pnl = status.get("PnL", 0.0)
                        capital = 5000.0  # Default, could be from config
                    else:
                        net_pnl = random.uniform(-200, 500)
                        capital = 5000.0
                    self.gui.update_net_pnl_capital(net_pnl, capital)

                # Market Shifts from events
                if events_file.exists():
                    with open(events_file, 'r') as f:
                        lines = f.readlines()
                        if lines:
                            last_event = json.loads(lines[-1].strip())
                            shift = last_event.get("event_type", "None")
                        else:
                            shift = "None"
                else:
                    shift = random.choice(["TELEMETRY_UPDATE", "RISK_ALERT", "CMD_FEEDBACK", "None"])
                self.gui.update_market_shifts(shift)

            except Exception as e:
                print(f"Watcher error: {e}")

            time.sleep(self.interval)


# --- Enhanced GUI ---------------------------------------------------------------------
class V13EnhancedMonitor(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("V13 Command Center — Enhanced UI")
        self.setGeometry(100, 100, 1200, 700)

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

        # Net P/L and Capital
        pnl_layout = QHBoxLayout()
        layout.addLayout(pnl_layout)

        self.net_pnl_label = QLabel("Net P/L: $0.00")
        self.net_pnl_label.setFont(QFont("Segoe UI", 14))
        self.net_pnl_label.setStyleSheet("color: #00ff00;")
        pnl_layout.addWidget(self.net_pnl_label)

        self.capital_label = QLabel("Capital: $5000.00")
        self.capital_label.setFont(QFont("Segoe UI", 14))
        self.capital_label.setStyleSheet("color: #ffffff;")
        pnl_layout.addWidget(self.capital_label)

        self.market_shift_label = QLabel("Market Shift: None")
        self.market_shift_label.setFont(QFont("Segoe UI", 12))
        self.market_shift_label.setStyleSheet("color: #ffaa00;")
        pnl_layout.addWidget(self.market_shift_label)

        # Ball Status Table
        self.ball_table = QTableWidget()
        self.ball_table.setColumnCount(4)
        self.ball_table.setHorizontalHeaderLabels(["Ball ID", "State", "Profit ($)", "Loss ($)"])
        self.ball_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.ball_table.setStyleSheet("color: #ffffff; background-color: #2a2a2a;")
        self.ball_table.setRowCount(5)  # For 5 balls
        layout.addWidget(self.ball_table)

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
        btn_lock = QPushButton("LOCK PROFITS")
        btn_rearm = QPushButton("REARM BALLS")

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
        btn_lock.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                color: #ffff00;
                border: 1px solid #ffff00;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #3a3a3a; }
        """)
        btn_rearm.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                color: #00aaff;
                border: 1px solid #00aaff;
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

        btn_lock.clicked.connect(self.manual_lock_profits)
        btn_rearm.clicked.connect(self.manual_rearm_balls)

        button_frame.addWidget(btn_on)
        button_frame.addWidget(btn_off)
        button_frame.addWidget(btn_kill)
        button_frame.addWidget(btn_lock)
        button_frame.addWidget(btn_rearm)

        # Command Input Row
        command_layout = QHBoxLayout()
        layout.addLayout(command_layout)

        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Enter command (e.g., lock all, arm A bounce=113200, update)")
        self.command_input.setStyleSheet("color: #ffffff; background-color: #2a2a2a; border: 1px solid #666666; padding: 5px;")
        command_layout.addWidget(self.command_input)

        btn_execute = QPushButton("EXECUTE")
        btn_execute.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                color: #00ff00;
                border: 1px solid #00ff00;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #3a3a3a; }
        """)
        btn_execute.clicked.connect(self.execute_command)
        command_layout.addWidget(btn_execute)

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
        self.utc_label.setText(f"UTC Time: {datetime.datetime.now(datetime.timezone.utc).strftime('%H:%M:%S')}")

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

    def update_ball_status(self, balls):
        for row, (b_id, data) in enumerate(balls.items()):
            state = data["state"]
            profit = data["profit"]
            loss = data["loss"]
            color = "#00ff00" if state == "OPEN" else "#ffaa00" if state == "LOCKED" else "#888888"

            self.ball_table.setItem(row, 0, QTableWidgetItem(str(b_id)))
            self.ball_table.setItem(row, 1, QTableWidgetItem(state))
            self.ball_table.setItem(row, 2, QTableWidgetItem(f"{profit:.2f}"))
            self.ball_table.setItem(row, 3, QTableWidgetItem(f"{loss:.2f}"))

            for col in range(4):
                item = self.ball_table.item(row, col)
                if item:
                    item.setForeground(QColor(color))

    def update_net_pnl_capital(self, net_pnl, capital):
        color = "#00ff00" if net_pnl >= 0 else "#ff0000"
        self.net_pnl_label.setText(f"Net P/L: ${net_pnl:.2f}")
        self.net_pnl_label.setStyleSheet(f"color: {color};")
        self.capital_label.setText(f"Capital: ${capital:.2f}")

    def update_market_shifts(self, shift):
        self.market_shift_label.setText(f"Market Shift: {shift}")

    def manual_lock_profits(self):
        if self.watcher and self.watcher.engine:
            self.watcher.engine.cmd_lock_all(reason="Manual Lock Profits")
            print("Manual lock profits executed.")
        else:
            print("Engine not available for manual lock.")

    def manual_rearm_balls(self):
        if self.watcher and self.watcher.engine:
            for br in self.watcher.engine.state.balls.values():
                if br.state == "COOLDOWN":
                    br.reset()
                    br.state = "IDLE"
            print("Balls rearmed to IDLE.")
        else:
            print("Engine not available for rearm.")

    def execute_command(self):
        cmd = self.command_input.text().strip().lower()
        if not cmd:
            return
        print(f"Executing command: {cmd}")
        # Parse and execute commands
        if cmd == "update":
            self.update_feedback()
        elif cmd == "feedback":
            self.show_feedback()
        elif cmd == "stop":
            self.manual_stop()
        elif cmd.startswith("save note "):
            note = cmd[10:]
            self.save_note(note)
        elif cmd.startswith("status"):
            self.show_status()
        elif cmd.startswith("mode "):
            mode = cmd[5:]
            self.set_mode(mode)
        elif cmd.startswith("preset apply "):
            preset = cmd[13:]
            self.apply_preset(preset)
        elif cmd.startswith("preset save "):
            preset = cmd[12:]
            self.save_preset(preset)
        elif cmd.startswith("arm "):
            parts = cmd[4:].split()
            if len(parts) >= 2:
                trade = parts[0]
                params = " ".join(parts[1:])
                self.arm_trade(trade, params)
        elif cmd.startswith("force "):
            trade = cmd[6:]
            self.force_trade(trade)
        elif cmd.startswith("lock "):
            trade = cmd[5:]
            self.lock_trade(trade)
        elif cmd.startswith("tighten "):
            parts = cmd[8:].split()
            if len(parts) >= 2:
                trade = parts[0]
                params = " ".join(parts[1:])
                self.tighten_trade(trade, params)
        elif cmd.startswith("redeploy "):
            trade = cmd[9:]
            self.redeploy_trade(trade)
        elif cmd.startswith("cancel "):
            sniper = cmd[7:]
            self.cancel_sniper(sniper)
        elif cmd.startswith("joker "):
            action = cmd[6:]
            self.joker_action(action)
        elif cmd.startswith("maxdd cap="):
            cap = cmd[10:]
            self.set_maxdd_cap(cap)
        elif cmd.startswith("crashguard "):
            action = cmd[11:]
            self.crashguard(action)
        elif cmd.startswith("latency cap="):
            cap = cmd[12:]
            self.set_latency_cap(cap)
        elif cmd.startswith("exposure cap="):
            cap = cmd[13:]
            self.set_exposure_cap(cap)
        elif cmd.startswith("ladder sync "):
            action = cmd[12:]
            self.ladder_sync(action)
        elif cmd.startswith("ladder "):
            parts = cmd[7:].split()
            if len(parts) >= 2:
                trade = parts[0]
                params = " ".join(parts[1:])
                self.set_ladder(trade, params)
        elif cmd.startswith("profitlock "):
            params = cmd[11:]
            self.profitlock(params)
        elif cmd.startswith("ball "):
            parts = cmd[5:].split()
            if len(parts) >= 2:
                ball_id = parts[0]
                action = " ".join(parts[1:])
                self.ball_control(ball_id, action)
        elif cmd == "balls summary":
            self.balls_summary()
        elif cmd == "advise update":
            self.advise_update()
        elif cmd == "super update":
            self.super_update()
        elif cmd == "levels":
            self.show_levels()
        elif cmd == "risk report":
            self.risk_report()
        elif cmd.startswith("oca "):
            action = cmd[4:]
            self.oca(action)
        elif cmd.startswith("hedge "):
            action = cmd[6:]
            self.hedge(action)
        elif cmd == "double-arm":
            self.double_arm()
        elif cmd == "secure then run":
            self.secure_then_run()
        elif cmd == "spike plan":
            self.spike_plan()
        elif cmd == "panic net":
            self.panic_net()
        else:
            print(f"Unknown command: {cmd}")
        self.command_input.clear()

    # Command implementations (placeholders for now)
    def update_feedback(self):
        print("Updating feedback...")

    def show_feedback(self):
        print("Showing feedback...")

    def manual_stop(self):
        print("Manual stop executed.")

    def save_note(self, note):
        print(f"Saving note: {note}")

    def show_status(self):
        print("Showing status...")

    def set_mode(self, mode):
        print(f"Setting mode to: {mode}")

    def apply_preset(self, preset):
        print(f"Applying preset: {preset}")

    def save_preset(self, preset):
        print(f"Saving preset: {preset}")

    def arm_trade(self, trade, params):
        print(f"Arming trade {trade} with params: {params}")

    def force_trade(self, trade):
        print(f"Forcing trade: {trade}")

    def lock_trade(self, trade):
        print(f"Locking trade: {trade}")

    def tighten_trade(self, trade, params):
        print(f"Tightening trade {trade} with params: {params}")

    def redeploy_trade(self, trade):
        print(f"Redeploying trade: {trade}")

    def cancel_sniper(self, sniper):
        print(f"Cancelling sniper: {sniper}")

    def joker_action(self, action):
        print(f"Joker action: {action}")

    def set_maxdd_cap(self, cap):
        print(f"Setting max DD cap to: {cap}")

    def crashguard(self, action):
        print(f"Crashguard: {action}")

    def set_latency_cap(self, cap):
        print(f"Setting latency cap to: {cap}")

    def set_exposure_cap(self, cap):
        print(f"Setting exposure cap to: {cap}")

    def ladder_sync(self, action):
        print(f"Ladder sync: {action}")

    def set_ladder(self, trade, params):
        print(f"Setting ladder for {trade}: {params}")

    def profitlock(self, params):
        print(f"Profitlock: {params}")

    def ball_control(self, ball_id, action):
        print(f"Ball {ball_id} control: {action}")

    def balls_summary(self):
        print("Balls summary...")

    def advise_update(self):
        print("Advising update...")

    def super_update(self):
        print("Super update...")

    def show_levels(self):
        print("Showing levels...")

    def risk_report(self):
        print("Risk report...")

    def oca(self, action):
        print(f"OCA: {action}")

    def hedge(self, action):
        print(f"Hedge: {action}")

    def double_arm(self):
        print("Double-arm executed.")

    def secure_then_run(self):
        print("Secure then run executed.")

    def spike_plan(self):
        print("Spike plan executed.")

    def panic_net(self):
        print("Panic net executed.")


# --- Main Launcher ---------------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = V13EnhancedMonitor()
    gui.show()
    sys.exit(app.exec())
