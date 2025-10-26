"""
alpaca_trade_core.py — V13 Manual Trading Framework
Build: 2025-10-18
Phase: 4 — Alpaca Trade Core (Paper Trading Integration)

Purpose
-------
Handle real order execution on Alpaca's paper trading account.
Provides functions for placing market orders, checking positions, and managing TP/SL.
"""

import requests
import json
from typing import Dict, Optional, List

CONFIG_PATH = "config/alpaca_keys.json"

def load_trade_keys() -> Dict:
    """Load API keys from local JSON file."""
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def _get_trade_headers(keys: Dict) -> Dict:
    """Return Alpaca API headers for trading."""
    return {
        "APCA-API-KEY-ID": keys["API_KEY_ID"],
        "APCA-API-SECRET-KEY": keys["API_SECRET_KEY"],
        "Content-Type": "application/json"
    }

def place_market_order(symbol: str, side: str, qty: float, time_in_force: str = "gtc") -> Optional[Dict]:
    """
    Place a market order on Alpaca paper account.
    side: 'buy' or 'sell'
    qty: quantity (e.g., 0.001 for BTC)
    Returns order dict or None on failure.
    """
    keys = load_trade_keys()
    base = keys.get("TRADE_ENDPOINT", "https://paper-api.alpaca.markets/v2")
    url = f"{base}/orders"
    headers = _get_trade_headers(keys)
    payload = {
        "symbol": symbol,
        "qty": qty,
        "side": side,
        "type": "market",
        "time_in_force": time_in_force
    }
    try:
        resp = requests.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"Order placement error: {e}")
        return None

def get_positions() -> List[Dict]:
    """Get current positions from Alpaca paper account."""
    keys = load_trade_keys()
    base = keys.get("TRADE_ENDPOINT", "https://paper-api.alpaca.markets/v2")
    url = f"{base}/positions"
    headers = _get_trade_headers(keys)
    try:
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"Positions fetch error: {e}")
        return []

def get_account() -> Optional[Dict]:
    """Get account info from Alpaca paper account."""
    keys = load_trade_keys()
    base = keys.get("TRADE_ENDPOINT", "https://paper-api.alpaca.markets/v2")
    url = f"{base}/account"
    headers = _get_trade_headers(keys)
    try:
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"Account fetch error: {e}")
        return None

def close_position(symbol: str) -> Optional[Dict]:
    """Close position for a symbol."""
    keys = load_trade_keys()
    base = keys.get("TRADE_ENDPOINT", "https://paper-api.alpaca.markets/v2")
    url = f"{base}/positions/{symbol}"
    headers = _get_trade_headers(keys)
    try:
        resp = requests.delete(url, headers=headers)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"Close position error: {e}")
        return None

def get_account_activities(after: Optional[str] = None, until: Optional[str] = None) -> List[Dict]:
    """
    Get account activities (realized P&L for closed positions).
    after: ISO 8601 timestamp (e.g., '2023-01-01T00:00:00Z')
    until: ISO 8601 timestamp
    Returns list of activity dicts.
    """
    keys = load_trade_keys()
    base = keys.get("TRADE_ENDPOINT", "https://paper-api.alpaca.markets/v2")
    url = f"{base}/account/activities"
    headers = _get_trade_headers(keys)
    params = {}
    if after:
        params["after"] = after
    if until:
        params["until"] = until
    try:
        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"Account activities fetch error: {e}")
        return []
