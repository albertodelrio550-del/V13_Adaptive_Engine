"""
paper_order_bridge.py — V13 Manual Trading Framework
Build: 2025-10-18
Phase: 3 — Paper Order Bridge (PnL Simulation)

Purpose
-------
Simulate order lifecycle and PnL tracking for OFFENSE / HOLD / DEFENSE modes.
Acts as a virtual bridge between Commander decisions and result telemetry.

This bridge NEVER sends real trades. It is a 100% paper simulation.
"""

import time
import json
import os
from typing import List, Dict


# ─────────────────────────────────────────────────────────────
# ⚙️ CONFIGURATION DEFAULTS
# ─────────────────────────────────────────────────────────────
DEFAULT_TP_USD = 10.0      # take-profit per simulated order
DEFAULT_SL_USD = 5.0       # stop-loss per simulated order
DEFAULT_MAX_DRAWDOWN = -150.0  # emergency cut level
LOG_PATH = "logs/session_log.json"


# ─────────────────────────────────────────────────────────────
# 💰 PAPER ORDER CLASS
# ─────────────────────────────────────────────────────────────
class PaperOrder:
    """Simulates a basic long/short order in paper mode."""

    def __init__(self, symbol: str, side: str, entry_price: float, capital: float):
        self.symbol = symbol
        self.side = side.upper()
        self.entry_price = entry_price
        self.capital = capital
        self.open_time = time.time()
        self.closed = False
        self.exit_price = None
        self.pnl = 0.0

    def update(self, current_price: float):
        """Recalculate unrealized PnL."""
        if self.closed:
            return self.pnl

        diff = (current_price - self.entry_price)
        if self.side == "SHORT":
            diff *= -1
        self.pnl = diff * (self.capital / self.entry_price)
        return self.pnl

    def close(self, price: float):
        """Close position and finalize PnL."""
        if not self.closed:
            self.exit_price = price
            self.closed = True
            self.update(price)
        return self.pnl


# ─────────────────────────────────────────────────────────────
# 🧩 PAPER ORDER BRIDGE
# ─────────────────────────────────────────────────────────────
class PaperOrderBridge:
    """Handles paper-only order logic and PnL simulation."""

    def __init__(self):
        self.orders: List[PaperOrder] = []
        self.virtual_balance = 0.0
        self.last_pnl = 0.0
        self.max_drawdown = DEFAULT_MAX_DRAWDOWN

    # ─────────────────────────────────────────
    # TRADE MANAGEMENT
    # ─────────────────────────────────────────
    def open_trade(self, symbol: str, side: str, price: float, capital: float):
        order = PaperOrder(symbol, side, price, capital)
        self.orders.append(order)
        print(f"[Bridge] Opened {side} @ {price} for {symbol}")

    def update_trades(self, current_price: float):
        """Update all open orders and check TP/SL."""
        active_orders = []
        for order in self.orders:
            pnl = order.update(current_price)
            # Check TP/SL thresholds
            if pnl >= DEFAULT_TP_USD:
                print(f"[Bridge] TP reached ({pnl:.2f}) — closing order.")
                order.close(current_price)
                self.virtual_balance += pnl
            elif pnl <= -DEFAULT_SL_USD:
                print(f"[Bridge] SL hit ({pnl:.2f}) — closing order.")
                order.close(current_price)
                self.virtual_balance += pnl
            else:
                active_orders.append(order)

        self.orders = active_orders
        self.last_pnl = sum([o.pnl for o in self.orders])
        return self.last_pnl

    def close_all(self, price: float):
        """Force close all open trades."""
        for order in self.orders:
            order.close(price)
            self.virtual_balance += order.pnl
        self.orders.clear()
        print("[Bridge] All trades closed.")

    # ─────────────────────────────────────────
    # RISK MANAGEMENT
    # ─────────────────────────────────────────
    def check_drawdown(self):
        total_pnl = self.virtual_balance + self.last_pnl
        if total_pnl <= self.max_drawdown:
            print(f"⚠️ [Bridge] Max drawdown hit ({total_pnl:.2f}). Triggering emergency close.")
            self.close_all(self.orders[-1].entry_price if self.orders else 0)
        return total_pnl

    # ─────────────────────────────────────────
    # TELEMETRY OUTPUT
    # ─────────────────────────────────────────
    def export_state(self) -> Dict:
        return {
            "virtual_pnl": round(self.virtual_balance + self.last_pnl, 2),
            "positions": [
                {
                    "symbol": o.symbol,
                    "side": o.side,
                    "entry_price": o.entry_price,
                    "pnl": round(o.pnl, 2),
                    "closed": o.closed
                } for o in self.orders
            ]
        }


# ─────────────────────────────────────────────────────────────
# 🧮 COMMANDER-INTEGRATION EXAMPLE
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    bridge = PaperOrderBridge()

    # Simulated commander actions
    bridge.open_trade("BTC/USD", "LONG", 120_000, 1000)
    time.sleep(1)
    bridge.update_trades(120_600)
    time.sleep(1)
    bridge.update_trades(120_800)
    time.sleep(1)
    bridge.update_trades(119_800)
    bridge.check_drawdown()

    print("\nCurrent bridge state:")
    print(json.dumps(bridge.export_state(), indent=2))
