# ============================================================
# V13_COMMANDER_VISUAL_INTELLIGENCE.PY
# Build: V13.2025.10.21.02
# Mode: PAPER (Data-linked hybrid with Ball Activity Pulse)
# ============================================================

"""
Purpose:
    Commander Visual Intelligence Monitor (C.V.I.M.)
    Displays real-time doctrine status, market environment, and simulated
    performance feedback from registry + datamap.

    Hybrid PAPER-safe mode:
        • Reads: /data/V13_DataMap.json, /data/doctrine_registry.json, /config/V13_RiskSentinel_Config.json
        • Synthesizes: PnL, accuracy, confidence, ball status, volatility & AMD phase
        • Displays immersive Commander dashboard with doctrine performance table & animated Ball Pulse

    Logs output to /logs/visual_intel_feed.log.
"""

import json, os, random, time, itertools
from datetime import datetime
from colorama import Fore, Style, init

init(autoreset=True)

# ------------------------------------------------------------
# PATHS
# ------------------------------------------------------------

data_map_path = "data/V13_DataMap.json"
doctrine_registry_path = "data/doctrine_registry.json"
risk_config_path = "config/V13_RiskSentinel_Config.json"
log_path = "logs/visual_intel_feed.log"

# ------------------------------------------------------------
# FILE LOADING UTILITIES
# ------------------------------------------------------------

def load_json(path, default={}):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return default

# ------------------------------------------------------------
# SYNTHETIC PERFORMANCE GENERATORS (PAPER SAFE)
# ------------------------------------------------------------

def synthesize_performance(name):
    pnl = round(random.uniform(-120, 320), 1)
    accuracy = round(random.uniform(0.70, 0.96), 3)
    confidence = "✅✅" if accuracy > 0.82 else ("✅" if accuracy > 0.75 else "⚠️")
    trades = random.randint(2, 7)
    wins = random.randint(int(trades/2), trades)
    win_rate = int((wins / trades) * 100)
    status = random.choice(["ACTIVE", "SCANNING", "STANDBY", "WAITING"])
    return {
        "PnL": pnl,
        "accuracy": accuracy,
        "confidence": confidence,
        "status": status,
        "trades": f"{wins}/{trades}",
        "win_rate": f"{win_rate}%"
    }

# ------------------------------------------------------------
# BALL STATUS PULSE ANIMATION
# ------------------------------------------------------------

ball_patterns = itertools.cycle([
    "🟢🟡⚪", "🟢🟢⚪", "🟢🟢🟡", "🟢🟢🟢", "🟢🟡⚪"
])

def get_ball_status(active=True):
    if not active:
        return random.choice(["⚪⚪⚪", "🟡⚪⚪"])
    return next(ball_patterns)

# ------------------------------------------------------------
# COMMANDER + MARKET CONTEXT
# ------------------------------------------------------------

def get_market_context(datamap):
    market = datamap.get("symbol", "BTC/USD")
    exchange = datamap.get("exchange", "PaperNet")
    feed = datamap.get("feed_type", "Simulated")
    volatility = round(random.uniform(1.0, 2.2), 2)
    amd_phase = random.choice(["Accumulation", "Manipulation", "Distribution"])
    bias = random.choice(["Bullish", "Bearish", "Neutral"])
    price = random.randint(65000, 67000)
    spread = round(random.uniform(5.0, 15.0), 2)
    liquidity = random.choice(["High", "Moderate", "Low"])
    return {
        "market": market,
        "exchange": exchange,
        "feed": feed,
        "volatility": volatility,
        "amd_phase": amd_phase,
        "bias": bias,
        "price": price,
        "spread": spread,
        "liquidity": liquidity
    }

# ------------------------------------------------------------
# COMMANDER STATUS
# ------------------------------------------------------------

def commander_status(risk):
    stage = risk.get("Stage", 4)
    discipline = random.randint(80, 95)
    override = risk.get("ManualOverride", "SEMI")
    deployed_capital = round(random.uniform(60, 80), 1)
    return {
        "stage": stage,
        "discipline": discipline,
        "override": override,
        "deployed_capital": deployed_capital
    }

# ------------------------------------------------------------
# DISPLAY FUNCTION
# ------------------------------------------------------------

