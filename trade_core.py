"""
trade_core.py — V13 Broker Abstraction

Provides a minimal broker interface used by commander_v13_manual.py:
  - place_market_order(symbol, side, qty)
  - get_positions()
  - close_position(symbol)
  - get_account()

Backends:
  - Alpaca Paper (existing): uses alpaca_trade_core
  - Binance Futures Testnet: python-binance futures endpoints

Selection:
  - Reads [ROUTING] DEFAULT_VENUE from config/V13_Config.ini
    * ALPACA (default)
    * BINANCE_FUTURES
"""

from __future__ import annotations

import json
import os
from configparser import ConfigParser
from typing import Dict, Any, List, Optional
from decimal import Decimal

# Reuse existing Alpaca implementation
import alpaca_trade_core as alpaca

try:
    from binance.client import Client as BinanceClient
    from binance.exceptions import BinanceAPIException as BinanceError
except Exception:
    BinanceClient = None
    BinanceError = Exception  # type: ignore


CFG_INI_PATH = os.path.join("config", "V13_Config.ini")
BINANCE_KEYS_PATH = os.path.join("config", "binance_keys.json")


def _load_ini_flag(section: str, key: str, default: str) -> str:
    cfg = ConfigParser()
    try:
        # read() tolerates comments/preamble; read_file() would not
        cfg.read(CFG_INI_PATH, encoding="utf-8-sig")
    except Exception:
        return default
    value = cfg.get(section, key, fallback=default)
    # Strip any inline comments like '; ...'
    if ';' in value:
        value = value.split(';', 1)[0].strip()
    return value


def _default_venue() -> str:
    return _load_ini_flag("ROUTING", "DEFAULT_VENUE", "ALPACA").upper()


def _run_env() -> str:
    return _load_ini_flag("MODE", "RUN_ENV", "PAPER").upper()


def _load_binance_client() -> Optional[BinanceClient]:
    if BinanceClient is None:
        return None
    # Load keys
    try:
        with open(BINANCE_KEYS_PATH, "r", encoding="utf-8-sig") as f:
            creds = json.load(f)
        key = creds.get("api_key") or os.getenv("BINANCE_API_KEY", "")
        sec = creds.get("api_secret") or os.getenv("BINANCE_API_SECRET", "")
    except Exception:
        key = os.getenv("BINANCE_API_KEY", "")
        sec = os.getenv("BINANCE_API_SECRET", "")
    if not key or not sec:
        return None

    c = BinanceClient(key, sec)
    # Default futures URL for test env
    if _run_env() == "PAPER":
        try:
            c.FUTURES_URL = c.FUTURES_TESTNET_URL
        except Exception:
            pass
    return c


def _load_binance_spot_client() -> Optional[BinanceClient]:
    if BinanceClient is None:
        return None
    try:
        with open(BINANCE_KEYS_PATH, "r", encoding="utf-8-sig") as f:
            creds = json.load(f)
        key = creds.get("api_key") or os.getenv("BINANCE_API_KEY", "")
        sec = creds.get("api_secret") or os.getenv("BINANCE_API_SECRET", "")
    except Exception:
        key = os.getenv("BINANCE_API_KEY", "")
        sec = os.getenv("BINANCE_API_SECRET", "")
    if not key or not sec:
        return None
    c = BinanceClient(key, sec, testnet=(_run_env()=="PAPER"))
    try:
        if _run_env()=="PAPER":
            c.API_URL = 'https://testnet.binance.vision/api'
    except Exception:
        pass
    return c


def _map_symbol_for_binance(symbol: str) -> str:
    # Naive mapping for common crypto spot symbols in Alpaca style
    mapping = {
        "BTCUSD": "BTCUSDT",
        "ETHUSD": "ETHUSDT",
    }
    return mapping.get(symbol, symbol)


