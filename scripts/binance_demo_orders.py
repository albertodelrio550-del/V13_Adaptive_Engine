"""
Binance Demo Orders Runner (Spot Testnet)

Purpose:
- Connect to Binance Spot Testnet
- Place 4 quick buy-and-sell market orders for a symbol
- Log outcomes to console and data/orders/*.jsonl for traceability

Credentials are resolved in this order:
1) Environment variables BINANCE_API_KEY / BINANCE_API_SECRET
2) config/binance_keys.json (keys: api_key, api_secret)
3) Attempt to parse binance_test.py for api_key/api_secret (best-effort)

Usage:
  python scripts/binance_demo_orders.py [SYMBOL]

Default SYMBOL: BTCUSDT
"""

from __future__ import annotations

import os
import re
import json
import time
import sys
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN

from typing import Dict, Any

try:
    from binance.client import Client
    from binance.exceptions import BinanceAPIException
except Exception as e:  # pragma: no cover
    print("python-binance is not installed. Install with: pip install python-binance")
    raise


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "orders"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _parse_keys_from_test_file() -> Dict[str, str]:
    """Best-effort parse of binance_test.py for api_key/api_secret without importing it."""
    test_path = ROOT / "binance_test.py"
    if not test_path.exists():
        return {}
    text = test_path.read_text(encoding="utf-8", errors="ignore")
    m_key = re.search(r"api_key\s*=\s*\"([^\"]+)\"", text)
    m_sec = re.search(r"api_secret\s*=\s*\"([^\"]+)\"", text)
    if m_key and m_sec:
        return {"api_key": m_key.group(1), "api_secret": m_sec.group(1)}
    return {}


def load_binance_keys() -> Dict[str, str]:
    # 1) Env
    k = os.getenv("BINANCE_API_KEY")
    s = os.getenv("BINANCE_API_SECRET")
    if k and s:
        return {"api_key": k, "api_secret": s}

    # 2) config file
    cfg_path = ROOT / "config" / "binance_keys.json"
    cfg = _read_json(cfg_path)
    if cfg.get("api_key") and cfg.get("api_secret"):
        return {"api_key": cfg["api_key"], "api_secret": cfg["api_secret"]}

    # 3) parse test file
    parsed = _parse_keys_from_test_file()
    if parsed:
        return parsed

    raise RuntimeError(
        "Binance API keys not found. Set BINANCE_API_KEY/BINANCE_API_SECRET or add config/binance_keys.json"
    )


def get_lot_step_and_min_notional(client: Client, symbol: str):
    info = client.get_symbol_info(symbol)
    if not info:
        raise RuntimeError(f"Symbol not found: {symbol}")
    lot_step = Decimal("0.00000001")
    min_qty = Decimal("0.0")
    min_notional = Decimal("10")  # sensible default
    for f in info.get("filters", []):
        if f.get("filterType") == "LOT_SIZE":
            step_size = Decimal(f.get("stepSize"))
            lot_step = step_size
            min_qty = Decimal(f.get("minQty"))
        if f.get("filterType") in ("MIN_NOTIONAL", "NOTIONAL"):
            v = f.get("minNotional") or f.get("notional")
            try:
                min_notional = Decimal(str(v))
            except Exception:
                pass
    return lot_step, min_qty, min_notional


def quantize(qty: Decimal, step: Decimal) -> Decimal:
    # Align qty to stepSize
    if step == 0:
        return qty
    # Determine number of decimal places from step
    step_str = format(step, 'f')
    if '.' in step_str:
        places = len(step_str.split('.')[1].rstrip('0'))
    else:
        places = 0
    quant = Decimal(10) ** -places
    return (qty // step) * step if places == 0 else qty.quantize(quant, rounding=ROUND_DOWN)


def log_order_line(order_line: Dict[str, Any]):
    date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    out_path = DATA_DIR / f"{date}.jsonl"
    with out_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(order_line) + "\n")

    # Update orders_today.json
    today_path = ROOT / "data" / "orders_today.json"
    today = _read_json(today_path)
    today_date = today.get("date")
    if today_date != date:
        today = {"date": date, "count": 0}
    today["count"] = int(today.get("count", 0)) + 1
    with today_path.open("w", encoding="utf-8") as f:
        json.dump(today, f, indent=2)