def render_dashboard():
    datamap = load_json(data_map_path)
    registry = load_json(doctrine_registry_path)
    risk = load_json(risk_config_path)

    doctrines = registry.keys() if registry else ["Fabio", "Marco", "Tanja", "TG_Capital", "Kane", "Mayne", "Umar"]
    market = get_market_context(datamap)
    commander = commander_status(risk)

    # Commander header
    print(Fore.WHITE + Style.BRIGHT + "\n===================== [COMMANDER VISUAL INTELLIGENCE] =====================")
    print(Fore.LIGHTBLACK_EX + f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(
        f"Commander Stage: {Fore.CYAN}{commander['stage']} {Fore.WHITE}| "
        f"Discipline: {Fore.GREEN}{commander['discipline']}% {Fore.WHITE}| "
        f"Override: {Fore.YELLOW}{commander['override']} {Fore.WHITE}| "
        f"Deployed Capital: {Fore.LIGHTWHITE_EX}{commander['deployed_capital']}%"
    )

    print(
        f"Active Doctrine: {Fore.LIGHTBLUE_EX}Marco (Liquidity Trap Engagement){Fore.WHITE}\n"
        f"Volatility: {Fore.RED}{market['volatility']} {Fore.WHITE}| AMD Phase: {Fore.YELLOW}{market['amd_phase']} "
        f"{Fore.WHITE}| Bias: {Fore.RED if market['bias']=='Bearish' else Fore.GREEN}{market['bias']}"
    )
    print(
        f"Market Context: {Fore.CYAN}{market['market']} {Fore.WHITE}| Exchange: {Fore.LIGHTBLACK_EX}{market['exchange']} "
        f"{Fore.WHITE}| Price: {Fore.GREEN}{market['price']} | Spread: {Fore.LIGHTBLACK_EX}{market['spread']} | Liquidity: {Fore.CYAN}{market['liquidity']}\n"
    )

    # Doctrine table
    print(Fore.LIGHTWHITE_EX + "Doctrine        | Status    | Capital | Accuracy |  PnL($) | Confidence | Trades | Win % | Market Info | Ball Status")
    print(Fore.LIGHTBLACK_EX + "---------------------------------------------------------------------------------------------------------------")

    total_cap = 0
    total_pnl = 0
    total_trades = 0
    total_wins = 0

    for doctrine in doctrines:
        perf = synthesize_performance(doctrine)
        cap = round(random.uniform(5, 18), 1)
        total_cap += cap
        total_pnl += perf['PnL']

        win_split = perf['trades'].split('/')
        wins = int(win_split[0])
        trades = int(win_split[1])
        total_wins += wins
        total_trades += trades

        pulse = get_ball_status(perf['status'] == 'ACTIVE')

        print(
            f"{Fore.CYAN if doctrine!='Umar' else Fore.MAGENTA}{doctrine:<14}{Fore.WHITE}| {perf['status']:<9}| {cap:>6}%   | {perf['accuracy']*100:>6.1f}%   | {perf['PnL']:>6}   | {perf['confidence']:<10}| "
            f"{perf['trades']:<6}| {perf['win_rate']:<6}| {market['market']} {Fore.GREEN if market['bias']=='Bullish' else Fore.RED}{market['bias']:<8}{Fore.WHITE}| {pulse}"
        )

    print(Fore.LIGHTBLACK_EX + "---------------------------------------------------------------------------------------------------------------")

    global_win_rate = (total_wins / total_trades) * 100 if total_trades else 0
    print(
        f"Total Active Capital: {Fore.CYAN}{round(total_cap,1)}% {Fore.WHITE}| Net Session PnL: {Fore.GREEN if total_pnl>=0 else Fore.RED}{round(total_pnl,1)} "
        f"{Fore.WHITE}| Open Trades: {Fore.CYAN}{total_trades} {Fore.WHITE}| Global Win Rate: {Fore.YELLOW}{global_win_rate:.1f}%"
    )
    print(Fore.LIGHTBLACK_EX + "---------------------------------------------------------------------------------------------------------------\n")

    # Adaptive Commander Speech Feed
    key_doctrine = max(doctrines, key=lambda d: synthesize_performance(d)["accuracy"])
    worst_doctrine = min(doctrines, key=lambda d: synthesize_performance(d)["PnL"])
    market_condition = "volatile" if market['volatility'] > 1.7 else "stable"

    speech_bank = [
        f"{key_doctrine} Doctrine showing superior accuracy under {market_condition} conditions — commendable control.",
        f"{worst_doctrine} Doctrine facing drawdown — initiating recalibration protocol.",
        f"Volatility at {market['volatility']} — Commander adjusting risk bias for synchronization.",
        f"Umar Doctrine monitoring discipline coherence — confidence integrity intact.",
        f"Commander confirms {market['market']} bias {market['bias']} — maintain adaptive posture."
    ]

    print(Fore.MAGENTA + Style.BRIGHT + f"🎙️  {random.choice(speech_bank)}")
    if random.random() > 0.5:
        print(Fore.MAGENTA + Style.BRIGHT + "🎙️  System morale optimal — doctrines synchronized.\n")
    else:
        print(Fore.MAGENTA + Style.BRIGHT + "🎙️  Adjusting engagement spread — feedback loop active.\n")
    print(Fore.LIGHTBLACK_EX + "==========================================================================\n")

    # Logging
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(f"[{datetime.now().isoformat()}] Visual cycle rendered. Market={market['market']} Vol={market['volatility']} Bias={market['bias']}\n")

# ------------------------------------------------------------
# MAIN LOOP (PAPER SIMULATION)
# ------------------------------------------------------------

def simulate_commander_visual(cycles=6, delay=1.5):
    print("\n=== V13 Commander Visual Intelligence — PAPER MODE (with Pulse) ===")
    for _ in range(cycles):
        render_dashboard()
        time.sleep(delay)
    print(Fore.GREEN + Style.BRIGHT + "\n[V13] Commander Visual Intelligence Simulation Complete.\n")

# ------------------------------------------------------------
# ENTRY POINT
# ------------------------------------------------------------

if __name__ == "__main__":
    simulate_commander_visual()

# ============================================================
# END OF V13_CommanderVisualIntelligence.py (with Ball Pulse)
# ============================================================