# Public interface -----------------------------------------------------------
def place_market_order(symbol: str, side: str, qty: float, time_in_force: str = "gtc") -> Optional[Dict[str, Any]]:
    venue = _default_venue()
    if venue == "BINANCE_FUTURES":
        c = _load_binance_client()
        if c is None:
            print("[trade_core] Binance client not available (missing keys or package)")
            return None
        b_symbol = _map_symbol_for_binance(symbol)
        try:
            # For futures we use MARKET order
            resp = c.futures_create_order(symbol=b_symbol, side=side.upper(), type="MARKET", quantity=str(qty))
            return {
                "id": resp.get("orderId"),
                "symbol": b_symbol,
                "side": side,
                "filled_qty": resp.get("executedQty", None),
                "filled_avg_price": None,  # not readily in response; would need extra query
                "raw": resp,
            }
        except BinanceError as e:
            print(f"[trade_core] Binance order error: {e}")
            return None
    if venue == "BINANCE_SPOT":
        c = _load_binance_spot_client()
        if c is None:
            print("[trade_core] Binance SPOT client not available (missing keys or package)")
            return None
        b_symbol = _map_symbol_for_binance(symbol)
        try:
            resp = c.create_order(symbol=b_symbol, side=side.upper(), type="MARKET", quantity=str(qty))
            return {
                "id": resp.get("orderId"),
                "symbol": b_symbol,
                "side": side,
                "filled_qty": resp.get("executedQty", None),
                "filled_avg_price": None,
                "raw": resp,
            }
        except BinanceError as e:
            print(f"[trade_core] Binance SPOT order error: {e}")
            return None
    # Default to Alpaca
    return alpaca.place_market_order(symbol, side, qty, time_in_force=time_in_force)


def get_positions() -> List[Dict[str, Any]]:
    venue = _default_venue()
    if venue == "BINANCE_FUTURES":
        c = _load_binance_client()
        if c is None:
            return []
        try:
            positions = c.futures_position_information()
            result: List[Dict[str, Any]] = []
            for p in positions:
                amt = float(p.get("positionAmt", 0))
                if amt == 0:
                    continue
                sym = p.get("symbol", "")
                entry = float(p.get("entryPrice", 0))
                result.append({
                    "symbol": sym,
                    "qty": amt,
                    "avg_entry_price": entry,
                })
            return result
        except BinanceError as e:
            print(f"[trade_core] Binance positions error: {e}")
            return []
    if venue == "BINANCE_SPOT":
        c = _load_binance_spot_client()
        if c is None:
            return []
        try:
            acct = c.get_account()
            bals = acct.get('balances', [])
            result: List[Dict[str, Any]] = []
            # Map balances to pseudo-positions for whitelisted symbols
            # e.g., BTCUSDT -> asset BTC
            for bal in bals:
                free = float(bal.get('free', '0'))
                if free > 0:
                    asset = bal.get('asset')
                    result.append({
                        "symbol": asset,
                        "qty": free,
                        "avg_entry_price": 0.0,
                    })
            return result
        except BinanceError as e:
            print(f"[trade_core] Binance SPOT positions error: {e}")
            return []
    return alpaca.get_positions()


def close_position(symbol: str) -> Optional[Dict[str, Any]]:
    venue = _default_venue()
    if venue == "BINANCE_FUTURES":
        c = _load_binance_client()
        if c is None:
            return None
        b_symbol = _map_symbol_for_binance(symbol)
        try:
            # fetch position amt
            positions = c.futures_position_information(symbol=b_symbol)
            if not positions:
                return None
            amt = float(positions[0].get("positionAmt", 0))
            if amt == 0:
                return None
            side = "SELL" if amt > 0 else "BUY"
            qty = abs(amt)
            resp = c.futures_create_order(symbol=b_symbol, side=side, type="MARKET", quantity=str(qty), reduceOnly=True)
            return {
                "id": resp.get("orderId"),
                "symbol": b_symbol,
                "filled_qty": resp.get("executedQty", None),
                "filled_avg_price": None,
                "raw": resp,
            }
        except BinanceError as e:
            print(f"[trade_core] Binance close error: {e}")
            return None
    if venue == "BINANCE_SPOT":
        c = _load_binance_spot_client()
        if c is None:
            return None
        b_symbol = _map_symbol_for_binance(symbol)
        # sell base asset equal to free balance
        base = b_symbol[:-4] if b_symbol.endswith('USDT') else b_symbol[:3]
        try:
            bal = c.get_asset_balance(asset=base)
            free = float(bal.get('free', '0'))
            if free <= 0:
                return None
            resp = c.create_order(symbol=b_symbol, side="SELL", type="MARKET", quantity=str(free))
            return {
                "id": resp.get("orderId"),
                "symbol": b_symbol,
                "filled_qty": resp.get("executedQty", None),
                "filled_avg_price": None,
                "raw": resp,
            }
        except BinanceError as e:
            print(f"[trade_core] Binance SPOT close error: {e}")
            return None
    return alpaca.close_position(symbol)


