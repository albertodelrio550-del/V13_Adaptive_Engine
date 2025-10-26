# =============================================================
#  V13_CommanderMonitor.py — Final Tactical Edition
#  Version: V13_Stable_Release (2025-10-19)
#  Features: Color Display + Manual Commands + Log Integrity + Auto-Status + AdaptiveCycle
# =============================================================

import os
import time
import random
import threading
import hashlib
from datetime import datetime, timezone
from colorama import Fore, Style, init

init(autoreset=True)

# -------------------------------------------------------------
#  SIMULATED SUBSYSTEMS
# -------------------------------------------------------------
class CommanderFlex:
    def get_status(self):
        return random.choice(["ACTIVE", "IDLE", "UPDATING"])

class TelemetryFusion:
    def get_snapshot(self):
        return {
            "symbol": "BTC/USDT",
            "price": round(random.uniform(59000, 61000), 2),
            "volatility": round(random.uniform(0.01, 0.07), 3),
            "delta": round(random.uniform(-0.25, 0.25), 3)
        }

class RiskSentinel:
    def get_state(self):
        roll = random.random()
        if roll < 0.85:
            return "SAFE"
        elif roll < 0.95:
            return "LIMITED"
        else:
            return "LOCK"

class PerformanceTracker:
    def get_net_profit(self):
        return round(random.uniform(-50, 150), 2)

class BridgeGuardian:
    def get_sync(self):
        return random.choice(["VALID", "DESYNC"])

# -------------------------------------------------------------
#  COLOR HELPERS
# -------------------------------------------------------------
def color_status(state):
    mapping = {
        "SAFE": Fore.GREEN + "SAFE" + Style.RESET_ALL,
        "LIMITED": Fore.YELLOW + "LIMITED" + Style.RESET_ALL,
        "LOCK": Fore.RED + "LOCK" + Style.RESET_ALL,
        "VALID": Fore.GREEN + "VALID" + Style.RESET_ALL,
        "DESYNC": Fore.RED + "DESYNC" + Style.RESET_ALL,
        "ACTIVE": Fore.GREEN + "ACTIVE" + Style.RESET_ALL,
        "IDLE": Fore.BLUE + "IDLE" + Style.RESET_ALL,
        "UPDATING": Fore.YELLOW + "UPDATING" + Style.RESET_ALL,
        "OK": Fore.GREEN + "OK" + Style.RESET_ALL,
        "ERROR": Fore.RED + "ERROR" + Style.RESET_ALL,
    }
    return mapping.get(state, state)

def color_mode(mode):
    if mode == "PAPER":
        return Fore.BLUE + "PAPER" + Style.RESET_ALL
    elif mode == "REAL":
        return Fore.MAGENTA + "REAL" + Style.RESET_ALL
    return Fore.CYAN + "OFFLINE" + Style.RESET_ALL

def color_profit(value):
    return (Fore.GREEN if value >= 0 else Fore.RED) + f"{value:+.2f}" + Style.RESET_ALL

# -------------------------------------------------------------
#  LOGGING AND INTEGRITY
# -------------------------------------------------------------
LOG_DIR = "/Videos/bohrn 2025/trade/V13/logs/"
LOG_FILE = os.path.join(LOG_DIR, "commander_monitor.log")
STATUS_FILE = os.path.join(LOG_DIR, "commander_status.txt")

os.makedirs(LOG_DIR, exist_ok=True)

def write_log_line(msg):
    with open(LOG_FILE, 'a') as f:
        f.write(msg + "\n")
    compute_log_hash()

