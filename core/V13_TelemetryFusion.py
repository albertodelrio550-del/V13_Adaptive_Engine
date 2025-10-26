"""TelemetryFusion — simplified but functional for PAPER mode.

This restores a simplified version of the module while being defensive
about optional heavy dependencies (like numpy). It simulates market
feed values for PAPER testing and exposes a small DataMap used by other
components.
"""

from datetime import datetime
import os
import random
import json

try:
    import numpy as np
except Exception:
    np = None


class TelemetryFeed:
    def __init__(self):
        # Basic config for PAPER testing
        self.refresh_rate = 1.0
        self.mode = 'PAPER'
        self.feed_symbols = ['BTC/USD']
        self.data_map = {s: {'price': 0.0, 'delta': 0.0, 'volume': 0, 'timestamp': None, 'doctrine_link': None} for s in self.feed_symbols}
        print("[TelemetryFusion] initialized (simplified PAPER mode)")

    def _simulate_feed(self, core_trade):
        base_price = random.uniform(10000, 70000)
        delta = random.uniform(-0.5, 0.5)
        volume = random.uniform(100, 10000)
        price = round(base_price * (1 + delta / 100), 2)

        self.data_map[core_trade]['price'] = price
        self.data_map[core_trade]['delta'] = delta
        self.data_map[core_trade]['volume'] = int(volume)
        self.data_map[core_trade]['timestamp'] = datetime.now().strftime('%H:%M:%S')

        return {
            'symbol': core_trade,
            'price': price,
            'delta': round(delta, 3),
            'volume': int(volume),
            'pnl': self._mock_pnl(delta),
            'timestamp': self.data_map[core_trade]['timestamp'],
        }

    def _mock_pnl(self, delta):
        return round(delta * random.uniform(5, 15), 2)

    def get_market_snapshot(self, core_trade):
        if core_trade not in self.feed_symbols:
            core_trade = self.feed_symbols[0]
        if self.mode == 'PAPER':
            return self._simulate_feed(core_trade)
        else:
            # live feed path not implemented in this simplified version
            return self._simulate_feed(core_trade)

    def get_data(self, core_trade):
        return self.data_map.get(core_trade, {'error': 'Trade not found'})

    def show_datamap(self):
        print('\n[TelemetryFusion] DataMap Snapshot:')
        for sym, v in self.data_map.items():
            print(f"  {sym}: price={v['price']} delta={v['delta']} vol={v['volume']}")


        base_price = random.uniform(10000, 70000)
        delta = random.uniform(-0.5, 0.5)
        volume = random.uniform(100, 10000)
        price = round(base_price * (1 + delta / 100), 2)

        self.data_map[core_trade]["price"] = price
        self.data_map[core_trade]["delta"] = delta
        self.data_map[core_trade]["volume"] = volume
        self.data_map[core_trade]["timestamp"] = datetime.now().strftime("%H:%M:%S")
        self.data_map[core_trade]["doctrine_link"] = self._find_doctrine_link(core_trade)

        return {
            "symbol": core_trade,
            "price": price,
            "delta": round(delta, 3),
            "volume": int(volume),
            "pnl": self._mock_pnl(delta),
            "timestamp": self.data_map[core_trade]["timestamp"],
        }

    # ---------------------------------------------------------------
    def _mock_pnl(self, delta):
        """Simple PnL simulation for PAPER feed."""
        return round(delta * random.uniform(5, 15), 2)

    # ---------------------------------------------------------------
    def _get_live_feed(self, core_trade):
        """Placeholder for future API integration."""
        print(f"⚠️ [TelemetryFusion] Live mode not yet implemented for {core_trade}.")
        return self._simulate_feed(core_trade)

    # ---------------------------------------------------------------
    def _find_doctrine_link(self, symbol):
        """Match telemetry symbol to a doctrine Core_Trade (for DDS mapping)."""
        doctrine_path = os.path.join(
            os.getcwd(), "Videos", "bohrn 2025", "trade", "V13", "docs", "Doctrine_V13"
        )

        for file in os.listdir(doctrine_path):
            if file.endswith(".json"):
                file_path = os.path.join(doctrine_path, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if data.get("Core_Trade") == symbol:
                            return data.get("Doctrine_Name")
                except Exception:
                    continue
        return None

    # ---------------------------------------------------------------
    def get_data(self, core_trade):
        """DDS-accessible data retriever for feedback modules."""
        if core_trade in self.data_map:
            return self.data_map[core_trade]
        else:
            return {"error": "Trade not found"}

    # ---------------------------------------------------------------
    def show_datamap(self):
        """Display full DataMap state for diagnostics."""
        print("\n🧩 [TelemetryFusion] Current DataMap Snapshot:")
        for sym, values in self.data_map.items():
            print(f"   {sym}: Price={values['price']} Δ={values['delta']} Vol={values['volume']} Link={values['doctrine_link']}")

    def emit_telemetry_update(self):
        """
        Emit TELEMETRY_UPDATE every 10s with simulated PAPER feed.
        """
        import time
        import threading

        def broadcast_loop():
            while True:
                # Generate simulated telemetry
                telemetry = {
                    "symbol": "BTCUSDT",
                    "net_pnl": round(random.uniform(50, 75), 1),
                    "drawdown": round(random.uniform(-5, -1), 1),
                    "volatility": round(random.uniform(0.1, 0.5), 2),
                    "timestamp": int(time.time())
                }
                print(f"[TelemetryFusion] Emitting TELEMETRY_UPDATE: {telemetry}")

                # Emit via SyncLoop
                try:
                    from core.V13_SyncLoop import emit_event
                    emit_event("TELEMETRY_UPDATE", telemetry)
                except ImportError:
                    pass  # SyncLoop not available

                # Trigger RiskSentinel processing
                try:
                    from core.V13_RiskSentinel import RiskMonitor
                    rm = RiskMonitor()
                    rm.monitor_telemetry(telemetry)
                except ImportError:
                    pass  # RiskSentinel not available

                time.sleep(10)  # Emit every 10 seconds

        # Start broadcast thread
        thread = threading.Thread(target=broadcast_loop, daemon=True)
        thread.start()

# ---------------------------------------------------------------------
# DIAGNOSTIC EXECUTION
# ---------------------------------------------------------------------
if __name__ == "__main__":
    tf = TelemetryFeed()
    snapshot = tf.get_market_snapshot("BTC/USDT")
    print("Sample Feed →", snapshot)
    tf.show_datamap()
    tf.emit_telemetry_update()
