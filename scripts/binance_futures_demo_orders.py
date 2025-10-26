"""
Binance Futures (UM) Testnet Demo Orders — python-binance client

Uses python-binance's futures_* endpoints with testnet URL override.
"""

from __future__ import annotations

import os
import json
import time
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any

from binance.client import Client
from binance.exceptions import BinanceAPIException

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "orders"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return {}


def load_keys() -> Dict[str, str]:
    k = os.getenv("BINANCE_API_KEY")
    s = os.getenv("BINANCE_API_SECRET")
    if k and s:
        return {"api_key": k, "api_secret": s}
    cfg = _read_json(ROOT / "config" / "binance_keys.json")
    if cfg.get("api_key") and cfg.get("api_secret"):
        return {"api_key": cfg["api_key"], "api_secret": cfg["api_secret"]}
    raise RuntimeError("Binance keys not found.")


def log_order_line(line: Dict[str, Any]):
    date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    out_path = DATA_DIR / f"{date}.jsonl"
    with out_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(line) + "\n")
    today_path = ROOT / "data" / "orders_today.json"
    today = _read_json(today_path)
    if today.get("date") != date:
        today = {"date": date, "count": 0}
    today["count"] = int(today.get("count", 0)) + 1
    with today_path.open("w", encoding="utf-8") as f:
        json.dump(today, f, indent=2)


def main():
    import sys
    cycles = 4
    symbol = "BTCUSDT"
    if len(sys.argv) >= 2:
        if sys.argv[1].isdigit():
            cycles = int(sys.argv[1])
        else:
            symbol = sys.argv[1].upper()
    if len(sys.argv) >= 3 and sys.argv[2].isdigit():
        cycles = int(sys.argv[2])

    keys = load_keys()
    c = Client(keys["api_key"], keys["api_secret"])  # python-binance
    # Force futures testnet
    c.FUTURES_URL = c.FUTURES_TESTNET_URL
    print("Futures URL:", c.FUTURES_URL)

    # Account sanity
    try:
        acct = c.futures_account()
        print("Futures account OK. Can place orders.")
    except BinanceAPIException as e:
        print("Futures account error:", e)
        return 2

    # Discover minQty
    min_qty = Decimal("0.001")
    try:
        info = c.futures_exchange_info()
        for s in info.get("symbols", []):
            if s.get("symbol") == symbol:
                for f in s.get("filters", []):
                    if f.get("filterType") == "LOT_SIZE":
                        min_qty = Decimal(str(f.get("minQty", "0.001")))
                break
    except Exception:
        pass

    qty = str(min_qty)
    successes = 0
    for i in range(1, cycles + 1):
        tag = f"FUT-DEMO-{i}-{int(time.time())}"
        print(f"[{i}/4] BUY market {symbol} qty={qty}")
        try:
            buy = c.futures_create_order(symbol=symbol, side="BUY", type="MARKET", quantity=qty)
            time.sleep(0.8)
            print("Close position (reduceOnly) SELL")
            sell = c.futures_create_order(symbol=symbol, side="SELL", type="MARKET", quantity=qty, reduceOnly=True)
            successes += 1
            log_order_line({
                "order_id": tag,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "intent": {"venue": "UMFUT", "symbol": symbol, "side": "BUY_SELL", "qty": qty},
                "status": "CYCLE_OK",
                "response": {"buy": {"orderId": buy.get("orderId")}, "sell": {"orderId": sell.get("orderId")}}
            })
        except BinanceAPIException as e:
            print("Futures order error:", e)
            log_order_line({
                "order_id": tag,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "intent": {"venue": "UMFUT", "symbol": symbol, "side": "BUY_SELL", "qty": qty},
                "status": "ERROR",
                "error": str(e)
            })
        time.sleep(1.0)

    print(f"Done. Successful cycles: {successes}/4")
    return 0 if successes > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