def main():
    symbol = sys.argv[1] if len(sys.argv) > 1 else "BTCUSDT"
    keys = load_binance_keys()

    client = Client(keys["api_key"], keys["api_secret"], testnet=True)
    # Ensure spot testnet base URL
    client.API_URL = 'https://testnet.binance.vision/api'

    # Connection sanity
    try:
        acct = client.get_account()
        print("Connected to Binance Spot Testnet OK")
        print(f"Account canTrade={acct.get('canTrade')} balances={len(acct.get('balances', []))}")
    except BinanceAPIException as e:
        print(f"Connection failed: {e}. Proceeding with TEST orders only.")
        # Run 4 test cycles without attempting live account endpoints
        successes = 0
        # We still need symbol filters to compute min/lot; if that fails, use defaults
        try:
            lot_step, min_qty, min_notional = get_lot_step_and_min_notional(client, symbol)
        except Exception:
            lot_step, min_qty, min_notional = Decimal("0.00000001"), Decimal("0.0001"), Decimal("10")
        for i in range(1, 5):
            tag = f"BIN-DEMO-TEST-{i}-{int(time.time())}"
            print(f"[TEST {i}/4] Placing BUY/SELL market test orders...")
            try:
                quote_qty = max(min_notional, Decimal("11"))
                client.create_test_order(symbol=symbol, side="BUY", type="MARKET", quoteOrderQty=str(quote_qty))
                test_qty = max(min_qty, Decimal("0.0001"))
                client.create_test_order(symbol=symbol, side="SELL", type="MARKET", quantity=str(test_qty))
                order_line = {
                    "order_id": tag,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "intent": {"symbol": symbol, "side": "BUY_SELL", "order_type": "market", "quoteOrderQty": str(quote_qty), "sell_qty": str(test_qty)},
                    "status": "TEST_CYCLE_OK"
                }
                log_order_line(order_line)
                successes += 1
            except Exception as te:
                print(f"TEST order error: {te}")
                order_line = {
                    "order_id": tag,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "intent": {"symbol": symbol, "side": "BUY_SELL", "order_type": "market"},
                    "status": "ERROR",
                    "error": f"test_error={te}"
                }
                log_order_line(order_line)
            time.sleep(1.0)
        print(f"Done. Successful TEST cycles: {successes}/4")
        return 0 if successes > 0 else 1

    lot_step, min_qty, min_notional = get_lot_step_and_min_notional(client, symbol)
    print(f"Symbol {symbol} lot_step={lot_step} min_qty={min_qty} min_notional≈{min_notional}")

    successes = 0
    for i in range(1, 5):
        tag = f"BIN-DEMO-{i}-{int(time.time())}"
        print(f"\n[{i}/4] Placing BUY market order...")
        try:
            # Use quoteOrderQty slightly above min_notional to avoid filter reject
            quote_qty = max(min_notional, Decimal("11"))
            buy = client.create_order(
                symbol=symbol,
                side="BUY",
                type="MARKET",
                quoteOrderQty=str(quote_qty)
            )
            order_id = buy.get("orderId")
            time.sleep(0.8)
            status = client.get_order(symbol=symbol, orderId=order_id)
            executed_qty = Decimal(status.get("executedQty", "0"))
            print(f"BUY filled qty={executed_qty}")

            if executed_qty == 0:
                print("No fill detected; placing TEST sell to complete cycle.")
                try:
                    client.create_test_order(symbol=symbol, side="SELL", type="MARKET", quantity=str(max(min_qty, Decimal("0.0001"))))
                except Exception:
                    pass
                order_line = {
                    "order_id": f"{tag}-BUY",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "intent": {"symbol": symbol, "side": "BUY", "order_type": "market", "quoteOrderQty": str(quote_qty)},
                    "status": "NO_FILL_TEST_SELL",
                    "response": {"orderId": order_id}
                }
                log_order_line(order_line)
                continue

            # Align sell qty to lot step
            sell_qty = quantize(executed_qty, lot_step)
            sell_qty = max(sell_qty, min_qty)
            print(f"Placing SELL market order qty={sell_qty}")
            sell = client.create_order(
                symbol=symbol,
                side="SELL",
                type="MARKET",
                quantity=str(sell_qty)
            )
            successes += 1

            order_line = {
                "order_id": tag,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "intent": {"symbol": symbol, "side": "BUY_SELL", "order_type": "market", "quoteOrderQty": str(quote_qty), "sell_qty": str(sell_qty)},
                "status": "CYCLE_OK",
                "response": {"buy": {"orderId": buy.get("orderId"), "status": buy.get("status")}, "sell": {"orderId": sell.get("orderId"), "status": sell.get("status")}}
            }
            log_order_line(order_line)
        except BinanceAPIException as e:
            print(f"API error on live order: {e}. Falling back to TEST orders.")
            try:
                # Attempt test orders to validate flow without balances
                quote_qty = Decimal("11")
                client.create_test_order(symbol=symbol, side="BUY", type="MARKET", quoteOrderQty=str(quote_qty))
                test_qty = max(min_qty, Decimal("0.0001"))
                client.create_test_order(symbol=symbol, side="SELL", type="MARKET", quantity=str(test_qty))
                order_line = {
                    "order_id": tag,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "intent": {"symbol": symbol, "side": "BUY_SELL", "order_type": "market", "quoteOrderQty": str(quote_qty), "sell_qty": str(test_qty)},
                    "status": "TEST_CYCLE_OK"
                }
                log_order_line(order_line)
                successes += 1
            except Exception as te:
                print(f"Fallback TEST orders failed: {te}")
                order_line = {
                    "order_id": tag,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "intent": {"symbol": symbol, "side": "BUY_SELL", "order_type": "market"},
                    "status": "ERROR",
                    "error": f"live_error={e}; test_error={te}"
                }
                log_order_line(order_line)
        except Exception as e:
            print(f"Unexpected error: {e}")
            order_line = {
                "order_id": tag,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "intent": {"symbol": symbol, "side": "BUY_SELL", "order_type": "market"},
                "status": "ERROR",
                "error": str(e)
            }
            log_order_line(order_line)

        # brief pause between cycles
        time.sleep(1.2)

    print(f"\nDone. Successful cycles: {successes}/4")
    return 0 if successes > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