def get_account() -> Optional[Dict[str, Any]]:
    venue = _default_venue()
    if venue == "BINANCE_FUTURES":
        c = _load_binance_client()
        if c is None:
            return None
        try:
            return c.futures_account()
        except BinanceError as e:
            print(f"[trade_core] Binance account error: {e}")
            return None
    if venue == "BINANCE_SPOT":
        c = _load_binance_spot_client()
        if c is None:
            return None
        try:
            return c.get_account()
        except BinanceError as e:
            print(f"[trade_core] Binance SPOT account error: {e}")
            return None
    return alpaca.get_account()


def get_account_activities(start_time: Optional[str] = None, end_time: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetch account activities (realized P&L for closed positions)."""
    venue = _default_venue()
    if venue == "BINANCE_SPOT":
        c = _load_binance_spot_client()
        if c is None:
            return []
        # Convert ISO8601 to ms since epoch if provided
        def _iso_to_ms(s: Optional[str]) -> Optional[int]:
            if not s:
                return None
            try:
                from datetime import datetime
                import datetime as _dt
                # Handle fractional seconds and timezone suffix
                dt = datetime.fromisoformat(s.replace('Z', '+00:00'))
                return int(dt.timestamp() * 1000)
            except Exception:
                return None
        start_ms = _iso_to_ms(start_time)
        end_ms = _iso_to_ms(end_time)
        # Pull trades for whitelisted symbols and approximate realized PnL
        syms = _load_ini_flag("ROUTING", "SYMBOL_WHITELIST", "BTCUSDT")
        symbols = [s.strip().upper() for s in syms.split(',') if s.strip()]
        out: List[Dict[str, Any]] = []
        for sym in symbols:
            try:
                params = {"symbol": sym}
                if start_ms:
                    params["startTime"] = start_ms
                if end_ms:
                    params["endTime"] = end_ms
                trades = c.get_my_trades(**params)
                # Approximate realized PnL as signed cash flow per trade
                for t in trades:
                    qty = float(t.get("qty") or t.get("origQty") or 0.0)
                    price = float(t.get("price") or 0.0)
                    is_buyer = bool(t.get("isBuyer"))
                    cash = price * qty
                    realized = -cash if is_buyer else cash
                    t["realizedPnl"] = realized
                    t["symbol"] = sym
                    out.append(t)
            except Exception:
                continue
        return out
    if venue == "BINANCE_FUTURES":
        c = _load_binance_client()
        if c is None:
            return []
        try:
            # Binance futures account trade list for realized P&L
            trades = c.futures_account_trades(startTime=start_time, endTime=end_time)
            return trades
        except BinanceError as e:
            print(f"[trade_core] Binance activities error: {e}")
            return []
    # Alpaca: use account activities endpoint
    import requests
    keys = alpaca.load_trade_keys()
    base = keys.get("TRADE_ENDPOINT", "https://paper-api.alpaca.markets/v2")
    url = f"{base}/account/activities"
    headers = alpaca._get_trade_headers(keys)
    params = {}
    if start_time:
        params["after"] = start_time
    if end_time:
        params["until"] = end_time
    try:
        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"[trade_core] Alpaca activities error: {e}")
        return []
