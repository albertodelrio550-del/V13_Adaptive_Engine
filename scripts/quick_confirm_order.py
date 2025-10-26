"""
Quick confirm order: buy then close the position once to validate routing.

Uses trade_core (routes per config/V13_Config.ini [ROUTING].DEFAULT_VENUE).
Default symbol: BTCUSD (mapped to BTCUSDT on Binance Futures).
Qty: 0.001
"""

from __future__ import annotations

import time
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

from trade_core import place_market_order, close_position, _load_binance_client, _default_venue

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "orders"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def log_line(line: Dict[str, Any]):
    date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    out = DATA_DIR / f"{date}.jsonl"
    out.write_text((out.read_text(encoding="utf-8") if out.exists() else "") + json.dumps(line) + "\n", encoding="utf-8")
    # update orders_today.json
    today_path = ROOT / "data" / "orders_today.json"
    try:
        today = json.loads(today_path.read_text(encoding="utf-8")) if today_path.exists() else {"date": date, "count": 0}
    except Exception:
        today = {"date": date, "count": 0}
    if today.get("date") != date:
        today = {"date": date, "count": 0}
    today["count"] = int(today.get("count", 0)) + 1
    today_path.write_text(json.dumps(today, indent=2), encoding="utf-8")


def main():
    symbol = "BTCUSD"
    qty = 0.001
    # Debug venue/URL
    print("Venue:", _default_venue())
    bc = _load_binance_client()
    if bc is not None:
        try:
            print("Futures URL:", getattr(bc, 'FUTURES_URL', '<none>'))
        except Exception:
            pass
        try:
            acct = bc.futures_account()
            print("Futures account OK (pre-check)")
        except Exception as e:
            print("Futures account error (pre-check):", e)
    print(f"Placing BUY market {symbol} qty={qty}")
    buy = place_market_order(symbol, "buy", qty)
    print("BUY response:", buy)
    log_line({
        "order_id": f"CONFIRM-{int(time.time())}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "intent": {"symbol": symbol, "side": "BUY", "qty": qty},
        "status": "POSTED",
        "response": buy,
    })
    # brief pause for fills to register
    time.sleep(1.0)
    print("Closing position (reduceOnly) if open...")
    close = close_position(symbol)
    print("CLOSE response:", close)
    log_line({
        "order_id": f"CONFIRM-{int(time.time())}-CLOSE",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "intent": {"symbol": symbol, "side": "CLOSE"},
        "status": "CLOSED",
        "response": close,
    })
    print("Done.")


if __name__ == "__main__":
    main()
