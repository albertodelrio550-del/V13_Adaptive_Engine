"""
Binance Spot Testnet confirm order: BUY then SELL on BTCUSDT.

Requires Spot Testnet API keys (https://testnet.binance.vision) with Spot trading enabled.
"""

from __future__ import annotations

import os
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from binance.client import Client
from binance.exceptions import BinanceAPIException

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "orders"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_keys():
    cfg = ROOT / 'config' / 'binance_keys.json'
    j = json.loads(cfg.read_text(encoding='utf-8-sig')) if cfg.exists() else {}
    k = os.getenv('BINANCE_API_KEY') or j.get('api_key')
    s = os.getenv('BINANCE_API_SECRET') or j.get('api_secret')
    if not k or not s:
        raise SystemExit('Missing BINANCE_API_KEY / BINANCE_API_SECRET or config/binance_keys.json')
    return k, s


def log_line(line: dict):
    date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    out = DATA_DIR / f"{date}.jsonl"
    out.write_text((out.read_text(encoding='utf-8') if out.exists() else '') + json.dumps(line) + "\n", encoding='utf-8')


def main():
    api_key, api_secret = load_keys()
    c = Client(api_key, api_secret, testnet=True)
    c.API_URL = 'https://testnet.binance.vision/api'

    try:
        acct = c.get_account()
        print('Spot account OK. canTrade=', acct.get('canTrade'))
    except BinanceAPIException as e:
        print('Spot account error:', e)
        return 2

    symbol = 'BTCUSDT'
    qty = '0.001'
    try:
        print('Placing BUY market', symbol, 'qty=', qty)
        buy = c.create_order(symbol=symbol, side='BUY', type='MARKET', quantity=qty)
        time.sleep(0.8)
        print('Placing SELL market', symbol, 'qty=', qty)
        sell = c.create_order(symbol=symbol, side='SELL', type='MARKET', quantity=qty)
        log_line({
            'order_id': f'SPOT-CONFIRM-{int(time.time())}',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'status': 'CYCLE_OK',
            'intent': {'symbol': symbol, 'qty': qty},
            'response': {'buy': {'orderId': buy.get('orderId')}, 'sell': {'orderId': sell.get('orderId')}}
        })
        print('Done OK')
        return 0
    except BinanceAPIException as e:
        print('Spot order error:', e)
        log_line({
            'order_id': f'SPOT-CONFIRM-{int(time.time())}',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'status': 'ERROR',
            'error': str(e)
        })
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

