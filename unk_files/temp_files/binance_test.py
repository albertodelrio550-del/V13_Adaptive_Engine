from binance.client import Client
from binance.exceptions import BinanceAPIException
import os
import json

# Load keys from config/binance_keys.json
try:
    with open("config/binance_keys.json", "r", encoding="utf-8-sig") as f:
        keys = json.load(f)
    api_key = keys["api_key"]
    api_secret = keys["api_secret"]
except Exception as e:
    print(f"❌ Failed to load keys: {e}")
    exit(1)

print(f"API: {api_key[:6]}...")  # sanity check
print(f"Secret: {api_secret[:6]}...")

try:
    client = Client(api_key, api_secret, testnet=True)
    client.API_URL = 'https://testnet.binance.vision/api'
    account = client.get_account()
    print("✅ Connected successfully!")
    print(account)
except BinanceAPIException as e:
    print(f"❌ Connection failed: {e}")
