import json
import requests
import time
from typing import Dict, Optional

CONFIG_PATH = "config/alpaca_keys.json"

def load_keys(path: str = CONFIG_PATH) -> Dict:
    """Load API keys from local JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _get_headers(keys: Dict) -> Dict:
    """Return Alpaca API headers."""
    return {
        "APCA-API-KEY-ID": keys["API_KEY_ID"],
        "APCA-API-SECRET-KEY": keys["API_SECRET_KEY"]
    }

def get_snapshot(symbol: str = "BTC/USD") -> Optional[Dict]:
    """
    Fetch the latest crypto quote snapshot from Alpaca Market Data API.
    Returns dict with bid/ask/timestamp or None on failure.
    """
    keys = load_keys()
    base = keys.get("DATA_ENDPOINT", "https://data.alpaca.markets/v1beta3/crypto")
    url = f"{base}/latest/quotes?symbols={symbol}"
    headers = _get_headers(keys)
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        # Data comes as a nested dict keyed by symbol
        q = data.get("quotes", {}).get(symbol, {})
        return {
            "symbol": symbol,
            "ask": q.get("ap"),
            "bid": q.get("bp"),
            "timestamp": q.get("t")
        }
    except Exception as e:
        print("Feed error:", e)
        return None

def get_snapshot_stocks(symbol: str) -> Optional[Dict]:
    """
    Returns the current market snapshot for the given stock symbol.
    Expected return format:
    {
        "symbol": "SPY",
        "last_price": 4314.21,
        "percent_change": 0.23
    }
    """
    keys = load_keys()
    base = "https://data.alpaca.markets/v2/stocks"  # Use correct stocks endpoint
    url = f"{base}/{symbol}/snapshot"
    headers = _get_headers(keys)
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        # Extract relevant fields
        latest_trade = data.get("latestTrade", {})
        prev_close = data.get("prevDailyBar", {}).get("c", 0)
        last_price = latest_trade.get("p", 0)
        percent_change = ((last_price - prev_close) / prev_close * 100) if prev_close else 0
        return {
            "symbol": symbol,
            "last_price": last_price,
            "percent_change": percent_change
        }
    except Exception as e:
        print("Stock feed error:", e)
        return None


if __name__ == "__main__":
    while True:
        quote = get_snapshot("BTC/USD")
        print(quote)
        time.sleep(3)
