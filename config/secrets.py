"""
config/secrets.py — V13 Manual Trading Framework
Build: 2025-10-18
Phase: 5.1 — Secure key loader
"""

import os, json

CONFIG_PATH = os.path.join("config", "alpaca_keys.json")

def load_alpaca_keys() -> dict:
    """
    Loads Alpaca credentials.
    1️⃣ Try environment variables.
    2️⃣ Fall back to config/alpaca_keys.json.
    """
    key = os.getenv("ALPACA_KEY_ID")
    secret = os.getenv("ALPACA_SECRET_KEY")
    data_ep = os.getenv("ALPACA_DATA_ENDPOINT")
    trade_ep = os.getenv("ALPACA_TRADE_ENDPOINT")

    # Prefer environment variables
    if key and secret:
        return {
            "API_KEY_ID": key,
            "API_SECRET_KEY": secret,
            "DATA_ENDPOINT": data_ep or "https://data.alpaca.markets/v1beta3/crypto/us",
            "TRADE_ENDPOINT": trade_ep or "https://paper-api.alpaca.markets/v2",
        }

    # Fallback to local file
    try:
        with open(CONFIG_PATH, "r") as f:
            creds = json.load(f)
            return creds
    except Exception as e:
        print(f"[Secrets] Error loading credentials → {e}")
        return {
            "API_KEY_ID": "",
            "API_SECRET_KEY": "",
            "DATA_ENDPOINT": "https://data.alpaca.markets/v1beta3/crypto/us",
            "TRADE_ENDPOINT": "https://paper-api.alpaca.markets/v2",
        }

if __name__ == "__main__":
    print(json.dumps(load_alpaca_keys(), indent=2))