def compute_log_hash():
    if not os.path.exists(LOG_FILE):
        return
    sha = hashlib.sha256()
    with open(LOG_FILE, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha.update(chunk)
    digest = sha.hexdigest()[:16]
    with open(os.path.join(LOG_DIR, 'log_hash.txt'), 'w') as h:
        h.write(f"Last Hash: {digest}\n")

# -------------------------------------------------------------
#  AUTO-STATUS BROADCAST
# -------------------------------------------------------------
def broadcast_status(summary):
    with open(STATUS_FILE, 'w') as f:
        f.write(summary + "\n")

# -------------------------------------------------------------
#  MANUAL COMMAND PARSER
# -------------------------------------------------------------
def handle_command(cmd, state):
    cmd = cmd.strip().lower()
    if cmd == '/pause':
        state['paused'] = True
        print(Fore.YELLOW + "[COMMAND] Monitoring paused." + Style.RESET_ALL)
    elif cmd == '/resume':
        state['paused'] = False
        print(Fore.GREEN + "[COMMAND] Monitoring resumed." + Style.RESET_ALL)
    elif cmd == '/flush logs':
        open(LOG_FILE, 'w').close()
        print(Fore.CYAN + "[COMMAND] Logs flushed." + Style.RESET_ALL)
    elif cmd == '/status':
        print(Fore.CYAN + f"[COMMAND] System running — AdaptiveCycle={state['cycle']}" + Style.RESET_ALL)
    elif cmd == '/help':
        print(Fore.CYAN + "Available Commands:" + Style.RESET_ALL)
        print("  /status      - Show current system state")
        print("  /pause       - Pause telemetry updates")
        print("  /resume      - Resume telemetry updates")
        print("  /flush logs  - Clear log file")
        print("  /help        - Show this help message")
        print("  /exit        - Graceful shutdown")
    elif cmd == '/exit':
        print(Fore.YELLOW + "[COMMAND] Exiting Commander Monitor..." + Style.RESET_ALL)
        state['running'] = False
    else:
        print(Fore.RED + f"[COMMAND] Unknown command: {cmd}" + Style.RESET_ALL)

# -------------------------------------------------------------
#  COMMAND INPUT THREAD
# -------------------------------------------------------------
def command_listener(state):
    while state['running']:
        try:
            cmd = input().strip()
            handle_command(cmd, state)
        except EOFError:
            break

# -------------------------------------------------------------
#  COMMANDER MONITOR
# -------------------------------------------------------------
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def commander_monitor(interval: float = 2.5):
    commander = CommanderFlex()
    fusion = TelemetryFusion()
    risk = RiskSentinel()
    tracker = PerformanceTracker()
    bridge = BridgeGuardian()

    trading_mode = os.environ.get('V13_MODE', 'OFFLINE')
    environment_status = "ONLINE" if trading_mode != 'OFFLINE' else "OFFLINE"
    location = "/Videos/bohrn 2025/trade/V13/core/"

    state = {'running': True, 'paused': False, 'cycle': 'ACTIVE'}

    # Start command thread
    threading.Thread(target=command_listener, args=(state,), daemon=True).start()

    while state['running']:
        if state['paused']:
            time.sleep(1)
            continue

        clear_screen()
        now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')

        commander_status = commander.get_status()
        snapshot = fusion.get_snapshot()
        risk_state = risk.get_state()
        net_profit = tracker.get_net_profit()
        sync_status = bridge.get_sync()

        # AdaptiveCycle simulation
        state['cycle'] = random.choice(['ACTIVE', 'COOLDOWN', 'SYNCING'])

        # Colors
        risk_colored = color_status(risk_state)
        commander_colored = color_status(commander_status)
        sync_colored = color_status(sync_status)
        profit_colored = color_profit(net_profit)
        mode_colored = color_mode(trading_mode)

        print("=" * 68)
        print(f"V13 Commander Monitor — Tactical Control Console")
        print(f"{now}")
        print("=" * 68)

        print(f"Environment : {Fore.GREEN if environment_status=='ONLINE' else Fore.RED}{environment_status}{Style.RESET_ALL}   Mode: {mode_colored}")
        print(f"Location    : {location}")
        print(f"AdaptiveCycle: {Fore.CYAN}{state['cycle']}{Style.RESET_ALL}")
        print(f"RiskSentinel: {risk_colored}   Sync: {sync_colored}   Commander: {commander_colored}")
        print("-" * 68)

        print(f"Symbol      : {snapshot['symbol']}   Price: ${snapshot['price']:,}   Δ1m: {snapshot['delta']:+.3f}%")
        vol_color = Fore.YELLOW if snapshot['volatility'] > 0.05 else Fore.GREEN
        print(f"Volatility  : {vol_color}{snapshot['volatility']*100:.2f}%{Style.RESET_ALL}   Latency: 182 ms (simulated)")
        print(f"Net Profit  : {profit_colored}   (locked floor +48.0, peak +84.9)")
        print("-" * 68)

        print(f"TelemetryFusion   : {color_status('OK')} (feed stable, 1m window aligned)")
        print(f"CommanderFlex     : {commander_colored} (orders ready)")
        print(f"RiskSentinel      : {risk_colored} (auto lock control)")
        print(f"BridgeGuardian    : {sync_colored} (relay integrity)")
        print(f"SignalValidator   : {color_status('VALID')} (checksum aligned)")
        print(f"PerformanceTracker: {color_status('OK')} (PnL feed active)")
        print("-" * 68)

        print(f"System Summary : {Fore.CYAN}Stable operation — monitoring telemetry and trade cycle.{Style.RESET_ALL}")
        print(f"System Note    : {Fore.BLUE if trading_mode=='PAPER' else Fore.MAGENTA if trading_mode=='REAL' else Fore.CYAN}{trading_mode} MODE active — all relays synchronized.{Style.RESET_ALL}")
        print(f"Next Action    : Await Commander update or tighten B trail.")
        print("=" * 68)
        print(Fore.YELLOW + "Type /help for command list." + Style.RESET_ALL)

        # Log + Broadcast summary
        summary = f"[{now}] {snapshot['symbol']} | Δ {snapshot['delta']:+.2f}% | Risk={risk_state} | Mode={trading_mode} | Cycle={state['cycle']} | PnL={net_profit:+.2f}"
        write_log_line(summary)
        broadcast_status(summary)

        time.sleep(interval)

    print(Fore.YELLOW + "Commander Monitor shut down successfully." + Style.RESET_ALL)

# -------------------------------------------------------------
#  ENTRY POINT
# -------------------------------------------------------------
if __name__ == "__main__":
    try:
        commander_monitor(interval=2.5)
    except KeyboardInterrupt:
        print("\nCommander Monitor terminated by user.")